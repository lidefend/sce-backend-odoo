<template>
  <section class="sc-empty" :data-density="density" data-semantic-component="ScEmptyState" data-semantic-layer="primitive" data-state="empty" role="status" :aria-labelledby="titleId">
    <h2 :id="titleId">{{ title }}</h2>
    <p v-if="description">{{ description }}</p>
    <div v-if="$slots.actions" class="sc-action-group"><slot name="actions" /></div>
  </section>
</template>
<script setup lang="ts">
import { useId } from 'vue';
withDefaults(defineProps<{ title: string; description?: string; density?: 'regular' | 'compact' }>(), { density: 'regular' });
const titleId = `sc-empty-${useId()}`;
</script>
<style scoped>.sc-empty h2,.sc-empty p{margin:0}.sc-empty h2{font-size:var(--sc-product-text-section);line-height:1.35}.sc-empty p{max-width:56ch;margin-inline:auto}.sc-empty .sc-action-group{justify-content:center}.sc-empty[data-density="compact"]{min-height:0;padding:var(--sc-product-space-2);gap:var(--sc-product-space-1)}.sc-empty[data-density="compact"] h2{font-size:var(--sc-product-text-sm)}.sc-empty[data-density="compact"] p{font-size:var(--sc-product-text-xs)}</style>
