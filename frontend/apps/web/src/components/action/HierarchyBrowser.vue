<template>
  <section class="hierarchy-browser" :aria-label="labels.surface_aria">
    <ProductListHeader
      class="hierarchy-head"
      :loading="loading"
      :show-search="true"
      :search-value="keyword"
      :search-label="labels.search_label"
      :search-placeholder="labels.search_placeholder"
      :aligned-layout="true"
      :layout-style="columnGridStyle"
      @search-input="onSearchInput"
      @search-submit="loadRows(0)"
      @search-clear="clearSearch"
    >
      <template #actions>
        <ScButton v-for="action in actions" :key="action.key" :variant="action.variant === 'primary' ? 'primary' : 'secondary'" @click="openAction(action)">{{ action.label }}</ScButton>
      </template>
    </ProductListHeader>
    <div v-if="errorMessage" class="hierarchy-error" role="alert">{{ errorMessage }}</div>
    <div ref="layoutElement" class="hierarchy-layout" :class="{ resizing: resizingSide }" :style="layoutGridStyle">
      <aside class="hierarchy-tree">
        <h3>{{ config.tree_title }}</h3>
        <button class="tree-all" :class="{ active: !selectedNode }" @click="selectAll">{{ labels.all }}</button>
        <HierarchyTreeNode
          v-for="node in rootNodes"
          :key="node.key"
          :node="node"
          :selected-key="selectedNode?.key || ''"
          :expanded-keys="expandedKeys"
          :empty-children-label="labels.empty_children"
          @select="selectNode"
          @toggle="toggleNode"
        />
      </aside>
      <div
        class="hierarchy-resizer hierarchy-resizer-left"
        role="separator"
        aria-orientation="vertical"
        :aria-label="labels.resize_left"
        :aria-valuenow="leftWidth"
        :aria-valuemin="leftMinWidth"
        :aria-valuemax="leftMaxWidth"
        tabindex="0"
        @pointerdown="startResize('left', $event)"
        @keydown="resizeWithKeyboard('left', $event)"
      />
      <main class="hierarchy-list">
        <div class="list-context">
          <div><h3>{{ currentTitle }}</h3><p>{{ labels.total_prefix }} {{ total }} {{ labels.total_suffix }}</p></div>
          <ScButton :disabled="loading" @click="loadRows(offset)">{{ loading ? labels.loading : labels.refresh }}</ScButton>
        </div>
        <div v-if="loading && !rows.length" class="list-state">{{ labels.loading }}</div>
        <ScEmptyState v-else-if="!rows.length" class="list-state" :title="String(config.empty_title || '')" :description="String(config.empty_hint || '')" />
        <ScDataTable v-else class="table-scroll" :label="String(config.title || labels.surface_aria)">
            <thead><tr><th v-for="column in listConfig.columns" :key="column.field">{{ column.label }}</th></tr></thead>
            <tbody>
              <tr v-for="row in rows" :key="Number(row.id)" tabindex="0" :class="{ selected: Number(selectedRow?.id) === Number(row.id) }" @click="selectedRow = row" @dblclick="openRow(row.id)" @keyup.enter="selectedRow = row">
                <td v-for="column in listConfig.columns" :key="column.field">{{ displayValue(row[column.field], column) }}</td>
              </tr>
            </tbody>
        </ScDataTable>
        <footer v-if="total > pageSize" class="pager">
          <ScButton :disabled="offset <= 0 || loading" @click="loadRows(Math.max(0, offset - pageSize))">{{ labels.previous }}</ScButton>
          <span>{{ labels.page_prefix }} {{ Math.floor(offset / pageSize) + 1 }} / {{ Math.ceil(total / pageSize) }} {{ labels.page_suffix }}</span>
          <ScButton :disabled="offset + pageSize >= total || loading" @click="loadRows(offset + pageSize)">{{ labels.next }}</ScButton>
        </footer>
      </main>
      <div
        class="hierarchy-resizer hierarchy-resizer-right"
        role="separator"
        aria-orientation="vertical"
        :aria-label="labels.resize_right"
        :aria-valuenow="rightWidth"
        :aria-valuemin="rightMinWidth"
        :aria-valuemax="rightMaxWidth"
        tabindex="0"
        @pointerdown="startResize('right', $event)"
        @keydown="resizeWithKeyboard('right', $event)"
      />
      <aside class="hierarchy-detail">
        <div class="detail-head"><h3>{{ detailConfig.title }}</h3><ScButton v-if="selectedRow" @click="openRow(selectedRow.id)">{{ labels.open }}</ScButton></div>
        <div class="hierarchy-detail-scroll">
          <div v-if="!selectedRow" class="detail-empty">{{ labels.select_hint }}</div>
          <template v-else>
            <section v-for="section in detailConfig.sections" :key="section.title" class="detail-section">
              <h4>{{ section.title }}</h4>
              <dl>
                <template v-for="field in section.fields" :key="field.field">
                  <dt>{{ field.label }}</dt><dd>{{ displayValue(selectedRow[field.field], field) }}</dd>
                </template>
              </dl>
            </section>
          </template>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import {
  loadHierarchyRows,
  loadHierarchyTree,
  type HierarchyLevelConfig,
  type HierarchyTreeNode as HierarchyNode,
} from '../../app/action_runtime/hierarchyCollectionDataSource';
import { formatDisplayValue } from '../../utils/display';
import ScButton from '../design-system/ScButton.vue';
import ScDataTable from '../design-system/ScDataTable.vue';
import ScEmptyState from '../design-system/ScEmptyState.vue';
import ProductListHeader from '../product-list/ProductListHeader.vue';
import HierarchyTreeNode from './HierarchyTreeNode.vue';

