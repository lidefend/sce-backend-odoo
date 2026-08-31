<template>
  <ProfessionalRelationFieldControl :field="field">
    <div :class="['many2one-widget-shell', { 'many2one-widget-shell--avatar': isAvatarMany2oneWidget }]">
      <span v-if="isAvatarMany2oneWidget" class="many2one-avatar" aria-hidden="true">
        {{ avatarText(many2oneTextValue) }}
      </span>
      <div class="many2one-combobox">
        <ScRelationField
          :id="controlId"
          class="input"
          appearance="form-field"
          :required="field.required"
          :invalid="field.invalid"
          :described-by="describedBy"
          :model-value="many2oneTextValue"
          :placeholder="placeholder"
          role="combobox"
          aria-autocomplete="list"
          :aria-expanded="isOpen"
          :aria-controls="listboxId"
          :aria-activedescendant="activeDescendant"
          @update:model-value="emitQuery"
          @focus="focusField"
          @change="emitCommit(($event.target as HTMLInputElement).value)"
          @keydown="handleKeydown"
          @blur="blurField"
        />
        <div v-if="isOpen" :id="listboxId" class="many2one-option-panel" role="listbox">
          <div v-if="visibleOptions.length" class="many2one-option-list" role="presentation">
            <div
              v-for="(option, optionIndex) in visibleOptions"
              :id="optionId(optionIndex)"
              :key="`${field.name}-option-${option.value}`"
              class="many2one-option-row"
              :data-active="activeIndex === optionIndex || undefined"
              role="option"
              :aria-selected="activeIndex === optionIndex"
            >
              <ScButton
                type="button"
                appearance="menu-item"
                size="small"
                variant="ghost"
                @mousedown.prevent
                @click="emitSelect(option.value, $event)"
              >
                {{ option.label }}
              </ScButton>
            </div>
          </div>
          <div class="many2one-actions">
            <ScButton
              v-if="field.many2oneOpenToken"
              type="button"
              class="many2one-action many2one-action--record"
              appearance="menu-item"
              size="small"
              variant="ghost"
              @mousedown.prevent
              @click="emitSelect(field.many2oneOpenToken || '', $event)"
            >
              {{ field.many2oneOpenLabel || '维护当前项' }}
            </ScButton>
            <ScButton
              v-if="field.many2oneSearchToken"
              type="button"
              class="many2one-action"
              appearance="menu-item"
              size="small"
              variant="ghost"
              @mousedown.prevent
              @click="emitSelect(field.many2oneSearchToken || '', $event)"
            >
              {{ field.many2oneSearchLabel }}
            </ScButton>
            <ScButton
              v-if="['page', 'dialog'].includes(field.relationCreateMode || '') && field.many2oneCreateToken"
              type="button"
              class="many2one-action"
              appearance="menu-item"
              size="small"
              variant="ghost"
              @mousedown.prevent
              @click="emitSelect(field.many2oneCreateToken || '', $event)"
            >
              {{ field.many2oneCreateLabel }}
            </ScButton>
            <ScButton
              v-if="showInlineCreate"
              type="button"
              class="many2one-action"
              appearance="menu-item"
              size="small"
              variant="ghost"
              @mousedown.prevent
              @click="emitInlineCreate($event)"
            >
              {{ field.many2oneInlineCreateLabel }}
            </ScButton>
          </div>
        </div>
      </div>
    </div>
  </ProfessionalRelationFieldControl>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import ScButton from '../design-system/ScButton.vue';
import ScRelationField from '../design-system/ScRelationField.vue';
import type { FormSectionFieldSchema } from '../template/formSection.types';
import ProfessionalRelationFieldControl from './ProfessionalRelationFieldControl.vue';

const props = defineProps<{
  field: FormSectionFieldSchema;
  controlId: string;
  describedBy?: string;
  placeholder: string;
}>();

const emit = defineEmits<{
  select: [value: string | number | boolean | null];
  query: [value: string];
  commit: [value: string];
}>();

const focused = ref(false);
const activeIndex = ref(-1);

