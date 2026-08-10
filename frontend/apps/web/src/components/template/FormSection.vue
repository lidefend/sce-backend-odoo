<template>
  <section :class="['template-form-section', toneClass, { 'template-form-section--readonly': allFieldsReadonly }]" data-component="FormSection">
    <div v-if="showHead" class="template-form-section-head">
      <h3 v-if="title" class="template-form-section-title">{{ title }}</h3>
      <slot name="action" />
    </div>
    <p v-if="hint" class="template-form-section-hint">{{ hint }}</p>
    <div :class="['template-form-section-grid', `template-form-section-grid--columns-${columns}`]">
      <template v-if="fields.length">
        <div
          v-for="field in fields"
          :key="field.key"
          :class="fieldClass(field)"
          :data-field-name="field.name"
          :data-field-key="field.key"
          :data-field-type="field.type"
          :data-field-state="fieldState(field)"
          :tabindex="fieldSelectionMode ? 0 : undefined"
          :role="fieldSelectionMode ? 'button' : undefined"
          :aria-pressed="fieldSelectionMode ? selectedFieldKey === fieldIdentity(field) : undefined"
          :draggable="fieldOrderEditable"
          @click.capture="emitFieldSelect(field, $event)"
          @keydown.enter="emitFieldSelect(field, $event)"
          @keydown.space="emitFieldSelect(field, $event)"
          @dragstart.stop="emitFieldOrderDragStart(field, $event)"
          @dragend.stop="emitFieldOrderDragEnd(field)"
          @dragover.prevent="emitFieldOrderDragOver(field, $event)"
          @dragleave="emitFieldOrderDragLeave(field)"
          @drop.prevent="emitFieldOrderDrop(field, $event)"
          @mouseup="emitFieldOrderPointerDrop(field, $event)"
        >
          <div class="field-label-row">
            <label v-if="!fieldConfigEditable" class="label" :for="fieldControlId(field)">
              {{ field.label }}
              <span v-if="field.required && !field.readonly" class="field-state field-state--required"><span aria-hidden="true">*</span><span class="sr-only">必填</span></span>
              <span v-else-if="field.readonly && !allFieldsReadonly" class="field-state">只读</span>
            </label>
            <input
              v-else
              class="field-label-editor"
              type="text"
              :value="field.label"
              :aria-label="`${field.label}显示名称`"
              @change="emitFieldLabelChange(field, ($event.target as HTMLInputElement).value)"
              @keydown.enter.prevent="emitFieldLabelChange(field, ($event.target as HTMLInputElement).value)"
            />
            <div v-if="fieldActionsFor(field).length" class="field-inline-config">
              <div
                v-if="fieldActionsFor(field).length"
                class="field-inline-actions"
                role="radiogroup"
                :aria-label="`${field.label}字段操作`"
              >
                <label
                  v-for="action in fieldActionsFor(field)"
                  :key="`${field.key}-${action.key}`"
                  class="field-inline-action"
                  :title="action.title"
                >
                  <input
                    type="radio"
                    :name="fieldActionGroupName(field)"
                    :value="action.value"
                    :checked="Boolean(action.checked)"
                    :disabled="Boolean(action.disabled)"
                    @change="emitFieldAction(field, action)"
                  />
                  <span>{{ action.label }}</span>
                </label>
              </div>
            </div>
          </div>
          <div :class="['field-control-row', { 'field-control-row--favorite': field.favoriteToggle }]">
            <button
              v-if="field.favoriteToggle"
              type="button"
              class="field-favorite-toggle"
              :class="{ 'field-favorite-toggle--active': field.favoriteToggle.active }"
              :aria-label="field.favoriteToggle.label"
              :aria-pressed="field.favoriteToggle.active"
              :title="field.favoriteToggle.label"
              :disabled="field.favoriteToggle.readonly"
              @click="emitFavoriteToggle(field)"
            >
              <ScIcon :name="field.favoriteToggle.active ? 'star' : 'star-outline'" :size="16" />
            </button>
            <div class="field-control-main">
              <div
                v-if="field.type === 'selection' && isRadioWidget(field)"
                class="native-radio-group"
                role="radiogroup"
                :aria-label="field.label"
                :aria-required="field.required || undefined"
                :aria-invalid="field.invalid || undefined"
                :aria-describedby="fieldDescribedBy(field)"
              >
                <label
                  v-for="option in field.selectionOptions || []"
                  :key="`${field.name}-radio-${option.value}`"
                  class="native-radio-option"
                >
                  <input
                    class="native-radio-input"
                    type="radio"
                    :name="fieldRadioGroupName(field)"
                    :value="option.value"
                    :checked="String(field.inputValue ?? '') === String(option.value)"
                    :disabled="field.readonly"
                    @change="!field.readonly && emitFieldChange(field, option.value)"
                  />
                  <span>{{ option.label }}</span>
                </label>
              </div>
              <template v-else-if="field.readonly">
                <slot name="readonly" :field="field">
                  <div
                    v-if="field.type === 'html'"
                    class="readonly-value readonly-value--html"
                    v-html="readonlyHtml(field)"
                  />
                  <span v-else class="readonly-value">{{ readonlyText(field) }}</span>
                </slot>
              </template>
              <template v-else-if="isRelationEditorField(field) && relationAdapter">
                <X2ManyRelationRenderer :field="field" :adapter="relationAdapter" />
              </template>
              <template v-else-if="isBaseFieldType(field.type)">
                <input
                  v-if="field.type === 'boolean'"
                  :id="fieldControlId(field)"
                  :checked="Boolean(field.value)"
                  class="input-checkbox"
                  :aria-required="field.required || undefined"
                  :aria-invalid="field.invalid || undefined"
                  :aria-describedby="fieldDescribedBy(field)"
                  type="checkbox"
                  @change="emitFieldChange(field, ($event.target as HTMLInputElement).checked)"
                />
                <ScFileField
                  v-else-if="field.type === 'binary'"
                  :id="fieldControlId(field)"
                  :required="field.required"
                  :invalid="field.invalid"
                  :described-by="fieldDescribedBy(field)"
                  @change="emitBinaryFieldChange(field, $event)"
                />
                <ScSelect
                  v-else-if="field.type === 'selection'"
                  :id="fieldControlId(field)"
                  :model-value="String(field.inputValue ?? '')"
                  class="input"
                  :required="field.required"
                  :invalid="field.invalid"
                  :described-by="fieldDescribedBy(field)"
                  @update:model-value="emitFieldChange(field, $event)"
                >
                  <option v-if="!field.required" value="">{{ selectPlaceholderText(field) }}</option>
                  <option v-for="option in field.selectionOptions || []" :key="`${field.name}-${option.value}`" :value="option.value">
                    {{ option.label }}
                  </option>
                </ScSelect>
                <div v-else-if="field.type === 'many2one'" :class="['many2one-widget-shell', { 'many2one-widget-shell--avatar': isAvatarMany2oneWidget(field) }]">
                  <span v-if="isAvatarMany2oneWidget(field)" class="many2one-avatar" aria-hidden="true">
                    {{ avatarText(many2oneTextValue(field)) }}
                  </span>
                  <div :class="['many2one-combobox', { 'is-open': many2oneFocusedField === field.name }]">
                    <ScRelationField
                      :id="fieldControlId(field)"
                      class="input"
                      :required="field.required"
                      :invalid="field.invalid"
                      :described-by="fieldDescribedBy(field)"
                      :model-value="many2oneTextValue(field)"
                      :placeholder="selectPlaceholderText(field)"
                      role="combobox"
                      aria-autocomplete="list"
                      :aria-expanded="many2oneFocusedField === field.name && hasMany2oneDropdown(field)"
                      :aria-controls="many2oneListboxId(field)"
                      :aria-activedescendant="many2oneActiveDescendant(field)"
                      @update:model-value="emitMany2oneQuery(field, $event)"
                      @focus="focusMany2one(field)"
                      @change="emitMany2oneCommit(field, ($event.target as HTMLInputElement).value)"
                      @keydown="handleMany2oneKeydown(field, $event)"
                      @blur="blurMany2one(field, $event)"
                    />
                    <div v-if="hasMany2oneDropdown(field)" :id="many2oneListboxId(field)" class="many2one-option-panel" role="listbox">
                      <div v-if="field.relationOptions?.length" class="many2one-option-list" role="presentation">
                        <button
                          v-for="(option, optionIndex) in field.relationOptions.slice(0, 8)"
                          :id="many2oneOptionId(field, optionIndex)"
                          :key="`${field.name}-option-${option.value}`"
                          type="button"
                          class="many2one-option"
                          :class="{ 'is-active': many2oneActiveIndex[field.name] === optionIndex }"
                          role="option"
                          :aria-selected="many2oneActiveIndex[field.name] === optionIndex"
                          @mousedown.prevent
                          @click="emitMany2oneAction(field, option.value, $event)"
                        >
                          {{ option.label }}
                        </button>
                      </div>
                      <div class="many2one-actions">
                        <button
                          v-if="field.many2oneOpenToken"
                          type="button"
                          class="many2one-action many2one-action--record"
                          @mousedown.prevent
                          @click="emitMany2oneAction(field, field.many2oneOpenToken || '', $event)"
                        >
                          {{ field.many2oneOpenLabel || '维护当前项' }}
                        </button>
                        <button
                          v-if="field.many2oneSearchToken"
                          type="button"
                          class="many2one-action"
                          @mousedown.prevent
                          @click="emitMany2oneAction(field, field.many2oneSearchToken || '', $event)"
                        >
                          {{ field.many2oneSearchLabel }}
                        </button>
                        <button
                          v-if="field.relationCreateMode === 'page' && field.many2oneCreateToken"
                          type="button"
                          class="many2one-action"
                          @mousedown.prevent
                          @click="emitMany2oneAction(field, field.many2oneCreateToken || '', $event)"
                        >
                          {{ field.many2oneCreateLabel }}
                        </button>
                        <button
                          v-if="showMany2oneInlineCreate(field)"
                          type="button"
                          class="many2one-action"
                          @mousedown.prevent
                          @click="emitMany2oneInlineCreate(field, $event)"
                        >
                          {{ field.many2oneInlineCreateLabel }}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-else-if="isDateRangeWidget(field)" class="native-date-range">
                  <ScDateField
                    :id="fieldControlId(field)"
                    :model-value="String(field.inputValue ?? '')"
                    class="input"
                    :aria-label="field.label"
                    :required="field.required"
                    :invalid="field.invalid"
                    :described-by="fieldDescribedBy(field)"
                    :placeholder="field.inputPlaceholder || inputPlaceholderText(field)"
                    @update:model-value="emitFieldChange(field, $event)"
                  />
                  <ScIcon v-if="field.dateRangeEndField" class="native-date-range-separator" name="arrow-right" :size="16" />
                  <ScDateField
                    v-if="field.dateRangeEndField"
                    :model-value="String(field.dateRangeEndInputValue ?? '')"
                    class="input"
                    :aria-label="`${field.label}结束日期`"
                    :placeholder="field.inputPlaceholder || inputPlaceholderText(field)"
                    @update:model-value="emitDateRangeEndChange(field, $event)"
                  />
                </div>
                <ScDateField
                  v-else-if="field.type === 'date' || field.type === 'datetime'"
                  :id="fieldControlId(field)"
                  :model-value="String(field.inputValue ?? '')"
                  class="input"
                  :with-time="field.type === 'datetime'"
                  :required="field.required"
                  :invalid="field.invalid"
                  :described-by="fieldDescribedBy(field)"
                  :placeholder="field.inputPlaceholder || inputPlaceholderText(field)"
                  @update:model-value="emitFieldChange(field, $event)"
                />
                <textarea
                  v-else-if="isMultilineField(field.type)"
                  :id="fieldControlId(field)"
                  :value="String(field.inputValue ?? '')"
                  class="input input--textarea"
                  :aria-required="field.required || undefined"
                  :aria-invalid="field.invalid || undefined"
                  :aria-describedby="fieldDescribedBy(field)"
                  :placeholder="field.inputPlaceholder || inputPlaceholderText(field)"
                  rows="4"
                  @input="emitFieldChange(field, ($event.target as HTMLTextAreaElement).value)"
                />
                <input
                  v-else
                  :id="fieldControlId(field)"
                  :value="String(field.inputValue ?? '')"
                  class="input"
                  :aria-required="field.required || undefined"
                  :aria-invalid="field.invalid || undefined"
                  :aria-describedby="fieldDescribedBy(field)"
                  :type="inputType(field.type)"
                  :placeholder="field.inputPlaceholder || inputPlaceholderText(field)"
                  @input="emitFieldChange(field, ($event.target as HTMLInputElement).value)"
                />
              </template>
              <template v-else>
                <input
                  :id="fieldControlId(field)"
                  :value="String(field.inputValue ?? '')"
                  class="input"
                  :aria-required="field.required || undefined"
                  :aria-invalid="field.invalid || undefined"
                  :aria-describedby="fieldDescribedBy(field)"
                  :type="inputType(field.type)"
                  :placeholder="field.inputPlaceholder || inputPlaceholderText(field)"
                  @input="emitFieldChange(field, ($event.target as HTMLInputElement).value)"
                />
              </template>
            </div>
          </div>
          <p v-if="field.helpText" :id="fieldHelpId(field)" class="field-supporting-text">{{ field.helpText }}</p>
          <p v-if="field.errorText" :id="fieldErrorId(field)" class="field-error-text" role="alert">{{ field.errorText }}</p>
        </div>
      </template>
      <slot v-else />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, useId, useSlots } from 'vue';