type Dict = Record<string, unknown>;
type LevelConfig = HierarchyLevelConfig;
type TreeNode = HierarchyNode;
type Column = { field: string; label: string; type?: string; ttype?: string; selection?: Array<[unknown, string]> };
type DetailSection = { title: string; fields: Column[] };
type SurfaceAction = { key: string; label: string; action_id: number; menu_id: number; variant: string; route: string };
const props = withDefaults(defineProps<{ config: Dict; preferenceScope?: string }>(), { preferenceScope: 'default' });
const emit = defineEmits<{ 'open-record': [row: Dict]; 'open-action': [action: SurfaceAction] }>();
const rows = ref<Dict[]>([]); const total = ref(0); const offset = ref(0); const keyword = ref('');
const selectedNode = ref<TreeNode | null>(null); const selectedRow = ref<Dict | null>(null); const expandedKeys = ref(new Set<string>());
const rootNodes = ref<TreeNode[]>([]); const loading = ref(false); const errorMessage = ref('');
const leftWidth = ref(280); const leftMinWidth = ref(180); const leftMaxWidth = ref(520);
const rightWidth = ref(320); const rightMinWidth = ref(220); const rightMaxWidth = ref(560);
const layoutElement = ref<HTMLElement | null>(null); const workspaceHeight = ref(560); const workspaceMinHeight = ref(560);
const resizingSide = ref<'' | 'left' | 'right'>('');
let rowsRequestEpoch = 0;
let resizeStartX = 0; let resizeStartWidth = 0;
const defaultLabels: Dict = { surface_aria: 'hierarchy browser', subtitle: '', search_label: 'Search', search_placeholder: '', all: 'All', empty_children: 'No child nodes', total_prefix: '', total_suffix: '', loading: 'Loading…', refresh: 'Refresh', previous: 'Previous', next: 'Next', page_prefix: '', page_suffix: '', load_error: 'Unable to load data', open: 'Open', select_hint: 'Select a row to view details', resize_left: 'Resize navigation column', resize_right: 'Resize detail column' };
const labels = computed(() => ({ ...defaultLabels, ...(props.config.labels && typeof props.config.labels === 'object' ? props.config.labels as Dict : {}) }) as Record<string, string>);
const levels = computed<LevelConfig[]>(() => {
  const tree = props.config.tree && typeof props.config.tree === 'object' ? props.config.tree as Dict : {};
  return (Array.isArray(tree.levels) ? tree.levels : []).map((value) => {
    const row = value as Dict;
    return { key: String(row.key), model: String(row.model), fields: Array.isArray(row.fields) ? row.fields.map(String) : ['id', 'name'], label_field: String(row.label_field || 'name'), code_field: String(row.code_field || ''), parent_key: String(row.parent_key || ''), parent_field: String(row.parent_field || ''), self_parent_field: String(row.self_parent_field || ''), order: String(row.order || 'id asc') };
  });
});
const listConfig = computed(() => {
  const raw = props.config.list && typeof props.config.list === 'object' ? props.config.list as Dict : {};
  return { model: String(raw.model || ''), fields: Array.isArray(raw.fields) ? raw.fields.map(String) : ['id', 'name'], columns: (Array.isArray(raw.columns) ? raw.columns : []).map((row) => row as Column), bindings: raw.bindings && typeof raw.bindings === 'object' ? raw.bindings as Dict : {}, order: String(raw.order || 'id asc'), pageSize: Math.max(10, Math.min(200, Number(raw.page_size || 50))) };
});
const detailConfig = computed(() => {
  const raw = props.config.detail && typeof props.config.detail === 'object' ? props.config.detail as Dict : {};
  return { title: String(raw.title || ''), sections: (Array.isArray(raw.sections) ? raw.sections : []).map((section) => { const row = section as Dict; return { title: String(row.title || ''), fields: (Array.isArray(row.fields) ? row.fields : []).map((field) => field as Column) } as DetailSection; }) };
});
const actions = computed<SurfaceAction[]>(() => (Array.isArray(props.config.actions) ? props.config.actions : []).map((value) => {
  const row = value as Dict;
  return { key: String(row.key || row.action_id || ''), label: String(row.label || ''), action_id: Number(row.action_id || 0), menu_id: Number(row.menu_id || 0), variant: String(row.variant || ''), route: String(row.route || '') };
}).filter((row) => row.key && row.label && row.action_id > 0));
const columnGridStyle = computed(() => ({ gridTemplateColumns: `${leftWidth.value}px calc(var(--sc-component-hierarchy-browser-resizer-width) * 1px) minmax(360px, 1fr) calc(var(--sc-component-hierarchy-browser-resizer-width) * 1px) ${rightWidth.value}px` }));
const layoutGridStyle = computed(() => ({ ...columnGridStyle.value, height: `${workspaceHeight.value}px` }));
const pageSize = computed(() => listConfig.value.pageSize);
const currentTitle = computed(() => selectedNode.value ? [selectedNode.value.code, selectedNode.value.label].filter(Boolean).join(' ') : labels.value.all);
function displayValue(value: unknown, field?: Column): string { return formatDisplayValue(value, field); }
async function loadTree(): Promise<void> {
  rootNodes.value = await loadHierarchyTree(levels.value);
  expandedKeys.value = new Set(rootNodes.value.slice(0, 1).map((node) => node.key));
}
async function loadRows(nextOffset = 0): Promise<void> {
  const requestEpoch = ++rowsRequestEpoch;
  loading.value = true; errorMessage.value = '';
  try {
    const result = await loadHierarchyRows({ config: listConfig.value, selectedNode: selectedNode.value, keyword: keyword.value, offset: nextOffset });
    if (requestEpoch !== rowsRequestEpoch) return;
    rows.value = result.rows; total.value = result.total; offset.value = nextOffset; selectedRow.value = rows.value[0] || null;
  } catch (error) { if (requestEpoch === rowsRequestEpoch) errorMessage.value = error instanceof Error ? error.message : labels.value.load_error; }
  finally { if (requestEpoch === rowsRequestEpoch) loading.value = false; }
}
function selectAll(): void { selectedNode.value = null; void loadRows(0); }
function onSearchInput(event: Event): void { keyword.value = String((event.target as HTMLInputElement | null)?.value || ''); }
function clearSearch(): void { keyword.value = ''; void loadRows(0); }
function selectNode(node: TreeNode): void { selectedNode.value = node; void loadRows(0); }
function toggleNode(node: TreeNode): void { const next = new Set(expandedKeys.value); if (next.has(node.key)) next.delete(node.key); else next.add(node.key); expandedKeys.value = next; }
function storageKey(): string { return `sc:hierarchy-browser:${props.preferenceScope}:columns`; }
function tokenNumber(name: string, fallback: number): number {
  const value = Number.parseFloat(window.getComputedStyle(document.documentElement).getPropertyValue(name));
  return Number.isFinite(value) ? value : fallback;
}
function loadColumnTokens(): void {
  leftWidth.value = tokenNumber('--sc-component-hierarchy-browser-tree-width', leftWidth.value);
  leftMinWidth.value = tokenNumber('--sc-component-hierarchy-browser-tree-min-width', leftMinWidth.value);
  leftMaxWidth.value = tokenNumber('--sc-component-hierarchy-browser-tree-max-width', leftMaxWidth.value);
  rightWidth.value = tokenNumber('--sc-component-hierarchy-browser-detail-width', rightWidth.value);
  rightMinWidth.value = tokenNumber('--sc-component-hierarchy-browser-detail-min-width', rightMinWidth.value);
  rightMaxWidth.value = tokenNumber('--sc-component-hierarchy-browser-detail-max-width', rightMaxWidth.value);
  workspaceMinHeight.value = tokenNumber('--sc-component-hierarchy-browser-min-height', workspaceMinHeight.value);
}
function updateWorkspaceHeight(): void {
  const top = layoutElement.value?.getBoundingClientRect().top;
  if (top === undefined) return;
  const bottomGutter = tokenNumber('--sc-page-padding', 24);
  workspaceHeight.value = Math.max(workspaceMinHeight.value, Math.floor(window.innerHeight - top - bottomGutter));
}
function restoreColumnWidths(): void {
  try {
    const saved = JSON.parse(window.localStorage.getItem(storageKey()) || '{}') as Dict;
    if (Number(saved.left) >= leftMinWidth.value && Number(saved.left) <= leftMaxWidth.value) leftWidth.value = Number(saved.left);
    if (Number(saved.right) >= rightMinWidth.value && Number(saved.right) <= rightMaxWidth.value) rightWidth.value = Number(saved.right);
  } catch { /* Ignore unavailable or malformed browser storage. */ }
}
function persistColumnWidths(): void {
  try { window.localStorage.setItem(storageKey(), JSON.stringify({ left: leftWidth.value, right: rightWidth.value })); } catch { /* Storage is an enhancement only. */ }
}
function applyResize(side: 'left' | 'right', delta: number): void {
  if (side === 'left') leftWidth.value = Math.max(leftMinWidth.value, Math.min(leftMaxWidth.value, resizeStartWidth + delta));
  else rightWidth.value = Math.max(rightMinWidth.value, Math.min(rightMaxWidth.value, resizeStartWidth - delta));
}
function onResizeMove(event: PointerEvent): void { if (resizingSide.value) applyResize(resizingSide.value, event.clientX - resizeStartX); }
function stopResize(): void {
  if (!resizingSide.value) return;
  resizingSide.value = ''; persistColumnWidths();
  window.removeEventListener('pointermove', onResizeMove); window.removeEventListener('pointerup', stopResize);
}
function startResize(side: 'left' | 'right', event: PointerEvent): void {
  event.preventDefault(); resizingSide.value = side; resizeStartX = event.clientX; resizeStartWidth = side === 'left' ? leftWidth.value : rightWidth.value;
  window.addEventListener('pointermove', onResizeMove); window.addEventListener('pointerup', stopResize);
}
function resizeWithKeyboard(side: 'left' | 'right', event: KeyboardEvent): void {
  if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
  event.preventDefault(); resizeStartWidth = side === 'left' ? leftWidth.value : rightWidth.value;
  const direction = event.key === 'ArrowRight' ? 1 : -1;
  applyResize(side, side === 'left' ? direction * 16 : direction * -16); persistColumnWidths();
}
function openRow(id: unknown): void { const recordId = Number(id || 0); if (recordId) emit('open-record', { id: recordId }); }
function openAction(action: SurfaceAction): void {
  if (action.key) emit('open-action', action);
}
onMounted(async () => {
  loadColumnTokens(); restoreColumnWidths(); await nextTick(); updateWorkspaceHeight(); window.addEventListener('resize', updateWorkspaceHeight);
  loading.value = true;
  try { await loadTree(); await loadRows(0); } catch (error) { errorMessage.value = error instanceof Error ? error.message : labels.value.load_error; }
  finally { loading.value = false; await nextTick(); updateWorkspaceHeight(); }
});
onBeforeUnmount(() => { window.removeEventListener('pointermove', onResizeMove); window.removeEventListener('pointerup', stopResize); window.removeEventListener('resize', updateWorkspaceHeight); });
</script>

