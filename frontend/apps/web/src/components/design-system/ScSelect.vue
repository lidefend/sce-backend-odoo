<template>
  <TDesignSelect
    ref="selectRef"
    v-native-control-projection="nativeProjection"
    class="sc-select"
    data-semantic-component="ScSelect" data-semantic-primitive="ScSelect"
    data-semantic-layer="primitive"
    data-focus-ring-owner="component"
    data-primitive-driver="tdesign"
    :data-option-count="tdesignOptions.length"
    :data-size="size"
    :data-status="status"
    :data-readonly="readonly || undefined"
    :data-appearance="appearance"
    :model-value="modelValue"
    :name="name"
    :options="tdesignOptions"
    :input-props="{ inputClass: `sc-select__control sc-select__control--${appearance}` }"
    :size="size"
    :status="invalid ? 'error' : status"
    :disabled="disabled"
    :readonly="readonly"
    :filterable="filterable"
    :loading="loading"
    :empty="emptyText"
    :reserve-keyword="false"
    :placeholder="placeholder"
    :aria-disabled="disabled || undefined"
    :aria-readonly="readonly || undefined"
    :aria-invalid="invalid || status === 'error' || undefined"
    :aria-describedby="describedBy"
    @change="onChange"
    @search="onSearch"
    @focus="onFocus"
    @blur="onBlur"
    @keydown="onKeydown"
    @keyup="onKeyup"
    @popup-visible-change="onPopupVisibleChange"
  />
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { TDesignSelect } from './tdesignPrimitiveBridge';
import { nativeControlProjection } from './nativeControlProjection';
import {
  resolvePrimitiveControlUpdate,
  resolvePrimitiveNativeEvent,
  selectPopupVisibilityEvent,
  type ScPrimitiveSize,
  type ScPrimitiveStatus,
} from './primitiveAdapter';

export interface ScSelectOption {
  value: string | number;
  label: string;
  disabled?: boolean;
}

const props = withDefaults(defineProps<{
  id?: string;
  name?: string;
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
  ariaLabel?: string;
  filterable?: boolean;
  loading?: boolean;
  emptyText?: string;
  appearance?: 'default' | 'form-field';
}>(), {
  id: undefined,
  name: undefined,
  options: () => [],
  placeholder: undefined,
  size: 'medium',
  status: 'default',
  describedBy: undefined,
  ariaLabel: undefined,
  appearance: 'default',
  filterable: false,
  loading: false,
  emptyText: undefined,
});
const emit = defineEmits<{
  'update:modelValue': [value: string];
  change: [value: string, event: Event];
  search: [value: string, event: Event];
  focus: [value: string, event: FocusEvent];
  blur: [value: string, event: FocusEvent];
  keydown: [event: KeyboardEvent];
  keyup: [event: KeyboardEvent];
  'popup-visible-change': [event: { visible: boolean; trigger: string }, nativeEvent: Event];
}>();
const selectRef = ref<{ focus?: () => void; $el?: HTMLElement } | null>(null);
let lastSearchValue: string | undefined;
let nativeInput: HTMLInputElement | null = null;
function onNativeSearch(event: Event) {
  if (event.target instanceof HTMLInputElement) emitSearchValue(event.target.value, event);
}
function bindNativeSearch() {
  const root = selectRef.value?.$el;
  const input = root instanceof HTMLInputElement ? root : root?.querySelector<HTMLInputElement>('input') ?? null;
  if (input === nativeInput) return;
  nativeInput?.removeEventListener('input', onNativeSearch);
  nativeInput = input;
  nativeInput?.addEventListener('input', onNativeSearch);
}
onMounted(bindNativeSearch);
onBeforeUnmount(() => nativeInput?.removeEventListener('input', onNativeSearch));
const vNativeControlProjection = nativeControlProjection;
const tdesignOptions = computed(() => props.options.map((option) => ({
  value: option.value,
  label: option.label,
  disabled: Boolean(option.disabled),
})));
const nativeProjection = computed(() => ({
  selector: 'input' as const,
  attributes: {
    id: props.id,
    name: props.name,
    required: props.required,
    'aria-readonly': props.readonly || undefined,
    'aria-required': props.required || undefined,
    'aria-invalid': props.invalid || props.status === 'error' || undefined,
    'aria-describedby': props.describedBy,
    'aria-label': props.ariaLabel,
  },
}));

function onChange(nextValue: unknown, context?: unknown) {
  const value = resolvePrimitiveControlUpdate({ value: nextValue, disabled: props.disabled, readonly: props.readonly });
  if (value === null) return;
  const event = resolvePrimitiveNativeEvent(context);
  if (!(event instanceof Event)) return;
  emit('update:modelValue', value);
  emit('change', value, event);
}

function emitSearchValue(value: unknown, event: Event) {
  const normalized = String(value || '');
  if (lastSearchValue === normalized) return;
  lastSearchValue = normalized;
  emit('search', normalized, event);
}

function onSearch(value: unknown, context?: unknown) {
  const event = resolvePrimitiveNativeEvent(context);
  if (event instanceof Event) emitSearchValue(value, event);
}

function onPopupVisibleChange(visible: unknown, context?: { trigger?: string; e?: Event }) {
  const event = resolvePrimitiveNativeEvent(context);
  if (event instanceof Event) {
    emit('popup-visible-change', selectPopupVisibilityEvent(visible, context?.trigger), event);
  }
}

function onFocus(context: { value: unknown; e: FocusEvent | KeyboardEvent }) {
  if (context.e instanceof FocusEvent) emit('focus', String(context.value ?? ''), context.e);
}
function onBlur(context: { value: unknown; e: FocusEvent | KeyboardEvent }) {
  if (context.e instanceof FocusEvent) emit('blur', String(context.value ?? ''), context.e);
}
function onKeydown(event: KeyboardEvent) {
  emit('keydown', event);
}
function onKeyup(event: KeyboardEvent) {
  emit('keyup', event);
}

defineExpose({
  focus: (options?: Parameters<HTMLElement['focus']>[0]) => (
    selectRef.value?.focus?.() ?? selectRef.value?.$el?.querySelector('input')?.focus(options)
  ),
});
</script>
