<template>
  <section class="product-page-pattern product-page-pattern--dashboard" data-product-page-pattern="dashboard" data-presentation-mode="dashboard" data-render-profile="readonly">
    <slot />
  </section>
</template>

<script setup lang="ts">
import { resolveProductPagePatternModel } from '../../app/presentation/productPagePattern';

resolveProductPagePatternModel({ key: 'dashboard', presentationMode: 'dashboard', renderProfile: 'readonly' });
</script>

<style scoped>
.product-page-pattern--dashboard { display:grid; gap:var(--sc-page-section-gap); min-width:0; }
</style>