<style scoped>
.hierarchy-browser {
  display: grid;
  gap: 0;
  min-width: 0;
  color: var(--sc-app-text-primary);
}

.hierarchy-head {
  display: block;
  min-height: var(--sc-product-toolbar-height);
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-component-toolbar-radius) var(--sc-component-toolbar-radius) 0 0;
  background: var(--sc-app-panel);
  box-shadow: none;
}
.hierarchy-head :deep(.product-list-header__tools) { min-height: var(--sc-product-toolbar-height); }

.hierarchy-head h2,
.list-context h3,
.hierarchy-tree h3 { margin: 0; }
.hierarchy-head h2 { font-size: var(--sc-product-text-section); }
.hierarchy-tree h3 {
  color: var(--sc-app-text-secondary);
  font-size: var(--sc-product-text-body);
  font-weight: 600;
  line-height: var(--sc-product-line-body);
}
.hierarchy-head p,
.list-context p { margin: var(--sc-space-2xs) 0 0; color: var(--sc-app-text-secondary); }

.hierarchy-head :deep(.product-list-header__search) { padding-block: var(--sc-space-2xs); }
.hierarchy-head :deep(.product-list-header__actions) { padding: var(--sc-space-xs) var(--sc-surface-padding); }

.hierarchy-layout {
  display: grid;
  gap: 0;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--sc-app-border);
  border-top: 0;
  border-radius: 0 0 var(--sc-component-panel-radius) var(--sc-component-panel-radius);
  background: var(--sc-app-panel);
}
.hierarchy-tree,
.hierarchy-list,
.hierarchy-detail { min-width: 0; height: 100%; background: var(--sc-app-panel); }
.hierarchy-tree { grid-column: 1; padding: var(--sc-surface-padding); overflow: auto; }
.hierarchy-list { grid-column: 3; display: flex; flex-direction: column; overflow: hidden; padding: var(--sc-surface-padding); }
.hierarchy-detail { grid-column: 5; display: flex; flex-direction: column; overflow: hidden; }

