<template>
  <div
    class="professional-base-field-control"
    data-semantic-component="ProfessionalBaseFieldControl"
    :data-state="model.controlState"
    data-professional-field-family="base"
    :data-professional-field-type="model.fieldType"
    :data-control-kind="model.controlKind"
    :data-presentation-mode="model.presentationMode"
    :data-render-profile="model.renderProfile"
    :data-control-state="model.controlState"
  >
    <template v-if="field.readonly">
      <slot v-if="hasReadonlyOverride" name="readonly" :field="field" />
      <template v-else>
        <div
          v-if="field.type === 'html'"
          class="professional-base-field-control__readonly professional-base-field-control__readonly--html"
          v-html="readonlyHtml"
        />
        <div
          v-else-if="taskActionFor(props.field)"
          role="button"
          tabindex="0"
          class="professional-base-field-control__readonly professional-base-field-control__readonly--action"
          :aria-label="`${taskActionLabel(props.field)}（办理动作）`"
          @click="taskActionRun(props.field)"
          @keydown.enter.prevent="taskActionRun(props.field)"
        >{{ taskActionLabel(props.field) }}</div>
        <span v-else class="professional-base-field-control__readonly">{{ readonlyText }}</span>
      </template>
    </template>
    <ScCheckbox
      v-else-if="field.type === 'boolean'"
      :checked="Boolean(field.value)"
      :required="field.required"
      :described-by="describedBy"
      :label="field.label || field.name"
      @change="emitValue($event)"
    />
    <ScSelect
      v-else-if="field.type === 'selection'"
      :id="controlId"
      :model-value="String(field.inputValue ?? '')"
      :required="field.required"
      :invalid="field.invalid"
      :described-by="describedBy"
      :placeholder="placeholder"
      :options="(field.selectionOptions || []).filter(Boolean).map((option) => ({ value: option.value, label: option.label }))"
      @update:model-value="emitValue"
    />
    <ScDateField
      v-else-if="field.type === 'date' || field.type === 'datetime'"
      :id="controlId"
      :model-value="String(field.inputValue ?? '')"
      :with-time="field.type === 'datetime'"
      :required="field.required"
      :invalid="field.invalid"
      :described-by="describedBy"
      :placeholder="placeholder"
      @update:model-value="emitValue"
    />
    <ScTextarea
      v-else-if="field.type === 'text' || field.type === 'html'"
      :model-value="String(field.inputValue ?? '')"
      :required="field.required"
      :status="field.invalid ? 'error' : 'default'"
      :described-by="describedBy"
      :placeholder="placeholder"
      :rows="4"
      @update:model-value="emitValue"
    />
    <ScNumberInput
      v-else-if="field.type === 'integer' || field.type === 'float'"
      :model-value="numericValue"
      :decimal-places="field.type === 'integer' ? 0 : undefined"
      :status="field.invalid ? 'error' : 'default'"
      :placeholder="placeholder"
      @update:model-value="emitValue($event ?? null)"
    />
    <ScInput v-else
      :id="controlId"
      :model-value="String(field.inputValue ?? '')"
      :type="field.type === 'integer' || field.type === 'float' ? 'number' : 'text'"
      :status="field.invalid ? 'error' : 'default'"
      :described-by="describedBy"
      :placeholder="placeholder"
      :aria-required="field.required || undefined"
      @update:model-value="emitValue"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue';
import ScDateField from '../design-system/ScDateField.vue';
import ScCheckbox from '../design-system/ScCheckbox.vue';
import ScInput from '../design-system/ScInput.vue';
import ScNumberInput from '../design-system/ScNumberInput.vue';
import ScSelect from '../design-system/ScSelect.vue';
import ScTextarea from '../design-system/ScTextarea.vue';
import { formatDisplayValue } from '../../utils/display';
import { sanitizeReadonlyHtml } from '../../utils/sanitizeReadonlyHtml';
import type { FormSectionFieldSchema } from '../template/formSection.types';
import {
  ScTaskActionResolverKey,
  type ScTaskActionDescriptor,
} from '../template/taskActionResolver';
import { resolveProfessionalBaseFieldModel } from './professionalBaseFieldModel';

const props = defineProps<{
  field: FormSectionFieldSchema;
  controlId: string;
  describedBy?: string;
  placeholder: string;
  hasReadonlyOverride?: boolean;
}>();

const emit = defineEmits<{
  'update:value': [value: string | number | boolean | null];
}>();

const normalizedType = computed(() => String(props.field.type || '').trim().toLowerCase());

const taskActionResolver = inject(ScTaskActionResolverKey, null);
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

