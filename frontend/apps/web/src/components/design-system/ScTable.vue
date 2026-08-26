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
    :row-class-name="rowClassName"
    :row-attributes="rowAttributes"
    :keyboard-row-hover="keyboardRowHover"
    :selected-row-keys="selectedRowKeys"
    :row-selection-type="rowSelectionType"
    :select-on-row-click="selectOnRowClick"
    :aria-label="label"
    :data-row-count="data.length"
    data-semantic-driver="tdesign-table"
    @row-click="emit('rowClick', $event)"
    @row-dblclick="emit('rowDblclick', $event)"
    @select-change="onSelectChange"
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
  rowClassName?: string | ((context: unknown) => unknown);
  rowAttributes?: Record<string, unknown> | ((context: unknown) => Record<string, unknown>);
  keyboardRowHover?: boolean;
  selectedRowKeys?: Array<string | number>;
  rowSelectionType?: 'single' | 'multiple';
  selectOnRowClick?: boolean;
  label: string;
}>(), {
  data: () => [],
  columns: () => [],
  rowKey: 'id',
  size: 'medium',
  hover: true,
  keyboardRowHover: true,
  selectedRowKeys: () => [],
});
const emit = defineEmits<{
  rowClick: [context: unknown];
  rowDblclick: [context: unknown];
  selectChange: [keys: Array<string | number>, context: unknown];
}>();
function onSelectChange(keys: Array<string | number>, context: unknown) { emit('selectChange', keys, context); }
</script>