import ScDateField from '../design-system/ScDateField.vue';
import ScFileField from '../design-system/ScFileField.vue';
import ScIcon from '../design-system/ScIcon.vue';
import ScRelationField from '../design-system/ScRelationField.vue';
import ScSelect from '../design-system/ScSelect.vue';
import X2ManyRelationRenderer from './X2ManyRelationRenderer.vue';
import { formatDisplayValue } from '../../utils/display';
import { sanitizeReadonlyHtml } from '../../utils/sanitizeReadonlyHtml';
import type {
  FormSectionFieldAction,
  FormSectionFieldActionPayload,
  FormSectionFieldSchema,
  FormSectionFieldChange,
  TemplateFieldType,
} from './formSection.types';
import type { RelationFieldAdapter } from './relationField.types';
import { resolveInputPlaceholder, resolveSelectPlaceholder } from './placeholder.mapper';

const props = withDefaults(defineProps<{
  title: string;
  hint?: string;
  columns?: 1 | 2 | 3;
  tone?: 'core' | 'advanced';
  fields?: FormSectionFieldSchema[];
  relationAdapter?: RelationFieldAdapter;
  fieldActions?: (field: FormSectionFieldSchema) => FormSectionFieldAction[];
  fieldOrderEditable?: boolean;
  fieldOrderIndex?: (field: FormSectionFieldSchema) => number;
  fieldOrderCount?: number;
  fieldOrderDraggingKey?: string;
  fieldOrderDropTargetKey?: string;
  fieldOrderDropPlacement?: 'before' | 'after' | '';
  fieldConfigEditable?: boolean;
  fieldGroupTitle?: string;
  fieldSelectionMode?: boolean;
  selectedFieldKey?: string;
  selectPlaceholder?: (label: string) => string;
  inputPlaceholder?: (label: string) => string;
}>(), {
  hint: '',
  columns: 2,
  tone: 'core',
  fields: () => [],
  relationAdapter: undefined,
  fieldActions: undefined,
  fieldOrderEditable: false,
  fieldOrderIndex: undefined,
  fieldOrderCount: 0,
  fieldOrderDraggingKey: '',
  fieldOrderDropTargetKey: '',
  fieldOrderDropPlacement: '',
  fieldConfigEditable: false,
  fieldGroupTitle: '',
  fieldSelectionMode: false,
  selectedFieldKey: '',
  selectPlaceholder: (label: string) => resolveSelectPlaceholder(label),
  inputPlaceholder: (label: string) => resolveInputPlaceholder(label),
});

