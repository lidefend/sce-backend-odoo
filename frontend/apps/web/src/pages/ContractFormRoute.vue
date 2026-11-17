<template>
  <section
    v-if="!page && !loadError"
    class="record-route-state"
    data-product-page-mode="form"
    data-state="loading"
    aria-busy="true"
  >
    <ProductFormLoadingSkeleton loading-label="正在载入业务表单" />
  </section>
  <section v-else-if="loadError" class="record-route-state" data-product-page-mode="form" data-state="error">
    <ScErrorState title="业务表单加载失败" description="页面资源未能载入，请检查网络后重试。">
      <template #actions><ScButton @click="reloadRoute">重新加载页面</ScButton></template>
    </ScErrorState>
  </section>
  <component :is="page" v-else />
</template>

<script setup lang="ts">
import { onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, shallowRef, type Component } from 'vue';
import ProductFormLoadingSkeleton from '../components/product-record/ProductFormLoadingSkeleton.vue';
import ScButton from '../components/design-system/ScButton.vue';
import ScErrorState from '../components/design-system/ScErrorState.vue';
import { markStartupPhase } from '../app/performance/startupTiming';
import { createContractFormRouteLoader } from './contractFormRouteLoader';

const page = shallowRef<Component | null>(null);
const loadError = ref('');
const pageLoader = createContractFormRouteLoader(() => import('./ContractFormPage.vue'));
let hasMounted = false;

async function loadPage() {
  loadError.value = '';
  markStartupPhase('skeleton_shown', 'ContractFormRoute');
  const result = await pageLoader.load();
  if ('module' in result) {
    page.value = result.module.default;
  } else if ('error' in result) {
    loadError.value = 'record_route_asset_load_failed';
  }
}

function resumeIfNeeded() {
  if (!page.value && !loadError.value) void loadPage();
}

function reloadRoute() {
  if (loadError.value) {
    window.location.reload();
    return;
  }
  void loadPage();
}

onMounted(() => {
  hasMounted = true;
  resumeIfNeeded();
});

onActivated(() => {
  if (hasMounted) resumeIfNeeded();
});

onDeactivated(() => {
  pageLoader.invalidate();
});

onBeforeUnmount(() => {
  pageLoader.invalidate();
});
</script>

<style scoped>
.record-route-state { max-width: 640px; }
</style>