.hierarchy-resizer {
  position: relative;
  z-index: 2;
  border: 0;
  background: var(--sc-app-border);
  cursor: col-resize;
  outline: none;
  touch-action: none;
}
.hierarchy-resizer::before {
  content: "";
  position: absolute;
  inset-block: 0;
  inset-inline: -5px;
}
.hierarchy-resizer::after {
  content: "";
  position: absolute;
  inset-block: 0;
  left: 50%;
  width: 1px;
  background: var(--sc-app-border);
  transform: translateX(-50%);
}
.hierarchy-resizer:hover::after,
.hierarchy-resizer:focus-visible::after,
.resizing .hierarchy-resizer::after { width: 2px; background: var(--sc-app-accent); }
.hierarchy-resizer-left { grid-column: 2; }
.hierarchy-resizer-right { grid-column: 4; }
.resizing { cursor: col-resize; user-select: none; }

.list-context { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--sc-toolbar-group-gap); }
.tree-all {
  width: 100%;
  min-height: var(--sc-touch-target-min);
  padding: var(--sc-space-xs);
  border: 0;
  border-radius: var(--sc-product-radius-control);
  background: transparent;
  color: var(--sc-app-text-primary);
  text-align: left;
  cursor: pointer;
}
.tree-all:hover { background: var(--sc-app-hover-bg); }
.tree-all.active { background: var(--sc-app-selected-bg); color: var(--sc-app-selected-text); }

