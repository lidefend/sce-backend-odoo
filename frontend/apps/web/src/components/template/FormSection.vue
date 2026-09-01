<template>
  <ScCard
    :class="['template-form-section', toneClass, { 'template-form-section--readonly': allFieldsReadonly }]"
    data-component="FormSection"
    data-semantic-component="FormSection"
    :data-state="allFieldsReadonly ? 'readonly' : 'editable'"
    :title="undefined"
    :appearance="preferReadonlyFacts ? 'fact' : 'form-section'"
  >
    <template v-if="showHead && $slots.action" #actions><slot name="action" /></template>
    <p v-if="hint" class="template-form-section-hint">{{ hint }}</p>
    <div :class="['template-form-section-grid', `template-form-section-grid--columns-${columns}`]">
      <template v-if="fields.length">
        <div
          v-for="(field, index) in fields"
          :key="field.key"
          :class="fieldClass(field, index)"
          :data-field-name="field.name"
          :data-field-key="field.key"
          :data-field-type="field.type"
          :data-widget-type="field.widget || undefined"
          :data-native-locator="field.nativeLocator || undefined"
          :data-occurrence-index="field.occurrenceIndex || undefined"
          :data-source-position="field.sourcePosition ?? undefined"
          :data-field-state="fieldState(field)"
          :data-field-auth="field.auth || undefined"
          :data-component-key="field.componentKey || undefined"
          :data-component-readiness="field.componentReadiness || undefined"
          :data-component-renderer="field.componentRenderer || undefined"
          :data-contract-adapter="field.contractAdapter || undefined"
          :data-contract-component-version="field.contractVersion || undefined"
          :data-component-fallback="field.componentFallback || undefined"
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
            <label v-if="!fieldConfigEditable && !field.hideLabel" class="label" :for="fieldControlId(field)">
              {{ field.label }}
              <span v-if="field.required && !field.readonly" class="field-state field-state--required"><span aria-hidden="true">*</span><span class="sr-only">必填</span></span>
              <span v-else-if="field.readonly && !allFieldsReadonly" class="field-state">只读</span>
            </label>
            <ScInput
              v-else-if="fieldConfigEditable"
              class="field-label-editor"
              type="text"
              size="small"
              :model-value="field.label"
              :aria-label="`${field.label}显示名称`"
              @change="emitFieldLabelChange(field, $event)"
              @keydown.enter.prevent="emitFieldLabelChange(field, ($event.target as HTMLInputElement).value)"
            />
            <div v-if="fieldActionsFor(field).length" class="field-inline-config">
              <ScRadioGroup
                v-if="fieldActionsFor(field).length"
                class="field-inline-actions"
                :model-value="selectedFieldActionValue(field)"
                :options="fieldActionOptions(field)"
                :name="fieldActionGroupName(field)"
                :label="`${field.label}字段操作`"
                size="small"
                @change="emitFieldActionValue(field, $event)"
              />
            </div>
          </div>
          <div :class="['field-control-row', { 'field-control-row--favorite': field.favoriteToggle }]">
            <ScIconButton
              v-if="field.favoriteToggle"
              class="field-favorite-toggle"
              appearance="favorite-toggle"
              :class="{ 'field-favorite-toggle--active': field.favoriteToggle.active }"
              :aria-pressed="field.favoriteToggle.active"
              :label="field.favoriteToggle.label"
              :disabled="field.favoriteToggle.readonly"
              @click="emitFavoriteToggle(field)"
            >
              <ScIcon :name="field.favoriteToggle.active ? 'star' : 'star-outline'" :size="16" />
            </ScIconButton>
            <div class="field-control-main">
              <ScRadioGroup
                v-if="field.type === 'selection' && isRadioWidget(field) && !(preferReadonlyFacts && field.readonly)"
                class="native-radio-group"
                :model-value="String(field.inputValue ?? '')"
                :options="field.selectionOptions || []"
                :name="fieldRadioGroupName(field)"
                :label="field.label"
                :required="field.required"
                :invalid="field.invalid"
                :readonly="field.readonly"
                :described-by="fieldDescribedBy(field)"
                @change="emitFieldChange(field, $event)"
              />
              <ProfessionalBusinessValueControl
                v-else-if="usesProfessionalBusinessValue(field)"
                :field="field"
                :control-id="fieldControlId(field)"
                :placeholder="field.inputPlaceholder || selectPlaceholderText(field)"
                @update:value="emitFieldChange(field, $event)"
              />
              <ProfessionalBaseFieldControl
                v-else-if="usesProfessionalBaseField(field)"
                :field="field"
                :control-id="fieldControlId(field)"
                :described-by="fieldDescribedBy(field)"
                :placeholder="field.inputPlaceholder || (field.type === 'selection' ? selectPlaceholderText(field) : inputPlaceholderText(field))"
                :has-readonly-override="Boolean(slots.readonly)"
                @update:value="emitFieldChange(field, $event)"
              >
                <template #readonly="readonlySlot">
                  <slot name="readonly" v-bind="readonlySlot" />
                </template>
              </ProfessionalBaseFieldControl>
              <SceneFieldControl
                v-else-if="usesSceneFieldControl(field) && !(preferReadonlyFacts && field.readonly)"
                :field="sceneField(field)"
                :model-value="contractFormDriverValue(field)"
                @update:model-value="emitFieldChange(field, $event)"
              />
              <ProfessionalRelationFieldControl v-else-if="usesProfessionalMany2many(field) && relationAdapter" :field="field">
                <X2ManyRelationRenderer :field="field" :adapter="relationAdapter" @reload-requested="emitFieldAction(field, { key: 'reload-requested', label: '刷新', value: 'reload-requested' })" />
              </ProfessionalRelationFieldControl>
              <PaymentSettlementDetailCollectionControl
                v-else-if="usesPaymentSettlementDetailCollection(field) && relationAdapter"
                :field="field"
                :adapter="relationAdapter"
                @reload-requested="emitFieldAction(field, { key: 'reload-requested', label: '刷新', value: 'reload-requested' })"
              />
              <ProfessionalDetailCollectionControl
                v-else-if="usesProfessionalOne2many(field) && relationAdapter"
                :field="field"
                :adapter="relationAdapter"
              >
                <X2ManyRelationRenderer :field="field" :adapter="relationAdapter" @reload-requested="emitFieldAction(field, { key: 'reload-requested', label: '刷新', value: 'reload-requested' })" />
              </ProfessionalDetailCollectionControl>
              <ProfessionalRelationFieldControl v-else-if="usesProfessionalMany2one(field) && field.readonly" :field="field">
                <slot name="readonly" :field="field">
                  <span class="readonly-value">{{ readonlyText(field) }}</span>
                </slot>
              </ProfessionalRelationFieldControl>
              <template v-else-if="field.readonly">
                <slot name="readonly" :field="field">
                  <div
                    v-if="field.type === 'html'"
                    class="readonly-value readonly-value--html"
                    v-html="readonlyHtml(field)"
                  />
                  <div
                    v-else-if="taskActionFor(field)"
                    role="button"
                    tabindex="0"
                    class="readonly-value readonly-value--action"
                    :aria-label="`${taskActionLabel(field)}（办理动作）`"
                    @click="taskActionRun(field)"
                    @keydown.enter.prevent="taskActionRun(field)"
                  >{{ taskActionLabel(field) }}</div>
                  <span v-else class="readonly-value">{{ readonlyText(field) }}</span>
                </slot>
              </template>
              <template v-else-if="isLegacyComplexField(field)">
                <ScFileField
                  v-if="field.type === 'binary'"
                  :id="fieldControlId(field)"
                  :required="field.required"
                  :invalid="field.invalid"
                  :described-by="fieldDescribedBy(field)"
                  @change="emitBinaryFieldChange(field, $event[0] || null)"
                />
                <ProfessionalMany2oneFieldControl
                  v-else-if="usesProfessionalMany2one(field)"
                  :field="field"
                  :control-id="fieldControlId(field)"
                  :described-by="fieldDescribedBy(field)"
                  :placeholder="selectPlaceholderText(field)"
                  @select="emitFieldChange(field, $event)"
                  @query="emitMany2oneQuery(field, $event)"
                  @commit="emitMany2oneCommit(field, $event)"
                />
                <ScRelationField
                  v-else-if="field.type === 'many2one'"
                  :id="fieldControlId(field)"
                  class="input"
                  appearance="form-field"
                  :required="field.required"
                  :invalid="field.invalid"
                  :described-by="fieldDescribedBy(field)"
                  :model-value="String(field.inputValue ?? '')"
                  :placeholder="selectPlaceholderText(field)"
                  @update:model-value="emitMany2oneQuery(field, $event)"
                  @change="emitMany2oneCommit(field, ($event.target as HTMLInputElement).value)"
                />
                <div v-else-if="isDateRangeWidget(field)" class="native-date-range">
                  <ScDateField
                    :id="fieldControlId(field)"
                    :model-value="String(field.inputValue ?? '')"
                    class="input"
                    appearance="form-field"
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
                    appearance="form-field"
                    :aria-label="`${field.label}结束日期`"
                    :placeholder="field.inputPlaceholder || inputPlaceholderText(field)"
                    @update:model-value="emitDateRangeEndChange(field, $event)"
                  />
                </div>
                <div v-else-if="field.type === 'monetary'" class="field-monetary-control">
                  <ScInput
                    :id="fieldControlId(field)"
                    :model-value="String(field.inputValue ?? '')"
                    class="input"
                    appearance="form-field"
                    :required="field.required"
                    :status="field.invalid ? 'error' : 'default'"
                    :described-by="fieldDescribedBy(field)"
                    type="number"
                    :step="monetaryInputStep(field.digits)"
                    :placeholder="field.inputPlaceholder || inputPlaceholderText(field)"
                    @update:model-value="emitFieldChange(field, $event)"
                  />
                  <span v-if="field.currencyLabel" class="field-currency-label">{{ field.currencyLabel }}</span>
                </div>
              </template>
              <template v-else>
                <ScInput
                  :id="fieldControlId(field)"
                  :model-value="String(field.inputValue ?? '')"
                  class="input"
                  appearance="form-field"
                  :required="field.required"
                  :status="field.invalid ? 'error' : 'default'"
                  :described-by="fieldDescribedBy(field)"
                  :type="inputType(field.type)"
                  :placeholder="field.inputPlaceholder || inputPlaceholderText(field)"
                  @update:model-value="emitFieldChange(field, $event)"
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
  </ScCard>
