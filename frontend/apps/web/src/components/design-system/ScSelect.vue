<template>
  <TSelect
    class="sc-design-select"
    :model-value="modelValue"
    :options="options"
    :disabled="disabled"
    :readonly="readonly"
    :status="invalid ? 'error' : 'default'"
    :select-input-props="selectInputProps"
    data-ui-engine="tdesign"
    @change="onChange"
  />
</template>

<script setup lang="ts">
import { computed, Fragment, Text, useSlots, type VNode } from 'vue';
import { TSelect } from './tdesignAdapter';

type SelectValue = string | number;
type SelectOption = { label: string; value: SelectValue; disabled?: boolean };

const props = withDefaults(defineProps<{
  modelValue: SelectValue;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  invalid?: boolean;
  describedBy?: string;
}>(), {
  disabled: false,
  readonly: false,
  required: false,
  invalid: false,
  describedBy: undefined,
});
const emit = defineEmits<{ 'update:modelValue': [value: string] }>();
const slots = useSlots();

function textContent(value: unknown): string {
  if (typeof value === 'string' || typeof value === 'number') return String(value);
  if (Array.isArray(value)) return value.map(textContent).join('');
  if (value && typeof value === 'object' && 'children' in value) {
    return textContent((value as VNode).children);
  }
  return '';
}

function collectOptions(nodes: VNode[], output: SelectOption[]): void {
  nodes.forEach((node) => {
    if (node.type === Fragment && Array.isArray(node.children)) {
      collectOptions(node.children as VNode[], output);
      return;
    }
    if (node.type === Text) return;
    if (node.type === 'option') {
      output.push({
        value: (node.props?.value ?? '') as SelectValue,
        label: textContent(node.children).trim(),
        disabled: node.props?.disabled === true || node.props?.disabled === '',
      });
    }
  });
}

const options = computed(() => {
  const output: SelectOption[] = [];
  collectOptions((slots.default?.() || []) as VNode[], output);
  return output;
});
const selectInputProps = computed(() => ({
  inputProps: {
    'aria-required': props.required || undefined,
    'aria-invalid': props.invalid || undefined,
    'aria-describedby': props.describedBy,
  },
}));
function onChange(value: SelectValue | SelectValue[]): void {
  if (props.readonly) return;
  emit('update:modelValue', String(Array.isArray(value) ? value[0] ?? '' : value ?? ''));
}
</script>
