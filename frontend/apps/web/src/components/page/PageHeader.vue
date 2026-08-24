<template><ProductPageHeader :title="title" :subtitle="subtitle" presentation-mode="collection" /></template>

<script setup lang="ts">
import ProductPageHeader from '../product-page-header/ProductPageHeader.vue';
defineProps<{
  title: string;
  subtitle: string;
}>();
</script>
