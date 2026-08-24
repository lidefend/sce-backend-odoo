<template>
  <ProductPageHeader
    class="template-page-header"
    :title="title"
    :subtitle="subtitle"
    :hide-title="hideTitle"
    :presentation-mode="presentationMode"
    :render-profile="renderProfile"
    :dirty-state="dirtyState"
    :primary-actions="primaryActions"
    :overflow-actions="overflowActions"
    :exit-action="exitAction"
  >
    <template v-if="$slots.meta" #meta><slot name="meta" /></template>
    <template v-if="$slots.status" #status><slot name="status" /></template>
    <template v-if="$slots.actions" #actions><slot name="actions" /></template>
  </ProductPageHeader>
</template>

<script setup lang="ts">
import type { ProductPageDirtyState, ProductPageHeaderAction, ProductPagePresentationMode, ProductPageRenderProfile } from '../../app/presentation/productPageHeader';
import ProductPageHeader from '../product-page-header/ProductPageHeader.vue';

withDefaults(defineProps<{
  title: string;
  subtitle?: string;
  hideTitle?: boolean;
  presentationMode?: ProductPagePresentationMode;
  renderProfile?: ProductPageRenderProfile;
  dirtyState?: ProductPageDirtyState;
  primaryActions?: ProductPageHeaderAction[];
  overflowActions?: ProductPageHeaderAction[];
  exitAction?: ProductPageHeaderAction | null;
}>(), {
  subtitle: '', hideTitle: false, presentationMode: 'workspace', renderProfile: 'readonly', dirtyState: 'clean',
  primaryActions: () => [], overflowActions: () => [], exitAction: null,
});
</script>

<style scoped>.template-page-header { margin-bottom:var(--sc-space-sm); }</style>