const many2oneFocusedField = ref('');
const many2oneActiveIndex = ref<Record<string, number>>({});
const formSectionDomId = `form-section-${useId().replace(/[^A-Za-z0-9_-]/g, '-')}`;

const emit = defineEmits<{
  (e: 'field-change', payload: FormSectionFieldChange): void;
  (e: 'field-action', payload: FormSectionFieldActionPayload): void;
  (e: 'field-order-move', payload: { field: FormSectionFieldSchema; delta: number }): void;
  (e: 'field-order-drag-start', payload: { field: FormSectionFieldSchema; event: DragEvent }): void;
  (e: 'field-order-drag-over', payload: { field: FormSectionFieldSchema; groupTitle: string; placement: 'before' | 'after' | '' }): void;
  (e: 'field-order-drag-leave', payload: { field: FormSectionFieldSchema; groupTitle: string }): void;
  (e: 'field-order-drop', payload: { field: FormSectionFieldSchema; groupTitle: string; placement: 'before' | 'after' | '' }): void;
  (e: 'field-order-drag-end', payload: { field: FormSectionFieldSchema }): void;
  (e: 'field-label-change', payload: { field: FormSectionFieldSchema; label: string }): void;
  (e: 'field-add-after', payload: { field: FormSectionFieldSchema; groupTitle: string }): void;
  (e: 'field-select', payload: { field: FormSectionFieldSchema; groupTitle: string }): void;
}>();

function fieldControlId(field: FormSectionFieldSchema) {
  return `${formSectionDomId}-field-${String(field.key || field.name).replace(/[^A-Za-z0-9_-]/g, '-')}`;
}

