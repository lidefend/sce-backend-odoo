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
    :data-readonly="readonly || undefined"
    :data-disabled="disabled || loading || undefined"
    :data-appearance="appearance"
    data-primitive-driver="tdesign"
    :model-value="modelValue"
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
  >
    <template v-if="$slots.prefix" #prefixIcon><slot name="prefix" /></template>
    <template v-if="$slots.suffix" #suffixIcon><slot name="suffix" /></template>
  </TDesignInput>
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
const tdesignInputRef = ref<{ $el?: HTMLElement } | null>(null);
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
  modelValue: '',
  size: 'medium',
  status: 'default',
  type: 'text',
  placeholder: undefined,
  describedBy: undefined,
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
function onTDesignKeydown(_value: string | number, context: { e?: KeyboardEvent }) {
  emit('keydown', context?.e ?? new KeyboardEvent('keydown'));
}
function onTDesignKeyup(_value: string | number, context: { e?: KeyboardEvent }) {
  emit('keyup', context?.e ?? new KeyboardEvent('keyup'));
}

defineExpose({
  focus: () => {
    if (!usesTDesignDriver.value) return inputRef.value?.focus();
    return tdesignInputRef.value?.$el?.querySelector<HTMLInputElement>('input')?.focus();
  },
});
</script>
