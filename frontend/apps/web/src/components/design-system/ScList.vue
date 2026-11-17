<template>
  <ul
    v-if="layout === 'inline'"
    v-bind="{ ...semanticPrimitiveIdentity('ScList'), ...$attrs }"
    class="sc-list-inline"
    data-list-layout="inline"
  >
    <li v-for="item in items" :key="item.key" class="sc-list-inline__item">
      <slot name="item" :item="item" />
    </li>
    <slot v-if="!items.length" />
  </ul>
  <TDesignList v-else v-bind="{ ...semanticPrimitiveIdentity('ScList'), ...$attrs }" :split="split" :stripe="stripe">
    <TDesignListItem v-for="item in items" :key="item.key"><slot name="item" :item="item" /></TDesignListItem>
    <slot v-if="!items.length" />
  </TDesignList>
</template>
<script setup lang="ts">
import { TDesignList, TDesignListItem } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';
export type ScListItem = { key: string | number; [key: string]: unknown };
defineOptions({ inheritAttrs: false });
withDefaults(defineProps<{
  split?: boolean;
  stripe?: boolean;
  items?: ScListItem[];
  layout?: 'list' | 'inline';
}>(), {
  split: true,
  stripe: false,
  items: () => [],
  layout: 'list',
});
</script>

<style scoped>
.sc-list-inline {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sc-space-xs);
  margin: 0;
  padding: 0;
  list-style: none;
}

.sc-list-inline__item {
  display: inline-flex;
  align-items: center;
  gap: var(--sc-space-xs);
  min-width: 0;
  max-width: 100%;
}
</style>
