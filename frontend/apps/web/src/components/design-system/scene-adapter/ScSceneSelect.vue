<template>
  <ScSelect
    :id="id"
    ref="selectRef"
    :name="name"
    :model-value="modelValue"
    :options="options"
    :placeholder="placeholder"
    :filterable="filterable"
    :size="size"
    :status="status"
    :disabled="disabled"
    :readonly="readonly"
    :required="required"
    :loading="loading"
    :described-by="describedBy"
    :aria-label="ariaLabel"
    :empty-text="emptyText"
    @pointerdown="onPointerdown"
    @update:model-value="emit('update:modelValue', String($event))"
    @change="onChange"
    @search="onSearch"
    @popup-visible-change="onPopup"
    @focus="onFocus"
    @blur="onBlur"
    @keydown="onKeydown"
    @keyup="onKeyup"
  />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import type {
  NoPortSlots,
  PrimitiveEventSource,
  PrimitiveHandle,
  SelectPortEmits,
  SelectPortProps,
} from '@sc/ui/primitive-port';
import ScSelect from '../ScSelect.vue';
import { createPrimitiveFocusSourceTracker } from './primitiveFocusSource';

withDefaults(defineProps<SelectPortProps>(), {
  options: () => [],
  placeholder: undefined,
  filterable: false,
  emptyText: undefined,
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
const emit = defineEmits<SelectPortEmits>();
defineSlots<NoPortSlots>();
const selectRef = ref<{ $el?: unknown } | null>(null);
const focusSourceTracker = createPrimitiveFocusSourceTracker();
let lastSource: PrimitiveEventSource = 'programmatic';
const source = (event: Event): PrimitiveEventSource => event.isTrusted ? lastSource : 'programmatic';

function onPointerdown() {
  focusSourceTracker.pointer();
  lastSource = 'pointer';
}
function onChange(value: string, event: Event) {
  emit('change', String(value), { source: source(event), nativeEvent: event });
}
function onSearch(value: string, event: Event) {
  emit('search', String(value), {
    source: source(event),
    nativeEvent: event instanceof InputEvent ? event : undefined,
  });
}
function onPopup(state: { visible: boolean; trigger: string }, event: Event) {
  emit('popupVisibleChange', state, { source: source(event), nativeEvent: event });
}
function onFocus(value: string, event: FocusEvent) {
  lastSource = focusSourceTracker.consume();
  emit('focus', String(value), { source: source(event), nativeEvent: event });
}
function onBlur(value: string, event: FocusEvent) {
  const blurSource = source(event);
  focusSourceTracker.programmatic();
  emit('blur', String(value), { source: blurSource, nativeEvent: event });
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
  const root = selectRef.value?.$el;
  const container = root instanceof Node ? (root instanceof Element ? root : root.parentElement) : null;
  const target = container instanceof HTMLInputElement ? container : container?.querySelector<HTMLInputElement>('input');
  target?.focus(options);
}
onMounted(() => focusSourceTracker.bind());
onBeforeUnmount(() => focusSourceTracker.unbind());
defineExpose({ focus });
</script>