function fieldActionGroupName(field: FormSectionFieldSchema) {
  return `${fieldControlId(field)}-action`;
}

function fieldRadioGroupName(field: FormSectionFieldSchema) {
  return `${fieldControlId(field)}-radio`;
}

function fieldHelpId(field: FormSectionFieldSchema) {
  return `${fieldControlId(field)}-help`;
}

function fieldErrorId(field: FormSectionFieldSchema) {
  return `${fieldControlId(field)}-error`;
}

function fieldDescribedBy(field: FormSectionFieldSchema) {
  const ids = [];
  if (field.helpText) ids.push(fieldHelpId(field));
  if (field.errorText) ids.push(fieldErrorId(field));
  return ids.length ? ids.join(' ') : undefined;
}

const slots = useSlots();
const toneClass = computed(() => (props.tone === 'advanced' ? 'template-form-section--advanced' : 'template-form-section--core'));
const showHead = computed(() => Boolean(props.title || slots.action));
const allFieldsReadonly = computed(() => props.fields.length > 0 && props.fields.every((field) => field.readonly));
function isBaseFieldType(type: TemplateFieldType) {
  return [
    'char',
    'text',
    'html',
    'selection',
    'many2one',
    'boolean',
    'binary',
    'date',
    'datetime',
    'integer',
    'float',
    'monetary',
  ].includes(String(type || '').trim().toLowerCase());
}

function isRelationEditorField(field: FormSectionFieldSchema) {
  return ['many2many', 'one2many'].includes(String(field.type || '').trim().toLowerCase());
}

function defaultSpanClass(type: TemplateFieldType) {
  return isMultilineField(type) || isRelationEditorType(type) ? 'field--full' : 'field--normal';
}

function isMultilineField(type: TemplateFieldType) {
  return ['text', 'html'].includes(String(type || '').trim().toLowerCase());
}

function isRelationEditorType(type: TemplateFieldType) {
  return ['many2many', 'one2many'].includes(String(type || '').trim().toLowerCase());
}

function inputType(type: TemplateFieldType) {
  const t = String(type || '').trim().toLowerCase();
  if (t === 'date') return 'date';
  if (t === 'datetime') return 'datetime-local';
  if (['integer', 'float', 'monetary'].includes(t)) return 'number';
  return 'text';
}

function fieldWidget(field: FormSectionFieldSchema) {
  return String(field.widget || '').trim().toLowerCase();
}

function fieldWidgetClass(field: FormSectionFieldSchema) {
  const widget = fieldWidget(field);
  return widget ? `field--widget-${widget.replace(/[^a-z0-9_-]/g, '-')}` : '';
}

function fieldIdentity(field: FormSectionFieldSchema) {
  return String(field.name || field.key || '').trim();
}

function fieldSpanClass(field: FormSectionFieldSchema) {
  return field.spanClass || defaultSpanClass(field.type);
}

function fieldClass(field: FormSectionFieldSchema) {
  const fieldKey = fieldIdentity(field);
  const isDropTarget = props.fieldOrderDropTargetKey === fieldKey && props.fieldOrderDraggingKey !== fieldKey;
  return [
    'field',
    fieldSpanClass(field),
    fieldWidgetClass(field),
    {
      'field--order-editable': props.fieldOrderEditable,
      'field--order-dragging': props.fieldOrderDraggingKey === fieldKey,
      'field--order-drop-target': isDropTarget,
      'field--order-drop-before': isDropTarget && props.fieldOrderDropPlacement !== 'after',
      'field--order-drop-after': isDropTarget && props.fieldOrderDropPlacement === 'after',
      'field--selectable': props.fieldSelectionMode,
      'field--selected': props.fieldSelectionMode && props.selectedFieldKey === fieldKey,
      'field--config-hidden': props.fieldSelectionMode && isFieldMarkedHidden(field),
      'field--empty': fieldHasEmptyValue(field),
    },
  ];
}

function fieldHasEmptyValue(field: FormSectionFieldSchema) {
  const value = field.inputValue ?? field.value;
  if (Array.isArray(value)) return value.length === 0;
  if (field.type === 'boolean') return value === null || value === undefined;
  return value === null || value === undefined || value === false || String(value).trim() === '';
}

function fieldState(field: FormSectionFieldSchema) {
  if (field.invalid) return 'invalid';
  if (field.readonly) return 'readonly';
  if (field.required) return 'required';
  if (fieldHasEmptyValue(field)) return 'empty';
  return 'ready';
}

function isRadioWidget(field: FormSectionFieldSchema) {
  return fieldWidget(field) === 'radio';
}

function isAvatarMany2oneWidget(field: FormSectionFieldSchema) {
  return ['many2one_avatar_user', 'many2one_avatar_employee'].includes(fieldWidget(field));
}

function isDateRangeWidget(field: FormSectionFieldSchema) {
  return fieldWidget(field) === 'daterange';
}

function selectedRelationLabel(field: FormSectionFieldSchema) {
  const value = String(field.inputValue ?? '').trim();
  if (!value) return '';
  const option = (field.relationOptions || []).find((item) => String(item.value) === value);
  return option?.label || '';
}

function many2oneTextValue(field: FormSectionFieldSchema) {
  return String(field.many2oneTextValue || selectedRelationLabel(field) || '').trim();
}

function showMany2oneInlineCreate(field: FormSectionFieldSchema) {
  const text = many2oneTextValue(field);
  if (!text || !field.relationInlineCreate?.enabled || !field.relationInlineCreate.createOnNoMatch) return false;
  const options = field.relationOptions || [];
  const normalized = text.trim().toLowerCase();
  const exact = options.some((item) => String(item.label || '').trim().toLowerCase() === normalized);
  if (exact) return false;
  return true;
}

