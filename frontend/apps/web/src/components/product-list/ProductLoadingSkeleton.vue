<template>
  <section class="product-loading-shell" :class="`mode-${mode}`" role="status" data-semantic-component="ProductLoadingSkeleton" data-state="loading" :data-mode="mode" aria-live="polite" aria-busy="true">
    <p class="sc-visually-hidden">{{ title }}，{{ loadingLabel }}</p>
    <ScSkeleton class="product-loading-skeleton" :loading="true" animation="gradient" :row-col="mode === 'kanban' ? kanbanSkeleton : listSkeleton" />
  </section>
</template>

<script setup lang="ts">
import ScSkeleton from '../design-system/ScSkeleton.vue';
withDefaults(defineProps<{ title: string; mode?: 'list' | 'kanban'; loadingLabel?: string }>(), { mode: 'list', loadingLabel: '正在载入数据' });
const listSkeleton = [
  { width: '100%', height: '44px', marginBottom: '12px' },
  ...Array.from({ length: 8 }, () => ({ width: '100%', height: '38px', marginBottom: '1px' })),
  { width: '42%', height: '32px', marginTop: '12px' },
];
const kanbanSkeleton = Array.from({ length: 12 }, (_, index) => ({ width: 'calc(25% - 12px)', height: '148px', marginRight: index % 4 === 3 ? '0' : '16px', marginBottom: '16px' }));
</script>

<style scoped>
.product-loading-shell { width: 100%; min-width: 0; }
.product-loading-skeleton { display: block; width: 100%; }
@media (max-width: 900px) { .product-loading-shell.mode-kanban :deep(.t-skeleton__row) { width: calc(50% - 8px) !important; margin-right: 16px !important; } }
@media (max-width: 560px) { .product-loading-shell.mode-kanban :deep(.t-skeleton__row) { width: 100% !important; margin-right: 0 !important; } }
</style>
