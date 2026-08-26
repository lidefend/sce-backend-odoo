<template>
  <article class="block block-alert-panel">
    <header class="block-header">
      <h4>{{ block.title || '提醒' }}</h4>
      <div class="block-header-actions">
        <ScButton
          v-for="action in actions"
          :key="`alert-action-${action.key}`"
          size="small"
          variant="ghost"
          @click="emitAction(action.key, {})"
        >
          {{ action.label || action.key }}
        </ScButton>
      </div>
    </header>

    <div v-if="items.length" class="alert-list">
      <article
        v-for="item in items"
        :key="item.id"
        class="alert-item"
        :class="`tone-${item.tone || 'danger'}`"
      >
        <p class="alert-title">
          <span>{{ item.title }}</span>
          <span class="alert-source" :class="`source-${item.source}`">{{ item.sourceLabel }}</span>
        </p>
        <p class="alert-desc">{{ item.description }}</p>
        <ScButton size="small" variant="primary" class="alert-open-btn" @click="emitAction(item.actionKey || 'open_scene', item.raw)">
          {{ item.buttonText }}
        </ScButton>
      </article>
    </div>
    <ScEmptyState v-else density="compact" :heading-level="5" title="当前无风险提醒" />
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { PageBlockActionEvent, PageOrchestrationBlock } from '../../../app/pageOrchestration';
import ScButton from '../../design-system/ScButton.vue';
import ScEmptyState from '../../design-system/ScEmptyState.vue';

const props = defineProps<{
  block: PageOrchestrationBlock;
  zoneKey: string;
  dataset: unknown;
}>();

const emit = defineEmits<{
  (event: 'action', payload: PageBlockActionEvent): void;
}>();

const actions = computed(() => (Array.isArray(props.block.actions) ? props.block.actions : []));
const maxItems = computed(() => {
  const payload = (props.block.payload && typeof props.block.payload === 'object')
    ? props.block.payload as Record<string, unknown>
    : {};
  const value = Number(payload.max_items || 0);
  return Number.isFinite(value) && value > 0 ? Math.trunc(value) : 0;
});
const items = computed(() => {
  if (!Array.isArray(props.dataset)) return [];
  const normalized = props.dataset.map((item, index) => {
    const row = item && typeof item === 'object' ? item as Record<string, unknown> : {};
    return {
      id: String(row.id || `alert-${index + 1}`),
      title: String(row.title || `提醒 ${index + 1}`),
      description: String(row.description || row.message || ''),
      source: normalizeSource(row.source),
      sourceLabel: String(row.source_label || row.sourceLabel || '业务事项'),
      tone: String(row.tone || row.alert_level || 'danger').toLowerCase(),
      buttonText: String(row.action_label || row.button_label || '查看'),
      actionKey: String(row.action_key || ''),
      raw: row,
    };
  });
  if (maxItems.value > 0) return normalized.slice(0, maxItems.value);
  return normalized;
});

function emitAction(actionKey: string, item: Record<string, unknown>) {
  const key = String(actionKey || '').trim();
  if (!key) return;
  emit('action', {
    actionKey: key,
    blockKey: props.block.key,
    zoneKey: props.zoneKey,
    item,
  });
}

function normalizeSource(value: unknown) {
  return String(value || 'business').toLowerCase().replace(/[^a-z0-9_-]/g, '_');
}

</script>

<style scoped>
.block {
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  background: var(--sc-app-panel);
  padding: 14px;
  height: 100%;
}
.block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.block-header h4 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}
.block-header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.alert-open-btn {
  justify-self: start;
}
.alert-list {
  display: grid;
  gap: 12px;
  margin-top: 12px;
  grid-template-columns: 1fr;
}

.alert-item {
  border: 1px solid var(--sc-app-danger-border);
  border-left-width: 5px;
  border-radius: 12px;
  padding: 12px;
  min-height: 100px;
}
.alert-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}
.alert-desc {
  margin: 6px 0 10px;
  font-size: 13px;
  color: var(--sc-app-text-secondary);
}
.alert-source {
  font-size: 11px;
  border-radius: 999px;
  padding: 1px 6px;
  border: 1px solid var(--sc-app-border);
  color: var(--sc-app-text-secondary);
  background: var(--sc-app-muted-bg);
}
.source-business {
  border-color: var(--sc-app-success-border);
  color: var(--sc-app-success-text);
  background: var(--sc-app-success-bg);
}
.source-capability_fallback {
  border-color: var(--sc-app-warning-border);
  color: var(--sc-app-warning-text);
  background: var(--sc-app-warning-bg);
}
.tone-danger { background: var(--sc-app-danger-bg); border-left-color: var(--sc-app-danger-text); }
.tone-warning { background: var(--sc-app-warning-bg); border-left-color: var(--sc-app-warning-text); }
.tone-info { background: var(--sc-app-info-bg); border-left-color: var(--sc-app-info-text); }
.tone-success { background: var(--sc-app-success-bg); border-left-color: var(--sc-app-success-text); }
.tone-neutral { background: var(--sc-app-muted-bg); border-left-color: var(--sc-app-border-strong); }
.risk-emphasis {
  border-left-width: 7px;
  box-shadow: 0 10px 20px var(--sc-app-shadow);
}
@container (max-width: 480px) {
  .block-header { align-items: flex-start; flex-direction: column; }
  .block-header-actions { width: 100%; }
}
</style>
