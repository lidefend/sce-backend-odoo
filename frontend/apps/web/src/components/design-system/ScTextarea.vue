<template>
  <textarea
    class="sc-input sc-textarea"
    data-semantic-component="ScTextarea"
    data-semantic-layer="primitive"
    :data-size="normalizePrimitiveSize(size)"
    :data-status="status"
    :data-loading="loading || undefined"
    :value="modelValue"
    :rows="rows"
    :disabled="disabled || loading"
    :readonly="readonly"
    :required="required"
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
  modelValue?: string;
  rows?: number;
  size?: ScPrimitiveSize;
  status?: ScPrimitiveStatus;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  loading?: boolean;
  placeholder?: string;
  describedBy?: string;
}>(), {
  modelValue: '',
  rows: 3,
  size: 'medium',
  status: 'default',
  placeholder: undefined,
  describedBy: undefined,
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
  input: [value: string, event: Event];
  change: [value: string, event: Event];
  focus: [value: string, event: FocusEvent];
  blur: [value: string, event: FocusEvent];
}>();

function eventValue(event: Event): string | null {
  return resolvePrimitiveControlUpdate({
    value: (event.target as HTMLTextAreaElement).value,
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

<style scoped>
.sc-textarea {
  min-height: calc(var(--sc-component-input-height-md) * 2px);
  padding-block: var(--sc-space-sm);
  resize: vertical;
}
</style>