.table-scroll { flex: 1; margin-top: var(--sc-space-sm); border: 0; border-radius: 0; box-shadow: none; }
.table-scroll :deep(.sc-product-table) { width: 100%; border-collapse: collapse; font-size: var(--sc-product-text-body); }
.table-scroll :deep(th),
.table-scroll :deep(td) {
  height: var(--sc-product-table-row-height);
  padding: calc(var(--sc-component-table-cell-padding-y) * 1px) calc(var(--sc-component-table-cell-padding-x) * 1px);
  border-bottom: 1px solid var(--sc-table-divider);
  text-align: left;
  white-space: nowrap;
}
.table-scroll :deep(th) {
  position: sticky;
  top: 0;
  height: calc(var(--sc-component-table-header-height) * 1px);
  background: var(--sc-table-header-bg);
  color: var(--sc-app-text-secondary);
}
.table-scroll :deep(tbody tr) { cursor: pointer; }
.table-scroll :deep(tbody tr:hover) { background: var(--sc-app-hover-bg); }
.table-scroll :deep(tbody tr.selected) { background: var(--sc-app-selected-bg); }

.list-state,
.detail-empty {
  display: grid;
  place-content: center;
  gap: var(--sc-space-xs);
  min-height: 380px;
  color: var(--sc-app-text-secondary);
  text-align: center;
}
.pager { display: flex; align-items: center; justify-content: flex-end; gap: var(--sc-toolbar-group-gap); padding-top: var(--sc-space-sm); }
.detail-head { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; gap: var(--sc-toolbar-gap); min-height: var(--sc-product-list-toolbar-height); padding: var(--sc-space-xs) var(--sc-surface-padding); border-bottom: 1px solid var(--sc-app-border); background: var(--sc-app-panel); }
.detail-head h3 { margin: 0; }
.hierarchy-detail-scroll { flex: 1 1 auto; min-height: 0; overflow: auto; padding: 0 var(--sc-surface-padding) var(--sc-surface-padding); }
.detail-section { margin-top: var(--sc-space-sm); padding-top: var(--sc-space-sm); border-top: 1px solid var(--sc-app-border); }
.detail-section h4 { margin: 0 0 var(--sc-space-xs); }
.detail-section dl { display: grid; grid-template-columns: minmax(70px, auto) 1fr; gap: var(--sc-space-xs) var(--sc-space-sm); margin: 0; font-size: var(--sc-product-text-sm); }
.detail-section dt { color: var(--sc-app-text-secondary); }
.detail-section dd { margin: 0; white-space: pre-wrap; word-break: break-word; }
.hierarchy-error {
  padding: var(--sc-space-xs) var(--sc-space-sm);
  border: 1px solid var(--sc-app-danger-border);
  border-radius: var(--sc-product-radius-control);
  background: var(--sc-app-danger-bg);
  color: var(--sc-app-danger-text);
}