const normalizedWidget = computed(() => String(props.field.widget || '').trim().toLowerCase());
const visibleOptions = computed(() => (props.field.relationOptions || []).filter(Boolean).slice(0, 8));
const many2oneTextValue = computed(() => {
  const value = String(props.field.inputValue ?? '').trim();
  if (!value) return '';
  const option = (props.field.relationOptions || []).filter(Boolean).find((item) => String(item.id ?? item.value) === value);
  return String(option?.label || '').trim();
});
const showInlineCreate = computed(() => {
  const text = many2oneTextValue.value;
  if (!text || !props.field.relationInlineCreate?.enabled || !props.field.relationInlineCreate.createOnNoMatch) return false;
  const normalized = text.trim().toLowerCase();
  return !visibleOptions.value.some((item) => String(item.label || '').trim().toLowerCase() === normalized);
});
const hasDropdown = computed(() => Boolean(
  visibleOptions.value.length
  || props.field.many2oneOpenToken
  || props.field.many2oneSearchToken
  || (['page', 'dialog'].includes(props.field.relationCreateMode || '') && props.field.many2oneCreateToken)
  || showInlineCreate.value
));
const isOpen = computed(() => focused.value && hasDropdown.value);
const listboxId = computed(() => `${String(props.controlId || '').replace(/[^A-Za-z0-9_-]/g, '-')}-many2one-options`);
const activeDescendant = computed(() => activeIndex.value >= 0 ? optionId(activeIndex.value) : undefined);
const isAvatarMany2oneWidget = computed(() => ['many2one_avatar_user', 'many2one_avatar_employee'].includes(normalizedWidget.value));

function optionId(index: number): string {
  return `${listboxId.value}-${index}`;
}

function avatarText(label: string): string {
  const text = String(label || '').trim();
  return text ? text.slice(0, 1).toUpperCase() : '';
}

function collapseDropdown(event: Event) {
  const target = event.currentTarget;
  const targetElement = target as unknown as { closest?: (selector: string) => { querySelector?: (selector: string) => HTMLInputElement | null } | null };
  const closest = target && typeof targetElement.closest === 'function'
    ? targetElement.closest.bind(target)
    : null;
  const input = closest?.('.many2one-combobox')?.querySelector?.('input') || null;
  window.setTimeout(() => input?.blur(), 0);
}

function emitSelect(value: string | number | boolean | null, event: Event) {
  focused.value = false;
  activeIndex.value = -1;
  emit('select', value);
  collapseDropdown(event);
}

function emitQuery(value: string) {
  activeIndex.value = -1;
  emit('query', value);
}

function emitCommit(value: string) {
  emit('commit', value);
}

function focusField() {
  focused.value = true;
  activeIndex.value = -1;
  if (!visibleOptions.value.length) emitQuery(many2oneTextValue.value);
}

function blurField(event: FocusEvent) {
  if (!focused.value) return;
  const targetValue = event.target instanceof HTMLInputElement ? event.target.value : '';
  emitCommit(targetValue);
  window.setTimeout(() => {
    focused.value = false;
  }, 0);
}

function handleKeydown(event: KeyboardEvent) {
  if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && visibleOptions.value.length) {
    event.preventDefault();
    const delta = event.key === 'ArrowDown' ? 1 : -1;
    activeIndex.value = (activeIndex.value + delta + visibleOptions.value.length) % visibleOptions.value.length;
    return;
  }
  if (event.key === 'Enter') {
    event.preventDefault();
    const option = activeIndex.value >= 0 ? visibleOptions.value[activeIndex.value] : undefined;
    const inputEl = event.target instanceof HTMLInputElement ? event.target : null;
    if (option) emit('select', option.value);
    else emitCommit(inputEl ? inputEl.value : '');
    focused.value = false;
    activeIndex.value = -1;
    inputEl?.blur();
    return;
  }
  if (event.key === 'Escape') {
    event.preventDefault();
    focused.value = false;
    activeIndex.value = -1;
  }
}

function emitInlineCreate(event: Event) {
  emitCommit(many2oneTextValue.value);
  collapseDropdown(event);
}
</script>

<style scoped>
.many2one-widget-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 8px;
  min-width: 0;
}

.many2one-widget-shell--avatar {
  grid-template-columns: auto minmax(0, 1fr);
  align-items: start;
}

.many2one-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  background: var(--sc-app-info-bg);
  color: var(--sc-app-text-primary);
  font-size: 13px;
  font-weight: 600;
}

.many2one-combobox {
  position: relative;
  min-width: 0;
}

.many2one-option-panel {
  position: absolute;
  z-index: var(--sc-component-relation-dropdown-z-index, 40);
  inset-inline: 0;
  margin-top: 6px;
  display: grid;
  gap: 6px;
  padding: 8px;
  border: 1px solid var(--sc-app-border);
  border-radius: 10px;
  background: var(--sc-app-surface-elevated);
  box-shadow: var(--sc-component-relation-dropdown-shadow, var(--sc-app-shadow-popover));
}

.many2one-option-list,
.many2one-actions {
  display: grid;
  gap: 4px;
}

.many2one-option-row[data-active='true'] {
  background: var(--sc-app-hover-bg);
  border-radius: 10px;
}
</style>
