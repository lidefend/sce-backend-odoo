<template>
  <TDesignTimeline v-bind="{ ...$attrs, ...semanticPrimitiveIdentity('ScTimeline') }" :layout="layout" :mode="mode">
    <TDesignTimelineItem v-for="item in items" :key="item.key" :label="item.label" :dot-color="item.dotColor">
      <slot name="item" :item="item" />
    </TDesignTimelineItem>
    <slot v-if="!items.length" />
  </TDesignTimeline>
</template>
<script setup lang="ts">
import { TDesignTimeline, TDesignTimelineItem } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';
export type ScTimelineItem = { key: string | number; label?: string; dotColor?: string; [key: string]: unknown };
defineOptions({ inheritAttrs: false });
withDefaults(defineProps<{ layout?: 'horizontal' | 'vertical'; mode?: 'alternate' | 'same'; items?: ScTimelineItem[] }>(), { layout: 'vertical', mode: 'same', items: () => [] });
</script>
