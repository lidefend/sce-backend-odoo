<template>
  <div
    class="professional-business-value"
    data-professional-field-family="business-value"
    :data-business-value-kind="kind"
    :data-presentation-mode="field.presentationMode"
    :data-render-profile="field.renderProfile"
    :data-control-state="field.readonly ? 'readonly' : 'editable'"
  >
    <template v-if="field.readonly">
      <ScMoney v-if="kind === 'sc.value.money'" :display="moneyDisplay" :label="field.label" />
      <ScStatusBadge
        v-else-if="kind === 'sc.display.status'"
        :value="String(field.inputValue ?? field.value ?? '')"
        :label="displayText"
        :semantic="statusSemantic(field.inputValue ?? field.value)"
      />
      <span v-else class="professional-business-value__readonly">{{ displayText }}</span>
    </template>
    <ScSelect
      v-else-if="isChoice"
      :id="controlId"
      :model-value="String(field.inputValue ?? '')"
      :disabled="field.readonly"
      :status="field.invalid ? 'error' : 'default'"
      @update:model-value="$emit('update:value', $event)"
    >
      <option value="">{{ placeholder || '请选择' }}</option>
      <option v-for="option in choiceOptions" :key="String(option.value)" :value="option.value">{{ option.label }}</option>
    </ScSelect>
    <ScInput
      v-else
      :id="controlId"
      :model-value="inputModelValue"
      :type="numeric ? 'number' : 'text'"
      :step="inputStep"
      :placeholder="placeholder"
      :disabled="field.readonly"
      :status="field.invalid ? 'error' : 'default'"
      @update:model-value="$emit('update:value', numeric ? numericValue($event) : $event)"
    />
    <span v-if="!field.readonly && suffix" class="professional-business-value__suffix">{{ suffix }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import ScInput from '../design-system/ScInput.vue';
import ScMoney from '../design-system/ScMoney.vue';
import ScSelect from '../design-system/ScSelect.vue';
import ScStatusBadge from '../design-system/ScStatusBadge.vue';
import { formatMonetaryDisplayValue, monetaryInputStep } from '../template/formSection.mapper';
import type { FormSectionFieldSchema } from '../template/formSection.types';
import {
  businessValueKind,
  formatDuration,
  formatPercentage,
  statusSemantic,
} from './professionalBusinessValueModel';

const props = defineProps<{
  field: FormSectionFieldSchema;
  controlId: string;
  placeholder?: string;
}>();

defineEmits<{ 'update:value': [value: string | number | boolean | null] }>();

const kind = computed(() => businessValueKind(props.field));
const isChoice = computed(() => ['sc.value.currency', 'sc.display.status', 'sc.value.user', 'sc.value.company'].includes(kind.value));
const numeric = computed(() => ['sc.value.money', 'sc.value.percentage', 'sc.value.duration'].includes(kind.value));
const inputModelValue = computed(() => typeof props.field.inputValue === 'boolean' ? String(props.field.inputValue) : props.field.inputValue ?? '');
const choiceOptions = computed(() => props.field.relationOptions?.length ? props.field.relationOptions : props.field.selectionOptions || []);
const inputStep = computed(() => kind.value === 'sc.value.money' ? monetaryInputStep(props.field.digits) : 'any');
const suffix = computed(() => {
  if (kind.value === 'sc.value.money') return props.field.currencyLabel || '';
  if (kind.value === 'sc.value.percentage') return '%';
  if (kind.value === 'sc.value.duration') return '小时';
  return '';
});
const moneyDisplay = computed(() => formatMonetaryDisplayValue(props.field.value, props.field.digits, props.field.currencyLabel));
const displayText = computed(() => {
  const value = props.field.value;
  if (kind.value === 'sc.value.percentage') return formatPercentage(value);
  if (kind.value === 'sc.value.duration') return formatDuration(value);
  if (kind.value === 'sc.display.status') {
    const selected = props.field.selectionOptions?.find((option) => String(option.value) === String(props.field.inputValue ?? value));
    return selected?.label || String(value ?? '—');
  }
  return String(value ?? '—') || '—';
});

function numericValue(value: string | number): number | null {
  if (value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
</script>

<style scoped>
.professional-business-value { align-items: center; display: flex; gap: var(--sc-space-2); min-width: 0; width: 100%; }
.professional-business-value__readonly { color: var(--sc-app-text-primary); font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.professional-business-value__suffix { color: var(--sc-app-text-secondary); flex: 0 0 auto; font-size: var(--sc-product-text-sm); }
</style>
