<template>
  <article class="block block-record-summary">
    <ScCard class="block-card" :bordered="false" :title="block.title || '摘要'">
      <template #actions>
        <div v-if="actions.length" class="summary-actions">
          <ScButton
            v-for="action in actions"
            :key="`summary-action-${action.key}`"
            size="small"
            variant="ghost"
            @click="emitAction(action.key)"
          >
            {{ action.label || action.key }}
          </ScButton>
        </div>
      </template>
      <div v-if="rows.length" class="summary-grid">
        <article v-for="item in rows" :key="item.key" class="summary-item">
          <p class="summary-label">{{ item.label }}</p>
          <p class="summary-value">{{ item.value }}</p>
        </article>
      </div>
      <ScEmptyState v-else density="compact" :heading-level="5" title="暂无摘要信息" />
    </ScCard>
  </article>
</template>

<script setup lang="ts">
import ScCard from '../../design-system/ScCard.vue';
import { computed } from 'vue';
import { FIELD_VALUE_EMPTY_TEXT } from '../../../utils/fieldSemantics.ts';
import type { PageOrchestrationBlock } from '../../../app/pageOrchestration';
import type { PageBlockActionEvent } from '../../../app/pageOrchestration';
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

const actions = computed(() => Array.isArray(props.block.actions) ? props.block.actions : []);

const rows = computed(() => {
  const source = props.dataset && typeof props.dataset === 'object' ? props.dataset as Record<string, unknown> : {};
  const rawRows = Array.isArray(props.dataset)
    ? props.dataset
    : (Array.isArray(source.rows) ? source.rows : (Array.isArray(source.items) ? source.items : []));
  return rawRows.map((item, index) => {
    const row = item && typeof item === 'object' ? item as Record<string, unknown> : {};
    const rawValue = row.value ?? row.description;
    return {
      key: String(row.key || `summary-${index + 1}`),
      label: String(row.label || row.title || `项 ${index + 1}`),
      value: rawValue === null || rawValue === undefined || typeof rawValue === 'object' ? FIELD_VALUE_EMPTY_TEXT : String(rawValue),
    };
  });
});

function emitAction(actionKey: string) {
  const key = String(actionKey || '').trim();
  if (!key) return;
  emit('action', {
    actionKey: key,
    blockKey: props.block.key,
    zoneKey: props.zoneKey,
    item: {},
  });
}
</script>

<style scoped>
.block { min-width: 0; height: 100%; }
.block-card { min-width: 0; height: 100%; }
.summary-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.summary-grid { display: grid; gap: 8px; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }
.summary-item { border: 1px solid var(--sc-app-border); border-radius: 8px; padding: 8px; background: var(--sc-app-muted-bg); }
.summary-label { margin: 0; font-size: 12px; color: var(--sc-app-text-secondary); }
.summary-value { margin: 4px 0 0; font-size: 14px; font-weight: 600; color: var(--sc-app-text-primary); }

</style>
