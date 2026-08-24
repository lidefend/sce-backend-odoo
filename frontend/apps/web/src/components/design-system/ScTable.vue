<template>
  <TDesignTable
    v-bind="semanticPrimitiveIdentity('ScTable')"
    :data="data"
    :columns="columns"
    :row-key="rowKey"
    :size="normalizePrimitiveSize(size)"
    :loading="loading"
    :hover="hover"
    :stripe="stripe"
    :aria-label="label"
    @row-click="emit('rowClick', $event)"
  >
    <template v-for="(_, name) in $slots" #[name]="slotProps">
      <slot :name="name" v-bind="slotProps ?? {}" />
    </template>
  </TDesignTable>
</template>

<script setup lang="ts">
import { TDesignTable } from './tdesignPrimitiveBridge';
import { normalizePrimitiveSize, semanticPrimitiveIdentity, type ScPrimitiveSize } from './primitiveAdapter';

withDefaults(defineProps<{
  data?: Record<string, unknown>[];
  columns?: Record<string, unknown>[];
  rowKey?: string;
  size?: ScPrimitiveSize;
  loading?: boolean;
  hover?: boolean;
  stripe?: boolean;
  label: string;
}>(), {
  data: () => [],
  columns: () => [],
  rowKey: 'id',
  hover: true,
});
const emit = defineEmits<{ rowClick: [context: unknown] }>();
</script>
