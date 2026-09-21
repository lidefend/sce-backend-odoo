<template>
  <ProductPageHeader :title="title" :subtitle="subtitle" :eyebrow="eyebrow" :presentation-mode="collectionMode">
    <template v-if="$slots.actions" #actions><slot name="actions" /></template>
  </ProductPageHeader>
</template>
<script setup lang="ts">
import ProductPageHeader from '../product-page-header/ProductPageHeader.vue';
import { resolveProductPageHeaderFixedMode } from '../../app/presentation/productPageHeaderAdapters';
defineProps<{ title: string; subtitle?: string; eyebrow?: string }>();

const collectionMode = resolveProductPageHeaderFixedMode('design-system');
</script>
