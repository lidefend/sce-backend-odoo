<template>
  <TDesignInput
    v-if="usesTDesignDriver"
    ref="tdesignInputRef"
    v-native-control-projection="nativeProjection"
    class="sc-input"
    data-semantic-component="ScInput" data-semantic-primitive="ScInput"
    data-semantic-layer="primitive"
    data-focus-ring-owner="component"
    :data-size="normalizePrimitiveSize(size)"
    :data-status="status"
    :data-loading="loading || undefined"
    :data-readonly="readonly || undefined"
    :data-disabled="disabled || loading || undefined"
    :data-appearance="appearance"
    data-primitive-driver="tdesign"
    :model-value="modelValue"
    :input-class="['sc-input__control', `sc-input__control--${appearance}`]"
    :type="tdesignType"
    :align="align"
    :size="normalizePrimitiveSize(size)"
    :status="status"
    :disabled="disabled || loading"
    :readonly="readonly"
    :placeholder="placeholder"
    :clearable="clearable"
    :autocomplete="autocomplete"
    :aria-busy="loading || undefined"
    :aria-describedby="describedBy"
    :aria-invalid="status === 'error' || undefined"
    :min="min"
    :max="max"
    :step="step"
    :minlength="minLength"
    :maxlength="maxLength"
    @update:model-value="onTDesignInput"
    @change="onTDesignChange"
    @focus="onTDesignFocus"
    @blur="onTDesignBlur"
    @keydown="onTDesignKeydown"
    @keyup="onTDesignKeyup"
    @compositionstart="onTDesignCompositionStart"
    @compositionend="onTDesignCompositionEnd"
  >
    <template v-if="$slots.prefix" #prefixIcon><slot name="prefix" /></template>
    <template v-if="$slots.suffix" #suffixIcon><slot name="suffix" /></template>
  </TDesignInput>
  <input
    v-else
    :id="id"
    ref="inputRef"
    class="sc-input"
    data-semantic-component="ScInput" data-semantic-primitive="ScInput"
    data-semantic-layer="primitive"
    data-primitive-driver="browser-specialized"
    :data-size="normalizePrimitiveSize(size)"
    :data-status="status"
    :data-loading="loading || undefined"
    :data-readonly="readonly || undefined"
    :data-disabled="disabled || loading || undefined"
    :data-appearance="appearance"
    :value="modelValue"
    :type="type"
    :disabled="disabled || loading"
    :readonly="readonly"
    :required="required"
    :min="min"
    :max="max"
    :step="step"
    :minlength="minLength"
    :maxlength="maxLength"
    :placeholder="placeholder"
    :autocomplete="autocomplete"
    :aria-busy="loading || undefined"
    :aria-describedby="describedBy"
    :aria-invalid="status === 'error' || undefined"
    :aria-label="ariaLabel"
    @input="onInput"
    @change="onChange"
    @focus="onFocus"
    @blur="onBlur"
    @compositionstart="onNativeCompositionStart"
    @compositionend="onNativeCompositionEnd"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { TDesignInput } from './tdesignPrimitiveBridge';
import { nativeControlProjection } from './nativeControlProjection';
import { normalizePrimitiveSize, resolvePrimitiveControlUpdate, resolvePrimitiveNativeEvent, type ScPrimitiveSize, type ScPrimitiveStatus } from './primitiveAdapter';

const inputRef = ref<HTMLInputElement | null>(null);
const tdesignInputRef = ref<{ $el?: HTMLElement } | null>(null);
const vNativeControlProjection = nativeControlProjection;

