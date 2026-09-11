<template>
  <TDesignSteps v-bind="{ ...$attrs, ...semanticPrimitiveIdentity('ScSteps') }" :class="{ 'sc-steps--nowrap': nowrap }" :current="current" :layout="layout" :readonly="readonly">
    <TDesignStepItem v-for="item in items" :key="item.value" :value="item.value" :title="item.label" :disabled="item.disabled" @click="!readonly && !item.disabled && emit('select', item.value)" />
  </TDesignSteps>
</template>
<script setup lang="ts">
import { TDesignStepItem, TDesignSteps } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';
export type ScStepItem = { value: string | number; label: string; disabled?: boolean };
defineOptions({ inheritAttrs: false });
withDefaults(defineProps<{ current?: string | number; layout?: 'horizontal' | 'vertical'; readonly?: boolean; nowrap?: boolean; items?: ScStepItem[] }>(), { current: 0, layout: 'horizontal', readonly: true, nowrap: false, items: () => [] });
const emit = defineEmits<{ select: [value: string | number] }>();
</script>
<style scoped>
.sc-steps--nowrap :deep(.t-steps-item__title) { white-space: nowrap; }
</style>
