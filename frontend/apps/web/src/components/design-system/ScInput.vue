<template>
  <input
    class="sc-input"
    data-semantic-component="ScInput"
    data-semantic-layer="primitive"
    :data-size="normalizePrimitiveSize(size)"
    :data-status="status"
    :data-loading="loading || undefined"
    :value="modelValue"
    :type="type"
    :disabled="disabled || loading"
    :readonly="readonly"
    :placeholder="placeholder"
    :aria-busy="loading || undefined"
    :aria-describedby="describedBy"
    :aria-invalid="status === 'error' || undefined"
    @input="onInput"
    @change="onChange"
    @focus="onFocus"
    @blur="onBlur"
  />
</template>

<script setup lang="ts">
import { normalizePrimitiveSize, resolvePrimitiveControlUpdate, type ScPrimitiveSize, type ScPrimitiveStatus } from './primitiveAdapter';

const props = withDefaults(defineProps<{
  modelValue?: string | number;
  size?: ScPrimitiveSize;
  status?: ScPrimitiveStatus;
  disabled?: boolean;
  readonly?: boolean;
  loading?: boolean;
  type?: 'text' | 'search' | 'number' | 'url' | 'tel' | 'password' | 'email' | 'date' | 'datetime-local' | 'time';
  placeholder?: string;
  describedBy?: string;
}>(), {
  modelValue: '',
  size: 'medium',
  status: 'default',
  type: 'text',
  placeholder: undefined,
  describedBy: undefined,
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
  input: [value: string, event: Event];
  change: [value: string, event: Event];
  focus: [value: string | number, event: FocusEvent];
  blur: [value: string | number, event: FocusEvent];
}>();

function eventValue(event: Event): string | null {
  return resolvePrimitiveControlUpdate({
    value: (event.target as HTMLInputElement).value,
    disabled: props.disabled,
    readonly: props.readonly,
    loading: props.loading,
  });
}
function onInput(event: Event) {
  const value = eventValue(event);
  if (value === null) return;
  emit('update:modelValue', value);
  emit('input', value, event);
}
function onChange(event: Event) {
  const value = eventValue(event);
  if (value !== null) emit('change', value, event);
}
function onFocus(event: FocusEvent) {
  emit('focus', props.modelValue, event);
}
function onBlur(event: FocusEvent) {
  emit('blur', props.modelValue, event);
}
</script>