function hasMany2oneDropdown(field: FormSectionFieldSchema) {
  return Boolean(
    field.relationOptions?.length
    || field.many2oneOpenToken
    || field.many2oneSearchToken
    || (field.relationCreateMode === 'page' && field.many2oneCreateToken)
    || showMany2oneInlineCreate(field),
  );
}

function avatarText(label: string) {
  const text = String(label || '').trim();
  return text ? text.slice(0, 1).toUpperCase() : '';
}

function selectPlaceholderText(field: FormSectionFieldSchema) {
  return props.selectPlaceholder(field.label);
}

function inputPlaceholderText(field: FormSectionFieldSchema) {
  return props.inputPlaceholder(field.label);
}

function readonlyText(field: FormSectionFieldSchema) {
  const fieldType = String(field.type || field.descriptor?.ttype || field.descriptor?.type || '').trim().toLowerCase();
  const normalizedValue = ['date', 'datetime', 'many2one'].includes(fieldType)
    && String(field.value).trim().toLowerCase() === 'false'
    ? ''
    : field.value;
  return formatDisplayValue(
    normalizedValue,
    { ...(field.descriptor || {}), type: fieldType || field.descriptor?.type },
    { emptyText: '-' },
  );
}

function readonlyHtml(field: FormSectionFieldSchema) {
  return sanitizeReadonlyHtml(field.value);
}

function fieldActionsFor(field: FormSectionFieldSchema) {
  return props.fieldActions?.(field) || [];
}

function isFieldMarkedHidden(field: FormSectionFieldSchema) {
  return fieldActionsFor(field).some((action) => (
    Boolean(action.checked)
    && String(action.value || action.key || '').trim().toLowerCase() === 'hide'
  ));
}

function emitFieldChange(field: FormSectionFieldSchema, value: string | number | boolean | null) {
  emit('field-change', {
    name: field.name,
    type: field.type,
    widget: field.widget,
    value,
    descriptor: field.descriptor,
  });
}

function emitBinaryFieldChange(field: FormSectionFieldSchema, event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    emitFieldChange(field, null);
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    const result = String(reader.result || '');
    const separatorIndex = result.indexOf(',');
    emit('field-change', {
      name: field.name,
      type: field.type,
      widget: field.widget,
      value: separatorIndex >= 0 ? result.slice(separatorIndex + 1) : result,
      descriptor: field.descriptor,
      fileName: file.name,
    });
  };
  reader.onerror = () => emitFieldChange(field, null);
  reader.readAsDataURL(file);
}

function collapseMany2oneDropdown(event: Event) {
  const target = event.currentTarget;
  const targetElement = target as unknown as { closest?: (selector: string) => { querySelector?: (selector: string) => HTMLInputElement | null } | null };
  const closest = target && typeof targetElement.closest === 'function'
    ? targetElement.closest.bind(target)
    : null;
  const input = closest?.('.many2one-combobox')?.querySelector?.('input') || null;
  window.setTimeout(() => input?.blur(), 0);
}

function emitMany2oneAction(field: FormSectionFieldSchema, value: string | number | boolean | null, event: Event) {
  many2oneFocusedField.value = '';
  many2oneActiveIndex.value[field.name] = -1;
  emitFieldChange(field, value);
  collapseMany2oneDropdown(event);
}

function emitMany2oneQuery(field: FormSectionFieldSchema, value: string) {
  many2oneActiveIndex.value[field.name] = -1;
  emit('field-change', {
    name: field.name,
    type: field.type,
    widget: field.widget,
    value,
    action: 'query',
    descriptor: field.descriptor,
  });
}

function many2oneDomKey(field: FormSectionFieldSchema) {
  return field.name.replace(/[^A-Za-z0-9_-]/g, '-');
}

function many2oneListboxId(field: FormSectionFieldSchema) {
  return `${formSectionDomId}-many2one-options-${many2oneDomKey(field)}`;
}

function many2oneOptionId(field: FormSectionFieldSchema, index: number) {
  return `${many2oneListboxId(field)}-${index}`;
}

function many2oneActiveDescendant(field: FormSectionFieldSchema) {
  const index = many2oneActiveIndex.value[field.name] ?? -1;
  return index >= 0 ? many2oneOptionId(field, index) : undefined;
}

function focusMany2one(field: FormSectionFieldSchema) {
  many2oneFocusedField.value = field.name;
  many2oneActiveIndex.value[field.name] = -1;
  emitMany2oneQuery(field, many2oneTextValue(field));
}

function blurMany2one(field: FormSectionFieldSchema, event: FocusEvent) {
  if (many2oneFocusedField.value !== field.name) return;
  emitMany2oneCommit(field, (event.target as HTMLInputElement).value);
  window.setTimeout(() => {
    if (many2oneFocusedField.value === field.name) many2oneFocusedField.value = '';
  }, 0);
}

function handleMany2oneKeydown(field: FormSectionFieldSchema, event: KeyboardEvent) {
  const options = (field.relationOptions || []).slice(0, 8);
  const current = many2oneActiveIndex.value[field.name] ?? -1;
  if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && options.length) {
    event.preventDefault();
    const delta = event.key === 'ArrowDown' ? 1 : -1;
    many2oneActiveIndex.value[field.name] = (current + delta + options.length) % options.length;
    return;
  }
  if (event.key === 'Enter') {
    event.preventDefault();
    const option = current >= 0 ? options[current] : undefined;
    if (option) emitFieldChange(field, option.value);
    else emitMany2oneCommit(field, (event.target as HTMLInputElement).value);
    many2oneFocusedField.value = '';
    many2oneActiveIndex.value[field.name] = -1;
    (event.target as HTMLInputElement).blur();
    return;
  }
  if (event.key === 'Escape') {
    event.preventDefault();
    many2oneFocusedField.value = '';
    many2oneActiveIndex.value[field.name] = -1;
  }
}

function emitMany2oneCommit(field: FormSectionFieldSchema, value: string) {
  emit('field-change', {
    name: field.name,
    type: field.type,
    widget: field.widget,
    value,
    action: 'commit',
    descriptor: field.descriptor,
  });
}

