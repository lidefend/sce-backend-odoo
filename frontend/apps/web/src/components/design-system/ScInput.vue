<template>
  <TDesignInput
    v-if="usesTDesignDriver"
    ref="tdesignInputRef"
    v-native-control-projection="nativeProjection"
    class="sc-input"
    data-semantic-component="ScInput"
    data-semantic-layer="primitive"
    :data-size="normalizePrimitiveSize(size)"
    :data-status="status"
    :data-loading="loading || undefined"
    data-primitive-driver="tdesign"
    :model-value="modelValue"
    :type="tdesignType"
    :disabled="disabled || loading"
    :readonly="readonly"
    :placeholder="placeholder"
    :aria-busy="loading || undefined"
    :aria-describedby="describedBy"
    :aria-invalid="status === 'error' || undefined"
    :min="min"
    :max="max"
    :step="step"
    @update:model-value="onTDesignInput"
    @change="onTDesignChange"
    @focus="onTDesignFocus"
    @blur="onTDesignBlur"
  />
  <input
    v-else
    ref="inputRef"
    class="sc-input"
    data-semantic-component="ScInput"
    data-semantic-layer="primitive"
    data-primitive-driver="browser-specialized"
    :data-size="normalizePrimitiveSize(size)"
    :data-status="status"
    :data-loading="loading || undefined"
    :value="modelValue"
    :type="type"
    :disabled="disabled || loading"
    :readonly="readonly"
    :required="required"
    :min="min"
    :max="max"
    :step="step"
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
import { computed, ref } from 'vue';
import { TDesignInput } from './tdesignPrimitiveBridge';
import { nativeControlProjection } from './nativeControlProjection';
import { normalizePrimitiveSize, resolvePrimitiveControlUpdate, type ScPrimitiveSize, type ScPrimitiveStatus } from './primitiveAdapter';

const inputRef = ref<HTMLInputElement | null>(null);
const tdesignInputRef = ref<{ focus?: () => void } | null>(null);
const vNativeControlProjection = nativeControlProjection;

const props = withDefaults(defineProps<{
  modelValue?: string | number;
  size?: ScPrimitiveSize;
  status?: ScPrimitiveStatus;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  loading?: boolean;
  type?: 'text' | 'search' | 'number' | 'url' | 'tel' | 'password' | 'email' | 'date' | 'datetime-local' | 'time';
  placeholder?: string;
  describedBy?: string;
  min?: string | number;
  max?: string | number;
  step?: string | number;
}>(), {
  modelValue: '',
  size: 'medium',
  status: 'default',
  type: 'text',
  placeholder: undefined,
  describedBy: undefined,
  min: undefined,
  max: undefined,
  step: undefined,
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
  input: [value: string, event: Event];
  change: [value: string, event: Event];
  focus: [value: string | number, event: FocusEvent];
  blur: [value: string | number, event: FocusEvent];
}>();

const usesTDesignDriver = computed(() => ['text', 'search', 'number', 'url', 'tel', 'password'].includes(props.type));
const tdesignType = computed(() => usesTDesignDriver.value ? props.type as 'text' | 'search' | 'number' | 'url' | 'tel' | 'password' : 'text');
const nativeProjection = computed(() => ({
  selector: 'input' as const,
  attributes: {
    required: props.required,
    'aria-busy': props.loading || undefined,
    'aria-describedby': props.describedBy,
    'aria-invalid': props.status === 'error' || undefined,
    min: props.min,
    max: props.max,
    step: props.step,
  },
}));

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

function tdesignEvent(context: unknown): Event {
  const event = (context as { e?: Event } | undefined)?.e;
  return event instanceof Event ? event : new Event('input');
}
function onTDesignInput(value: string | number, context?: unknown) {
  const next = resolvePrimitiveControlUpdate({ value, disabled: props.disabled, readonly: props.readonly, loading: props.loading });
  if (next === null) return;
  emit('update:modelValue', next);
  emit('input', next, tdesignEvent(context));
}
function onTDesignChange(value: string | number, context?: unknown) {
  const next = resolvePrimitiveControlUpdate({ value, disabled: props.disabled, readonly: props.readonly, loading: props.loading });
  if (next !== null) emit('change', next, tdesignEvent(context));
}
function onTDesignFocus(value: string | number, context: { e?: FocusEvent }) {
  emit('focus', value, context?.e ?? new FocusEvent('focus'));
}
function onTDesignBlur(value: string | number, context: { e?: FocusEvent }) {
  emit('blur', value, context?.e ?? new FocusEvent('blur'));
}

defineExpose({
  focus: () => usesTDesignDriver.value ? tdesignInputRef.value?.focus?.() : inputRef.value?.focus(),
});
</script>
