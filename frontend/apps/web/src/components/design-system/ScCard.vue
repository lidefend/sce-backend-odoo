<template>
  <TDesignCard
    v-bind="{ ...$attrs, ...semanticPrimitiveIdentity('ScCard') }"
    :title="title"
    :subtitle="subtitle"
    :bordered="bordered"
    :data-appearance="appearance"
  >
    <template v-if="$slots.actions" #actions><slot name="actions" /></template>
    <slot />
  </TDesignCard>
</template>

<script setup lang="ts">
import { TDesignCard } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';

defineOptions({ inheritAttrs: false });
withDefaults(defineProps<{
  title?: string;
  subtitle?: string;
  bordered?: boolean;
  appearance?: 'default' | 'summary' | 'task' | 'section' | 'context' | 'relation';
}>(), {
  bordered: true,
  appearance: 'default',
});
</script>

<style scoped>
[data-appearance='summary'] { overflow: hidden; }
[data-appearance='summary'] :deep(.t-card__body) { padding: 0; }
[data-appearance='task'] :deep(.t-card__header) { align-items: center; }
[data-appearance='task'] :deep(.t-card__body) { padding-top: 8px; }
</style>
