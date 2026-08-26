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
  appearance?: 'default' | 'summary' | 'task' | 'section' | 'context' | 'relation' | 'form-section' | 'auth' | 'account' | 'main-surface' | 'flow' | 'kanban-record';
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
[data-appearance='auth'] :deep(.t-card__body) { display: grid; gap: 18px; padding: 32px; }
[data-appearance='account'] :deep(.t-card__body) { display: grid; gap: 16px; padding: 28px; }
[data-appearance='kanban-record'] :deep(.t-card__body) { display: grid; gap: var(--sc-card-gap); padding: var(--sc-product-space-2); }
[data-appearance='main-surface'] { width: 100%; min-width: 0; }
[data-appearance='main-surface'] :deep(.t-card__body) { padding: 0 20px 24px; }
[data-appearance='flow'] { width: 100%; min-width: 0; border: 0; background: transparent; box-shadow: none; }
[data-appearance='flow'] :deep(.t-card__body) { padding: 0; }
@media (max-width: 640px) {
  [data-appearance='auth'] :deep(.t-card__body) { padding: 22px; }
  [data-appearance='main-surface'] :deep(.t-card__body) { padding: 0 0 18px; }
}
</style>
