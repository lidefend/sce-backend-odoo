<template>
  <ScDrawer
    v-if="mobile"
    :open="visible"
    title="主导航"
    appearance="navigation"
    placement="left"
    @close="emit('close')"
  >
    <ScAside
      :id="surfaceId"
      v-bind="$attrs"
      width="100%"
      class="product-mobile-navigation-surface"
      data-semantic-component="ProductMobileNavigationDrawer"
      data-navigation-driver="official-drawer"
    >
      <slot />
    </ScAside>
  </ScDrawer>
  <ScAside
    v-else-if="visible"
    :id="surfaceId"
    v-bind="$attrs"
    data-semantic-component="ProductMobileNavigationDrawer"
    data-navigation-driver="official-aside"
  >
    <slot />
  </ScAside>
</template>

<script setup lang="ts">
import ScAside from '../design-system/ScAside.vue';
import ScDrawer from '../design-system/ScDrawer.vue';

defineOptions({ inheritAttrs: false });
withDefaults(defineProps<{
  visible: boolean;
  mobile: boolean;
  surfaceId?: string;
}>(), { surfaceId: 'primary-sidebar' });
const emit = defineEmits<{ (event: 'close'): void }>();
</script>

<style scoped>
.product-mobile-navigation-surface {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: var(--sc-navigation-bg);
}
.product-mobile-navigation-surface :deep(.workspace-sidebar-panel) {
  flex: 1;
  min-height: 0;
}
</style>