@media (max-width: 1100px) {
  .hierarchy-head :deep(.product-list-header__tools--aligned) {
    grid-template-columns: 260px calc(var(--sc-component-hierarchy-browser-resizer-width) * 1px) minmax(360px, 1fr) !important;
    grid-template-areas: 'leading divider-left search' 'leading divider-left actions';
  }
  .hierarchy-head :deep(.product-list-header__search) { padding-inline: var(--sc-surface-padding); }
  .hierarchy-layout { grid-template-columns: 260px calc(var(--sc-component-hierarchy-browser-resizer-width) * 1px) minmax(0, 1fr) !important; }
  .hierarchy-detail { grid-column: 1 / 4; border-top: 1px solid var(--sc-app-border); }
  .hierarchy-resizer-right { display: none; }
}

@media (max-width: 800px) {
  .hierarchy-head :deep(.product-list-header__tools--aligned) {
    grid-template-columns: minmax(0, 1fr) !important;
    grid-template-areas: 'leading' 'search' 'actions';
  }
  .hierarchy-head :deep(.product-list-header__search) { padding: var(--sc-space-xs) var(--sc-surface-padding); }
  .hierarchy-head :deep(.product-list-header__actions) { align-items: stretch; flex-direction: column; }
  .hierarchy-layout { display: flex; flex-direction: column; }
  .hierarchy-layout { height: auto !important; min-height: calc(var(--sc-component-hierarchy-browser-min-height) * 1px); }
  .hierarchy-resizer { display: none; }
  .hierarchy-tree { max-height: 320px; }
  .hierarchy-list,
  .hierarchy-detail { border-top: 1px solid var(--sc-app-border); }
}
</style>
