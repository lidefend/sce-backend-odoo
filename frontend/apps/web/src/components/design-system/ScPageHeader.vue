<template>
  <ProductPageHeader :title="title" :subtitle="subtitle" :eyebrow="eyebrow" presentation-mode="collection">
    <template v-if="$slots.actions" #actions><slot name="actions" /></template>
  </ProductPageHeader>
</template>
<script setup lang="ts">
import ProductPageHeader from '../product-page-header/ProductPageHeader.vue';
defineProps<{ title: string; subtitle?: string; eyebrow?: string }>();
</script>
