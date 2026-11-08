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
    @focus="onFocus"
    @blur="onBlur"
    @keydown="onKeydown"
    @keyup="onKeyup"
  />
</template>
<script setup lang="ts">
import { computed, ref } from 'vue';
import { TDesignDatePicker } from './tdesignPrimitiveBridge';
import { nativeControlProjection } from './nativeControlProjection';
import type { ScPrimitiveSize } from './primitiveAdapter';

const props = withDefaults(defineProps<{ id?:string; name?:string; modelValue:string; withTime?:boolean; size?:ScPrimitiveSize; loading?:boolean; readonly?:boolean; disabled?:boolean; clearable?:boolean; required?:boolean; invalid?:boolean; describedBy?:string; ariaLabel?:string; appearance?:'default'|'form-field' }>(), {
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
  appearance:'default',
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
  emit('update:modelValue', next);
  // TDesign's picker emits a semantic context for calendar selections, not a
  // native DOM event. Preserve the value change and use a normalized,
  // untrusted change event so adapters can classify it as programmatic rather
  // than dropping the field update entirely.
  emit('change', next, event ?? new Event('change'));
}
function onFocus(value: unknown, context?: unknown) {
  const event = nativeEvent(context);
  if (event instanceof FocusEvent) emit('focus', String(value ?? ''), event);
}
function onBlur(value: unknown, context?: unknown) {
  const event = nativeEvent(context);
  if (event instanceof FocusEvent) emit('blur', String(value ?? ''), event);
}
function onKeydown(_value: unknown, context?: unknown) {
  const event = nativeEvent(context);
  if (event instanceof KeyboardEvent) emit('keydown', event);
}
function onKeyup(_value: unknown, context?: unknown) {
  const event = nativeEvent(context);
  if (event instanceof KeyboardEvent) emit('keyup', event);
}
defineExpose({ focus: (options?: Parameters<HTMLElement['focus']>[0]) => dateRef.value?.focus?.(options) });
</script>

<style scoped>
[data-semantic-component='ScDateField'] { width: 100%; }
</style>