function emitMany2oneInlineCreate(field: FormSectionFieldSchema, event: Event) {
  emitMany2oneCommit(field, many2oneTextValue(field));
  collapseMany2oneDropdown(event);
}

function emitDateRangeEndChange(field: FormSectionFieldSchema, value: string | number | boolean | null) {
  const name = String(field.dateRangeEndField || '').trim();
  if (!name) return;
  emit('field-change', {
    name,
    type: field.type,
    widget: field.widget,
    value,
    descriptor: field.descriptor,
  });
}

function emitFavoriteToggle(field: FormSectionFieldSchema) {
  const favorite = field.favoriteToggle;
  if (!favorite || favorite.readonly) return;
  emit('field-change', {
    name: favorite.name,
    type: 'boolean',
    value: !favorite.active,
    descriptor: favorite.descriptor,
  });
}

function emitFieldAction(field: FormSectionFieldSchema, action: FormSectionFieldAction) {
  if (action.disabled) return;
  emit('field-action', { field, action });
}

function emitFieldOrderDragStart(field: FormSectionFieldSchema, event: DragEvent) {
  if (!props.fieldOrderEditable) return;
  emit('field-order-drag-start', { field, event });
}

function resolveFieldOrderDropPlacement(event?: DragEvent | MouseEvent): 'before' | 'after' | '' {
  const target = event?.currentTarget as HTMLElement | null | undefined;
  if (!target || typeof target.getBoundingClientRect !== 'function') return '';
  const rect = target.getBoundingClientRect();
  if (!rect.height) return '';
  const clientY = Number(event?.clientY || 0);
  if (!Number.isFinite(clientY) || clientY <= 0) return '';
  return clientY >= rect.top + rect.height / 2 ? 'after' : 'before';
}

function emitFieldOrderDragOver(field: FormSectionFieldSchema, event?: DragEvent) {
  if (!props.fieldOrderEditable) return;
  emit('field-order-drag-over', { field, groupTitle: props.fieldGroupTitle || '', placement: resolveFieldOrderDropPlacement(event) });
}

function emitFieldOrderDragLeave(field: FormSectionFieldSchema) {
  if (!props.fieldOrderEditable) return;
  emit('field-order-drag-leave', { field, groupTitle: props.fieldGroupTitle || '' });
}

function emitFieldOrderDrop(field: FormSectionFieldSchema, event?: DragEvent | MouseEvent) {
  if (!props.fieldOrderEditable) return;
  emit('field-order-drop', { field, groupTitle: props.fieldGroupTitle || '', placement: resolveFieldOrderDropPlacement(event) });
}

function emitFieldOrderPointerDrop(field: FormSectionFieldSchema, event: MouseEvent) {
  if (!props.fieldOrderEditable || !props.fieldOrderDraggingKey) return;
  emitFieldOrderDrop(field, event);
  emitFieldOrderDragEnd(field);
}

function emitFieldOrderDragEnd(field: FormSectionFieldSchema) {
  if (!props.fieldOrderEditable) return;
  emit('field-order-drag-end', { field });
}

function emitFieldLabelChange(field: FormSectionFieldSchema, label: string) {
  if (!props.fieldConfigEditable) return;
  const normalized = String(label || '').trim();
  if (!normalized || normalized === field.label) return;
  emit('field-label-change', { field, label: normalized });
}

function isInteractiveFieldTarget(event?: Event) {
  const target = event?.target;
  const targetElement = target as unknown as { closest?: (selector: string) => unknown };
  if (!target || typeof targetElement.closest !== 'function') return false;
  if (props.fieldSelectionMode) {
    return Boolean(targetElement.closest('button, a, .field-inline-config, .field-label-editor'));
  }
  return Boolean(targetElement.closest('button, input, select, textarea, a, .field-inline-config, .field-control-row'));
}

function emitFieldSelect(field: FormSectionFieldSchema, event?: Event) {
  if (!props.fieldSelectionMode) return;
  if (isInteractiveFieldTarget(event)) return;
  event?.preventDefault();
  event?.stopPropagation();
  emit('field-select', { field, groupTitle: props.fieldGroupTitle || '' });
}
</script>

<style scoped>
.template-form-section {
  grid-column: 1 / -1;
  min-width: 0;
  container-type: inline-size;
  border: 0;
  border-top: 1px solid var(--sc-app-border);
  border-radius: 0;
  background: transparent;
  padding: 14px 0 0;
}

.template-form-section--core {
  border-top: 0;
  padding-top: 0;
}

.template-form-section--advanced {
  border-top: 1px solid var(--sc-app-border);
  margin-top: 2px;
}

.template-form-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
  min-width: 0;
}

.template-form-section-title {
  margin: 0;
  font-size: 14px;
  color: var(--sc-app-text-primary);
  font-weight: 500;
  overflow-wrap: anywhere;
}

.template-form-section-hint {
  margin: -4px 0 10px;
  font-size: 12px;
  color: var(--sc-app-text-primary);
}

.field-supporting-text,
.field-error-text {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.45;
}

.field-supporting-text {
  color: var(--sc-semantic-text-muted);
}

.field-error-text {
  color: var(--sc-app-danger-text);
}

.field :is(input, select, textarea)[aria-invalid='true'] {
  border-color: var(--sc-app-danger-border);
}

.template-form-section-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  row-gap: 12px;
  column-gap: 20px;
  min-width: 0;
}

.template-form-section--readonly .template-form-section-grid {
  row-gap: 10px;
}

.field {
  display: grid;
  gap: 0;
  min-width: 0;
  align-content: start;
  border: 1px solid transparent;
  border-radius: 6px;
  transition: border-color 120ms ease, box-shadow 120ms ease, background-color 120ms ease, opacity 120ms ease;
}

.field--order-editable {
  padding: 6px;
  margin: -6px;
  cursor: default;
  background: color-mix(in srgb, var(--sc-app-info-bg) 42%, transparent);
}

