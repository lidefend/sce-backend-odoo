<template>
  <TDesignDescriptions v-bind="{ ...$attrs, ...semanticPrimitiveIdentity('ScDescriptions') }" :title="title" :column="column" :bordered="bordered">
    <TDesignDescriptionsItem v-for="item in items" :key="item.key" :label="item.label"><slot name="item" :item="item">{{ item.value }}</slot></TDesignDescriptionsItem>
    <slot v-if="!items.length" />
  </TDesignDescriptions>
</template>
<script setup lang="ts">
import { TDesignDescriptions, TDesignDescriptionsItem } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';
export type ScDescriptionItem = { key: string | number; label: string; value?: unknown; [key: string]: unknown };
defineOptions({ inheritAttrs: false });
withDefaults(defineProps<{ title?: string; column?: number; bordered?: boolean; items?: ScDescriptionItem[] }>(), { column: 2, bordered: false, items: () => [] });
</script>
