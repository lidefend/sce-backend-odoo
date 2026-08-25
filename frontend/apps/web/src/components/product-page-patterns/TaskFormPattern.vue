<template>
  <section class="product-page-pattern product-page-pattern--task" data-product-page-pattern="task-form" data-presentation-mode="task" :data-render-profile="model.renderProfile">
    <slot />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ProductPageRenderProfile } from '../../app/presentation/productPageHeader';
import { resolveProductPagePatternModel } from '../../app/presentation/productPagePattern';

const props = defineProps<{ renderProfile: ProductPageRenderProfile }>();
const model = computed(() => resolveProductPagePatternModel({ key: 'task-form', presentationMode: 'task', renderProfile: props.renderProfile }));
</script>

<style scoped>
.product-page-pattern--task {
  display: grid;
  align-content: start;
  gap: var(--sc-page-section-gap);
  min-width: 0;
  width: min(100%, var(--sc-content-form-max));
  margin-inline: auto;
  container-type: inline-size;
}
</style>