.field--order-dragging {
  opacity: 0.56;
}

.field--order-drop-target {
  border-color: var(--sc-semantic-surface-interactive);
  background: var(--sc-app-info-bg);
}

.field--order-drop-before {
  box-shadow: inset 0 3px 0 var(--sc-semantic-surface-interactive);
}

.field--order-drop-after {
  box-shadow: inset 0 -3px 0 var(--sc-semantic-surface-interactive);
}

.field--selectable {
  padding: 6px;
  margin: -6px;
  cursor: pointer;
}

.field--selectable:hover,
.field--selectable:focus-visible {
  border-color: var(--sc-app-border-strong);
  background: var(--sc-app-hover-bg);
  outline: none;
}

.field--selected {
  border-color: var(--sc-semantic-surface-interactive);
  background: var(--sc-app-info-bg);
  box-shadow: 0 0 0 3px var(--sc-app-focus-ring);
}

.field--config-hidden {
  border-style: dashed;
  opacity: 0.68;
  background: color-mix(in srgb, var(--sc-app-muted-bg) 72%, transparent);
}

.field--compact,
.field--normal,
.field--half {
  grid-column: span 1;
}

.field--wide,
.field--full {
  grid-column: 1 / -1;
}

.template-form-section-grid--columns-1 > .field--wide,
.template-form-section-grid--columns-1 > .field--full {
  grid-column: 1 / -1;
}

.field--large .input,
.field--large textarea.input {
  min-height: 92px;
}

@container (min-width: 680px) {
  .template-form-section-grid--columns-2,
  .template-form-section-grid--columns-3 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .template-form-section-grid--columns-2 > .field--wide,
  .template-form-section-grid--columns-3 > .field--wide {
    grid-column: span 2;
  }
}

@container (min-width: 1240px) {
  .template-form-section-grid--columns-3 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.field-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
  margin-bottom: 3px;
}

.label {
  font-size: 13px;
  color: var(--sc-app-text-primary);
  font-weight: 600;
  margin: 0;
  min-width: 0;
  overflow-wrap: anywhere;
}

.field-label-editor {
  flex: 1 1 140px;
  min-width: 96px;
  max-width: 220px;
  height: 28px;
  border: 1px solid var(--sc-app-border);
  border-radius: 5px;
  background: var(--sc-app-input-bg);
  color: var(--sc-app-text-primary);
  padding: 4px 8px;
  font-size: 13px;
  font-weight: 600;
}

.field-favorite-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--sc-semantic-text-muted);
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}

.field-favorite-toggle:hover:not(:disabled) {
  background: var(--sc-app-hover-bg);
  color: var(--sc-app-text-secondary);
}

.field-favorite-toggle--active {
  color: var(--sc-app-warning-text);
}

.field-favorite-toggle:disabled {
  cursor: default;
  opacity: 0.62;
}

.field-state {
  display: inline-flex;
  align-items: center;
  min-height: 18px;
  margin-left: 4px;
  padding: 0 5px;
  border: 1px solid var(--sc-app-border);
  border-radius: 999px;
  color: var(--sc-app-text-primary);
  font-size: 10px;
  font-weight: 600;
  line-height: 1;
  vertical-align: 1px;
}

.field-state--required {
  min-height: auto;
  margin-left: 2px;
  padding: 0;
  border: 0;
  color: var(--sc-app-danger-text);
  font-size: 14px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.field-inline-config {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}

.field--order-editable {
  cursor: grab;
}

.field--order-editable:active {
  cursor: grabbing;
}

.field-inline-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--sc-semantic-text-muted);
  font-size: 12px;
  line-height: 1;
}

.field-inline-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.field-inline-action input {
  margin: 0;
}

.field-control-row {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 6px;
  min-width: 0;
}

.field-control-main {
  flex: 1 1 auto;
  display: grid;
  min-width: 0;
}

.readonly-value {
  font-size: 13px;
  color: var(--sc-app-text-secondary);
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  min-width: 0;
  overflow-wrap: anywhere;
}

.readonly-value--html {
  display: block;
  line-height: 1.65;
}

.readonly-value--html :deep(ul),
.readonly-value--html :deep(ol) {
  margin: 0;
  padding-inline-start: 20px;
}

.readonly-value--html :deep(p) {
  margin: 0 0 6px;
}

.template-form-section--readonly .readonly-value {
  min-height: 28px;
  color: var(--sc-app-text-primary);
  font-size: 14px;
}

.template-form-section--readonly :deep(.contract-readonly-value) {
  min-height: 28px;
  color: var(--sc-app-text-primary);
  font-size: 14px;
}

/* Business document sections: visible grouping without a dark navigation treatment. */
.template-form-section {
  padding: 18px 20px 20px;
  border: 1px solid var(--sc-app-border);
  border-radius: 10px;
  background: var(--sc-app-panel);
  box-shadow: 0 2px 8px color-mix(in srgb, var(--sc-app-shadow) 8%, transparent);
}

.template-form-section--core,
.template-form-section--advanced {
  padding-top: 18px;
  border-top: 1px solid var(--sc-app-border);
  margin-top: 0;
}

.template-form-section-head {
  position: relative;
  min-height: 28px;
  margin: -18px -20px 14px;
  padding: 12px 16px 10px 20px;
  border-bottom: 1px solid var(--sc-app-border);
  border-radius: 10px 10px 0 0;
  background: linear-gradient(90deg, var(--sc-app-info-bg) 0%, color-mix(in srgb, var(--sc-app-info-bg) 48%, var(--sc-app-panel)) 62%, var(--sc-app-panel) 100%);
}

.template-form-section-head::before {
  position: absolute;
  top: 11px;
  bottom: 9px;
  left: 0;
  width: 4px;
  border-radius: 0 999px 999px 0;
  background: var(--sc-semantic-surface-interactive);
  content: '';
}

.template-form-section-title {
  color: var(--sc-app-info-text);
  font-size: 15px;
  font-weight: 700;
}

