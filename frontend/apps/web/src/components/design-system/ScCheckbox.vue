<template>
  <TCheckbox
    class="sc-design-checkbox"
    :model-value="modelValue"
    :name="name"
    :disabled="disabled"
    :readonly="readonly"
    :indeterminate="indeterminate"
    :aria-label="label"
    :aria-describedby="describedBy"
    :aria-required="required || undefined"
    :aria-invalid="invalid || undefined"
    data-ui-engine="tdesign"
    @change="$emit('update:modelValue', Boolean($event))"
  >
    <slot />
  </TCheckbox>
</template>

<script setup lang="ts">
import { TCheckbox } from './tdesignAdapter';

withDefaults(defineProps<{
  modelValue: boolean;
  name?: string;
  label?: string;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  invalid?: boolean;
  describedBy?: string;
  indeterminate?: boolean;
}>(), {
  name: undefined,
  label: undefined,
  disabled: false,
  readonly: false,
  required: false,
  invalid: false,
  describedBy: undefined,
  indeterminate: false,
});
defineEmits<{ 'update:modelValue': [value: boolean] }>();
</script>
