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
import { normalizePrimitiveSize, type ScPrimitiveSize, type ScPrimitiveStatus } from './primitiveAdapter';

const props = withDefaults(defineProps<{
  modelValue?: string | number;
  size?: ScPrimitiveSize;
  status?: ScPrimitiveStatus;
  disabled?: boolean;
  readonly?: boolean;
  loading?: boolean;
  type?: 'text' | 'search' | 'number' | 'url' | 'tel' | 'password';
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

function eventValue(event: Event): string {
  return (event.target as HTMLInputElement).value;
}
function onInput(event: Event) {
  const value = eventValue(event);
  emit('update:modelValue', value);
  emit('input', value, event);
}
function onChange(event: Event) {
  emit('change', eventValue(event), event);
}
function onFocus(event: FocusEvent) {
  emit('focus', props.modelValue, event);
}
function onBlur(event: FocusEvent) {
  emit('blur', props.modelValue, event);
}
</script>
