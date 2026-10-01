<template>
  <ScCard
    class="list-card-container"
    appearance="table"
    :bordered="false"
    data-semantic-component="ProductListSurface"
    data-list-card-container="official"
  >
    <slot />
  </ScCard>
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
 * Standard query lists have one container in both populated and empty states.
 * Dedicated worksheets and other page types do not instantiate this surface.
 * There is no model-dependent pass-through path left in this component.
 */
import ScCard from '../design-system/ScCard.vue';

defineOptions({ inheritAttrs: false });

</script>

<style scoped>
.list-card-container {
  box-sizing: border-box;
  padding: 32px;
  display: block;
  min-width: 0;
  width: 100%;
}
@media (max-width: 760px) {
  .list-card-container { padding: var(--sc-space-md); }
}
</style>