const model = computed(() => resolveProfessionalBaseFieldModel({
  fieldType: String(props.field.type || ''),
  widget: props.field.widget,
  presentationMode: props.field.presentationMode || 'unscoped',
  renderProfile: props.field.renderProfile || 'unscoped',
  readonly: props.field.readonly,
}));
const normalizedReadonlyValue = computed(() => (
  ['date', 'datetime'].includes(normalizedType.value)
  && String(props.field.value).trim().toLowerCase() === 'false'
    ? ''
    : props.field.value
));
const readonlyText = computed(() => formatDisplayValue(
  normalizedReadonlyValue.value,
  { ...(props.field.descriptor || {}), type: normalizedType.value || props.field.descriptor?.type },
  { emptyText: '-' },
));
const readonlyHtml = computed(() => sanitizeReadonlyHtml(props.field.value));
const numericValue = computed(() => {
  if (props.field.inputValue === '' || props.field.inputValue === null || typeof props.field.inputValue === 'undefined') return undefined;
  const value = Number(props.field.inputValue);
  return Number.isFinite(value) ? value : undefined;
});

function emitValue(value: string | number | boolean | null) {
  emit('update:value', value);
}
</script>

<style scoped>
.professional-base-field-control,
.professional-base-field-control :deep(.sc-input) {
  width: 100%;
}

.professional-base-field-control :deep(.sc-input):not(.sc-textarea) {
  box-sizing: border-box;
  height: calc(var(--sc-component-input-height-md) * 1px);
  min-height: calc(var(--sc-component-input-height-md) * 1px);
  padding-inline: calc(var(--sc-component-input-padding-x) * 1px);
}

/* TDesign driver: .sc-input is the t-input__wrap, and t-input already carries
 * its own internal padding. An extra wrap-level padding-inline would shift the
 * input control 8px right vs select/checkbox controls (which have no wrap
 * padding), breaking horizontal alignment across field widgets. Reset it so the
 * visible control edges line up on the same vertical grid line. */
.professional-base-field-control :deep(.sc-input[data-primitive-driver='tdesign']):not(.sc-textarea) {
  padding-inline: 0;
}

.professional-base-field-control__textarea {
  box-sizing: border-box;
  width: 100%;
  min-height: 88px;
  padding: var(--sc-space-xs) calc(var(--sc-component-input-padding-x) * 1px);
  color: var(--sc-color-text-primary);
  background: var(--sc-app-input-bg);
  border: 1px solid var(--sc-color-border-default);
  border-radius: var(--sc-component-input-radius);
  font: inherit;
  resize: vertical;
}

.professional-base-field-control__readonly {
  min-height: calc(var(--sc-component-input-height-md) * 1px);
  color: var(--sc-app-text-primary);
  font-size: calc(var(--sc-component-input-font-size) * 1px);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

/* A readonly fact that is actually the next business action (下一步办理).
 * Pressable action link so the "当前任务" card is a real entry point.
 * Kept at the readonly weight (400) so the density baseline
 * (form.readonly-weight-uniform) stays green - the click affordance is
 * carried by the link color, underline and pointer cursor instead. */
.professional-base-field-control__readonly--action {
  padding: 0;
  border: 0;
  background: transparent;
  font: inherit;
  color: var(--sc-text-link, var(--sc-app-accent)) !important;
  font-weight: 400 !important;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.professional-base-field-control__readonly--action:hover {
  opacity: 0.8;
}

.professional-base-field-control__readonly--action:focus-visible {
  outline: 2px solid var(--sc-app-accent);
  outline-offset: 2px;
  border-radius: 2px;
}

.professional-base-field-control[data-professional-field-type='integer'] :deep(.sc-input),
.professional-base-field-control[data-professional-field-type='float'] :deep(.sc-input),
.professional-base-field-control[data-professional-field-type='integer'] .professional-base-field-control__readonly,
.professional-base-field-control[data-professional-field-type='float'] .professional-base-field-control__readonly {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.professional-base-field-control[data-professional-field-type='date'] :deep(.t-date-picker),
.professional-base-field-control[data-professional-field-type='datetime'] :deep(.t-date-picker) {
  width: 100%;
}

.professional-base-field-control[data-professional-field-type='date'] :deep(.sc-input),
.professional-base-field-control[data-professional-field-type='datetime'] :deep(.sc-input),
.professional-base-field-control[data-professional-field-type='date'] .professional-base-field-control__readonly,
.professional-base-field-control[data-professional-field-type='datetime'] .professional-base-field-control__readonly {
  font-variant-numeric: tabular-nums;
}
</style>
