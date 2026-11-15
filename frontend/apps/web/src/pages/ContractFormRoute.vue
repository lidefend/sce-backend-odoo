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
    <ScButton @click="reloadRoute">重新加载页面</ScButton>
  </section>
  <component :is="page" v-else />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, shallowRef, type Component } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import ProductFormLoadingSkeleton from '../components/product-record/ProductFormLoadingSkeleton.vue';
import ScButton from '../components/design-system/ScButton.vue';
import { markStartupPhase } from '../app/performance/startupTiming';

const page = shallowRef<Component | null>(null);
const loadError = ref('');
const ASSET_LOAD_TIMEOUT_MS = 15000;
let loadGeneration = 0;

async function loadPage() {
  const generation = ++loadGeneration;
  loadError.value = '';
  markStartupPhase('skeleton_shown', 'ContractFormRoute');
  let timeoutId: number | null = null;
  try {
    const timeout = new Promise<never>((_, reject) => {
      timeoutId = window.setTimeout(() => {
        reject(new Error('record_route_asset_load_timeout'));
      }, ASSET_LOAD_TIMEOUT_MS);
    });
    const module = await Promise.race([import('./ContractFormPage.vue'), timeout]);
    if (generation !== loadGeneration) return;
    page.value = module.default;
  } catch {
    if (generation !== loadGeneration) return;
    loadError.value = 'record_route_asset_load_failed';
  } finally {
    if (timeoutId !== null) window.clearTimeout(timeoutId);
  }
}

function reloadRoute() {
  if (loadError.value) {
    window.location.reload();
    return;
  }
  void loadPage();
}

onMounted(() => {
  void loadPage();
});

onBeforeRouteLeave(() => {
  loadGeneration += 1;
});

onBeforeUnmount(() => {
  loadGeneration += 1;
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
