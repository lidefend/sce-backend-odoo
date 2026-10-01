<template>
  <article class="block block-record-table">
    <ScCard class="block-card" :bordered="false" :title="block.title || '表格'">

      <div v-if="rows.length" class="table-wrap">
        <ScTable class="mini-table" :label="block.title || '表格'" :data="rows" :columns="tableColumns" row-key="__rowKey" size="small" stripe />
      </div>
      <ScEmptyState v-else density="compact" :heading-level="5" :title="emptyMessage" />
    </ScCard>
  </article>
</template>

<script setup lang="ts">
import ScCard from '../../design-system/ScCard.vue';
import { computed } from 'vue';
import { FIELD_VALUE_EMPTY_TEXT } from '../../../utils/fieldSemantics.ts';
import type { PageOrchestrationBlock } from '../../../app/pageOrchestration';
import ScTable from '../../design-system/ScTable.vue';
import ScEmptyState from '../../design-system/ScEmptyState.vue';

const props = defineProps<{
  block: PageOrchestrationBlock;
  zoneKey: string;
  dataset: unknown;
}>();

type DataRow = Record<string, unknown>;

const source = computed(() => (
  props.dataset && typeof props.dataset === 'object' ? props.dataset as Record<string, unknown> : {}
));

const columns = computed<string[]>(() => {
  const raw = source.value.columns;
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => String(item || '').trim()).filter(Boolean);
});

const rows = computed<DataRow[]>(() => {
  const raw = source.value.rows;
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((item) => item && typeof item === 'object' && !Array.isArray(item))
    .map((item, index) => ({ ...(item as DataRow), __rowKey: index }));
});

const tableColumns = computed(() => columns.value.map((col, index) => ({
  colKey: col,
  title: columnLabel(col, index),
  cell: (_h: unknown, { row }: { row: DataRow }) => stringify(row[col]),
})));

const emptyMessage = computed(() => String(source.value.empty_message || '暂无数据'));

function columnLabel(col: string, index: number) {
  const labels = source.value.column_labels && typeof source.value.column_labels === 'object'
    ? source.value.column_labels as Record<string, string>
    : {};
  return labels[col] || `字段 ${index + 1}`;
}

function stringify(value: unknown) {
  if (value === null || value === undefined) return FIELD_VALUE_EMPTY_TEXT;
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}
</script>

<style scoped>
.block { min-width: 0; height: 100%; }
.block-card { min-width: 0; height: 100%; }
.table-wrap { max-width: 100%; overflow: auto; }
.mini-table { min-width: 560px; }

</style>
