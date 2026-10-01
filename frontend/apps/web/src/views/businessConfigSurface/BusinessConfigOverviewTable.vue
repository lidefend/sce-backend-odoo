<template>
  <section class="configuration-overview" data-configuration-overview aria-label="配置总览">
    <h2>配置总览</h2>
    <p>{{ snapshotSummary.overview_scope }}</p>
    <p>草稿按配置记录状态统计；设计器未发布变更另见“待发布变更”。</p>
    <ScTable
      label="配置总览"
      data-configuration-overview-table="v1"
      row-key="sourceKey"
      size="small"
      :data="sourceRows"
      :columns="sourceColumns"
    />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { BusinessConfigSnapshotSummaryPayload } from '../../api/businessConfig';
import ScTable from '../../components/design-system/ScTable.vue';

/* Column titles are presentation labels for the declared count fields; the
 * source row label itself comes from the contract's source_category_labels. */
const COUNT_COLUMNS = [
  { colKey: 'total', title: '可见数量' },
  { colKey: 'draft', title: '草稿' },
  { colKey: 'published', title: '已发布' },
  { colKey: 'disabled', title: '已停用' },
  { colKey: 'saved', title: '已保存偏好' },
];

const props = defineProps<{ snapshotSummary: BusinessConfigSnapshotSummaryPayload }>();

const sourceColumns = computed(() => [
  { colKey: 'source', title: '来源', align: 'left' as const },
  ...COUNT_COLUMNS.map((column) => ({ ...column, align: 'right' as const })),
]);

const sourceRows = computed(() => {
  const labels = props.snapshotSummary.source_category_labels || {};
  return Object.entries(props.snapshotSummary.source_counts || {}).map(([sourceKey, counts]) => ({
    sourceKey,
    // An undeclared key keeps its raw value; it is never silently reclassified.
    source: labels[sourceKey] || sourceKey,
    total: counts.total,
    draft: counts.draft,
    published: counts.published,
    disabled: counts.disabled,
    saved: counts.saved,
  }));
});
</script>
