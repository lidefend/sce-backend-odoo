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
    @pointerdown="lastSource = 'pointer'"
    @keydown="onKeydown"
    @keyup="onKeyup"
    @update:model-value="onUpdate"
    @input="onInput"
    @change="onChange"
    @focus="onFocus"
    @blur="onBlur"
    @compositionstart="onCompositionStart"
    @compositionend="onCompositionEnd"
  />
</template>

<script setup lang="ts">
import { ref } from 'vue';
import type {
  InputPortEmits,
  InputPortProps,
  NoPortSlots,
  PrimitiveEventSource,
  PrimitiveHandle,
} from '@sc/ui/primitive-port';
import ScInput from '../ScInput.vue';

withDefaults(defineProps<InputPortProps>(), {
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

function sourceFor(event: Event): PrimitiveEventSource {
  return event.isTrusted ? lastSource : 'programmatic';
}
function onUpdate(value: string) {
  emit('update:modelValue', String(value));
}
function onInput(value: string, event: Event) {
  emit('input', String(value), { source: sourceFor(event), nativeEvent: event });
}
function onChange(value: string, event: Event) {
  emit('update:modelValue', String(value));
  emit('input', String(value), { source: sourceFor(event), nativeEvent: event });
  emit('change', String(value), { source: sourceFor(event), nativeEvent: event });
}
function onFocus(value: string | number, event: FocusEvent) {
  emit('focus', String(value), { source: sourceFor(event), nativeEvent: event });
}
function onBlur(value: string | number, event: FocusEvent) {
  emit('blur', String(value), { source: sourceFor(event), nativeEvent: event });
}
function onKeydown(event: KeyboardEvent) {
  lastSource = 'keyboard';
  emit('keydown', { source: 'keyboard', nativeEvent: event });
}
function onKeyup(event: KeyboardEvent) {
  emit('keyup', { source: 'keyboard', nativeEvent: event });
}
function onCompositionStart(event: CompositionEvent) {
  lastSource = 'keyboard';
  emit('compositionstart', { source: 'keyboard', nativeEvent: event });
}
function onCompositionEnd(event: CompositionEvent) {
  emit('compositionend', { source: 'keyboard', nativeEvent: event });
}

function focus(options?: Parameters<PrimitiveHandle['focus']>[0]) {
  const root = inputRef.value?.$el;
  const container = root instanceof Node ? (root instanceof Element ? root : root.parentElement) : null;
  const target = container instanceof HTMLInputElement
    ? container
    : container?.querySelector<HTMLInputElement>('input');
  target?.focus(options);
}

defineExpose({ focus });
</script>
