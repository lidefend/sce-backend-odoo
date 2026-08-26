<template>
  <section class="product-loading-shell" :class="`mode-${mode}`" role="status" data-semantic-component="ProductLoadingSkeleton" data-state="loading" :data-mode="mode" aria-live="polite" aria-busy="true">
    <p class="sc-visually-hidden">{{ title }}，{{ loadingLabel }}</p>
    <ScSkeleton class="product-loading-skeleton" :loading="true" animation="gradient" :row-col="mode === 'kanban' ? kanbanSkeleton : listSkeleton" />
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import ScSkeleton from '../design-system/ScSkeleton.vue';
withDefaults(defineProps<{ title: string; mode?: 'list' | 'kanban'; loadingLabel?: string }>(), { mode: 'list', loadingLabel: '正在载入数据' });
const listSkeleton = [
  { width: '100%', height: '44px', marginBottom: '12px' },
  ...Array.from({ length: 8 }, () => ({ width: '100%', height: '38px', marginBottom: '1px' })),
  { width: '42%', height: '32px', marginTop: '12px' },
];
const viewportWidth = ref(typeof window === 'undefined' ? 1200 : window.innerWidth);
const kanbanColumnCount = computed(() => viewportWidth.value <= 560 ? 1 : viewportWidth.value <= 900 ? 2 : 4);
const kanbanSkeleton = computed(() => Array.from({ length: 12 }, (_, index) => {
  const columns = kanbanColumnCount.value;
  const gap = columns === 1 ? 0 : 16;
  return {
    width: columns === 1 ? '100%' : `calc(${100 / columns}% - ${gap * (columns - 1) / columns}px)`,
    height: '148px',
    marginRight: index % columns === columns - 1 ? '0' : `${gap}px`,
    marginBottom: '16px',
  };
}));
function syncViewportWidth() { viewportWidth.value = window.innerWidth; }
onMounted(() => window.addEventListener('resize', syncViewportWidth, { passive: true }));
onBeforeUnmount(() => window.removeEventListener('resize', syncViewportWidth));
</script>

<style scoped>
.product-loading-shell { width: 100%; min-width: 0; }
.product-loading-skeleton { display: block; width: 100%; }
</style>
