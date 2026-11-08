<template>
  <ScTextarea
    :id="id"
    ref="textareaRef"
    :name="name"
    :model-value="modelValue"
    :rows="rows"
    :max-rows="maxRows"
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
import { onBeforeUnmount, onMounted, ref } from 'vue';
import type {
  NoPortSlots,
  PrimitiveEventSource,
  PrimitiveHandle,
  TextareaPortEmits,
  TextareaPortProps,
} from '@sc/ui/primitive-port';
import ScTextarea from '../ScTextarea.vue';

const props = withDefaults(defineProps<TextareaPortProps>(), {
  placeholder: undefined,
  rows: 3,
  maxRows: undefined,
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
const emit = defineEmits<TextareaPortEmits>();
defineSlots<NoPortSlots>();

const textareaRef = ref<{ $el?: unknown } | null>(null);
let lastSource: PrimitiveEventSource = 'programmatic';
let lastEditSource: PrimitiveEventSource = 'programmatic';
let lastValue = '';
let committedValue = '';
let nativeTextarea: HTMLTextAreaElement | null = null;
let lastNativeInputEvent: Event | undefined;

function resolveNativeTextarea(): HTMLTextAreaElement | null {
  const root = textareaRef.value?.$el;
  const container = root instanceof Node ? (root instanceof Element ? root : root.parentElement) : null;
  return container instanceof HTMLTextAreaElement
    ? container
    : container?.querySelector<HTMLTextAreaElement>('textarea') ?? null;
}
function sourceFor(event: Event): PrimitiveEventSource {
  return event.isTrusted ? lastSource : 'programmatic';
}
function eventValue(event: Event): string {
  return event.target instanceof HTMLTextAreaElement
    ? event.target.value
    : nativeTextarea?.value ?? String(props.modelValue ?? '');
}
function blockEdit(): boolean {
  return props.disabled || props.readonly || props.loading;
}
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
  if (value === lastValue) return;
  lastEditSource = sourceFor(event);
  lastValue = value;
  emit('update:modelValue', value);
  emit('input', value, { source: lastEditSource, nativeEvent: event });
}
function commitValue(event: Event) {
  const value = lastValue || eventValue(event);
  if (value === committedValue) return;
  committedValue = value;
  emit('change', value, { source: lastEditSource, nativeEvent: event });
}
function onNativeChange(event: Event) {
  if (blockEdit()) return;
  lastValue = eventValue(event);
  commitValue(event);
}
function onNativeFocus(event: FocusEvent) {
  const value = eventValue(event);
  lastSource = 'programmatic';
  lastEditSource = 'programmatic';
  lastValue = value;
  committedValue = value;
  emit('focus', value, { source: 'programmatic', nativeEvent: event });
}
function onNativeBlur(event: FocusEvent) {
  emit('blur', lastValue, { source: sourceFor(event), nativeEvent: event });
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
function unbindNativeTextarea() {
  if (!nativeTextarea) return;
  nativeTextarea.removeEventListener('pointerdown', onNativePointerdown);
  nativeTextarea.removeEventListener('keydown', onNativeKeydown);
  nativeTextarea.removeEventListener('keyup', onNativeKeyup);
  nativeTextarea.removeEventListener('input', onNativeInput, true);
  nativeTextarea.removeEventListener('change', onNativeChange);
  nativeTextarea.removeEventListener('focus', onNativeFocus);
  nativeTextarea.removeEventListener('blur', onNativeBlur);
  nativeTextarea.removeEventListener('compositionstart', onNativeCompositionStart);
  nativeTextarea.removeEventListener('compositionupdate', onNativeCompositionUpdate);
  nativeTextarea.removeEventListener('compositionend', onNativeCompositionEnd);
  nativeTextarea = null;
  lastNativeInputEvent = undefined;
}
function bindNativeTextarea() {
  const target = resolveNativeTextarea();
  if (target === nativeTextarea) return;
  unbindNativeTextarea();
  nativeTextarea = target;
  nativeTextarea?.addEventListener('pointerdown', onNativePointerdown);
  nativeTextarea?.addEventListener('keydown', onNativeKeydown);
  nativeTextarea?.addEventListener('keyup', onNativeKeyup);
  nativeTextarea?.addEventListener('input', onNativeInput, true);
  nativeTextarea?.addEventListener('change', onNativeChange);
  nativeTextarea?.addEventListener('focus', onNativeFocus);
  nativeTextarea?.addEventListener('blur', onNativeBlur);
  nativeTextarea?.addEventListener('compositionstart', onNativeCompositionStart);
  nativeTextarea?.addEventListener('compositionupdate', onNativeCompositionUpdate);
  nativeTextarea?.addEventListener('compositionend', onNativeCompositionEnd);
}
onMounted(bindNativeTextarea);
onBeforeUnmount(unbindNativeTextarea);

function focus(options?: Parameters<PrimitiveHandle['focus']>[0]) {
  resolveNativeTextarea()?.focus(options);
}

defineExpose({ focus });
</script>
