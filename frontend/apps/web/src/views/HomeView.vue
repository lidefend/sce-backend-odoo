<template>
  <ScPage class="home-page sc-product-workspace-stack" content-layout="data-grid" data-product-page-mode="dashboard" data-semantic-component="HomeView">
    <ProductPageHeader :title="pageTitle" :subtitle="pageSubtitle" presentation-mode="dashboard" render-profile="readonly" />
    <DashboardPattern>
      <WorkspaceHome />
    </DashboardPattern>
  </ScPage>
</template>

<script setup lang="ts">
import { usePageIdentityRuntime } from '../app/pageIdentityRuntime';
import DashboardPattern from '../components/product-page-patterns/DashboardPattern.vue';
import ProductPageHeader from '../components/product-page-header/ProductPageHeader.vue';
import WorkspaceHome from '../components/role-home/WorkspaceHome.vue';
import ScPage from '../components/design-system/ScPage.vue';

const { title: pageTitle, subtitle: pageSubtitle } = usePageIdentityRuntime();
</script>
