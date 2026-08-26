<template>
  <section class="worksheet" :aria-label="labels.surface_aria" data-semantic-component="HierarchicalWorksheet" :data-state="loading ? 'loading' : errorMessage ? 'error' : sourceRows.length ? 'ready' : 'empty'" :aria-busy="loading || undefined">
    <ProductListHeader
      class="worksheet-head"
      :loading="loading"
      :show-search="true"
      :search-value="keyword"
      :search-label="labels.search"
      :search-placeholder="labels.search_placeholder"
      :aligned-layout="false"
      @search-input="onSearchInput"
      @search-submit="keyword = keyword.trim()"
      @search-clear="keyword = ''"
    >
      <template #actions>
        <ScButton v-for="action in actions" :key="action.key" :variant="action.variant === 'primary' ? 'primary' : 'secondary'" @click="emit('open-action', action)">{{ action.label }}</ScButton>
      </template>
    </ProductListHeader>
    <div v-if="errorMessage" class="worksheet-error" role="alert">{{ errorMessage }}</div>
    <div class="worksheet-layout" :style="layoutStyle">
      <aside class="worksheet-navigation">
        <h3>{{ navigationTitle }}</h3>
        <ScButton class="navigation-all" appearance="tree-item" variant="ghost" size="small" :class="{ active: !selectedNavigationNode }" @click="selectNavigation(null)">{{ labels.all }}</ScButton>
        <HierarchyTreeNode
          v-for="node in navigationRoots"
          :key="node.key"
          :node="node"
          :selected-key="selectedNavigationNode?.key || ''"
          :expanded-keys="navigationExpandedKeys"
          empty-children-label=""
          @select="selectNavigation"
          @toggle="toggleNavigation"
        />
      </aside>
      <div class="worksheet-resizer worksheet-resizer-navigation" role="separator" aria-orientation="vertical" :aria-label="labels.resize_navigation" tabindex="0" @pointerdown="startNavigationResize" />
      <main class="worksheet-main" :style="mainStyle">
        <section class="worksheet-grid-pane">
          <div class="worksheet-grid-toolbar">
            <div><strong>{{ currentScopeTitle }}</strong><span>{{ labels.total_prefix }} {{ visibleLeafCount }} {{ labels.total_suffix }}</span></div>
            <div v-if="!sourceOrderMode" class="worksheet-grid-actions">
              <ScButton @click="expandAll">{{ labels.expand_all }}</ScButton>
              <ScButton @click="collapseAll">{{ labels.collapse_all }}</ScButton>
            </div>
          </div>
          <div v-if="loading" class="worksheet-state">{{ labels.loading }}</div>
          <div v-else-if="!visibleRows.length" class="worksheet-state">{{ labels.empty }}</div>
          <div v-else class="worksheet-table-scroll">
            <ScTable
              :data="worksheetTableData"
              :columns="worksheetTableColumns"
              row-key="key"
              size="small"
              :table-content-width="tableContentWidth"
              :row-class-name="worksheetRowClassName"
              :row-attributes="worksheetRowAttributes"
              :label="currentScopeTitle"
              @row-click="onWorksheetRowClick"
              @row-dblclick="onWorksheetRowDblclick"
            />
          </div>
        </section>
        <div class="worksheet-resizer worksheet-resizer-detail" role="separator" aria-orientation="horizontal" :aria-label="labels.resize_detail" tabindex="0" @pointerdown="startDetailResize" />
        <section class="worksheet-detail">
          <nav class="worksheet-tabs" aria-label="detail tabs">
            <ScButton v-for="tab in detailTabs" :key="tab.key" variant="ghost" size="small" appearance="section-tab" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.label }}</ScButton>
            <ScButton
              v-if="selectedRecord"
              class="worksheet-open-record"
              variant="secondary"
              data-semantic-action="record.open"
              @click="emit('open-record', selectedRecord)"
            >{{ labels.open || '打开记录' }}</ScButton>
          </nav>
          <div v-if="!selectedRecord" class="worksheet-detail-empty">{{ labels.select_hint }}</div>
          <dl v-else class="worksheet-detail-fields">
            <template v-for="field in activeTabFields" :key="field.field">
              <dt>{{ field.label }}</dt><dd>{{ formatValue(selectedRecord[field.field], field) }}</dd>
            </template>
          </dl>
        </section>
      </main>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, h, onBeforeUnmount, onMounted, ref } from 'vue';
