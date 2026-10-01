<template>
  <article class="block block-entry-grid">
    <ScCard class="block-card" :bordered="false" :title="block.title || '入口'">
      <template #actions>
        <div class="block-header-actions">
          <ScButton
            v-for="action in actions"
            :key="`entry-action-${action.key}`"
            size="small"
            variant="ghost"
            @click="emitAction(action.key, {})"
          >
            {{ action.label || action.key }}
          </ScButton>
        </div>
      </template>

      <div v-if="items.length" class="entry-grid">
        <component
          :is="item.actionable ? ScButton : 'article'"
          v-for="item in items"
          :key="item.id"
          :variant="item.actionable ? 'ghost' : undefined"
          :appearance="item.actionable ? 'structured-content' : undefined"
          :type="item.actionable ? 'button' : undefined"
          class="entry-item"
          :class="{ 'entry-item--readonly': !item.actionable }"
          @click="item.actionable ? emitAction(item.actionKey || 'open_scene', item.raw) : undefined"
        >
          <p class="entry-title">{{ item.title }}</p>
          <p class="entry-hint">{{ item.hint }}</p>
          <div v-if="item.metaRows.length" class="entry-meta">
            <span v-for="meta in item.metaRows" :key="`${item.id}-${meta.label}`" class="entry-meta-chip">
              {{ meta.label }} {{ meta.value }}
            </span>
          </div>
        </component>
      </div>

      <ScEmptyState v-else density="compact" :heading-level="5" title="当前无可用入口" />
    </ScCard>
  </article>
</template>

<script setup lang="ts">
import ScCard from '../../design-system/ScCard.vue';
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
  const payload = props.block.payload && typeof props.block.payload === 'object'
    ? props.block.payload as Record<string, unknown>
    : {};
  const value = Number(payload.max_items || 0);
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
});
const items = computed(() => {
  if (!Array.isArray(props.dataset)) return [];
  const rows = maxItems.value > 0 ? props.dataset.slice(0, maxItems.value) : props.dataset;
  return rows.map((item, index) => {
    const row = item && typeof item === 'object' ? item as Record<string, unknown> : {};
    return {
      id: String(row.id || row.key || `entry-${index + 1}`),
      title: String(row.title || row.label || `入口 ${index + 1}`),
      hint: String(row.hint || row.subtitle || ''),
      actionKey: String(row.action_key || ''),
      actionable: Boolean(
        String(row.action_key || '').trim()
        || String(row.scene_key || '').trim()
        || String(row.route || '').trim()
        || Number(row.action_id || row.menu_id || row.entry_id || 0) > 0
      ),
      metaRows: [
        {
          label: '可用',
          value: Number(row.allow_count || row.ready_count || 0),
        },
        {
          label: '功能',
          value: Number(row.capability_count || 0),
        },
      ].filter((meta) => Number.isFinite(meta.value) && meta.value > 0),
      raw: row,
    };
  });
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
</script>

<style scoped>
.block { min-width: 0; height: 100%; }
.block-card { min-width: 0; height: 100%; }
.block-header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.entry-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}
.entry-item {
  border: 1px solid var(--sc-app-border);
  border-radius: 12px;
  background: var(--sc-app-panel);
  padding: 14px;
  text-align: left;
  cursor: pointer;
  min-height: 104px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
}
article.entry-item {
  display: block;
}

.entry-item:hover {
  border-color: var(--sc-semantic-surface-interactive);
  box-shadow: 0 14px 28px var(--sc-app-focus-ring);
  transform: translateY(-2px);
}
.entry-item--readonly {
  cursor: default;
}
.entry-item--readonly:hover {
  border-color: var(--sc-app-border);
  box-shadow: none;
  transform: none;
}
.entry-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}
.entry-hint {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--sc-app-text-secondary);
}
.entry-meta {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.entry-meta-chip {
  font-size: 11px;
  border-radius: 999px;
  padding: 2px 8px;
  border: 1px solid var(--sc-app-info-border);
  color: var(--sc-app-info-text);
  background: var(--sc-app-info-bg);
}
@container (max-width: 480px) {
  .entry-grid { grid-template-columns: 1fr; }
}
</style>
