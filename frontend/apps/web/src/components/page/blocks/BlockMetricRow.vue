<template>
  <article class="block block-metric-row">
    <header v-if="block.title" class="block-header">
      <h4>{{ block.title }}</h4>
    </header>

    <div v-if="metrics.length" class="metric-grid" :data-metric-count="metrics.length">
      <component
        :is="item.actionKey ? ScButton : 'article'"
        v-for="item in metrics"
        :key="item.key"
        class="metric-item"
        :class="`tone-${item.tone || 'neutral'}`"
        :type="item.actionKey ? 'button' : undefined"
        :variant="item.actionKey ? 'ghost' : undefined"
        :data-metric-key="item.key"
        :data-metric-tone="item.tone"
        :data-interactive="Boolean(item.actionKey)"
        :aria-label="item.actionKey ? `${item.label}：${item.value}` : undefined"
        @click="item.actionKey ? emitAction(item) : undefined"
      >
        <p class="metric-label">{{ item.label }}</p>
        <p class="metric-value">{{ item.value }}</p>
        <p v-if="item.delta || item.hint" class="metric-meta">{{ item.delta || item.hint }}</p>
      </component>
    </div>
    <ScEmptyState v-else density="compact" :heading-level="5" title="暂无指标" description="当前看板尚未提供可展示的指标数据。" />
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { PageBlockActionEvent, PageOrchestrationBlock } from '../../../app/pageOrchestration';
import ScButton from '../../design-system/ScButton.vue';
import ScEmptyState from '../../design-system/ScEmptyState.vue';

const METRIC_TONES = new Set(['neutral', 'success', 'warning', 'danger', 'info']);

type MetricItem = {
  key: string;
  label: string;
  value: string | number;
  delta?: string;
  hint?: string;
  tone?: string;
  actionKey?: string;
  raw?: Record<string, unknown>;
};

const props = defineProps<{
  block: PageOrchestrationBlock;
  zoneKey: string;
  dataset: unknown;
}>();

const emit = defineEmits<{
  (event: 'action', payload: PageBlockActionEvent): void;
}>();

const metrics = computed<MetricItem[]>(() => {
  if (Array.isArray(props.dataset)) {
    return props.dataset.map((item, index) => {
      const row = item && typeof item === 'object' ? item as Record<string, unknown> : {};
      return {
        key: String(row.key || `metric-${index + 1}`),
        label: String(row.label || `指标 ${index + 1}`),
        value: String(row.value ?? '--'),
        delta: String(row.delta || ''),
        hint: String(row.hint || ''),
        tone: normalizeMetricTone(row.tone),
        actionKey: String(row.action_key || ''),
        raw: row,
      };
    });
  }
  if (!props.dataset || typeof props.dataset !== 'object') return [];
  const row = props.dataset as Record<string, unknown>;
  return Object.entries(row)
    .filter(([key]) => !['title', 'subtitle', 'message', 'hint'].includes(key))
    .slice(0, 8)
    .map(([key, value]) => ({
      key,
      label: key,
      value: typeof value === 'object' ? JSON.stringify(value) : String(value ?? '--'),
      tone: 'neutral',
    }));
});

function normalizeMetricTone(value: unknown) {
  const tone = String(value || 'neutral').trim().toLowerCase();
  return METRIC_TONES.has(tone) ? tone : 'neutral';
}

function emitAction(item: MetricItem) {
  const actionKey = String(item.actionKey || '').trim();
  if (!actionKey) return;
  emit('action', {
    actionKey,
    blockKey: props.block.key,
    zoneKey: props.zoneKey,
    item: item.raw || {},
  });
}
</script>

<style scoped>
.block {
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  background: var(--sc-app-panel);
  padding: 12px;
  height: 100%;
}
.block-header h4 {
  margin: 0 0 10px;
  font-size: 15px;
  font-weight: 600;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}
.metric-item {
  border-radius: 10px;
  border: 1px solid var(--sc-app-border);
  padding: 12px;
  min-height: 110px;
  text-align: left;
  color: inherit;
  font: inherit;
  overflow: hidden;
}
.metric-item[data-interactive='true'] { cursor: pointer; }
.metric-item[data-interactive='true'] :deep(.sc-btn__content) {
  display: block;
  width: 100%;
  text-align: left;
}
.metric-item[data-interactive='true']:hover {
  border-color: var(--sc-semantic-surface-interactive);
  box-shadow: 0 10px 20px var(--sc-app-focus-ring);
}
.metric-item[data-interactive='true']:focus-visible { outline: 3px solid var(--sc-app-focus-ring); outline-offset: 2px; }
.metric-label {
  margin: 0;
  font-size: 13px;
  color: var(--sc-app-text-secondary);
}
.metric-value {
  margin: 8px 0 0;
  font-size: 26px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}
.metric-meta {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--sc-app-text-secondary);
}
.tone-success { background: var(--sc-app-success-bg); }
.tone-warning { background: var(--sc-app-warning-bg); }
.tone-danger { background: var(--sc-app-danger-bg); }
.tone-info { background: var(--sc-app-info-bg); }
.tone-neutral { background: var(--sc-app-muted-bg); }
@container (max-width: 480px) {
  .metric-grid { grid-template-columns: 1fr; }
  .metric-item { min-height: 96px; }
}
@media (prefers-reduced-motion: reduce) { .metric-item { transition: none; } }
</style>
