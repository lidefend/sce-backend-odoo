<template>
  <TDesignDatePicker
    ref="dateRef"
    v-native-control-projection="nativeProjection"
    data-semantic-component="ScDateField" data-semantic-primitive="ScDateField"
    data-semantic-driver="tdesign-date-picker"
    data-semantic-layer="primitive"
    data-focus-ring-owner="component"
    :data-appearance="appearance"
    :value="modelValue"
    :name="name"
    :data-size="size"
    :disabled="disabled || loading"
    :readonly="readonly"
    :clearable="clearable"
    :enable-time-picker="withTime"
    :aria-invalid="invalid || undefined"
    :aria-busy="loading || undefined"
    :aria-describedby="describedBy"
    @change="onChange"
  />
</template>
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, onUpdated, ref } from 'vue';
import { TDesignDatePicker } from './tdesignPrimitiveBridge';
import { nativeControlProjection } from './nativeControlProjection';
import type { ScPrimitiveSize } from './primitiveAdapter';

const props = withDefaults(defineProps<{
  id?: string;
  name?: string;
  modelValue: string;
  withTime?: boolean;
  size?: ScPrimitiveSize;
  loading?: boolean;
  readonly?: boolean;
  disabled?: boolean;
  clearable?: boolean;
  required?: boolean;
  invalid?: boolean;
  describedBy?: string;
  ariaLabel?: string;
  appearance?: 'default' | 'form-field';
}>(), {
  id: undefined,
  name: undefined,
  size: 'medium',
  loading: false,
  withTime: false,
  readonly: false,
  disabled: false,
  clearable: false,
  required: false,
  invalid: false,
  describedBy: undefined,
  ariaLabel: undefined,
  appearance: 'default',
});
const vNativeControlProjection = nativeControlProjection;
const nativeProjection = computed(() => ({
  selector: 'input' as const,
  attributes: {
    id: props.id,
    name: props.name,
    required: props.required,
    'aria-required': props.required ? 'true' : undefined,
    'aria-invalid': props.invalid ? 'true' : undefined,
    'aria-describedby': props.describedBy,
    'aria-label': props.ariaLabel,
  },
}));
const dateRef = ref<{ $el?: unknown; focus?: (options?: Parameters<HTMLElement['focus']>[0]) => void } | null>(null);
let nativeInput: HTMLInputElement | null = null;
const emit = defineEmits<{
  'update:modelValue': [value: string];
  change: [value: string, event: Event];
  focus: [value: string, event: FocusEvent];
  blur: [value: string, event: FocusEvent];
  keydown: [event: KeyboardEvent];
  keyup: [event: KeyboardEvent];
}>();
function nativeEvent(context: unknown): Event | undefined {
  const event = (context as { e?: unknown } | undefined)?.e;
  return event instanceof Event ? event : undefined;
}
function onChange(value: unknown, context?: unknown) {
  const next = String(value ?? '');
  const event = nativeEvent(context);
  if (!event) return;
  emit('update:modelValue', next);
  emit('change', next, event);
}
function resolveNativeInput(): HTMLInputElement | null {
  const byId = props.id && typeof document !== 'undefined' ? document.getElementById(props.id) : null;
  if (byId instanceof HTMLInputElement) return byId;
  const root = dateRef.value?.$el;
  const container = root instanceof Node ? (root instanceof Element ? root : root.parentElement) : null;
  return container instanceof HTMLInputElement
    ? container
    : container?.querySelector<HTMLInputElement>('input') ?? null;
}
function onFocus(event: FocusEvent) {
  emit('focus', props.modelValue, event);
}
function onBlur(event: FocusEvent) {
  emit('blur', props.modelValue, event);
}
function onKeydown(event: KeyboardEvent) {
  emit('keydown', event);
}
function onKeyup(event: KeyboardEvent) {
  emit('keyup', event);
}
function unbindNativeInput() {
  if (!nativeInput) return;
  nativeInput.removeEventListener('focus', onFocus);
  nativeInput.removeEventListener('blur', onBlur);
  nativeInput.removeEventListener('keydown', onKeydown);
  nativeInput.removeEventListener('keyup', onKeyup);
  nativeInput = null;
}
function bindNativeInput() {
  const target = resolveNativeInput();
  if (target === nativeInput) return;
  unbindNativeInput();
  nativeInput = target;
  nativeInput?.addEventListener('focus', onFocus);
  nativeInput?.addEventListener('blur', onBlur);
  nativeInput?.addEventListener('keydown', onKeydown);
  nativeInput?.addEventListener('keyup', onKeyup);
}
onMounted(() => nextTick(bindNativeInput));
onUpdated(bindNativeInput);
onBeforeUnmount(unbindNativeInput);
defineExpose({
  focus: (options?: Parameters<HTMLElement['focus']>[0]) => {
    resolveNativeInput()?.focus(options);
  },
});
</script>

<style scoped>
[data-semantic-component='ScDateField'] { width: 100%; }
</style>
