<template>
  <TDesignTabs
    v-bind="semanticPrimitiveIdentity('ScTabs')"
    :value="modelValue"
    :size="tdesignTabsSize(size)"
    :aria-disabled="disabled || undefined"
    @change="onChange"
  >
    <slot>
      <TDesignTabPanel v-for="item in items" :key="item.value" :value="item.value" :label="tabLabel(item)" :disabled="disabled || item.disabled">
        <slot name="panel" :item="item" />
      </TDesignTabPanel>
    </slot>
  </TDesignTabs>
</template>

<script setup lang="ts">
import { h } from 'vue';
import { TDesignTabPanel, TDesignTabs } from './tdesignPrimitiveBridge';
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
const emit = defineEmits<{ 'update:modelValue': [value: string | number]; change: [value: string | number] }>();
function tabLabel(item: ScTabItem) {
  return h('span', { class: item.labelClass, ...item.labelAttributes }, item.label);
}
function onChange(value: string | number) {
  if (props.disabled) return;
  emit('update:modelValue', value);
  emit('change', value);
}
</script>
