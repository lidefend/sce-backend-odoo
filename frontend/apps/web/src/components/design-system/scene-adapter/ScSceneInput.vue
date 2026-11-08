<template>
  <ScInput
    :id="id"
    ref="inputRef"
    :name="name"
    :model-value="modelValue"
    :type="type"
    :input-mode="inputMode"
    :size="size"
    :status="status"
    :disabled="disabled"
    :readonly="readonly"
    :required="required"
    :loading="loading"
    :placeholder="placeholder"
    :described-by="describedBy"
    :aria-label="ariaLabel"
  />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import type {
  InputPortEmits,
  InputPortProps,
  NoPortSlots,
  PrimitiveEventSource,
  PrimitiveHandle,
} from '@sc/ui/primitive-port';
import ScInput from '../ScInput.vue';

const props = withDefaults(defineProps<InputPortProps>(), {
  type: 'text',
  inputMode: undefined,
  placeholder: undefined,
  size: 'medium',
  status: 'default',
  disabled: false,
  readonly: false,
  required: false,
  loading: false,
  describedBy: undefined,
  ariaLabel: undefined,
  name: undefined,
  id: undefined,
});
const emit = defineEmits<InputPortEmits>();
defineSlots<NoPortSlots>();

const inputRef = ref<{ $el?: unknown } | null>(null);
let lastSource: PrimitiveEventSource = 'programmatic';
let lastEditSource: PrimitiveEventSource = 'programmatic';
let controlledValue = String(props.modelValue ?? '');
let lastEditValue = controlledValue;
let committedValue = controlledValue;
let pendingUserEcho: string | undefined;
let nativeInput: HTMLInputElement | null = null;
let lastNativeInputEvent: Event | undefined;

function resolveNativeInput(): HTMLInputElement | null {
  const root = inputRef.value?.$el;
  const container = root instanceof Node ? (root instanceof Element ? root : root.parentElement) : null;
  return container instanceof HTMLInputElement
    ? container
    : container?.querySelector<HTMLInputElement>('input') ?? null;
}

function sourceFor(event: Event): PrimitiveEventSource {
  return event.isTrusted ? lastSource : 'programmatic';
}
function eventValue(event: Event): string {
  return event.target instanceof HTMLInputElement
    ? event.target.value
    : nativeInput?.value ?? String(props.modelValue ?? '');
}
function blockEdit(): boolean {
  return props.disabled || props.readonly || props.loading;
}
watch(
  () => String(props.modelValue ?? ''),
  (value) => {
    controlledValue = value;
    if (pendingUserEcho === value) {
      pendingUserEcho = undefined;
      return;
    }
    pendingUserEcho = undefined;
    lastEditValue = value;
    committedValue = value;
  },
  { flush: 'sync' },
);
function onNativePointerdown() {
  lastSource = 'pointer';
}
function onNativeKeydown(event: KeyboardEvent) {
  lastSource = 'keyboard';
  emit('keydown', { source: 'keyboard', nativeEvent: event });
}
function onNativeKeyup(event: KeyboardEvent) {
  emit('keyup', { source: 'keyboard', nativeEvent: event });
}
function onNativeInput(event: Event) {
  if (blockEdit()) return;
  if (event === lastNativeInputEvent) return;
  lastNativeInputEvent = event;
  const value = eventValue(event);
  if (value === lastEditValue) return;
  lastEditSource = sourceFor(event);
  lastEditValue = value;
  pendingUserEcho = value;
  emit('update:modelValue', value);
  emit('input', value, { source: lastEditSource, nativeEvent: event });
}
function commitValue(event: Event) {
  const displayedValue = eventValue(event);
  const value = displayedValue === controlledValue ? displayedValue : lastEditValue;
  if (value === committedValue) return;
  committedValue = value;
  emit('change', value, { source: lastEditSource, nativeEvent: event });
}
function onNativeChange(event: Event) {
  if (blockEdit()) return;
  lastEditValue = eventValue(event);
  commitValue(event);
}
function onNativeFocus(event: FocusEvent) {
  const value = eventValue(event);
  lastSource = 'programmatic';
  lastEditSource = 'programmatic';
  controlledValue = value;
  lastEditValue = value;
  committedValue = value;
  emit('focus', value, { source: 'programmatic', nativeEvent: event });
}
function onNativeBlur(event: FocusEvent) {
  emit('blur', lastEditValue, { source: sourceFor(event), nativeEvent: event });
  commitValue(event);
}
function onNativeCompositionStart(event: CompositionEvent) {
  lastSource = 'keyboard';
  emit('compositionstart', { source: 'keyboard', nativeEvent: event });
}
function onNativeCompositionUpdate(event: CompositionEvent) {
  lastSource = 'keyboard';
  void event;
}
function onNativeCompositionEnd(event: CompositionEvent) {
  lastSource = 'keyboard';
  emit('compositionend', { source: 'keyboard', nativeEvent: event });
}
function unbindNativeInput() {
  if (!nativeInput) return;
  nativeInput.removeEventListener('pointerdown', onNativePointerdown);
  nativeInput.removeEventListener('keydown', onNativeKeydown);
  nativeInput.removeEventListener('keyup', onNativeKeyup);
  nativeInput.removeEventListener('input', onNativeInput, true);
  nativeInput.removeEventListener('change', onNativeChange);
  nativeInput.removeEventListener('focus', onNativeFocus);
  nativeInput.removeEventListener('blur', onNativeBlur);
  nativeInput.removeEventListener('compositionstart', onNativeCompositionStart);
  nativeInput.removeEventListener('compositionupdate', onNativeCompositionUpdate);
  nativeInput.removeEventListener('compositionend', onNativeCompositionEnd);
  nativeInput = null;
  lastNativeInputEvent = undefined;
}
function bindNativeInput() {
  const target = resolveNativeInput();
  if (target === nativeInput) return;
  unbindNativeInput();
  nativeInput = target;
  nativeInput?.addEventListener('pointerdown', onNativePointerdown);
  nativeInput?.addEventListener('keydown', onNativeKeydown);
  nativeInput?.addEventListener('keyup', onNativeKeyup);
  nativeInput?.addEventListener('input', onNativeInput, true);
  nativeInput?.addEventListener('change', onNativeChange);
  nativeInput?.addEventListener('focus', onNativeFocus);
  nativeInput?.addEventListener('blur', onNativeBlur);
  nativeInput?.addEventListener('compositionstart', onNativeCompositionStart);
  nativeInput?.addEventListener('compositionupdate', onNativeCompositionUpdate);
  nativeInput?.addEventListener('compositionend', onNativeCompositionEnd);
}
onMounted(bindNativeInput);
onBeforeUnmount(unbindNativeInput);

function focus(options?: Parameters<PrimitiveHandle['focus']>[0]) {
  resolveNativeInput()?.focus(options);
}

defineExpose({ focus });
</script>
