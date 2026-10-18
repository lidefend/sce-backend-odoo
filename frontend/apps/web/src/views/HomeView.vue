<template>
  <ScPage class="home-page sc-product-workspace-stack" content-layout="data-grid" data-product-page-mode="dashboard" data-semantic-component="HomeView">
    <ProductPageHeader :title="pageTitle" :subtitle="pageSubtitle" presentation-mode="dashboard" render-profile="readonly" />
    <PlatformDutyPanel v-if="isPlatformControlAdmin" />
    <DashboardPattern>
      <WorkspaceHome />
    </DashboardPattern>
  </ScPage>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { usePageIdentityRuntime } from '../app/pageIdentityRuntime';
import DashboardPattern from '../components/product-page-patterns/DashboardPattern.vue';
import PlatformDutyPanel from '../components/platform-duty/PlatformDutyPanel.vue';
import ProductPageHeader from '../components/product-page-header/ProductPageHeader.vue';
import WorkspaceHome from '../components/role-home/WorkspaceHome.vue';
import ScPage from '../components/design-system/ScPage.vue';
import { useSessionStore } from '../stores/session';

const { title: pageTitle, subtitle: pageSubtitle } = usePageIdentityRuntime();
const session = useSessionStore();
const isPlatformControlAdmin = computed(
  () => session.user?.is_platform_admin === true && session.user?.platform_duty?.audience === 'platform-admin',
);
</script>
