<template>
  <ScCard
    v-if="adopted"
    class="list-card-container"
    appearance="table"
    :bordered="false"
    data-semantic-component="ProductListSurface"
    data-list-card-container="official"
  >
    <slot />
  </ScCard>
  <slot v-else />
</template>

<script setup lang="ts">
/**
 * The official list surface container.
 *
 * Reference: `Tencent/tdesign-vue-next-starter@aeed57076217f7777158b905f353d73585bad1c4`
 * `src/pages/list/base/index.vue` wraps the query row and the table in one card
 * (`t-card.list-card-container :bordered="false"`, body padding removed).
 * This component is that container, expressed with the project's own primitive:
 * the card's `table` appearance already carries the zero body padding, so the
 * composition adds no selector of its own onto the vendor's internals.
 *
 * It composes; it does not decide. Whether a list is adopted is resolved from the
 * model by `app/presentation/standardListComposition.ts`, and outside the adopted
 * scope the slot is passed through unchanged so a list never renders through two
 * competing containers.
 */
import ScCard from '../design-system/ScCard.vue';

defineOptions({ inheritAttrs: false });

defineProps<{ adopted: boolean }>();
</script>

<style scoped>
.list-card-container {
  display: block;
  min-width: 0;
  width: 100%;
}
</style>
