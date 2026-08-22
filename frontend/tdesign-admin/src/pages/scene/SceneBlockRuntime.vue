<template>
  <section v-if="visible && !structural" class="scene-block" :class="`scene-block--${safeKind}`">
    <header v-if="showHeader" class="scene-block__header">
      <div>
        <h2>{{ blockTitle }}</h2>
        <p v-if="blockDescription">{{ blockDescription }}</p>
      </div>
      <t-space v-if="actions.length && !actionKinds.has(kind)" size="small">
        <t-button
          v-for="action in actions"
          :key="actionKey(action)"
          size="small"
          :theme="actionTheme(action)"
          :variant="actionVariant(action)"
          @click="emit('action', action)"
        >
          {{ actionLabel(action) }}
        </t-button>
      </t-space>
    </header>

    <t-alert v-if="unsupported" theme="warning" :title="blockTitle" :message="unsupportedMessage" />
    <t-alert
      v-else-if="kind === 'alert_panel'"
      :theme="alertTheme"
      :title="blockTitle"
      :message="alertMessage"
      close=""
    />

    <div v-else-if="metricKinds.has(kind) && metricItems.length" class="metric-grid">
      <article v-for="item in metricItems" :key="itemKey(item)" class="metric-item">
        <span>{{ itemLabel(item) }}</span>
        <strong>{{ itemValue(item) }}</strong>
        <small v-if="itemDescription(item)">{{ itemDescription(item) }}</small>
        <t-progress
          v-if="kind === 'progress_summary' && progressValue(item) !== null"
          :percentage="progressValue(item) || 0"
          size="small"
        />
      </article>
    </div>

    <div v-else-if="kind === 'toolbar'" class="toolbar-content">
      <t-space v-if="viewModes.length" size="small" break-line>
        <t-tag v-for="mode in viewModes" :key="String(mode.key || mode.value)" variant="light">
          {{ mode.label || mode.name || mode.key }}
        </t-tag>
      </t-space>
      <span v-if="searchFieldCount" class="toolbar-meta">{{ searchFieldCount }} 个检索字段</span>
      <span v-if="!viewModes.length && !searchFieldCount && !actions.length" class="empty-copy">暂无可用工具</span>
    </div>

    <div v-else-if="kind === 'statusbar'" class="statusbar-content">
      <t-tag
        v-for="state in statusbarStates"
        :key="itemKey(state)"
        :theme="toneTheme(state.tone || state.status || state.value)"
        :variant="state.active === true || state.current === true ? 'dark' : 'light'"
      >
        {{ itemLabel(state) }}
      </t-tag>
      <span v-if="!statusbarStates.length" class="empty-copy">暂无状态</span>
    </div>

    <div v-else-if="actionKinds.has(kind)" class="block-actions">
      <t-button
        v-for="action in actions"
        :key="actionKey(action)"
        :theme="actionTheme(action)"
        :variant="actionVariant(action)"
        @click="emit('action', action)"
      >
        {{ actionLabel(action) }}
      </t-button>
      <span v-if="!actions.length" class="empty-copy">暂无可执行操作</span>
    </div>

    <div v-else-if="listKinds.has(kind) && listItems.length" class="item-list" :class="`item-list--${kind}`">
      <button
        v-for="item in listItems"
        :key="itemKey(item)"
        type="button"
        class="item-row"
        :disabled="!hasItemTarget(item)"
        @click="emitItem(item)"
      >
        <span class="item-row__body">
          <strong>{{ itemLabel(item) }}</strong>
          <small v-if="itemDescription(item)">{{ itemDescription(item) }}</small>
        </span>
        <t-tag v-if="itemValue(item) !== '—'" size="small" variant="light" :theme="toneTheme(item.tone || item.status)">
          {{ itemValue(item) }}
        </t-tag>
        <t-icon v-if="hasItemTarget(item)" name="chevron-right" />
      </button>
    </div>

    <t-table
      v-else-if="tableKinds.has(kind) && tableRows.length"
      :data="tableRows"
      :columns="tableColumns"
      row-key="id"
      size="small"
      stripe
      hover
    />

    <div v-else-if="kind === 'kanban_board' && kanbanLanes.length" class="scene-kanban">
      <section v-for="lane in kanbanLanes" :key="lane.key" class="scene-kanban__lane">
        <header>
          <strong>{{ lane.label }}</strong
          ><t-tag size="small" variant="light">{{ lane.items.length }}</t-tag>
        </header>
        <button
          v-for="item in lane.items"
          :key="itemKey(item)"
          type="button"
          class="scene-kanban__card"
          :disabled="!hasItemTarget(item)"
          @click="emitItem(item)"
        >
          <strong>{{ itemLabel(item) }}</strong
          ><small>{{ itemDescription(item) }}</small>
        </button>
      </section>
    </div>

    <div v-else-if="kind === 'content' && projectionItems.length" class="metric-grid">
      <article v-for="item in projectionItems" :key="itemKey(item)" class="metric-item">
        <span>{{ itemLabel(item) }}</span>
        <strong>{{ itemValue(item) }}</strong>
        <small v-if="itemDescription(item)">{{ itemDescription(item) }}</small>
      </article>
    </div>

    <p v-else class="empty-copy">{{ emptyText }}</p>
  </section>
