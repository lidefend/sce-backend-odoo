<template>
  <section class="sc-alert sc-alert-danger" data-semantic-component="ScErrorState" data-semantic-layer="primitive" data-state="error" role="alert" :aria-labelledby="titleId">
    <h2 :id="titleId">{{ title }}</h2>
    <p>{{ description }}</p>
    <div v-if="$slots.actions" class="sc-action-group sc-error-state__actions"><slot name="actions" /></div>
  </section>
</template>
<script setup lang="ts">
import { useId } from 'vue';
defineProps<{ title: string; description: string }>();
const titleId = `sc-error-${useId()}`;
</script>
<style scoped>.sc-alert{display:grid;gap:var(--sc-product-space-2)}.sc-alert h2,.sc-alert p{margin:0}.sc-alert h2{font-size:var(--sc-product-text-section);line-height:1.35}.sc-error-state__actions{justify-content:flex-start}</style>
