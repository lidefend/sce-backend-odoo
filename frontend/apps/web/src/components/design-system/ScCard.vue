<template>
  <TDesignCard
    v-bind="{ ...$attrs, ...semanticPrimitiveIdentity('ScCard') }"
    :title="title"
    :subtitle="subtitle"
    :bordered="bordered"
    :body-style="cardBodyStyle"
    :header-style="cardHeaderStyle"
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
  appearance?: 'default' | 'summary' | 'task' | 'section' | 'task-section' | 'context' | 'relation' | 'form-section' | 'fact' | 'auth' | 'account' | 'main-surface' | 'flow' | 'kanban-record' | 'metric' | 'table' | 'record' | 'config';
}>(), {
  bordered: true,
  appearance: 'default',
});

type CardStyle = Record<string, string | number>;

const cardBodyStyle = computed<CardStyle>(() => {
  const styles: Partial<Record<NonNullable<typeof props.appearance>, CardStyle>> = {
    summary: { padding: '0' },
    task: { display: 'grid', alignContent: 'start', height: 'max-content', padding: '8px 20px 18px' },
    'task-section': { display: 'grid', gridTemplateColumns: 'var(--sc-task-section-columns)', columnGap: '32px', rowGap: '16px', padding: '4px 0 20px' },
    fact: { padding: '0' },
    auth: { display: 'grid', gap: '18px', padding: 'var(--sc-card-body-padding)' },
    account: { display: 'grid', gap: '16px', padding: '28px' },
    'kanban-record': { display: 'grid', gap: 'var(--sc-card-gap)', padding: 'var(--sc-product-space-2)' },
    metric: { padding: '10px' },
    table: { padding: '0' },
    record: { display: 'grid', gap: 'var(--sc-product-space-3)', padding: 'var(--sc-product-space-3)' },
    config: { display: 'grid', gridTemplateRows: 'auto 1fr auto auto', gap: '12px', padding: '14px' },
    'main-surface': { padding: 'var(--sc-card-body-padding)' },
    flow: { padding: '0' },
  };
  return styles[props.appearance] || {};
});

const cardHeaderStyle = computed<CardStyle>(() => {
  if (props.appearance === 'task') return { alignItems: 'center', paddingBlock: '14px 8px' } as CardStyle;
  if (props.appearance === 'task-section') return { alignItems: 'center', padding: '18px 0 10px', borderTop: '1px solid var(--sc-app-border)' } as CardStyle;
  return {} as CardStyle;
});
</script>

<style scoped>
[data-appearance='summary'] { overflow: hidden; }
[data-appearance='fact'] { border: 0; background: transparent; box-shadow: none; }
[data-appearance='task-section'] { --sc-task-section-columns: repeat(2, minmax(0, 1fr)); border: 0; border-radius: 0; background: transparent; box-shadow: none; }
[data-appearance='auth'] { --sc-card-body-padding: 32px; }
[data-appearance='main-surface'] { --sc-card-body-padding: 0 20px 24px; width: 100%; min-width: 0; }
[data-appearance='flow'] { width: 100%; min-width: 0; border: 0; background: transparent; box-shadow: none; }
@media (max-width: 640px) {
  [data-appearance='auth'] { --sc-card-body-padding: 22px; }
  [data-appearance='main-surface'] { --sc-card-body-padding: 0 0 18px; }
  [data-appearance='task-section'] { --sc-task-section-columns: minmax(0, 1fr); }
}
</style>
