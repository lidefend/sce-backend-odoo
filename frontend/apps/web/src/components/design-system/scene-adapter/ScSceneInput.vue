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
import { createPrimitiveFocusSourceTracker } from './primitiveFocusSource';

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
const focusSourceTracker = createPrimitiveFocusSourceTracker();
let lastSource: PrimitiveEventSource = 'programmatic';
let lastEditSource: PrimitiveEventSource = 'programmatic';
let controlledValue = String(props.modelValue ?? '');
let lastEditValue = controlledValue;
let committedValue = controlledValue;
const pendingUserEchoes: string[] = [];
const supersededUserEchoes: string[] = [];
const staleUserEchoes: string[] = [];
// Echo values are full control snapshots, so the history exists only to
// recognize delayed acknowledgements. Bound every queue to keep a long-lived
// control finite without turning event ordering into a time window.
const MAX_TRACKED_ECHO_VALUES = 256;
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
function trimEchoQueue(queue: string[]) {
  if (queue.length > MAX_TRACKED_ECHO_VALUES) {
    queue.splice(0, queue.length - MAX_TRACKED_ECHO_VALUES);
  }
}
function rememberStaleUserEchoes(values: string[]) {
  for (const value of values) {
    if (value && !staleUserEchoes.includes(value)) staleUserEchoes.push(value);
  }
  trimEchoQueue(staleUserEchoes);
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
      trimEchoQueue(supersededUserEchoes);
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
  trimEchoQueue(pendingUserEchoes);
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
onMounted(() => {
  focusSourceTracker.bind();
  bindNativeInput();
});
onBeforeUnmount(() => {
  focusSourceTracker.unbind();
  unbindNativeInput();
});

function focus(options?: Parameters<PrimitiveHandle['focus']>[0]) {
  focusSourceTracker.programmatic();
  lastSource = 'programmatic';
  resolveNativeInput()?.focus(options);
}

defineExpose({ focus });
</script>