</template>

<script setup lang="ts">
import { computed, inject, useId, useSlots } from 'vue';
import { SceneFieldControl, useOptionalSceneUiKit } from '@sc/ui/form';
import ScCard from '../design-system/ScCard.vue';
import ScDateField from '../design-system/ScDateField.vue';
import ScFileField from '../design-system/ScFileField.vue';
import ScIcon from '../design-system/ScIcon.vue';
import ScIconButton from '../design-system/ScIconButton.vue';
import ScInput from '../design-system/ScInput.vue';
import ScRelationField from '../design-system/ScRelationField.vue';
import ScRadioGroup, { type ScRadioOption } from '../design-system/ScRadioGroup.vue';
import ProfessionalBaseFieldControl from '../professional-fields/ProfessionalBaseFieldControl.vue';
import ProfessionalBusinessValueControl from '../professional-fields/ProfessionalBusinessValueControl.vue';
import ProfessionalDetailCollectionControl from '../professional-fields/ProfessionalDetailCollectionControl.vue';
import ProfessionalMany2oneFieldControl from '../professional-fields/ProfessionalMany2oneFieldControl.vue';
import ProfessionalRelationFieldControl from '../professional-fields/ProfessionalRelationFieldControl.vue';
import PaymentSettlementDetailCollectionControl from '../professional-fields/PaymentSettlementDetailCollectionControl.vue';
import { isProfessionalBaseFieldCandidate } from '../professional-fields/professionalBaseFieldModel';
import { isProfessionalBusinessValueField } from '../professional-fields/professionalBusinessValueModel';
import { isProfessionalDetailCollectionField } from '../professional-fields/professionalDetailCollectionModel';
import { isProfessionalRelationField } from '../professional-fields/professionalRelationFieldModel';
import { isPaymentSettlementDetailCollectionField } from '../professional-fields/paymentSettlementDetailCollectionModel';
import X2ManyRelationRenderer from './X2ManyRelationRenderer.vue';
import { formatDisplayValue } from '../../utils/display';
import { sanitizeReadonlyHtml } from '../../utils/sanitizeReadonlyHtml';
import { formatMonetaryDisplayValue, monetaryInputStep } from './formSection.mapper';
import type {
  FormSectionFieldAction,
  FormSectionFieldActionPayload,
  FormSectionFieldSchema,
  FormSectionFieldChange,
  TemplateFieldType,
} from './formSection.types';
import type { RelationFieldAdapter } from './relationField.types';
import { resolveInputPlaceholder, resolveSelectPlaceholder } from './placeholder.mapper';
import {
  normalizeContractFormDriverValue,
  toContractFormDriverFieldChange,
  toContractFormSceneField,
  usesContractFormDriverField,
} from './contractFormDriverField';
import {
  ScTaskActionResolverKey,
  type ScTaskActionDescriptor,
} from './taskActionResolver';

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
  preferReadonlyFacts?: boolean;
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
  preferReadonlyFacts: false,
});

