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

<script setup lang="ts" generic="Row extends TablePortRow">
import { computed } from 'vue';
import type {
  NoPortSlots,
  PrimitiveEventSource,
  TablePortEmits,
  TablePortProps,
  TablePortRow,
} from '@sc/ui/primitive-port';
import ScTable from '../ScTable.vue';

const props = defineProps<TablePortProps<Row>>();
const emit = defineEmits<TablePortEmits<Row>>();
defineSlots<NoPortSlots>();
const tableRows = computed<Record<string, unknown>[]>(() => props.rows.map(
  (row) => Object.fromEntries(Object.entries(row)),
));
const tableColumns = computed(() => props.columns.map((column) => ({
  ...column,
  colKey: column.key,
  title: column.label,
})));

function resolveOriginalRow(candidate: unknown): Row | undefined {
  if (!candidate || typeof candidate !== 'object') return undefined;
  const key = props.rowKey ?? 'id';
  const identity = Reflect.get(candidate, key);
  if (typeof identity !== 'string' && typeof identity !== 'number') return undefined;
  return props.rows.find((row) => Reflect.get(row, key) === identity);
}
function onRowClick(context: unknown) {
  if (!context || typeof context !== 'object' || !('row' in context)) return;
  const row = resolveOriginalRow(context.row);
  if (!row) return;
  const nativeEvent = 'e' in context && context.e instanceof Event ? context.e : undefined;
  const source: PrimitiveEventSource = nativeEvent && !nativeEvent.isTrusted ? 'programmatic' : 'pointer';
  emit('rowActivate', row, { source, nativeEvent });
}
function rowAttributes(context: unknown) {
  if (!props.interactiveRows || !context || typeof context !== 'object' || !('row' in context)) return {};
  const row = resolveOriginalRow(context.row);
  if (!row) return {};
  return {
    tabindex: 0,
    onKeydown: (event: KeyboardEvent) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
      emit('rowActivate', row, { source: 'keyboard', nativeEvent: event });
    },
  };
}
</script>
