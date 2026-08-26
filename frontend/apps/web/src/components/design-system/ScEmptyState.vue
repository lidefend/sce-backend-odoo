<template>
  <section class="sc-empty" :data-density="density" data-semantic-component="ScEmptyState" data-semantic-layer="primitive" data-state="empty" role="status" :aria-labelledby="titleId">
    <component :is="titleTag" :id="titleId" class="sc-empty__title">{{ title }}</component>
    <p v-if="description">{{ description }}</p>
    <div v-if="$slots.actions" class="sc-action-group"><slot name="actions" /></div>
  </section>
</template>
<script setup lang="ts">
import { computed, useId } from 'vue';
const props = withDefaults(defineProps<{
  title: string;
  description?: string;
  density?: 'regular' | 'compact';
  headingLevel?: 2 | 3 | 4 | 5 | 6;
}>(), { density: 'regular', headingLevel: 2 });
const titleId = `sc-empty-${useId()}`;
const titleTag = computed(() => `h${props.headingLevel}`);
</script>
<style scoped>.sc-empty__title,.sc-empty p{margin:0}.sc-empty__title{font-size:var(--sc-product-text-section);line-height:1.35}.sc-empty p{max-width:56ch;margin-inline:auto}.sc-empty .sc-action-group{justify-content:center}.sc-empty[data-density="compact"]{min-height:0;padding:var(--sc-product-space-2);gap:var(--sc-product-space-1)}.sc-empty[data-density="compact"] .sc-empty__title{font-size:var(--sc-product-text-sm)}.sc-empty[data-density="compact"] p{font-size:var(--sc-product-text-xs)}</style>
