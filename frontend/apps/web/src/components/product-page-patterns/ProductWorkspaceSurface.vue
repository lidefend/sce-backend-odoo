<template>
  <div class="product-workspace-surface" data-workspace-composition="official-dashboard-workspace">
    <ScCard v-if="$slots.summary" :title="summaryTitle" :bordered="false" class="product-workspace-surface__summary">
      <slot name="summary" />
    </ScCard>
    <ScCard v-if="$slots.query" :title="queryTitle" :bordered="false" class="product-workspace-surface__query">
      <slot name="query" />
    </ScCard>
    <ScCard :title="mainTitle" :bordered="false" class="product-workspace-surface__main">
      <template v-if="$slots['main-actions']" #actions><slot name="main-actions" /></template>
      <slot />
    </ScCard>
    <ScCard v-if="$slots.secondary" :title="secondaryTitle" :bordered="false" class="product-workspace-surface__secondary">
      <slot name="secondary" />
    </ScCard>
  </div>
</template>

<script setup lang="ts">
// Starter dashboard/base: ordered responsive card regions, shared header/actions/body.
// Business summaries, query scope and work-item execution remain with the caller.
import ScCard from '../design-system/ScCard.vue';
defineProps<{ mainTitle?: string; summaryTitle?: string; queryTitle?: string; secondaryTitle?: string }>();
</script>

<style scoped>
.product-workspace-surface {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-content: start;
  gap: var(--sc-page-section-gap);
  min-width: 0;
  width: 100%;
}
.product-workspace-surface > * { min-width: 0; }
</style>
