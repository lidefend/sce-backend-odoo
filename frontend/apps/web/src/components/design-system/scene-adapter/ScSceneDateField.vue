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
    :placeholder="placeholder"
    :described-by="describedBy"
    :aria-label="ariaLabel"
    @pointerdown="lastSource = 'pointer'"
    @update:model-value="onUpdate"
    @change="onChange"
    @focus="onFocus"
    @blur="onBlur"
    @keydown="onKeydown"
    @keyup="onKeyup"
  />
</template>

<script setup lang="ts">
import { ref } from 'vue';
import type {
  CanonicalDateValue,
  DateFieldPortEmits,
  DateFieldPortProps,
  NoPortSlots,
  PrimitiveEventSource,
  PrimitiveHandle,
} from '@sc/ui/primitive-port';
import ScDateField from '../ScDateField.vue';

const props = withDefaults(defineProps<DateFieldPortProps>(), {
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
const emit = defineEmits<DateFieldPortEmits<CanonicalDateValue>>();
defineSlots<NoPortSlots>();
const dateRef = ref<{ $el?: unknown } | null>(null);
let lastSource: PrimitiveEventSource = 'programmatic';
const source = (event: Event): PrimitiveEventSource => event.isTrusted ? lastSource : 'programmatic';
const canonical = (value: string): CanonicalDateValue => ({
  precision: props.modelValue.precision,
  value,
});
function onUpdate(value: string) {
  emit('update:modelValue', canonical(value));
}
function onChange(value: string, event: Event) {
  emit('change', canonical(value), { source: source(event), nativeEvent: event });
}
function onFocus(value: string, event: FocusEvent) {
  emit('focus', canonical(value), { source: source(event), nativeEvent: event });
}
function onBlur(value: string, event: FocusEvent) {
  emit('blur', canonical(value), { source: source(event), nativeEvent: event });
}
function onKeydown(event: KeyboardEvent) {
  lastSource = 'keyboard';
  emit('keydown', { source: 'keyboard', nativeEvent: event });
}
function onKeyup(event: KeyboardEvent) {
  emit('keyup', { source: 'keyboard', nativeEvent: event });
}
function focus(options?: Parameters<PrimitiveHandle['focus']>[0]) {
  const root = dateRef.value?.$el;
  const container = root instanceof Node ? (root instanceof Element ? root : root.parentElement) : null;
  const target = container instanceof HTMLInputElement ? container : container?.querySelector<HTMLInputElement>('input');
  target?.focus(options);
}
defineExpose({ focus });
</script>