</template>
<script setup lang="ts">
import { computed } from 'vue';

import { normalizeSceneBlockKind, resolveSceneBlockRegistryEntry, sceneBlockReasonCode } from './sceneBlockRegistry';

type Dict = Record<string, any>;

const props = defineProps<{ block: Dict }>();
const emit = defineEmits<{ action: [action: Dict] }>();

const metricKinds = new Set(['metric_row', 'overview_strip', 'progress_summary', 'record_summary']);
const listKinds = new Set(['todo_list', 'warning_list', 'shortcut_grid', 'activity_feed', 'entry_grid']);
const tableKinds = new Set(['record_table', 'list_view', 'relation_block']);
const actionKinds = new Set(['primary_actions', 'smart_actions', 'action_bar']);
const kind = computed(() =>
  normalizeSceneBlockKind(props.block.kind || props.block.type || props.block.block_type || 'content'),
);
const registryEntry = computed(() => resolveSceneBlockRegistryEntry(kind.value));
const safeKind = computed(() => kind.value.replace(/[^a-z0-9_-]/g, '-') || 'content');
const payload = computed(() => asDict(props.block.payload));
const visible = computed(() => props.block.visible !== false);
const structural = computed(() => ['page_shell', 'header_bar', 'footer', 'pagination'].includes(kind.value));
const unsupported = computed(() => !registryEntry.value);
const unsupportedMessage = computed(() =>
  String(
    props.block.reason_code ||
      props.block.reasonCode ||
      `${sceneBlockReasonCode(kind.value)}: ${kind.value || 'unknown'}`,
  ),
);
const blockTitle = computed(() => String(props.block.title || payload.value.title || kindLabel(kind.value)));
const blockDescription = computed(() =>
  String(props.block.description || payload.value.description || payload.value.summary || ''),
);
const actions = computed(() => normalizeRows(props.block.actions || payload.value.actions));
const showHeader = computed(() => kind.value !== 'alert_panel' && Boolean(blockTitle.value || actions.value.length));
const metricItems = computed(() =>
  normalizeRows(
    payload.value.overview_items ||
      payload.value.metrics ||
      payload.value.items ||
      payload.value.summary_items ||
      asDict(payload.value.group_summary).items,
  ),
);
const projectionItems = computed(() => {
  const projection = asDict(payload.value.projection);
  return normalizeRows(projection.overview_strip || projection.summary_items || asDict(projection.group_summary).items);
});
const listItems = computed(() =>
  normalizeRows(
    payload.value.items ||
      payload.value.entries ||
      payload.value.rows ||
      payload.value.records ||
      payload.value.activities ||
      payload.value.alerts ||
      payload.value.todos,
  ),
);
const tableRows = computed(() =>
  normalizeRows(payload.value.rows || payload.value.records || payload.value.items || props.block.rows),
);
const tableColumns = computed(() => {
  const configured = normalizeRows(payload.value.columns || asDict(props.block.data_deps).columns)
    .map((column) => ({
      colKey: String(column.colKey || column.fieldCode || column.field_code || column.name || column.key || ''),
      title: String(column.title || column.label || column.string || column.name || column.key || ''),
      minWidth: Number(column.minWidth || column.width || 120),
    }))
    .filter((column) => column.colKey);
  if (configured.length) return configured;
  const first = tableRows.value[0] || {};
  return Object.keys(first)
    .filter((key) => !key.startsWith('_') && key !== 'id')
    .slice(0, 8)
    .map((key) => ({ colKey: key, title: key, minWidth: 120 }));
});
const kanbanLanes = computed(() => {
  const rows = normalizeRows(payload.value.lanes || payload.value.columns);
  if (rows.length) {
    return rows.map((lane) => ({
      key: String(lane.key || lane.id || lane.label),
      label: String(lane.label || lane.name || lane.key || '未分类'),
      items: normalizeRows(lane.items || lane.rows || lane.records),
    }));
  }
  const items = normalizeRows(payload.value.items || payload.value.records);
  const groups = new Map<string, Dict[]>();
  items.forEach((item) => {
    const key = String(item.group_key || item.state || item.status || 'default');
    groups.set(key, [...(groups.get(key) || []), item]);
  });
  return [...groups].map(([key, laneItems]) => ({ key, label: key === 'default' ? '未分类' : key, items: laneItems }));
});
const viewModes = computed(() => normalizeRows(payload.value.view_modes || payload.value.available_view_modes));
const searchFieldCount = computed(() => {
  const searchSurface = asDict(payload.value.search_surface);
  return normalizeRows(searchSurface.fields).length + normalizeRows(searchSurface.filters).length;
});
const statusbarStates = computed(() =>
  normalizeRows(payload.value.states || payload.value.items || props.block.states),
);
const alertMessage = computed(
  () => blockDescription.value || String(payload.value.message || payload.value.text || '暂无告警'),
);
const alertTheme = computed<'info' | 'success' | 'warning' | 'error'>(() => {
  const tone = String(payload.value.tone || props.block.tone || 'warning').toLowerCase();
  if (['danger', 'error', 'red', 'blocked', 'overdue'].includes(tone)) return 'error';
  if (['success', 'green', 'done', 'completed'].includes(tone)) return 'success';
  if (['warning', 'amber', 'pending'].includes(tone)) return 'warning';
  return 'info';
});
const emptyText = computed(() => blockDescription.value || '暂无数据');

