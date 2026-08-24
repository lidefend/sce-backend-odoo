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
.product-page-pattern--collection { display:grid; gap:var(--sc-page-section-gap); min-width:0; }
</style>