const sceneUiKit = useOptionalSceneUiKit();
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
function isLegacyComplexField(field: FormSectionFieldSchema) {
  return ['many2one', 'binary', 'monetary'].includes(String(field.type || '').trim().toLowerCase())
    || isDateRangeWidget(field);
}

function isRelationEditorField(field: FormSectionFieldSchema) {
  return ['many2many', 'one2many'].includes(String(field.type || '').trim().toLowerCase());
}

function usesProfessionalBaseField(field: FormSectionFieldSchema) {
  const candidate = isProfessionalBaseFieldCandidate(String(field.type || ''), fieldWidget(field));
  if (!candidate) return false;
  return !field.componentRenderer || field.componentRenderer === 'ProfessionalBaseFieldControl';
}

function usesProfessionalBusinessValue(field: FormSectionFieldSchema) {
  return field.componentRenderer === 'ProfessionalBusinessValueControl'
    && isProfessionalBusinessValueField(field);
}

function usesProfessionalMany2one(field: FormSectionFieldSchema) {
  return field.type === 'many2one'
    && field.componentRenderer === 'ProfessionalRelationFieldControl'
    && isProfessionalRelationField(field);
}

function usesProfessionalMany2many(field: FormSectionFieldSchema) {
  return field.type === 'many2many'
    && field.componentRenderer === 'ProfessionalRelationFieldControl'
    && isProfessionalRelationField(field);
}