import { formatDisplayValue } from '../../utils/display';
import {
  collectNodeIds,
  loadHierarchicalWorksheet,
  relationId,
  type WorksheetDict,
  type WorksheetHierarchyConfig,
  type WorksheetNode,
  type WorksheetSheetConfig,
} from '../../app/action_runtime/hierarchicalWorksheetDataSource';
import { shouldOpenWorksheetRecordFromKeyboard } from '../../app/action_runtime/hierarchicalWorksheetInteraction';
import ScButton from '../design-system/ScButton.vue';
import ScTable from '../design-system/ScTable.vue';
import ProductListHeader from '../product-list/ProductListHeader.vue';
import HierarchyTreeNode from './HierarchyTreeNode.vue';

type Dict = Record<string, unknown>;
type Column = { field: string; label: string; type: string; selection: Array<[string, string]>; align: string; width: number; precision?: number };
type DetailField = { field: string; label: string; type: string; selection: Array<[string, string]> };
type DetailTab = { key: string; label: string; fields: DetailField[] };
type SurfaceAction = { key: string; label: string; action_id: number; menu_id: number; route: string; variant: string };
type VisibleEntry = { key: string; node: WorksheetNode; record: WorksheetDict | null; ordinal: number; rowKind: string };
type NavigationTreeNode = { key: string; id: number; levelKey?: string; code: string; label: string; children: NavigationTreeNode[] };

const props = withDefaults(defineProps<{ config: Dict; preferenceScope?: string }>(), { preferenceScope: 'default' });
const emit = defineEmits<{ 'open-record': [row: WorksheetDict]; 'open-action': [action: SurfaceAction] }>();

function openRecordFromKeyboard(event: KeyboardEvent, record: WorksheetDict | null): void {
  if (shouldOpenWorksheetRecordFromKeyboard(event, record)) emit('open-record', record as WorksheetDict);
}
const hierarchyConfig = computed(() => props.config.hierarchy as unknown as WorksheetHierarchyConfig);
const sheetConfig = computed(() => props.config.sheet as unknown as WorksheetSheetConfig);
const labels = computed(() => props.config.labels as Record<string, string>);
const columns = computed<Column[]>(() => Array.isArray((props.config.sheet as Dict)?.columns) ? (props.config.sheet as Dict).columns as Column[] : []);
const detailTabs = computed<DetailTab[]>(() => Array.isArray((props.config.detail as Dict)?.tabs) ? (props.config.detail as Dict).tabs as DetailTab[] : []);
const actions = computed<SurfaceAction[]>(() => (Array.isArray(props.config.actions) ? props.config.actions : []).map((raw) => raw as SurfaceAction));
const treeColumn = computed(() => String((props.config.hierarchy as Dict)?.tree_column || columns.value.find((column) => column.field === 'name')?.field || columns.value[0]?.field || ''));
const navigationTitle = computed(() => String((props.config.hierarchy as Dict)?.navigation_title || ''));
const roots = ref<WorksheetNode[]>([]);
const nodesById = ref(new Map<number, WorksheetNode>());
const recordsByNode = ref(new Map<number, WorksheetDict>());
const sourceRows = ref<WorksheetDict[]>([]);
const recordCount = ref(0);
const loading = ref(false);
const errorMessage = ref('');
const keyword = ref('');
const selectedNavigationNode = ref<WorksheetNode | null>(null);
const selectedNode = ref<WorksheetNode | null>(null);
const selectedRecord = ref<WorksheetDict | null>(null);
const sheetExpandedKeys = ref(new Set<string>());
const navigationExpandedKeys = ref(new Set<string>());
const activeTab = ref('');
const navigationWidth = ref(260);
const detailHeight = ref(210);
let resizeMode: '' | 'navigation' | 'detail' = '';
let resizeStart = 0;
let resizeStartSize = 0;

