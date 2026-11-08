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
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import type {
  NoPortSlots,
  PrimitiveEventSource,
  PrimitiveHandle,
  TextareaPortEmits,
  TextareaPortProps,
} from '@sc/ui/primitive-port';
import ScTextarea from '../ScTextarea.vue';
import { createPrimitiveFocusSourceTracker } from './primitiveFocusSource';

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
const focusSourceTracker = createPrimitiveFocusSourceTracker();
let lastSource: PrimitiveEventSource = 'programmatic';
let lastEditSource: PrimitiveEventSource = 'programmatic';
let controlledValue = String(props.modelValue ?? '');
let lastEditValue = controlledValue;
let committedValue = controlledValue;
const pendingUserEchoes: string[] = [];
const supersededUserEchoes: string[] = [];
const staleUserEchoes: string[] = [];
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
function rememberStaleUserEchoes(values: string[]) {
  for (const value of values) {
    if (value && !staleUserEchoes.includes(value)) staleUserEchoes.push(value);
  }
}
function consumeUserEcho(queue: string[], value: string): boolean {
  const index = queue.indexOf(value);
  if (index >= 0) {
    // The parent may coalesce several edits and echo only the latest value.
    // That echo acknowledges every earlier value in this ordered queue.
    const removed = queue.splice(0, index + 1);
    rememberStaleUserEchoes(removed.slice(0, -1));
    return true;
  }
  let joined = '';
  for (let prefixEnd = 0; prefixEnd < queue.length; prefixEnd += 1) {
    joined += queue[prefixEnd];
    if (joined === value) {
      const removed = queue.splice(0, prefixEnd + 1);
      rememberStaleUserEchoes(removed);
      return true;
    }
  }
  return false;
}
function consumeStaleUserEcho(value: string): boolean {
  const index = staleUserEchoes.indexOf(value);
  if (index < 0) return false;
  staleUserEchoes.splice(index, 1);
  return true;
}
function currentUserAuthority(): string {
  return pendingUserEchoes[pendingUserEchoes.length - 1] ?? controlledValue;
}
function removeTrackedUserEcho(queue: string[], value: string) {
  const index = queue.indexOf(value);
  if (index >= 0) queue.splice(index, 1);
}
watch(
  () => String(props.modelValue ?? ''),
  (value) => {
    if (consumeUserEcho(pendingUserEchoes, value)) {
      controlledValue = value;
      return;
    }
    if (consumeUserEcho(supersededUserEchoes, value)) {
      const authority = currentUserAuthority();
      if (value !== authority) {
        // A delayed parent echo must not overwrite a newer external value or
        // a newer edit the user has started after that external update.
        emit('update:modelValue', authority);
      }
      return;
    }
    if (consumeStaleUserEcho(value)) {
      const authority = currentUserAuthority();
      if (value !== authority) emit('update:modelValue', authority);
      return;
    }
    if (pendingUserEchoes.length) {
      supersededUserEchoes.push(...pendingUserEchoes);
      pendingUserEchoes.splice(0);
    }
    controlledValue = value;
    lastEditValue = value;
    committedValue = value;
  },
  { flush: 'sync' },
);
function onNativePointerdown() {
  focusSourceTracker.pointer();
  lastSource = 'pointer';
}
function onNativeKeydown(event: KeyboardEvent) {
  focusSourceTracker.keyboard();
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
  // Preserve older delayed echoes, but let a new edit reclaim the same value
  // as current user intent rather than treating its echo as stale history.
  removeTrackedUserEcho(supersededUserEchoes, value);
  removeTrackedUserEcho(pendingUserEchoes, value);
  removeTrackedUserEcho(staleUserEchoes, value);
  pendingUserEchoes.push(value);
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
  lastSource = focusSourceTracker.consume();
  lastEditSource = lastSource;
  controlledValue = value;
  lastEditValue = value;
  committedValue = value;
  emit('focus', value, { source: lastEditSource, nativeEvent: event });
}
function onNativeBlur(event: FocusEvent) {
  const blurSource = sourceFor(event);
  focusSourceTracker.programmatic();
  emit('blur', lastEditValue, { source: blurSource, nativeEvent: event });
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
onMounted(() => {
  focusSourceTracker.bind();
  bindNativeTextarea();
});
onBeforeUnmount(() => {
  focusSourceTracker.unbind();
  unbindNativeTextarea();
});

function focus(options?: Parameters<PrimitiveHandle['focus']>[0]) {
  focusSourceTracker.programmatic();
  lastSource = 'programmatic';
  resolveNativeTextarea()?.focus(options);
}

defineExpose({ focus });
</script>