function usesProfessionalOne2many(field: FormSectionFieldSchema) {
  return field.type === 'one2many'
    && field.componentRenderer === 'ProfessionalDetailCollectionControl'
    && isProfessionalDetailCollectionField(field);
}

function usesPaymentSettlementDetailCollection(field: FormSectionFieldSchema) {
  return isPaymentSettlementDetailCollectionField(field);
}

function usesSceneFieldControl(field: FormSectionFieldSchema) {
  if (isProfessionalRelationField(field) || isProfessionalDetailCollectionField(field) || isPaymentSettlementDetailCollectionField(field)) return false;
  return usesContractFormDriverField(field, sceneUiKit?.kit.value || 'sc-native');
}

function sceneField(field: FormSectionFieldSchema) {
  const type = String(field.type || '').trim().toLowerCase();
  return toContractFormSceneField(
    field,
    fieldControlId(field),
    field.inputPlaceholder || (type === 'selection' ? selectPlaceholderText(field) : inputPlaceholderText(field)),
  );
}

function contractFormDriverValue(field: FormSectionFieldSchema) {
  return normalizeContractFormDriverValue(field.inputValue, String(field.type || ''));
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

// TDesign 24 栅格系统字段宽度映射
const FIELD_SPAN_UNITS: Record<string, number> = {
  'field--compact': 8,
  'field--normal': 12,
  'field--half': 12,
  'field--wide': 16,
  'field--full': 24,
};

function fieldSpanUnits(spanClass: string): number {
  return FIELD_SPAN_UNITS[spanClass] ?? 12;
}

function fieldSpanClass(field: FormSectionFieldSchema, index: number) {
  const explicitSpan = field.spanClass || '';
  const base = explicitSpan || (defaultSpanClass(field.type) === 'field--full' || fieldWidget(field) === 'textarea'
    ? 'field--full'
    : 'field--normal');
  if (base === 'field--full') return base;

  // Orphan-column fill (TDesign 24 栅格系统): a normal/half-width field that
  // starts a new row alone leaves blank cells when its row has no pairing fields —
  // either because it is the last field of the section, or because the next field
  // spans the full row. Widen such a field to span the full row (24 units).
  let units = 0;
  for (let i = 0; i < index; i++) {
    const prev = props.fields[i];
    const prevSpan = prev.spanClass || defaultSpanClass(prev.type);
    units += fieldSpanUnits(prevSpan);
  }
  const isLast = index === props.fields.length - 1;
  const next = props.fields[index + 1];
  const nextSpan = next ? (next.spanClass || defaultSpanClass(next.type)) : '';
  const nextIsFullRow = nextSpan === 'field--full';
  if (units % 24 === 0 && (isLast || nextIsFullRow)) {
    return 'field--full';
  }
  return base;
}

function fieldClass(field: FormSectionFieldSchema, index: number) {
  const fieldKey = fieldIdentity(field);
  const isDropTarget = props.fieldOrderDropTargetKey === fieldKey && props.fieldOrderDraggingKey !== fieldKey;
  return [
    'field',
    fieldSpanClass(field, index),
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
      'field--readonly-empty-relation': isReadonlyEmptyRelation(field),
    },
  ];
}