const leafValues = computed(() => new Set(hierarchyConfig.value.leaf_values || []));
const itemValues = computed(() => new Set(sheetConfig.value.item_values || []));
const summaryValues = computed(() => new Set(sheetConfig.value.summary_values || []));
const sourceOrderMode = computed(() => sheetConfig.value.presentation_mode === 'source_order');
const navigationRoots = computed(() => {
  const maxDepth = Number(hierarchyConfig.value.navigation_depth || 4);
  const clone = (node: WorksheetNode): WorksheetNode | null => {
    if (leafValues.value.has(node.kind) || node.depth >= maxDepth) return null;
    return { ...node, children: node.children.map(clone).filter(Boolean) as WorksheetNode[] };
  };
  return roots.value.map(clone).filter(Boolean) as WorksheetNode[];
});
const selectedScopeIds = computed(() => selectedNavigationNode.value ? collectNodeIds(selectedNavigationNode.value) : null);
const selectedScopeRecordIds = computed(() => (
  hierarchyConfig.value.navigation_mode === 'sheet_groups' && selectedNavigationNode.value
    ? new Set(selectedNavigationNode.value.recordIds || [])
    : null
));
const currentScopeTitle = computed(() => selectedNavigationNode.value ? [selectedNavigationNode.value.code, selectedNavigationNode.value.label].filter(Boolean).join(' ') : labels.value.all);
const visibleRows = computed<VisibleEntry[]>(() => {
  const output: VisibleEntry[] = [];
  const term = keyword.value.trim().toLowerCase();
  const scope = selectedScopeIds.value;
  if (sourceOrderMode.value) {
    let ordinal = 0;
    sourceRows.value.forEach((record) => {
      const nodeId = relationId(record[sheetConfig.value.binding_field]);
      const rowKind = String(record[sheetConfig.value.row_kind_field] || '');
      const isItem = !itemValues.value.size || itemValues.value.has(rowKind);
      if (selectedScopeRecordIds.value && !selectedScopeRecordIds.value.has(Number(record.id || 0))) return;
      if (hierarchyConfig.value.navigation_mode !== 'sheet_groups' && scope && (!nodeId || !scope.has(nodeId))) return;
      if (term && !Object.values(record).map(String).join(' ').toLowerCase().includes(term)) return;
      const recordId = Number(record.id || 0);
      const node = nodesById.value.get(nodeId) || {
        key: `source:${recordId}`,
        id: -recordId,
        code: '',
        label: String(record.name || ''),
        kind: rowKind,
        depth: rowKind === 'heading' ? 0 : 1,
        raw: record,
        children: [],
      };
      output.push({ key: `source:${recordId}`, node, record, ordinal: isItem ? ++ordinal : 0, rowKind });
    });
    return output;
  }
  const containsMatch = (node: WorksheetNode): boolean => {
    const record = recordsByNode.value.get(node.id);
    if (!term) return true;
    return [node.code, node.label, ...(record ? Object.values(record).map(String) : [])].join(' ').toLowerCase().includes(term)
      || node.children.some(containsMatch);
  };
  const visit = (node: WorksheetNode) => {
    if (scope && !scope.has(node.id)) return;
    if (!containsMatch(node)) return;
    const record = recordsByNode.value.get(node.id) || null;
    if (record || !leafValues.value.has(node.kind)) output.push({ key: node.key, node, record, ordinal: 0, rowKind: '' });
    if ((sheetExpandedKeys.value.has(node.key) || term) && node.children.length) node.children.forEach(visit);
  };
  roots.value.forEach(visit);
  let ordinal = 0;
  return output.map((entry) => ({ ...entry, ordinal: entry.record ? ++ordinal : 0 }));
});
const visibleLeafCount = computed(() => {
  const count = visibleRows.value.filter((entry) => entry.record && (!itemValues.value.size || itemValues.value.has(entry.rowKind))).length;
  return count || (keyword.value || selectedNavigationNode.value ? 0 : recordCount.value);
});
const activeTabFields = computed(() => detailTabs.value.find((tab) => tab.key === activeTab.value)?.fields || []);
const layoutStyle = computed(() => ({ gridTemplateColumns: `${navigationWidth.value}px 1px minmax(0, 1fr)` }));
const mainStyle = computed(() => ({ gridTemplateRows: `minmax(320px, 1fr) 1px ${detailHeight.value}px` }));
const tableContentWidth = computed(() => `${columns.value.reduce((sum, column) => sum + Number(column.width || 120), 0)}px`);
const worksheetTableData = computed(() => visibleRows.value as unknown as Array<Record<string, unknown>>);
const worksheetTableColumns = computed(() => columns.value.map((column) => ({
  colKey: column.field,
  title: column.label,
  width: column.width,
  className: ({ row }: { row: VisibleEntry }) => [`align-${column.align}`, { 'variance-nonzero': isVarianceCell(row, column) }],
  cell: (_h: unknown, { row }: { row: VisibleEntry }) => worksheetCell(row, column),
})));

