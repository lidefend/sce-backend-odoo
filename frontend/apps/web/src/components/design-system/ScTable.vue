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
    :row-attributes="tdesignRowAttributes"
    :keyboard-row-hover="keyboardRowHover"
    :disable-data-page="disableDataPage"
    :table-content-width="tableContentWidth"
    :foot-data="footData"
    :selected-row-keys="selectedRowKeys"
    :row-selection-type="rowSelectionType"
    :select-on-row-click="selectOnRowClick"
    :aria-label="label"
    :data-row-count="data.length"
    :data-appearance="appearance"
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
import { computed, type ComputedRef } from 'vue';
import { TDesignTable } from './tdesignPrimitiveBridge';
import type { TDesignTableRowAttributes, TDesignTableRowData } from './tdesignPrimitiveBridge';
import { normalizePrimitiveSize, semanticPrimitiveIdentity, type ScPrimitiveSize } from './primitiveAdapter';

const props = withDefaults(defineProps<{
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
  disableDataPage?: boolean;
  tableContentWidth?: string;
  footData?: Record<string, unknown>[];
  selectedRowKeys?: Array<string | number>;
  rowSelectionType?: 'single' | 'multiple';
  selectOnRowClick?: boolean;
  label: string;
  appearance?: 'default' | 'surface' | 'flush' | 'collection';
}>(), {
  data: () => [],
  columns: () => [],
  rowKey: 'id',
  size: 'medium',
  hover: true,
  keyboardRowHover: true,
  disableDataPage: true,
  selectedRowKeys: () => [],
  footData: () => [],
  appearance: 'default',
});
function projectRowAttributes(attributes: Record<string, unknown> | undefined): Record<string, unknown> {
  return Object.fromEntries(Object.entries(attributes || {}).map(([name, value]) => [
    name,
    /^on[A-Z]/.test(name) && typeof value === 'function' ? value : String(value ?? ''),
  ]));
}
const tdesignRowAttributes = computed(() => typeof props.rowAttributes === 'function'
  ? (context: unknown) => projectRowAttributes(props.rowAttributes instanceof Function ? props.rowAttributes(context) : undefined)
  : projectRowAttributes(props.rowAttributes)) as unknown as ComputedRef<TDesignTableRowAttributes<TDesignTableRowData>>;
const emit = defineEmits<{
  rowClick: [context: unknown];
  rowDblclick: [context: unknown];
  selectChange: [keys: Array<string | number>, context: unknown];
}>();
function onSelectChange(keys: Array<string | number>, context: unknown) { emit('selectChange', keys, context); }
</script>