function isReadonlyEmptyRelation(field: FormSectionFieldSchema) {
  if (!field.readonly || !props.relationAdapter || !isRelationEditorField(field)) return false;
  if (field.type === 'one2many') {
    return props.relationAdapter.visibleOne2manyRows(field.name).length === 0;
  }
  return props.relationAdapter.selectedRelationOptions(field.name).length === 0
    && props.relationAdapter.relationIds(field.name).length === 0;
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

function isDateRangeWidget(field: FormSectionFieldSchema) {
  return fieldWidget(field) === 'daterange';
}

function selectPlaceholderText(field: FormSectionFieldSchema) {
  return props.selectPlaceholder(field.label);
}

function inputPlaceholderText(field: FormSectionFieldSchema) {
  return props.inputPlaceholder(field.label);
}

function readonlyText(field: FormSectionFieldSchema) {
  const fieldType = String(field.type || field.descriptor?.ttype || field.descriptor?.type || '').trim().toLowerCase();
  if (fieldType === 'monetary') {
    return formatMonetaryDisplayValue(field.value, field.digits, field.currencyLabel);
  }
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

const taskActionResolver = inject(ScTaskActionResolverKey, null);

/**
 * Resolve a readonly fact into a clickable business action, when the page
 * layer has registered a task-action resolver (see taskActionResolver.ts).
 * Returns null for plain facts - they keep rendering as readonly text.
 */
function taskActionFor(field: FormSectionFieldSchema): ScTaskActionDescriptor | null {
  if (!taskActionResolver) return null;
  return taskActionResolver(field);
}

function taskActionLabel(field: FormSectionFieldSchema): string {
  const action = taskActionFor(field);
  return action ? action.label : '';
}

function taskActionRun(field: FormSectionFieldSchema) {
  const action = taskActionFor(field);
  if (action) void action.run();
}

function readonlyHtml(field: FormSectionFieldSchema) {
  return sanitizeReadonlyHtml(field.value);
}

function fieldActionsFor(field: FormSectionFieldSchema) {
  return props.fieldActions?.(field) || [];
}

function fieldActionOptions(field: FormSectionFieldSchema): ScRadioOption[] {
  return fieldActionsFor(field).map((action) => ({
    value: action.value,
    label: action.label,
    disabled: Boolean(action.disabled),
  }));
}

function selectedFieldActionValue(field: FormSectionFieldSchema) {
  return fieldActionsFor(field).find((action) => action.checked)?.value || '';
}

function emitFieldActionValue(field: FormSectionFieldSchema, value: string | number | boolean) {
  const action = fieldActionsFor(field).find((candidate) => String(candidate.value) === String(value));
  if (action) emitFieldAction(field, action);
}

function isFieldMarkedHidden(field: FormSectionFieldSchema) {
  return fieldActionsFor(field).some((action) => (
    Boolean(action.checked)
    && String(action.value || action.key || '').trim().toLowerCase() === 'hide'
  ));
}

function emitFieldChange(field: FormSectionFieldSchema, value: string | number | boolean | null) {
  emit('field-change', toContractFormDriverFieldChange(field, value));
}

function emitBinaryFieldChange(field: FormSectionFieldSchema, file: File | null) {
  if (!file) {
    emitFieldChange(field, null);
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    const result = String(reader.result || '');
    const separatorIndex = result.indexOf(',');
    emit('field-change', {
      occurrenceKey: field.key,
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

function emitMany2oneQuery(field: FormSectionFieldSchema, value: string) {
  emit('field-change', {
    occurrenceKey: field.key,
    name: field.name,
    type: field.type,
    widget: field.widget,
    value,
    action: 'query',
    descriptor: field.descriptor,
  });
}

function emitMany2oneCommit(field: FormSectionFieldSchema, value: string) {
  emit('field-change', {
    occurrenceKey: field.key,
    name: field.name,
    type: field.type,
    widget: field.widget,
    value,
    action: 'commit',
    descriptor: field.descriptor,
  });
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

.template-form-section-grid {
  display: grid;
  grid-template-columns: repeat(24, minmax(0, 1fr));
  row-gap: calc(var(--sc-pattern-task-form-field-gap, 12) * 1px);
  column-gap: calc(var(--sc-pattern-task-form-column-gap, 24) * 1px);
  min-width: 0;
}

/* 小屏幕：1 列布局，减小间隙 */
@container (max-width: 479px) {
  .template-form-section-grid {
    grid-template-columns: minmax(0, 1fr);
    column-gap: 0;
  }
}

/* 中等屏幕：2 列布局 */
@container (min-width: 480px) and (max-width: 959px) {
  .template-form-section-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: calc(var(--sc-pattern-task-form-column-gap, 24) * 1px);
  }
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

/* TDesign 24 栅格系统字段宽度映射（大屏幕默认） */
.field--compact {
  grid-column: span 8;
}

.field--normal,
.field--half {
  grid-column: span 12;
}

.field--wide {
  grid-column: span 16;
}

.field--full {
  grid-column: span 24;
}

/* 小屏幕：1 列布局，所有字段全宽 */
@container (max-width: 479px) {
  .field--compact,
  .field--normal,
  .field--half,
  .field--wide,
  .field--full {
    grid-column: 1 / -1;
  }
}

/* 中等屏幕：2 列布局 */
@container (min-width: 480px) and (max-width: 959px) {
  .field--compact,
  .field--normal,
  .field--half {
    grid-column: span 1;
  }
  .field--wide,
  .field--full {
    grid-column: 1 / -1;
  }
}

.field-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sc-pattern-task-form-label-row-gap, 8px);
  flex-wrap: wrap;
  min-width: 0;
  margin-bottom: var(--sc-pattern-task-form-label-row-margin-bottom, 3px);
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
  font-weight: 600;
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
  gap: var(--sc-pattern-task-form-inline-config-gap, 6px);
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
  gap: var(--sc-pattern-task-form-inline-actions-gap, 8px);
  color: var(--sc-semantic-text-muted);
  font-size: 12px;
  line-height: 1;
}

.field-control-row {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: var(--sc-pattern-task-form-control-row-gap, 6px);
  min-width: 0;
}

.field-control-main {
  flex: 1 1 auto;
  display: grid;
  min-width: 0;
}

.readonly-value {
  font-size: 14px;
  color: var(--sc-app-text-primary);
  min-height: 32px;
  line-height: 22px;
  display: inline-flex;
  align-items: center;
  min-width: 0;
  overflow-wrap: anywhere;
}

/* A readonly fact that is actually the next business action (下一步办理).
 * It is rendered as a pressable action link instead of dead text so the
 * "当前任务" card is a real entry point, not a static hint. */
.readonly-value--action {
  padding: 0;
  border: 0;
  background: transparent;
  font: inherit;
  color: var(--sc-text-link, var(--sc-app-accent));
  font-weight: 400;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.readonly-value--action:hover {
  opacity: 0.8;
}

.readonly-value--action:focus-visible {
  outline: 2px solid var(--sc-app-accent);
  outline-offset: 2px;
  border-radius: 2px;
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

.template-form-section--readonly .template-form-section-grid {
  row-gap: calc(var(--sc-pattern-task-form-field-gap, 12) * 1px);
  column-gap: var(--sc-pattern-task-form-readonly-column-gap, 26px);
}

.template-form-section--readonly .field--readonly-empty-relation {
  grid-template-columns: minmax(150px, 220px) minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.template-form-section--readonly .field--readonly-empty-relation :deep(.relation-readonly-empty) {
  padding: 6px 10px;
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
  .template-form-section--readonly .template-form-section-grid {
    row-gap: 12px;
  }

  .template-form-section--readonly .field--readonly-empty-relation {
    grid-template-columns: minmax(0, 1fr);
    gap: 4px;
  }
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

.native-radio-group {
  display: grid;
  gap: 8px;
  align-items: start;
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
.field-monetary-control {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
}

.field-currency-label {
  color: var(--sc-app-text-secondary);
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
</style>
