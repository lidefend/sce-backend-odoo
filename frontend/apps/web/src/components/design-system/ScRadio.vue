<template>
  <TDesignRadio
    v-bind="semanticPrimitiveIdentity('ScRadio')"
    data-primitive-driver="tdesign"
    :checked="checked"
    :value="value"
    :name="name"
    :disabled="disabled || readonly"
    :data-checked="checked || undefined"
    :data-disabled="disabled || undefined"
    :data-readonly="readonly || undefined"
    :aria-label="label"
    :aria-required="required || undefined"
    :aria-invalid="invalid || undefined"
    :aria-describedby="describedBy"
    @change="onChange"
  />
</template>

<script setup lang="ts">
import { TDesignRadio } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';

const props = withDefaults(defineProps<{
  checked?: boolean;
  value: string | number | boolean;
  name?: string;
  label: string;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  invalid?: boolean;
  describedBy?: string;
}>(), {
  checked: false,
  name: undefined,
  describedBy: undefined,
});

const emit = defineEmits<{
  'update:checked': [checked: boolean];
  change: [checked: boolean, event: Event];
}>();

function onChange(checked: boolean, context?: { e?: Event }) {
  if (props.disabled || props.readonly) return;
  emit('update:checked', checked);
  emit('change', checked, context?.e ?? new Event('change'));
}
</script>
