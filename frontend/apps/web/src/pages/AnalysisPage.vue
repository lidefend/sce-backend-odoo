<template>
  <section
    class="analysis-page"
    :data-analysis-view="model.viewType"
    :data-analysis-state="model.ok ? 'ready' : 'unavailable'"
    :data-analysis-reason="model.reasonCode"
  >
    <slot name="toolbar" />
    <header class="analysis-head">
      <div>
        <p class="analysis-eyebrow">{{ model.viewType === 'pivot' ? labels.pivotEyebrow : labels.graphEyebrow }}</p>
        <h2>{{ title }}</h2>
      </div>
      <p class="analysis-count">{{ model.rows.length }} {{ labels.groupSuffix }}</p>
    </header>
    <ScInlineState v-if="!model.ok" state="error" :label="`${labels.unavailable}：${model.reasonCode}`" />
    <ScEmptyState v-else-if="!model.rows.length" :title="labels.emptyTitle" :description="labels.emptyHint" />
    <ScTable
      v-else-if="model.viewType === 'pivot'"
      :data="model.rows"
      :columns="tableColumns"
      row-key="__key"
      appearance="worksheet"
      :label="title"
      table-content-width="960px"
    />
    <div v-else class="analysis-chart" role="img" :aria-label="title" :data-graph-type="model.graphType">
      <article v-for="row in graphRows" :key="row.key" class="analysis-bar-row">
        <p class="analysis-bar-label">{{ row.label }}</p>
        <div class="analysis-bar-track"><span class="analysis-bar-fill" :style="{ width: `${row.percent}%` }" /></div>
        <p class="analysis-bar-value">{{ row.value }}</p>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import ScEmptyState from '../components/design-system/ScEmptyState.vue';
import ScInlineState from '../components/design-system/ScInlineState.vue';
import ScTable from '../components/design-system/ScTable.vue';
import type { AnalysisSurfaceModel } from '../app/contracts/actionViewAnalysisContract';

const props = defineProps<{
  title: string;
  model: AnalysisSurfaceModel;
  labels: {
    pivotEyebrow: string; graphEyebrow: string; groupSuffix: string;
    unavailable: string; emptyTitle: string; emptyHint: string;
  };
}>();

const tableColumns = computed(() => [...props.model.dimensions, ...props.model.measures].map((field) => ({
  colKey: field.name, title: field.label, ellipsis: true,
})));
const graphRows = computed(() => {
  const measure = props.model.measures[0];
  if (!measure) return [];
  const rows = props.model.rows.map((row) => ({
    key: row.__key, label: row.__label, value: Number(row[measure.name] || 0),
  }));
  const maximum = Math.max(0, ...rows.map((row) => Math.abs(row.value)));
  return rows.map((row) => ({ ...row, percent: maximum > 0 ? Math.max(2, Math.abs(row.value) / maximum * 100) : 0 }));
});
</script>

<style scoped>
.analysis-page { display: grid; gap: 16px; min-width: 0; }
.analysis-head { display: flex; align-items: end; justify-content: space-between; gap: 16px; }
.analysis-eyebrow, .analysis-count { margin: 0; color: var(--sc-text-secondary); font-size: 13px; }
.analysis-head h2 { margin: 4px 0 0; font-size: 20px; color: var(--sc-text-primary); }
.analysis-chart { display: grid; gap: 12px; padding: 18px; border: 1px solid var(--sc-border-secondary); border-radius: 10px; background: var(--sc-bg-container); }
.analysis-bar-row { display: grid; grid-template-columns: minmax(120px, 220px) minmax(120px, 1fr) minmax(72px, auto); gap: 12px; align-items: center; }
.analysis-bar-label, .analysis-bar-value { margin: 0; font-size: 13px; }
.analysis-bar-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.analysis-bar-value { text-align: right; font-variant-numeric: tabular-nums; }
.analysis-bar-track { height: 12px; overflow: hidden; border-radius: 999px; background: var(--sc-bg-secondary); }
.analysis-bar-fill { display: block; height: 100%; border-radius: inherit; background: var(--sc-semantic-surface-interactive); }
@media (max-width: 640px) {
  .analysis-bar-row { grid-template-columns: 1fr auto; }
  .analysis-bar-track { grid-column: 1 / -1; grid-row: 2; }
}
</style>