function worksheetCell(entry: VisibleEntry, column: Column) {
  if (column.field !== treeColumn.value) return displayCell(entry, column);
  const toggle = !sourceOrderMode.value && entry.node.children.length
    ? h('button', {
      class: 'row-toggle',
      'aria-label': entry.node.label,
      onClick: (event: MouseEvent) => { event.stopPropagation(); toggleSheet(entry.node); },
    }, sheetExpandedKeys.value.has(entry.node.key) ? '▾' : '▸')
    : h('span', { class: 'row-toggle-spacer' });
  return h('div', { class: 'tree-cell', style: { paddingLeft: `${entry.node.depth * 18}px` } }, [
    toggle,
    h('span', displayCell(entry, column)),
  ]);
}
function worksheetRowClassName({ row }: { row: VisibleEntry }) {
  return {
    'group-row': !row.record,
    'record-row': Boolean(row.record),
    'item-row': itemValues.value.has(row.rowKind),
    'heading-row': row.rowKind === 'heading',
    'summary-row': summaryValues.value.has(row.rowKind),
    selected: selectedRecord.value?.id === row.record?.id,
  };
}
function worksheetRowAttributes({ row }: { row: VisibleEntry }) {
  return {
    tabindex: 0,
    onKeyup: (event: KeyboardEvent) => openRecordFromKeyboard(event, row.record),
  };
}
function worksheetContextRow(context: unknown): VisibleEntry | null {
  if (!context || typeof context !== 'object') return null;
  const row = (context as { row?: unknown }).row;
  return row && typeof row === 'object' ? row as VisibleEntry : null;
}
function onWorksheetRowClick(context: unknown) {
  const row = worksheetContextRow(context);
  if (row) selectEntry(row);
}
function onWorksheetRowDblclick(context: unknown) {
  const row = worksheetContextRow(context);
  if (row?.record) emit('open-record', row.record);
}

