<template><ProductPageHeader :title="title" :subtitle="subtitle" :presentation-mode="collectionMode" /></template>

<script setup lang="ts">
import ProductPageHeader from '../product-page-header/ProductPageHeader.vue';
import { resolveProductPageHeaderFixedMode } from '../../app/presentation/productPageHeaderAdapters';

defineProps<{
  title: string;
  subtitle: string;
}>();

const collectionMode = resolveProductPageHeaderFixedMode('page');
</script>
