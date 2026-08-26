<template>
  <TDesignTabs
    v-bind="semanticPrimitiveIdentity('ScTabs')"
    :value="modelValue"
    :list="items.length ? tdesignItems : undefined"
    :size="tdesignTabsSize(size)"
    :aria-disabled="disabled || undefined"
    @change="onChange"
  >
    <slot v-if="!items.length" />
  </TDesignTabs>
</template>

<script setup lang="ts">
import { computed, h, useSlots } from 'vue';
import { TDesignTabs } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity, tdesignTabsSize, type ScPrimitiveSize } from './primitiveAdapter';

export interface ScTabItem {
  value: string | number;
  label: string;
  disabled?: boolean;
  labelClass?: string;
  labelAttributes?: Record<string, string | number | boolean | undefined>;
}

const props = withDefaults(defineProps<{ modelValue: string | number; items?: ScTabItem[]; size?: ScPrimitiveSize; disabled?: boolean }>(), {
  items: () => [],
  size: 'medium',
});
const slots = useSlots();
const emit = defineEmits<{ 'update:modelValue': [value: string | number]; change: [value: string | number] }>();
function tabLabel(item: ScTabItem) {
  return (render: typeof h) => render('span', { class: item.labelClass, ...item.labelAttributes }, item.label);
}
const tdesignItems = computed(() => props.items.map((item) => ({
  value: item.value,
  label: tabLabel(item),
  disabled: props.disabled || item.disabled,
  panel: () => slots.panel?.({ item }),
})));
function onChange(value: string | number) {
  if (props.disabled) return;
  emit('update:modelValue', value);
  emit('change', value);
}
</script>