function groupValue(node: WorksheetNode, field: string): unknown {
  const source = hierarchyConfig.value.group_field_map?.[field];
  const value = source ? node.raw[source] : '';
  return value === null || value === undefined || value === false ? '' : value;
}
function formatValue(value: unknown, field: { type: string; selection?: Array<[string, string]>; precision?: number }): string {
  if (
    typeof field.precision === 'number'
    && ['float', 'monetary'].includes(String(field.type || '').trim().toLowerCase())
  ) {
    const numeric = typeof value === 'number' ? value : Number(value);
    if (Number.isFinite(numeric)) {
      return numeric.toLocaleString('zh-CN', {
        minimumFractionDigits: field.precision,
        maximumFractionDigits: field.precision,
      });
    }
  }
  return formatDisplayValue(value, { type: field.type, selection: field.selection || [] });
}
function displayCell(entry: VisibleEntry, column: Column): string {
  if (entry.record && column.field === sheetConfig.value.ordinal_field) return entry.ordinal ? String(entry.ordinal) : '';
  if ((sheetConfig.value.blank_fields_by_kind?.[entry.rowKind] || []).includes(column.field)) return '';
  if (entry.record) return formatValue(entry.record[column.field], column);
  if (!hierarchyConfig.value.group_field_map?.[column.field]) return '';
  const value = groupValue(entry.node, column.field);
  return value === '' ? '' : formatValue(value, column);
}
function isVarianceCell(entry: VisibleEntry, column: Column): boolean {
  if (!entry.record || column.field !== sheetConfig.value.variance_field) return false;
  const value = Number(entry.record[column.field] || 0);
  return Number.isFinite(value) && Math.abs(value) > Number(sheetConfig.value.variance_tolerance || 0);
}
function selectEntry(entry: VisibleEntry) {
  selectedNode.value = entry.node;
  selectedRecord.value = entry.record;
}
function selectNavigation(rawNode: NavigationTreeNode | null) {
  const node = rawNode as WorksheetNode | null;
  if (!node) { selectedNavigationNode.value = null; return; }
  const find = (items: WorksheetNode[]): WorksheetNode | null => {
    for (const item of items) {
      if (item.id === node.id) return item;
      const nested = find(item.children);
      if (nested) return nested;
    }
    return null;
  };
  selectedNavigationNode.value = find(roots.value) || node;
}
function toggleNavigation(rawNode: NavigationTreeNode) {
  const node = rawNode as WorksheetNode;
  const next = new Set(navigationExpandedKeys.value);
  if (next.has(node.key)) next.delete(node.key); else next.add(node.key);
  navigationExpandedKeys.value = next;
}
function toggleSheet(node: WorksheetNode) {
  const next = new Set(sheetExpandedKeys.value);
  if (next.has(node.key)) next.delete(node.key); else next.add(node.key);
  sheetExpandedKeys.value = next;
}
function expandAll() {
  const keys = new Set<string>();
  const visit = (node: WorksheetNode) => { if (node.children.length) keys.add(node.key); node.children.forEach(visit); };
  roots.value.forEach(visit);
  sheetExpandedKeys.value = keys;
}
function collapseAll() { sheetExpandedKeys.value = new Set(); }
function onSearchInput(value: string) { keyword.value = value; }
function storageKey() { return `sc:hierarchical-worksheet:${props.preferenceScope}:layout`; }
function persistLayout() { window.localStorage.setItem(storageKey(), JSON.stringify({ navigationWidth: navigationWidth.value, detailHeight: detailHeight.value })); }
function restoreLayout() {
  try {
    const value = JSON.parse(window.localStorage.getItem(storageKey()) || '{}');
    if (Number(value.navigationWidth) >= 200 && Number(value.navigationWidth) <= 480) navigationWidth.value = Number(value.navigationWidth);
    if (Number(value.detailHeight) >= 140 && Number(value.detailHeight) <= 420) detailHeight.value = Number(value.detailHeight);
  } catch { /* optional preference */ }
}
function startNavigationResize(event: PointerEvent) { event.preventDefault(); resizeMode = 'navigation'; resizeStart = event.clientX; resizeStartSize = navigationWidth.value; bindResize(); }
function startDetailResize(event: PointerEvent) { event.preventDefault(); resizeMode = 'detail'; resizeStart = event.clientY; resizeStartSize = detailHeight.value; bindResize(); }
function bindResize() { window.addEventListener('pointermove', resizeMove); window.addEventListener('pointerup', stopResize); }
function resizeMove(event: PointerEvent) {
  if (resizeMode === 'navigation') navigationWidth.value = Math.max(200, Math.min(480, resizeStartSize + event.clientX - resizeStart));
  if (resizeMode === 'detail') detailHeight.value = Math.max(140, Math.min(420, resizeStartSize - (event.clientY - resizeStart)));
}
function stopResize() { if (resizeMode) persistLayout(); resizeMode = ''; window.removeEventListener('pointermove', resizeMove); window.removeEventListener('pointerup', stopResize); }

onMounted(async () => {
  restoreLayout(); loading.value = true;
  try {
    const result = await loadHierarchicalWorksheet(hierarchyConfig.value, sheetConfig.value);
    roots.value = result.roots; nodesById.value = result.nodesById; recordsByNode.value = result.recordsByNode; sourceRows.value = result.sourceRows; recordCount.value = result.recordCount;
    expandAll();
    const navigationKeys = new Set<string>();
    navigationRoots.value.forEach((root) => navigationKeys.add(root.key));
    navigationExpandedKeys.value = navigationKeys;
    activeTab.value = detailTabs.value[0]?.key || '';
    const firstRecord = visibleRows.value.find((entry) => entry.record);
    if (firstRecord) selectEntry(firstRecord);
  } catch (error) { errorMessage.value = error instanceof Error ? error.message : String(error); }
  finally { loading.value = false; }
});
onBeforeUnmount(() => stopResize());
</script>

