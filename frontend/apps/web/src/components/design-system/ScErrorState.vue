<template>
  <section class="sc-alert sc-alert-danger" :data-density="density" data-semantic-component="ScErrorState" data-semantic-layer="primitive" data-state="error" role="alert" :aria-labelledby="titleId">
    <component :is="titleTag" :id="titleId" class="sc-error-state__title">{{ title }}</component>
    <p>{{ description }}</p>
    <div v-if="$slots.actions" class="sc-action-group sc-error-state__actions"><slot name="actions" /></div>
  </section>
</template>
<script setup lang="ts">
import { computed, useId } from 'vue';
const props = withDefaults(defineProps<{
  title: string;
  description: string;
  density?: 'regular' | 'compact';
  headingLevel?: 2 | 3 | 4 | 5 | 6;
}>(), { density: 'regular', headingLevel: 2 });
const titleId = `sc-error-${useId()}`;
const titleTag = computed(() => `h${props.headingLevel}`);
</script>
<style scoped>.sc-alert{display:grid;gap:var(--sc-product-space-2);min-width:0}.sc-error-state__title,.sc-alert p{margin:0;overflow-wrap:anywhere}.sc-error-state__title{font-size:var(--sc-product-text-section);line-height:1.35}.sc-error-state__actions{justify-content:flex-start}.sc-alert[data-density="compact"]{padding:var(--sc-product-space-2);gap:var(--sc-product-space-1)}.sc-alert[data-density="compact"] .sc-error-state__title{font-size:var(--sc-product-text-sm)}.sc-alert[data-density="compact"] p{font-size:var(--sc-product-text-xs)}</style>
