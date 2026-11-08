<template>
  <ScDateField
    :id="id"
    ref="dateRef"
    :name="name"
    :model-value="modelValue.value"
    :with-time="modelValue.precision === 'datetime'"
    :size="size"
    :invalid="status === 'error'"
    :disabled="disabled"
    :readonly="readonly"
    :required="required"
    :loading="loading"
    :clearable="clearable"
    :placeholder="placeholder"
    :described-by="describedBy"
    :aria-label="ariaLabel"
    @pointerdown="onPointerdown"
    @update:model-value="onUpdate"
    @change="onChange"
    @focus="onFocus"
    @blur="onBlur"
    @keydown="onKeydown"
    @keyup="onKeyup"
  />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import type {
  CanonicalDateValue,
  DateFieldPortEmits,
  DateFieldPortProps,
  NoPortSlots,
  PrimitiveEventSource,
  PrimitiveHandle,
} from '@sc/ui/primitive-port';
import ScDateField from '../ScDateField.vue';
import { createPrimitiveFocusSourceTracker } from './primitiveFocusSource';

const props = withDefaults(defineProps<DateFieldPortProps>(), {
  placeholder: undefined,
  size: 'medium',
  status: 'default',
  disabled: false,
  readonly: false,
  required: false,
  loading: false,
  clearable: false,
  describedBy: undefined,
  ariaLabel: undefined,
  name: undefined,
  id: undefined,
});
const emit = defineEmits<DateFieldPortEmits<CanonicalDateValue>>();
defineSlots<NoPortSlots>();
const dateRef = ref<{ $el?: unknown } | null>(null);
const focusSourceTracker = createPrimitiveFocusSourceTracker();
let lastSource: PrimitiveEventSource = 'programmatic';
const source = (event: Event): PrimitiveEventSource => event.isTrusted ? lastSource : 'programmatic';
const canonical = (value: string): CanonicalDateValue => ({
  precision: props.modelValue.precision,
  value,
});
function onPointerdown() {
  focusSourceTracker.pointer();
  lastSource = 'pointer';
}
function onUpdate(value: string) {
  emit('update:modelValue', canonical(value));
}
function onChange(value: string, event: Event) {
  const nativeEvent = event instanceof Event ? event : undefined;
  emit('change', canonical(value), {
    source: nativeEvent?.isTrusted ? source(nativeEvent) : lastSource,
    nativeEvent,
  });
}
function onFocus(value: string, event: FocusEvent) {
  lastSource = focusSourceTracker.consume();
  emit('focus', canonical(value), { source: source(event), nativeEvent: event });
}
function onBlur(value: string, event: FocusEvent) {
  const blurSource = source(event);
  focusSourceTracker.programmatic();
  emit('blur', canonical(value), { source: blurSource, nativeEvent: event });
}
function onKeydown(event: KeyboardEvent) {
  focusSourceTracker.keyboard();
  lastSource = 'keyboard';
  emit('keydown', { source: 'keyboard', nativeEvent: event });
}
function onKeyup(event: KeyboardEvent) {
  emit('keyup', { source: 'keyboard', nativeEvent: event });
}
function focus(options?: Parameters<PrimitiveHandle['focus']>[0]) {
  focusSourceTracker.programmatic();
  lastSource = 'programmatic';
  const root = dateRef.value?.$el;
  const container = root instanceof Node ? (root instanceof Element ? root : root.parentElement) : null;
  const target = container instanceof HTMLInputElement ? container : container?.querySelector<HTMLInputElement>('input');
  target?.focus(options);
}
onMounted(() => focusSourceTracker.bind());
onBeforeUnmount(() => focusSourceTracker.unbind());
defineExpose({ focus });
</script>
