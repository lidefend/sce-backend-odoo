<template>
  <section
    v-if="!page && !loadError"
    data-product-page-mode="form"
    data-state="loading"
    aria-busy="true"
  >
    <ProductFormLoadingSkeleton loading-label="正在载入业务表单" />
  </section>
  <section
    v-else-if="loadError"
    class="record-route-error"
    data-product-page-mode="form"
    data-state="error"
    role="alert"
  >
    <h1>业务表单加载失败</h1>
    <p>页面资源未能载入，请检查网络后重试。</p>
    <ScButton @click="loadPage">重新加载</ScButton>
  </section>
  <component :is="page" v-else />
</template>

<script setup lang="ts">
import { onMounted, ref, shallowRef, type Component } from 'vue';
import ProductFormLoadingSkeleton from '../components/product-record/ProductFormLoadingSkeleton.vue';
import ScButton from '../components/design-system/ScButton.vue';
import { markStartupPhase } from '../app/performance/startupTiming';

const page = shallowRef<Component | null>(null);
const loadError = ref('');

async function loadPage() {
  loadError.value = '';
  markStartupPhase('skeleton_shown', 'ContractFormRoute');
  try {
    const module = await import('./ContractFormPage.vue');
    page.value = module.default;
  } catch {
    loadError.value = 'record_route_asset_load_failed';
  }
}

onMounted(() => {
  void loadPage();
});
</script>

<style scoped>
.record-route-error {
  display: grid;
  gap: var(--sc-product-space-3);
  max-width: 640px;
  padding: var(--sc-product-space-4);
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-product-panel-radius);
  background: var(--sc-app-panel);
  color: var(--sc-app-text-primary);
}

.record-route-error h1,
.record-route-error p {
  margin: 0;
}

.record-route-error p {
  color: var(--sc-semantic-text-muted);
}

.record-route-error :deep(button) {
  justify-self: start;
}
</style>
