<template>
  <article class="block block-progress-summary">
    <header class="block-header">
      <h4>{{ block.title || '进展' }}</h4>
    </header>
    <p v-if="summaryText" class="summary-text">{{ summaryText }}</p>
    <div class="progress-list">
      <article v-for="item in rows" :key="item.key" class="progress-item" :class="`kind-${item.kind}`">
        <div class="progress-line">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}{{ item.unit }}</strong>
        </div>
        <ScProgress v-if="item.kind === 'rate'" class="progress-track" :percentage="item.value" status="active" />
      </article>
    </div>
    <ScEmptyState v-if="!rows.length" density="compact" :heading-level="5" title="当前暂无进度数据" />
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { PageOrchestrationBlock } from '../../../app/pageOrchestration';
import ScEmptyState from '../../design-system/ScEmptyState.vue';
import ScProgress from '../../design-system/ScProgress.vue';

const props = defineProps<{
  block: PageOrchestrationBlock;
  zoneKey: string;
  dataset: unknown;
}>();

function clampPercent(raw: unknown) {
  const num = Number(raw || 0);
  if (!Number.isFinite(num)) return 0;
  return Math.max(0, Math.min(100, Math.round(num)));
}

function normalizeCount(raw: unknown) {
  const num = Number(raw || 0);
  if (!Number.isFinite(num)) return 0;
  return Math.max(0, Math.round(num));
}

const rows = computed(() => {
  const source = props.dataset && typeof props.dataset === 'object' ? props.dataset as Record<string, unknown> : {};
  const rawRows = Array.isArray(props.dataset)
    ? props.dataset
    : (Array.isArray(source.rows) ? source.rows : (Array.isArray(source.items) ? source.items : []));
  return rawRows.map((item, index) => {
    const row = item && typeof item === 'object' ? item as Record<string, unknown> : {};
    const unit = String(row.unit || '%');
    return {
      key: String(row.key || `progress-${index + 1}`),
      label: String(row.label || `进展 ${index + 1}`),
      value: unit === '%' ? clampPercent(row.value) : normalizeCount(row.value),
      unit,
      kind: unit === '%' ? 'rate' : 'count',
    };
  });
});

const summaryText = computed(() => {
  const source = props.dataset && typeof props.dataset === 'object' ? props.dataset as Record<string, unknown> : {};
  return String(source.summary || '').trim();
});
</script>

<style scoped>
.block { border: 1px solid var(--sc-app-border); border-radius: 8px; background: var(--sc-app-panel); padding: 12px; height: 100%; }
.block-header h4 { margin: 0 0 10px; font-size: 15px; font-weight: 600; }
.summary-text { margin: 0 0 10px; color: var(--sc-app-text-secondary); font-size: 13px; line-height: 1.5; }
.progress-list { display: grid; gap: 10px; }
.progress-item { border: 1px solid var(--sc-app-border); border-radius: 8px; padding: 10px; background: var(--sc-app-info-bg); min-height: 66px; }
.progress-item.kind-count { background: var(--sc-app-warning-bg); border-color: var(--sc-app-warning-border); }
.progress-line { display: flex; justify-content: space-between; font-size: 13px; }
.progress-track { margin-top: 8px; width: 100%; }
</style>
