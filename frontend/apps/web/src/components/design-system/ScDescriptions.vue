<template>
  <TDesignDescriptions v-bind="{ ...semanticPrimitiveIdentity('ScDescriptions'), ...$attrs }" :class="{ 'sc-descriptions--compact': compact }" :title="title" :column="column" :bordered="bordered">
    <TDesignDescriptionsItem v-for="item in items" :key="item.key" ><template #label><slot name="label" :item="item">{{ item.label }}</slot></template><slot name="item" :item="item">{{ item.value }}</slot></TDesignDescriptionsItem>
    <slot v-if="!items.length" />
  </TDesignDescriptions>
</template>
<script setup lang="ts">
import { TDesignDescriptions, TDesignDescriptionsItem } from './tdesignPrimitiveBridge';
import { semanticPrimitiveIdentity } from './primitiveAdapter';
export type ScDescriptionItem = { key: string | number; label: string; value?: unknown; [key: string]: unknown };
defineOptions({ inheritAttrs: false });
withDefaults(defineProps<{ title?: string; column?: number; bordered?: boolean; compact?: boolean; items?: ScDescriptionItem[] }>(), { title: '', column: 2, bordered: false, compact: false, items: () => [] });
</script>

<style scoped>
.sc-descriptions--compact {
  width: max-content;
  max-width: 100%;
}

.sc-descriptions--compact :deep(.t-descriptions__body) {
  width: auto;
}
</style>
