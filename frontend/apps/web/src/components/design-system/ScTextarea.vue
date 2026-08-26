<template>
  <TDesignTextarea
    ref="textareaRef"
    v-native-control-projection="nativeProjection"
    class="sc-input sc-textarea"
    data-semantic-component="ScTextarea"
    data-semantic-layer="primitive"
    :data-size="normalizePrimitiveSize(size)"
    :data-status="status"
    :data-loading="loading || undefined"
    data-primitive-driver="tdesign"
    :model-value="modelValue"
    :autosize="{ minRows: rows }"
    :disabled="disabled || loading"
    :readonly="readonly"
    :placeholder="placeholder"
    :aria-busy="loading || undefined"
    :aria-describedby="describedBy"
    :aria-invalid="status === 'error' || undefined"
    @update:model-value="onTDesignInput"
    @change="onTDesignChange"
    @focus="onTDesignFocus"
    @blur="onTDesignBlur"
  ></TDesignTextarea>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { TDesignTextarea } from './tdesignPrimitiveBridge';
import { nativeControlProjection } from './nativeControlProjection';
import { normalizePrimitiveSize, resolvePrimitiveControlUpdate, type ScPrimitiveSize, type ScPrimitiveStatus } from './primitiveAdapter';

const textareaRef = ref<{ focus?: () => void } | null>(null);
const vNativeControlProjection = nativeControlProjection;

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

const nativeProjection = computed(() => ({
  selector: 'textarea' as const,
  attributes: {
    required: props.required,
    'aria-busy': props.loading || undefined,
    'aria-describedby': props.describedBy,
    'aria-invalid': props.status === 'error' || undefined,
  },
}));

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

function eventFrom(context: unknown, name: string): Event {
  const event = (context as { e?: Event } | undefined)?.e;
  return event instanceof Event ? event : new Event(name);
}
function onTDesignInput(value: string | number, context?: unknown) {
  const next = resolvePrimitiveControlUpdate({ value, disabled: props.disabled, readonly: props.readonly, loading: props.loading });
  if (next === null) return;
  emit('update:modelValue', next);
  emit('input', next, eventFrom(context, 'input'));
}
function onTDesignChange(value: string | number, context?: unknown) {
  const next = resolvePrimitiveControlUpdate({ value, disabled: props.disabled, readonly: props.readonly, loading: props.loading });
  if (next !== null) emit('change', next, eventFrom(context, 'change'));
}
function onTDesignFocus(value: string | number, context: { e?: FocusEvent }) {
  emit('focus', String(value ?? ''), context?.e ?? new FocusEvent('focus'));
}
function onTDesignBlur(value: string | number, context: { e?: FocusEvent }) {
  emit('blur', String(value ?? ''), context?.e ?? new FocusEvent('blur'));
}

defineExpose({ focus: () => textareaRef.value?.focus?.() });
</script>

<style scoped>
.sc-textarea :deep(textarea) {
  min-height: calc(var(--sc-component-input-height-md) * 2px);
  padding-block: var(--sc-space-sm);
  resize: vertical;
}
</style>
