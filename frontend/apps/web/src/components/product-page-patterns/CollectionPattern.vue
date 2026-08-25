<template>
  <section class="product-page-pattern product-page-pattern--collection" data-product-page-pattern="collection" data-presentation-mode="collection" data-render-profile="readonly">
    <slot />
  </section>
</template>

<script setup lang="ts">
import { resolveProductPagePatternModel } from '../../app/presentation/productPagePattern';

resolveProductPagePatternModel({ key: 'collection', presentationMode: 'collection', renderProfile: 'readonly' });
</script>

<style scoped>
.product-page-pattern--collection {
  display: grid;
  align-content: start;
  gap: var(--sc-product-workspace-stack-gap);
  min-width: 0;
  width: 100%;
  container-type: inline-size;
}
</style>
