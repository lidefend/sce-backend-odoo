<template>
  <TDesignList v-bind="{ ...$attrs, ...semanticPrimitiveIdentity('ScList') }" :split="split" :stripe="stripe">
    <TDesignListItem v-for="item in items" :key="item.key"><slot name="item" :item="item" /></TDesignListItem>
    <slot v-if="!items.length" />
  </TDesignList>
</template>
<script setup lang="ts">
import { TDesignList, TDesignListItem } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';
export type ScListItem = { key: string | number; [key: string]: unknown };
defineOptions({ inheritAttrs: false });
withDefaults(defineProps<{ split?: boolean; stripe?: boolean; items?: ScListItem[] }>(), { split: true, stripe: false, items: () => [] });
</script>
