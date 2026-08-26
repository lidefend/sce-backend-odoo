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
        <span v-else class="professional-base-field-control__readonly">{{ readonlyText }}</span>
      </template>
    </template>
    <input
      v-else-if="field.type === 'boolean'"
      :id="controlId"
      :checked="Boolean(field.value)"
      class="professional-base-field-control__checkbox"
      :aria-required="field.required || undefined"
      :aria-invalid="field.invalid || undefined"
      :aria-describedby="describedBy"
      type="checkbox"
      @change="emitValue(($event.target as HTMLInputElement).checked)"
    />
    <ScSelect
      v-else-if="field.type === 'selection'"
      :id="controlId"
      :model-value="String(field.inputValue ?? '')"
      :required="field.required"
      :invalid="field.invalid"
      :described-by="describedBy"
      :placeholder="placeholder"
      :options="(field.selectionOptions || []).map((option) => ({ value: option.value, label: option.label }))"
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
    <textarea
      v-else-if="field.type === 'text' || field.type === 'html'"
      :id="controlId"
      :value="String(field.inputValue ?? '')"
      class="professional-base-field-control__textarea"
      :aria-required="field.required || undefined"
      :aria-invalid="field.invalid || undefined"
      :aria-describedby="describedBy"
      :placeholder="placeholder"
      rows="4"
      @input="emitValue(($event.target as HTMLTextAreaElement).value)"
    />
    <ScInput
      v-else
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
import { computed } from 'vue';
import ScDateField from '../design-system/ScDateField.vue';
import ScInput from '../design-system/ScInput.vue';
import ScSelect from '../design-system/ScSelect.vue';
import { formatDisplayValue } from '../../utils/display';
import { sanitizeReadonlyHtml } from '../../utils/sanitizeReadonlyHtml';
import type { FormSectionFieldSchema } from '../template/formSection.types';
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

function emitValue(value: string | number | boolean | null) {
  emit('update:value', value);
}
</script>

<style scoped>
.professional-base-field-control,
.professional-base-field-control :deep(.sc-input) {
  width: 100%;
}

.professional-base-field-control :deep(.sc-input) {
  box-sizing: border-box;
  height: calc(var(--sc-component-input-height-md) * 1px);
  min-height: calc(var(--sc-component-input-height-md) * 1px);
  padding-inline: calc(var(--sc-component-input-padding-x) * 1px);
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

.professional-base-field-control[data-professional-field-type='integer'] :deep(.sc-input),
.professional-base-field-control[data-professional-field-type='float'] :deep(.sc-input),
.professional-base-field-control[data-professional-field-type='integer'] .professional-base-field-control__readonly,
.professional-base-field-control[data-professional-field-type='float'] .professional-base-field-control__readonly {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.professional-base-field-control[data-professional-field-type='date'] :deep(.sc-input),
.professional-base-field-control[data-professional-field-type='datetime'] :deep(.sc-input),
.professional-base-field-control[data-professional-field-type='date'] .professional-base-field-control__readonly,
.professional-base-field-control[data-professional-field-type='datetime'] .professional-base-field-control__readonly {
  font-variant-numeric: tabular-nums;
}
</style>
