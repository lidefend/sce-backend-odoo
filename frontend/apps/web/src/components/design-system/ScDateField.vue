<template>
  <TDatePicker
    class="sc-design-date-field"
    :model-value="modelValue"
    :format="withTime ? 'YYYY-MM-DD HH:mm' : 'YYYY-MM-DD'"
    :value-type="withTime ? 'YYYY-MM-DDTHH:mm:ss' : 'YYYY-MM-DD'"
    :enable-time-picker="withTime"
    :readonly="readonly"
    :disabled="disabled"
    :status="invalid ? 'error' : 'default'"
    :input-props="inputProps"
    data-ui-engine="tdesign"
    allow-input
    clearable
    @change="onChange"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { TDatePicker } from './tdesignAdapter';

const props = withDefaults(defineProps<{
  modelValue: string;
  withTime?: boolean;
  readonly?: boolean;
  disabled?: boolean;
  required?: boolean;
  invalid?: boolean;
  describedBy?: string;
}>(), {
  withTime: false,
  readonly: false,
  disabled: false,
  required: false,
  invalid: false,
  describedBy: undefined,
});
const emit = defineEmits<{ 'update:modelValue': [value: string] }>();
const inputProps = computed(() => ({
  'aria-required': props.required || undefined,
  'aria-invalid': props.invalid || undefined,
  'aria-describedby': props.describedBy,
}));
function onChange(value: string | number | string[] | Date | Date[]) {
  emit('update:modelValue', Array.isArray(value) ? String(value[0] || '') : String(value || ''));
}
</script>