<style scoped>
.worksheet { display: grid; min-width: 0; color: var(--sc-app-text-primary); }
.worksheet-head { min-height: var(--sc-product-toolbar-height); border: 1px solid var(--sc-app-border); border-radius: var(--sc-component-toolbar-radius) var(--sc-component-toolbar-radius) 0 0; background: var(--sc-app-panel); box-shadow: none; }
.worksheet-layout { display: grid; height: calc(100vh - 170px); min-height: 600px; overflow: hidden; border: 1px solid var(--sc-app-border); border-top: 0; background: var(--sc-app-panel); }
.worksheet-navigation { min-width: 0; overflow: auto; padding: var(--sc-space-sm); }
.worksheet-navigation h3 { margin: 0 0 var(--sc-space-xs); color: var(--sc-app-text-secondary); font-size: var(--sc-product-text-body); }
.navigation-all { width: 100%; min-height: var(--sc-touch-target-min); padding: var(--sc-space-xs); text-align: left; }
.worksheet-resizer { position: relative; z-index: 2; background: var(--sc-app-border); }
.worksheet-resizer::after { position: absolute; content: ''; inset: -5px; }
.worksheet-resizer:hover { background: var(--sc-app-accent); }
.worksheet-resizer-navigation { cursor: col-resize; }
.worksheet-main { display: grid; min-width: 0; min-height: 0; overflow: hidden; }
.worksheet-grid-pane { display: grid; grid-template-rows: auto minmax(0, 1fr); min-height: 0; }
.worksheet-grid-toolbar { display: flex; align-items: center; justify-content: space-between; min-height: 48px; padding: 0 var(--sc-space-sm); border-bottom: 1px solid var(--sc-app-border); }
.worksheet-grid-toolbar span { margin-left: var(--sc-space-sm); color: var(--sc-app-text-secondary); }
.worksheet-grid-actions { display: flex; gap: var(--sc-space-xs); }
.worksheet-state { display: grid; place-items: center; color: var(--sc-app-text-secondary); }
.worksheet-table-scroll { min-height: 0; overflow: auto; }
:deep(.t-table) { width: 100%; font-size: var(--sc-product-text-body); }
:deep(.t-table th) { position: sticky; top: 0; white-space: nowrap; }
:deep(.t-table td) { overflow: hidden; text-overflow: ellipsis; }
:deep(.t-table tr.selected td) { background: var(--sc-app-selected-bg); }
:deep(.t-table .group-row td), :deep(.t-table .heading-row td) { background: var(--sc-app-subtle-bg); font-weight: 600; }
:deep(.t-table .summary-row td) { background: var(--sc-app-selected-bg); font-weight: 600; }
:deep(.align-right) { text-align: right; font-variant-numeric: tabular-nums; }
:deep(.variance-nonzero) { color: var(--sc-app-warning-text); font-weight: 600; }
:deep(.tree-cell) { display: flex; align-items: center; gap: var(--sc-space-2xs); min-width: 220px; }
:deep(.row-toggle) { width: 20px; padding: 0; border: 0; background: transparent; color: var(--sc-app-text-secondary); cursor: pointer; }
:deep(.row-toggle-spacer) { display: inline-block; width: 20px; }
.worksheet-resizer-detail { cursor: row-resize; }
.worksheet-detail { min-height: 0; overflow: hidden; background: var(--sc-app-panel); }
.worksheet-tabs { display: flex; min-height: 38px; padding: 0 var(--sc-space-sm); border-bottom: 1px solid var(--sc-app-border); }
.worksheet-open-record { margin: auto 0 auto auto; }
.worksheet-detail-empty { padding: var(--sc-space-md); color: var(--sc-app-text-secondary); }
.worksheet-detail-fields { display: grid; grid-template-columns: max-content minmax(180px, 1fr) max-content minmax(180px, 1fr); gap: var(--sc-space-xs) var(--sc-space-sm); max-height: calc(100% - 38px); margin: 0; padding: var(--sc-space-sm); overflow: auto; }
.worksheet-detail-fields dt { color: var(--sc-app-text-secondary); }
.worksheet-detail-fields dd { margin: 0; overflow-wrap: anywhere; }
.worksheet-error { padding: var(--sc-space-sm); color: var(--sc-app-danger); }
@media (max-width: 960px) { .worksheet-layout { grid-template-columns: 1fr !important; height: auto; } .worksheet-navigation, .worksheet-resizer-navigation { display: none; } .worksheet-main { min-height: 680px; } }
</style>