const props = withDefaults(defineProps<{
  id?: string;
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
  ariaLabel?: string;
  autocomplete?: string;
  min?: string | number;
  max?: string | number;
  step?: string | number;
  minLength?: number;
  maxLength?: number;
  clearable?: boolean;
  align?: 'left' | 'center' | 'right';
  appearance?: 'default' | 'navigation-search' | 'form-field' | 'record-title' | 'relation-tag-entry' | 'collection-search' | 'numeric-entry';
}>(), {
  id: undefined,
  modelValue: '',
  size: 'medium',
  status: 'default',
  type: 'text',
  placeholder: undefined,
  describedBy: undefined,
  ariaLabel: undefined,
  autocomplete: undefined,
  min: undefined,
  max: undefined,
  step: undefined,
  minLength: undefined,
  maxLength: undefined,
  clearable: false,
  align: undefined,
  appearance: 'default',
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
  input: [value: string, event: Event];
  change: [value: string, event: Event];
  focus: [value: string | number, event: FocusEvent];
  blur: [value: string | number, event: FocusEvent];
  keydown: [event: KeyboardEvent];
  keyup: [event: KeyboardEvent];
  compositionstart: [event: CompositionEvent];
  compositionend: [event: CompositionEvent];
}>();

const usesTDesignDriver = computed(() => ['text', 'search', 'number', 'url', 'tel', 'password'].includes(props.type));
const tdesignType = computed(() => usesTDesignDriver.value ? props.type as 'text' | 'search' | 'number' | 'url' | 'tel' | 'password' : 'text');
const nativeProjection = computed(() => ({
  selector: 'input' as const,
  attributes: {
    id: props.id,
    required: props.required,
    'aria-busy': props.loading || undefined,
    'aria-describedby': props.describedBy,
    'aria-invalid': props.status === 'error' || undefined,
    'aria-label': props.ariaLabel,
    min: props.min,
    max: props.max,
    step: props.step,
    autocomplete: props.autocomplete,
    minlength: props.minLength,
    maxlength: props.maxLength,
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
  return resolvePrimitiveNativeEvent(context) ?? new Event('input');
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
function onTDesignFocus(value: string | number, context?: unknown) {
  const event = resolvePrimitiveNativeEvent(context);
  emit('focus', value, event instanceof FocusEvent ? event : new FocusEvent('focus'));
}
function onTDesignBlur(value: string | number, context?: unknown) {
  const event = resolvePrimitiveNativeEvent(context);
  emit('blur', value, event instanceof FocusEvent ? event : new FocusEvent('blur'));
}
function onTDesignKeydown(_value: string | number, context?: unknown) {
  const event = resolvePrimitiveNativeEvent(context);
  emit('keydown', event instanceof KeyboardEvent ? event : new KeyboardEvent('keydown'));
}
function onTDesignKeyup(_value: string | number, context?: unknown) {
  const event = resolvePrimitiveNativeEvent(context);
  emit('keyup', event instanceof KeyboardEvent ? event : new KeyboardEvent('keyup'));
}

// IME callers commit text by reading the DOM event (`event.target.value`), so a
// `compositionend` here must carry the real `CompositionEvent`. TDesign reports
// composition through its own `(value, context)` signature and its raw `value` is
// stale at commit time, so the driver payload is resolved through the shared
// `resolvePrimitiveNativeEvent` contract instead of being re-derived locally.
function onNativeCompositionStart(event: Event) {
  if (event instanceof CompositionEvent) emit('compositionstart', event);
}
function onNativeCompositionEnd(event: Event) {
  if (event instanceof CompositionEvent) emit('compositionend', event);
}
function onTDesignCompositionStart(_value: string | number, context?: unknown) {
  const event = resolvePrimitiveNativeEvent(context);
  if (event instanceof CompositionEvent) emit('compositionstart', event);
}
function onTDesignCompositionEnd(_value: string | number, context?: unknown) {
  const event = resolvePrimitiveNativeEvent(context);
  if (event instanceof CompositionEvent) emit('compositionend', event);
}

defineExpose({
  focus: () => {
    if (!usesTDesignDriver.value) return inputRef.value?.focus();
    return tdesignInputRef.value?.$el?.querySelector<HTMLInputElement>('input')?.focus();
  },
});
</script>
