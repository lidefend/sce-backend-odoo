<template>
  <ProfessionalRelationFieldControl
    :field="field"
    data-semantic-component="ProfessionalMany2oneFieldControl"
  >
    <div :class="['many2one-widget-shell', { 'many2one-widget-shell--avatar': isAvatarMany2oneWidget }]">
      <span v-if="isAvatarMany2oneWidget" class="many2one-avatar" aria-hidden="true">
        {{ avatarText(displayName) }}
      </span>
      <div class="many2one-combobox">
        <ScRelationField
          :id="controlId"
          ref="relationFieldRef"
          class="input"
          appearance="form-field"
          panel-class="many2one-option-panel"
          :panel-id="panelId"
          :required="field.required"
          :invalid="field.invalid"
          :described-by="describedBy"
          :model-value="relationValue"
          :query-value="queryKeyword"
          :options="primitiveOptions"
          :clearable="canClear"
          :placeholder="placeholder"
          @update:model-value="onValueChange"
          @update:query-value="onQueryValueChange"
        >
          <template #panel-actions>
            <ScButton
              v-if="field.many2oneOpenToken"
              type="button"
              class="many2one-action many2one-action--record"
              appearance="menu-item"
              size="small"
              variant="ghost"
              @mousedown.prevent
              @click="runLifecycleAction(field.many2oneOpenToken)"
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
              @click="runLifecycleAction(field.many2oneSearchToken)"
            >
              {{ field.many2oneSearchLabel }}
            </ScButton>
            <ScButton
              v-if="createEntryVisible"
              type="button"
              class="many2one-action"
              appearance="menu-item"
              size="small"
              variant="ghost"
              @mousedown.prevent
              @click="runLifecycleAction(field.many2oneCreateToken || '')"
            >
              {{ field.many2oneCreateLabel }}
            </ScButton>
            <ScButton
              v-if="canClear"
              type="button"
              class="many2one-action many2one-action--clear"
              appearance="menu-item"
              size="small"
              variant="ghost"
              @mousedown.prevent
              @click="clearSelection"
            >
              {{ clearSelectionLabel }}
            </ScButton>
            <ScButton
              v-if="showInlineCreate"
              type="button"
              class="many2one-action many2one-inline-create"
              appearance="menu-item"
              size="small"
              variant="ghost"
              @mousedown.prevent
              @click="stageInlineCreate"
            >
              {{ field.many2oneInlineCreateLabel }}
            </ScButton>
          </template>
        </ScRelationField>
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
import {
  resolveProfessionalMany2oneDisplayValue,
  resolveProfessionalMany2oneQueryKeyword,
  resolveProfessionalMany2oneRecordValue,
} from './professionalRelationFieldModel';

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

// This control owns no candidate list, no keyboard navigation, no popup state
// and no search keyword of its own: the official Select drives all of that and
// the relation runtime owns the keyword and the selected value.
const relationFieldRef = ref<{ close: () => void; focus: () => void } | null>(null);

const normalizedWidget = computed(() => String(props.field.widget || '').trim().toLowerCase());
const relationValue = computed(() => resolveProfessionalMany2oneRecordValue(props.field));
const queryKeyword = computed(() => resolveProfessionalMany2oneQueryKeyword(props.field));
const displayName = computed(() => resolveProfessionalMany2oneDisplayValue(props.field));
const panelId = computed(() => `${String(props.controlId || '').replace(/[^A-Za-z0-9_-]/g, '-')}-many2one-options`);
const isAvatarMany2oneWidget = computed(() => ['many2one_avatar_user', 'many2one_avatar_employee'].includes(normalizedWidget.value));
const clearSelectionLabel = computed(() => '清除选择');
const canClear = computed(() => Boolean(relationValue.value));
const createEntryVisible = computed(() => (
  ['page', 'dialog'].includes(String(props.field.relationCreateMode || ''))
  && Boolean(props.field.many2oneCreateToken)
));
// The selected record keeps one option row even when the running query filtered
// it out, so the official Select can always resolve a label for the value.
const primitiveOptions = computed(() => {
  const rows = (props.field.relationOptions || [])
    .filter(Boolean)
    .slice(0, 8)
    .map((option) => ({ value: String(option.value), label: String(option.label || '') }));
  const value = relationValue.value;
  if (value && !rows.some((option) => option.value === value)) {
    rows.unshift({ value, label: displayName.value || `#${value}` });
  }
  return rows;
});
const showInlineCreate = computed(() => {
  const text = queryKeyword.value;
  if (!text || !props.field.relationInlineCreate?.enabled || !props.field.relationInlineCreate.createOnNoMatch) return false;
  const normalized = text.toLowerCase();
  return !primitiveOptions.value.some((option) => option.label.trim().toLowerCase() === normalized);
});

function avatarText(label: string): string {
  const text = String(label || '').trim();
  return text ? text.slice(0, 1).toUpperCase() : '';
}

function onValueChange(value: string) {
  emit('select', value);
}

// The official Select emits the query-keyword channel on every input change;
// the relation runtime owns the keyword and debounces the actual request, so
// the primitive's debounced `query` event is intentionally not duplicated here.
function onQueryValueChange(value: string) {
  emit('query', String(value || ''));
}

function runLifecycleAction(token: string) {
  // Business dialog hand-off only: close the official panel before the page or
  // dialog that owns the action takes focus.
  relationFieldRef.value?.close();
  emit('select', token);
}

function clearSelection() {
  relationFieldRef.value?.close();
  emit('select', '');
}

function stageInlineCreate() {
  const text = queryKeyword.value.trim();
  if (!text) return;
  relationFieldRef.value?.close();
  emit('commit', text);
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
.many2one-combobox :deep(.t-select__wrap) {
  width: 100%;
}
</style>
