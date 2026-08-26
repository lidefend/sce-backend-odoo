<template>
  <TDesignRadioGroup
    v-bind="semanticPrimitiveIdentity('ScRadioGroup')"
    class="sc-radio-group"
    data-primitive-driver="tdesign"
    :data-disabled="disabled || undefined"
    :model-value="modelValue"
    :options="options"
    :name="name"
    :disabled="disabled"
    :readonly="readonly"
    :direction="direction"
    :size="normalizePrimitiveSize(size)"
    :aria-label="label"
    :aria-required="required || undefined"
    :aria-invalid="invalid || undefined"
    :aria-describedby="describedBy"
    @change="onChange"
  />
</template>

<script setup lang="ts">
import { TDesignRadioGroup } from './tdesignPrimitiveBridge';
import { normalizePrimitiveSize, semanticPrimitiveIdentity, type ScPrimitiveSize } from './primitiveAdapter';

export interface ScRadioOption {
  value: string | number | boolean;
  label: string;
  disabled?: boolean;
}

const props = withDefaults(defineProps<{
  modelValue?: string | number | boolean;
  options?: readonly ScRadioOption[];
  name?: string;
  label: string;
  direction?: 'horizontal' | 'vertical';
  size?: ScPrimitiveSize;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  invalid?: boolean;
  describedBy?: string;
}>(), {
  modelValue: '',
  options: () => [],
  name: undefined,
  direction: 'horizontal',
  size: 'medium',
  describedBy: undefined,
});

const emit = defineEmits<{ 'update:modelValue': [value: string | number | boolean]; change: [value: string | number | boolean, event: Event] }>();
function onChange(value: string | number | boolean, context: { e?: Event }) {
  if (props.disabled || props.readonly) return;
  emit('update:modelValue', value);
  emit('change', value, context?.e ?? new Event('change'));
}
</script>

<style scoped>
.sc-radio-group { display: flex; flex-wrap: wrap; gap: var(--sc-space-xs) var(--sc-space-sm); min-width: 0; }
</style>