function asDict(value: unknown): Dict {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Dict) : {};
}

function normalizeRows(value: unknown): Dict[] {
  return Array.isArray(value) ? value.filter((item): item is Dict => Boolean(item && typeof item === 'object')) : [];
}

function kindLabel(value: string) {
  const labels: Record<string, string> = {
    activity_feed: '最新动态',
    alert_panel: '风险提醒',
    content: '业务内容',
    kanban_board: '业务看板',
    list_view: '业务列表',
    metric_row: '核心指标',
    overview_strip: '业务概览',
    progress_summary: '进度概览',
    record_table: '业务记录',
    shortcut_grid: '快捷入口',
    todo_list: '待办事项',
    toolbar: '页面工具',
    warning_list: '风险事项',
  };
  return labels[value] || '场景内容';
}

function itemKey(item: Dict) {
  return String(item.key || item.id || item.code || item.name || item.label || JSON.stringify(item));
}

function itemLabel(item: Dict) {
  return String(item.label || item.title || item.name || item.display_name || item.key || '未命名事项');
}

function itemDescription(item: Dict) {
  return String(item.description || item.subtitle || item.summary || item.hint || item.note || '');
}

function itemValue(item: Dict) {
  const value = item.value ?? item.count ?? item.total ?? item.status_label;
  return value === undefined || value === null || value === '' ? '—' : String(value);
}

function progressValue(item: Dict): number | null {
  const value = Number(item.percentage ?? item.progress ?? item.value);
  return Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : null;
}

function actionKey(action: Dict) {
  return String(action.key || action.intent || action.label || JSON.stringify(action));
}