.template-form-section--readonly .template-form-section-grid {
  row-gap: 12px;
  column-gap: 26px;
}

.template-form-section--readonly .label {
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  font-weight: 500;
}

.template-form-section--readonly .readonly-value,
.template-form-section--readonly :deep(.contract-readonly-value) {
  min-height: 24px;
  color: var(--sc-app-text-primary);
  font-size: 14px;
  font-weight: 550;
}

@media (max-width: 760px) {
  .template-form-section {
    padding: 14px 14px 16px;
    border-radius: 9px;
  }

  .template-form-section-head {
    margin: -14px -14px 12px;
    padding: 10px 12px 9px 16px;
    border-radius: 9px 9px 0 0;
  }

  .template-form-section--readonly .template-form-section-grid {
    row-gap: 12px;
  }
}

.input {
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-component-input-radius);
  padding: 7px 10px;
  height: 36px;
  min-height: 36px;
  width: 100%;
  min-width: 0;
  font-size: 14px;
  line-height: 1.35;
  color: var(--sc-app-text-primary);
  background: var(--sc-app-input-bg);
  box-sizing: border-box;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, background-color 0.18s ease;
}

.input::placeholder {
  color: var(--sc-semantic-text-muted);
}

.input:focus {
  outline: none;
  border-color: var(--sc-semantic-surface-interactive);
  box-shadow: 0 0 0 3px var(--sc-app-focus-ring);
}

.input:hover:not(:disabled):not(:focus) {
  border-color: var(--sc-app-border-strong);
}

.input:disabled,
.input[readonly] {
  background: var(--sc-app-muted-bg);
  color: var(--sc-app-text-secondary);
  cursor: not-allowed;
}

.field[data-field-type='integer'] .input,
.field[data-field-type='float'] .input,
.field[data-field-type='monetary'] .input,
.field[data-field-type='integer'] :deep(.contract-readonly-value),
.field[data-field-type='float'] :deep(.contract-readonly-value),
.field[data-field-type='monetary'] :deep(.contract-readonly-value) {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.field[data-field-type='date'] .input,
.field[data-field-type='datetime'] .input,
.field[data-field-type='date'] :deep(.contract-readonly-value),
.field[data-field-type='datetime'] :deep(.contract-readonly-value) {
  font-variant-numeric: tabular-nums;
}

textarea.input {
  min-height: 104px;
  height: auto;
  resize: vertical;
}

select.input {
  appearance: none;
  background-image: linear-gradient(45deg, transparent 50%, var(--sc-app-text-secondary) 50%), linear-gradient(135deg, var(--sc-app-text-secondary) 50%, transparent 50%);
  background-position: calc(100% - 16px) calc(50% - 2px), calc(100% - 11px) calc(50% - 2px);
  background-size: 5px 5px, 5px 5px;
  background-repeat: no-repeat;
  padding-right: 30px;
}

.native-radio-group {
  display: grid;
  gap: 8px;
  align-items: start;
}

.native-radio-option {
  display: inline-flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 0;
  color: var(--sc-app-text-secondary);
  font-size: 13px;
  line-height: 1.35;
}

.native-radio-input {
  margin-top: 2px;
  accent-color: var(--sc-semantic-surface-interactive);
}

.native-radio-input:disabled {
  cursor: default;
}

.native-radio-input:disabled + span {
  color: var(--sc-semantic-text-muted);
}

.many2one-widget-shell {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 0;
}

.many2one-widget-shell--avatar .many2one-combobox > .input {
  padding-left: 42px;
}

.many2one-combobox {
  position: relative;
  display: grid;
  gap: 6px;
  width: 100%;
  min-width: 0;
}

.many2one-option-panel {
  position: absolute;
  z-index: 20;
  top: calc(100% + 2px);
  left: 0;
  right: 0;
  display: none;
  max-height: 260px;
  overflow: auto;
  border: 1px solid var(--sc-app-border-strong);
  border-radius: var(--sc-component-panel-radius);
  background: var(--sc-app-panel);
  box-shadow: var(--sc-semantic-shadow-modal);
}

.many2one-combobox.is-open .many2one-option-panel {
  display: grid;
}

.many2one-option-list {
  display: grid;
}

.many2one-option {
  min-height: 32px;
  border: 0;
  border-bottom: 1px solid var(--sc-app-border);
  background: var(--sc-app-panel);
  color: var(--sc-app-text-primary);
  padding: 6px 10px;
  text-align: left;
  cursor: pointer;
}

.many2one-option:hover,
.many2one-option.is-active {
  background: var(--sc-app-info-bg);
}

.many2one-actions {
  display: grid;
  min-width: 0;
  border-top: 1px solid var(--sc-app-border);
}

.many2one-action {
  min-height: 30px;
  border: 0;
  border-bottom: 1px solid var(--sc-app-border);
  background: var(--sc-app-panel);
  color: var(--sc-app-success-text);
  padding: 6px 10px;
  font-size: 12px;
  line-height: 1.2;
  text-align: left;
  cursor: pointer;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.many2one-action--record {
  font-weight: 600;
}

.many2one-action:hover {
  background: var(--sc-app-success-bg);
}

.many2one-avatar {
  position: absolute;
  left: 10px;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: var(--sc-app-muted-bg);
  color: var(--sc-app-text-secondary);
  font-size: 11px;
  font-weight: 700;
  pointer-events: none;
}

.native-date-range {
  display: grid;
  grid-template-columns: minmax(130px, 1fr) auto minmax(130px, 1fr);
  gap: 6px;
  align-items: center;
  min-width: 0;
}

.native-date-range-separator {
  color: var(--sc-semantic-text-muted);
  font-size: 13px;
}

.input[type='date'] {
  min-width: 0;
  padding-right: 10px;
}

@media (max-width: 860px) {
  .native-date-range {
    grid-template-columns: 1fr;
  }

  .native-date-range-separator {
    display: none;
  }
}
</style>
