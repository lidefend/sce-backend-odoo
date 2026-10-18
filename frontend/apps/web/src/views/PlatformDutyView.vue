<template>
  <ScPage
    class="platform-duty-page"
    content-layout="data-grid"
    data-product-page-mode="dashboard"
    data-semantic-component="PlatformDutyView"
  >
    <ProductPageHeader
      title="平台控制台"
      subtitle="平台职责、租户登记与运维入口由后端契约声明，本页只渲染。"
      presentation-mode="dashboard"
      render-profile="readonly"
    />
    <PlatformDutyPanel />
  </ScPage>
</template>

<script setup lang="ts">
import ProductPageHeader from '../components/product-page-header/ProductPageHeader.vue';
import PlatformDutyPanel from '../components/platform-duty/PlatformDutyPanel.vue';
import ScPage from '../components/design-system/ScPage.vue';
</script>
