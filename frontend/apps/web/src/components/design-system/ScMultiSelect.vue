<template>
  <TSelect
    ref="control"
    class="sc-design-select sc-design-multi-select"
    :model-value="modelValue"
    :options="options"
    :disabled="disabled"
    :readonly="readonly"
    :status="invalid ? 'error' : 'default'"
    :aria-label="label"
    data-ui-engine="tdesign"
    multiple
    clearable
    @change="onChange"
  />
</template>

<script setup lang="ts">
import { computed, Fragment, nextTick, onMounted, onUpdated, ref, Text, useSlots, type ComponentPublicInstance, type VNode } from 'vue';
import { TSelect } from './tdesignAdapter';

type SelectValue = string | number;
type SelectOption = { label: string; value: SelectValue; disabled?: boolean };

const props = withDefaults(defineProps<{
  modelValue: SelectValue[];
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  invalid?: boolean;
  label?: string;
  describedBy?: string;
}>(), {
  disabled: false,
  readonly: false,
  required: false,
  invalid: false,
  label: undefined,
  describedBy: undefined,
});
const emit = defineEmits<{ 'update:modelValue': [value: string[]] }>();
const slots = useSlots();
const control = ref<ComponentPublicInstance | null>(null);

function textContent(value: unknown): string {
  if (typeof value === 'string' || typeof value === 'number') return String(value);
  if (Array.isArray(value)) return value.map(textContent).join('');
  if (value && typeof value === 'object' && 'children' in value) return textContent((value as VNode).children);
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
function syncNativeAccessibility(): void {
  const input = (control.value?.$el as HTMLElement | undefined)?.querySelector('input');
  if (!input) return;
  const attributes: Record<string, string | undefined> = {
    'aria-label': props.label,
    'aria-required': props.required ? 'true' : undefined,
    'aria-invalid': props.invalid ? 'true' : undefined,
    'aria-describedby': props.describedBy,
  };
  Object.entries(attributes).forEach(([name, value]) => {
    if (value === undefined || value === '') input.removeAttribute(name);
    else input.setAttribute(name, value);
  });
}
function onChange(value: unknown): void {
  if (props.readonly) return;
  emit('update:modelValue', (Array.isArray(value) ? value : [value]).map((item) => String(item ?? '')));
}
onMounted(() => nextTick(syncNativeAccessibility));
onUpdated(() => nextTick(syncNativeAccessibility));
</script>
