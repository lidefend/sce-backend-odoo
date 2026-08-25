<template>
  <section
    v-if="items.length"
    class="collection-summary-strip"
    data-semantic-component="CollectionSummaryStrip"
    :aria-label="ariaLabel"
  >
    <article
      v-for="item in items"
      :key="item.key"
      class="collection-summary-strip__item"
      :class="`collection-summary-strip__item--${resolveTone(item.tone)}`"
      :data-summary-key="item.key"
      :data-summary-tone="resolveTone(item.tone)"
    >
      <p class="collection-summary-strip__label">{{ item.label }}</p>
      <p class="collection-summary-strip__value">{{ item.value }}</p>
    </article>
  </section>
</template>

<script setup lang="ts">
export type CollectionSummaryTone = 'neutral' | 'danger' | 'warning' | 'success' | 'info';

export type CollectionSummaryItem = {
  key: string;
  label: string;
  value: string;
  tone?: string;
};

defineProps<{
  ariaLabel: string;
  items: readonly CollectionSummaryItem[];
}>();

const allowedTones = new Set<CollectionSummaryTone>(['neutral', 'danger', 'warning', 'success', 'info']);

function resolveTone(value: string | undefined): CollectionSummaryTone {
  const normalized = String(value || '').trim();
  return allowedTones.has(normalized as CollectionSummaryTone)
    ? normalized as CollectionSummaryTone
    : 'neutral';
}
</script>

<style scoped src="./CollectionSummaryStrip.css"></style>
