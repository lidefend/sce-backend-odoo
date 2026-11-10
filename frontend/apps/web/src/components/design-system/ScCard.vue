<template>
  <TDesignCard
    v-bind="{ ...semanticPrimitiveIdentity('ScCard'), ...$attrs }"
    :title="title"
    :subtitle="subtitle"
    :bordered="bordered"
    :body-class-name="cardBodyClassName"
    :header-class-name="cardHeaderClassName"
    :data-appearance="appearance"
  >
    <template v-if="$slots.actions" #actions><slot name="actions" /></template>
    <slot />
  </TDesignCard>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { TDesignCard } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';

defineOptions({ inheritAttrs: false });
const props = withDefaults(defineProps<{
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

const cardBodyClassName = computed(() => [
  'sc-card__body',
  `sc-card__body--${props.appearance}`,
  props.bodyClassName,
].filter(Boolean).join(' '));
const cardHeaderClassName = computed(() => `sc-card__header--${props.appearance}`);
</script>

<style scoped>
[data-appearance='summary'] { overflow: hidden; }
:deep(.sc-card__body--summary) { padding: 0; }
[data-appearance='fact'] { border: 0; background: transparent; box-shadow: none; }
:deep(.sc-card__body--fact) { padding: 0; }
[data-appearance='form-section'] { border: 0; border-radius: 0; background: transparent; box-shadow: none; }
:deep(.sc-card__body--form-section) { padding: 0; }
:deep(.sc-card__body--task) {
  display: grid;
  align-content: start;
  height: max-content;
  padding: var(--sc-space-xs) var(--sc-space-lg) var(--sc-space-md);
}
:deep(.sc-card__header--task) {
  align-items: center;
  padding-block: var(--sc-space-sm) var(--sc-space-xs);
}
[data-appearance='task-section'] {
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}
:deep(.sc-card__body--task-section) {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: var(--sc-space-xl);
  row-gap: var(--sc-space-md);
  padding: var(--sc-space-2xs) 0 var(--sc-space-lg);
}
:deep(.sc-card__header--task-section) {
  align-items: center;
  padding: var(--sc-space-md) 0 var(--sc-space-xs);
  border-top: 1px solid var(--sc-app-border);
}
[data-appearance='auth'] { --sc-card-body-padding: var(--sc-space-xl); }
:deep(.sc-card__body--auth) {
  display: grid;
  gap: var(--sc-space-md);
  padding: var(--sc-card-body-padding);
}
:deep(.sc-card__body--account) {
  display: grid;
  gap: var(--sc-space-md);
  padding: var(--sc-space-xl);
}
:deep(.sc-card__body--kanban-record) {
  display: grid;
  gap: var(--sc-card-gap);
  padding: var(--sc-product-space-2);
}
:deep(.sc-card__body--metric) { padding: var(--sc-space-xs); }
:deep(.sc-card__body--table) { padding: 0; }
:deep(.sc-card__body--record) {
  display: grid;
  gap: var(--sc-product-space-3);
  padding: var(--sc-product-space-3);
}
:deep(.sc-card__body--config) {
  display: grid;
  grid-template-rows: auto 1fr auto auto;
  gap: var(--sc-space-sm);
  padding: var(--sc-space-sm);
}
[data-appearance='main-surface'] { --sc-card-body-padding: 0 var(--sc-space-md) var(--sc-space-md); width: 100%; min-width: 0; }
:deep(.sc-card__body--main-surface) { padding: var(--sc-card-body-padding); }
[data-appearance='flow'] { width: 100%; min-width: 0; border: 0; background: transparent; box-shadow: none; }
:deep(.sc-card__body--flow) { padding: 0; }
@media (max-width: 640px) {
  [data-appearance='auth'] { --sc-card-body-padding: var(--sc-space-lg); }
  [data-appearance='main-surface'] { --sc-card-body-padding: 0 0 var(--sc-space-md); }
  :deep(.sc-card__body--task-section) { grid-template-columns: minmax(0, 1fr); }
}
</style>
