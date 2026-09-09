<template>
  <TDesignSelect
    ref="selectRef"
    v-native-control-projection="nativeProjection"
    class="sc-select"
    data-semantic-component="ScSelect"
    data-semantic-layer="primitive"
    data-focus-ring-owner="component"
    data-primitive-driver="tdesign"
    :data-size="size"
    :data-status="status"
    :data-readonly="readonly || undefined"
    :data-appearance="appearance"
    :model-value="modelValue"
    :options="tdesignOptions"
    :size="size"
    :status="invalid ? 'error' : status"
    :disabled="disabled"
    :readonly="readonly"
    :filterable="filterable"
    :input-value="filterable ? searchValue : undefined"
    :loading="loading"
    :empty="emptyText"
    :reserve-keyword="false"
    :placeholder="placeholder"
    :aria-disabled="disabled || undefined"
    :aria-readonly="readonly || undefined"
    :aria-required="required || undefined"
    :aria-invalid="invalid || status === 'error' || undefined"
    :aria-describedby="describedBy"
    @change="onChange"
    @input-change="onInputChange"
    @search="onInputChange"
    @popup-visible-change="emit('popup-visible-change', Boolean($event))"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { TDesignSelect } from './tdesignPrimitiveBridge';
import { nativeControlProjection } from './nativeControlProjection';
import { resolvePrimitiveControlUpdate, type ScPrimitiveSize, type ScPrimitiveStatus } from './primitiveAdapter';

export interface ScSelectOption {
  value: string | number;
  label: string;
  disabled?: boolean;
}

const props = withDefaults(defineProps<{
  modelValue: string | number;
  options?: readonly ScSelectOption[];
  placeholder?: string;
  size?: ScPrimitiveSize;
  status?: ScPrimitiveStatus;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  invalid?: boolean;
  describedBy?: string;
  filterable?: boolean;
  searchValue?: string;
  loading?: boolean;
  emptyText?: string;
  appearance?: 'default' | 'form-field';
}>(), {
  options: () => [],
  placeholder: undefined,
  size: 'medium',
  status: 'default',
  describedBy: undefined,
  appearance: 'default',
  filterable: false,
  searchValue: undefined,
  loading: false,
  emptyText: undefined,
});
const emit = defineEmits<{
  'update:modelValue': [value: string];
  change: [value: string];
  search: [value: string];
  'popup-visible-change': [visible: boolean];
}>();
const selectRef = ref<{ focus?: () => void; $el?: HTMLElement } | null>(null);
let lastSearchValue: string | undefined;
const vNativeControlProjection = nativeControlProjection;
const tdesignOptions = computed(() => props.options.map((option) => ({
  value: option.value,
  label: option.label,
  disabled: Boolean(option.disabled),
})));
const nativeProjection = computed(() => ({
  selector: 'input' as const,
  attributes: {
    required: props.required,
    'aria-readonly': props.readonly || undefined,
    'aria-required': props.required || undefined,
    'aria-invalid': props.invalid || props.status === 'error' || undefined,
    'aria-describedby': props.describedBy,
  },
}));

function onChange(nextValue: unknown) {
  const value = resolvePrimitiveControlUpdate({ value: nextValue, disabled: props.disabled, readonly: props.readonly });
  if (value === null) return;
  emit('update:modelValue', value);
  emit('change', value);
}

function onInputChange(value: unknown) {
  const normalized = String(value || '');
  if (lastSearchValue === normalized) return;
  lastSearchValue = normalized;
  emit('search', normalized);
}

defineExpose({ focus: () => selectRef.value?.focus?.() ?? selectRef.value?.$el?.querySelector('input')?.focus() });
</script>
