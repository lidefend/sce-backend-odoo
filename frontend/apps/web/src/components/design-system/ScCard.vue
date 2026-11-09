<template>
  <TDesignCard
    v-bind="{ ...semanticPrimitiveIdentity('ScCard'), ...$attrs }"
    :title="title"
    :subtitle="subtitle"
    :bordered="bordered"
    :body-class-name="bodyClassName"
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
  bodyClassName?: string;
  appearance?: 'default' | 'summary' | 'task' | 'section' | 'task-section' | 'context' | 'relation' | 'form-section' | 'fact' | 'auth' | 'account' | 'main-surface' | 'flow' | 'kanban-record' | 'metric' | 'table' | 'record' | 'config';
}>(), {
  title: undefined,
  subtitle: undefined,
  bordered: true,
  bodyClassName: undefined,
  appearance: 'default',
});
</script>

<style scoped>
[data-appearance='summary'] { overflow: hidden; }
[data-appearance='summary'] :deep(.t-card__body) { padding: 0; }
[data-appearance='fact'] { border: 0; background: transparent; box-shadow: none; }
[data-appearance='fact'] :deep(.t-card__body) { padding: 0; }
[data-appearance='form-section'] { border: 0; border-radius: 0; background: transparent; box-shadow: none; }
[data-appearance='form-section'] :deep(.t-card__body) { padding: 0; }
[data-appearance='task'] :deep(.t-card__body) {
  display: grid;
  align-content: start;
  height: max-content;
  padding: var(--sc-space-xs) var(--sc-space-lg) var(--sc-space-md);
}
[data-appearance='task'] :deep(.t-card__header) {
  align-items: center;
  padding-block: var(--sc-space-sm) var(--sc-space-xs);
}
[data-appearance='task-section'] {
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}
[data-appearance='task-section'] :deep(.t-card__body) {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: var(--sc-space-xl);
  row-gap: var(--sc-space-md);
  padding: var(--sc-space-2xs) 0 var(--sc-space-lg);
}
[data-appearance='task-section'] :deep(.t-card__header) {
  align-items: center;
  padding: var(--sc-space-md) 0 var(--sc-space-xs);
  border-top: 1px solid var(--sc-app-border);
}
[data-appearance='auth'] { --sc-card-body-padding: var(--sc-space-xl); }
[data-appearance='auth'] :deep(.t-card__body) {
  display: grid;
  gap: var(--sc-space-md);
  padding: var(--sc-card-body-padding);
}
[data-appearance='account'] :deep(.t-card__body) {
  display: grid;
  gap: var(--sc-space-md);
  padding: var(--sc-space-xl);
}
[data-appearance='kanban-record'] :deep(.t-card__body) {
  display: grid;
  gap: var(--sc-card-gap);
  padding: var(--sc-product-space-2);
}
[data-appearance='metric'] :deep(.t-card__body) { padding: var(--sc-space-xs); }
[data-appearance='table'] :deep(.t-card__body) { padding: 0; }
[data-appearance='record'] :deep(.t-card__body) {
  display: grid;
  gap: var(--sc-product-space-3);
  padding: var(--sc-product-space-3);
}
[data-appearance='config'] :deep(.t-card__body) {
  display: grid;
  grid-template-rows: auto 1fr auto auto;
  gap: var(--sc-space-sm);
  padding: var(--sc-space-sm);
}
[data-appearance='main-surface'] { --sc-card-body-padding: 0 var(--sc-space-md) var(--sc-space-md); width: 100%; min-width: 0; }
[data-appearance='main-surface'] :deep(.t-card__body) { padding: var(--sc-card-body-padding); }
[data-appearance='flow'] { width: 100%; min-width: 0; border: 0; background: transparent; box-shadow: none; }
[data-appearance='flow'] :deep(.t-card__body) { padding: 0; }
@media (max-width: 640px) {
  [data-appearance='auth'] { --sc-card-body-padding: var(--sc-space-lg); }
  [data-appearance='main-surface'] { --sc-card-body-padding: 0 0 var(--sc-space-md); }
  [data-appearance='task-section'] :deep(.t-card__body) { grid-template-columns: minmax(0, 1fr); }
}
</style>
