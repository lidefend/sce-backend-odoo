<template>
  <ScTable
    :data="tableRows"
    :columns="tableColumns"
    :row-key="rowKey"
    :loading="loading"
    :label="accessibleLabel"
    :empty-text="emptyText"
    :row-attributes="rowAttributes"
    @row-click="onRowClick"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type {
  NoPortSlots,
  PrimitiveEventSource,
  TablePortEmits,
  TablePortProps,
  TablePortRow,
} from '@sc/ui/primitive-port';
import ScTable from '../ScTable.vue';

const props = defineProps<TablePortProps<TablePortRow>>();
const emit = defineEmits<TablePortEmits<TablePortRow>>();
defineSlots<NoPortSlots>();
const tableRows = computed(() => props.rows.map((row) => ({ ...row })));
const tableColumns = computed(() => props.columns.map((column) => ({
  ...column,
  colKey: column.key,
  title: column.label,
})));

function onRowClick(context: unknown) {
  const record = context as { row?: unknown; e?: Event };
  if (!record?.row || typeof record.row !== 'object') return;
  const nativeEvent = record.e;
  const source: PrimitiveEventSource = nativeEvent && !nativeEvent.isTrusted ? 'programmatic' : 'pointer';
  emit('rowActivate', record.row as TablePortRow, { source, nativeEvent });
}
function rowAttributes(context: { row?: unknown }) {
  if (!props.interactiveRows || !context?.row || typeof context.row !== 'object') return {};
  return {
    tabindex: 0,
    onKeydown: (event: KeyboardEvent) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
      emit('rowActivate', context.row as TablePortRow, { source: 'keyboard', nativeEvent: event });
    },
  };
}
</script>