function actionLabel(action: Dict) {
  const key = String(action.key || '');
  const labels: Record<string, string> = {
    open_my_work: '打开我的工作',
    open_risk_center: '打开风险中心',
    open_scene: '打开场景',
    quick_search: '快速检索',
    refresh: '刷新',
  };
  return String(action.label && action.label !== key ? action.label : labels[key] || key || '执行');
}

function actionTheme(action: Dict) {
  const tone = String(action.tone || action.theme || action.tier || '').toLowerCase();
  if (['danger', 'error'].includes(tone)) return 'danger';
  if (tone === 'warning') return 'warning';
  if (tone === 'success') return 'success';
  return 'primary';
}

function actionVariant(action: Dict) {
  return String(action.tier || '').toLowerCase() === 'primary' ? 'base' : 'outline';
}

function toneTheme(value: unknown): 'primary' | 'success' | 'warning' | 'danger' {
  const tone = String(value || '').toLowerCase();
  if (['danger', 'error', 'red', 'blocked', 'overdue'].includes(tone)) return 'danger';
  if (['warning', 'amber', 'pending'].includes(tone)) return 'warning';
  if (['success', 'green', 'done', 'completed'].includes(tone)) return 'success';
  return 'primary';
}

function itemAction(item: Dict) {
  return asDict(
    item.action || item.target || (item.route || item.scene_key || item.action_id || item.menu_id ? item : null),
  );
}

function hasItemTarget(item: Dict) {
  return Object.keys(itemAction(item)).length > 0;
}

function emitItem(item: Dict) {
  const action = itemAction(item);
  if (Object.keys(action).length) emit('action', action);
}
</script>
<style scoped>
.scene-block {
  min-width: 0;
  padding: 18px;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 8px;
  background: var(--td-bg-color-container);
}

.scene-block__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.scene-block__header h2,
.scene-block__header p {
  margin: 0;
}

.scene-block__header h2 {
  font-size: 18px;
}

.scene-block__header p {
  margin-top: 5px;
  color: var(--td-text-color-secondary);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.metric-item {
  display: grid;
  gap: 7px;
  min-width: 0;
  padding: 14px;
  border-left: 3px solid var(--td-brand-color);
  background: var(--td-bg-color-secondarycontainer);
}
.scene-kanban {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}
.scene-kanban__lane {
  padding: 12px;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
  background: var(--td-bg-color-secondarycontainer);
}
.scene-kanban__lane > header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}
.scene-kanban__card {
  display: grid;
  width: 100%;
  gap: 5px;
  padding: 12px;
  margin-top: 8px;
  text-align: left;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 5px;
  background: var(--td-bg-color-container);
  cursor: pointer;
}
.scene-kanban__card small {
  color: var(--td-text-color-secondary);
}

.metric-item span,
.metric-item small,
.toolbar-meta,
.empty-copy {
  color: var(--td-text-color-secondary);
}

.metric-item strong {
  font-size: 24px;
  overflow-wrap: anywhere;
}

.item-list {
  display: grid;
  gap: 8px;
}

.item-list--shortcut_grid {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.item-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-width: 0;
  padding: 12px 14px;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
  background: var(--td-bg-color-container);
  color: var(--td-text-color-primary);
  text-align: left;
}

.item-row:not(:disabled) {
  cursor: pointer;
}

.item-row:not(:disabled):hover {
  border-color: var(--td-brand-color);
  background: var(--td-bg-color-container-hover);
}

.item-row__body {
  display: grid;
  flex: 1;
  gap: 4px;
  min-width: 0;
}

.item-row__body strong,
.item-row__body small {
  overflow-wrap: anywhere;
}

.item-row__body small {
  color: var(--td-text-color-secondary);
}

.toolbar-content {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.statusbar-content,
.block-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.empty-copy {
  margin: 0;
  padding: 8px 0;
}

@media (width <= 720px) {
  .scene-block__header {
    flex-direction: column;
  }

  .item-list--shortcut_grid {
    grid-template-columns: 1fr;
  }
}
</style>
