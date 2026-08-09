<template>
  <section ref="plannerElement" class="hierarchy-planner" :aria-label="labels.surface_aria">
    <ProductListHeader
      class="planner-head"
      :loading="loading"
      :show-search="true"
      :search-value="keyword"
      :search-label="labels.search_label"
      :search-placeholder="labels.search_placeholder"
      :aligned-layout="true"
      :layout-style="headerLayoutStyle"
      @search-input="onSearchInput"
      @search-submit="keyword = keyword.trim()"
      @search-clear="keyword = ''"
    >
      <template #leading><div class="planner-title"><strong>{{ title }}</strong><span>{{ labels.total_prefix }} {{ displayedTotal }} {{ labels.total_suffix }}</span></div></template>
      <template #actions>
        <ScButton v-if="createConfig.enabled" variant="primary" @click="createRecord">{{ createConfig.label }}</ScButton>
        <ScButton v-for="action in actions" :key="action.key" :variant="action.variant === 'primary' ? 'primary' : 'secondary'" @click="emit('open-action', action)">{{ action.label }}</ScButton>
      </template>
    </ProductListHeader>
    <dl v-if="governanceFacts.length" class="planner-governance" aria-label="governance status">
      <div v-for="fact in governanceFacts" :key="fact.key"><dt>{{ fact.label }}</dt><dd>{{ fact.value }}</dd></div>
    </dl>

    <div v-if="errorMessage" class="planner-error" role="alert">{{ errorMessage }}</div>
    <div v-if="successMessage" class="planner-success" role="status">{{ successMessage }}</div>
    <main class="planner-canvas">
      <div class="planner-toolbar">
        <div class="planner-selection">
          <span v-if="selectedEntry">{{ labels.selected_prefix }}：{{ selectedEntry.node.code }} {{ selectedEntry.node.label }}</span>
          <span v-else>{{ labels.select_hint }}</span>
        </div>
        <div class="planner-commands">
          <ScButton
            v-for="command in toolbarCommands"
            :key="command.key"
            :disabled="!commandEnabled(command) || commandBusy"
            variant="secondary"
            @click="runCommand(command)"
          >{{ command.label }}</ScButton>
          <ScButton :disabled="!selectedRecord" @click="openSelected">{{ labels.open }}</ScButton>
          <ScButton :disabled="!selectedRecord" @click="showDetail = !showDetail">{{ labels.details }}</ScButton>
          <div class="planner-menu">
            <ScButton :aria-expanded="activeMenu === 'more'" @click="toggleMenu('more')">{{ labels.more }}</ScButton>
            <div v-if="activeMenu === 'more'" class="planner-menu-popover">
              <ScButton v-for="command in overflowCommands" :key="command.key" :disabled="!commandEnabled(command) || commandBusy" variant="ghost" @click="runCommand(command)">{{ command.label }}</ScButton>
            </div>
          </div>
          <div class="planner-menu">
            <ScButton :aria-expanded="activeMenu === 'view'" @click="toggleMenu('view')">{{ labels.view }}</ScButton>
            <div v-if="activeMenu === 'view'" class="planner-menu-popover">
              <ScButton variant="ghost" @click="expandAll(); closeMenus()">{{ labels.expand_all }}</ScButton>
              <ScButton variant="ghost" @click="collapseAll(); closeMenus()">{{ labels.collapse_all }}</ScButton>
              <ScButton variant="ghost" :disabled="loading" @click="reload(); closeMenus()">{{ labels.refresh }}</ScButton>
            </div>
          </div>
        </div>
      </div>

      <div v-if="loading" class="planner-state">{{ labels.loading }}</div>
      <ScEmptyState v-else-if="!visibleEntries.length" class="planner-state" :title="String(config.empty_title || '')" :description="String(config.empty_hint || '')" />
      <ScDataTable v-else class="planner-grid" :label="title" :table-style="tableStyle">
        <colgroup><col v-for="column in columns" :key="column.field" :style="columnStyle(column)" /></colgroup>
        <thead><tr><th v-for="column in columns" :key="column.field">{{ column.label }}</th></tr></thead>
        <tbody>
          <tr
            v-for="entry in visibleEntries"
            :key="entry.node.key"
            :class="{ selected: Number(selectedRecord?.id) === entry.node.id, parent: entry.node.children.length }"
            tabindex="0"
            @click="selectEntry(entry)"
            @dblclick="openRecord(entry.record)"
            @keyup.enter="selectEntry(entry)"
          >
            <td v-for="column in columns" :key="column.field" :class="{ 'code-column': column.field === codeField }">
              <div v-if="column.field === codeField" class="code-cell" :style="{ paddingInlineStart: `${entry.depth * indentSize}px` }">
                <span v-if="entry.depth" class="tree-elbow" aria-hidden="true" /><span>{{ displayValue(entry.record[column.field], column) }}</span>
              </div>
              <div v-if="column.field === outlineField" class="outline-cell" :style="{ paddingInlineStart: `${entry.depth * indentSize}px` }">
                <button
                  v-if="entry.node.children.length"
                  class="outline-toggle"
                  :aria-label="entry.node.label"
                  @click.stop="toggle(entry.node)"
                ><ScIcon name="chevron-right" :size="14" :class="{ 'is-expanded': expandedKeys.has(entry.node.key) }" /></button>
                <span v-else class="outline-toggle-spacer" />
                <span>{{ displayValue(entry.record[column.field], column) }}</span>
              </div>
              <template v-else-if="column.field !== codeField">{{ displayValue(entry.record[column.field], column) }}</template>
            </td>
          </tr>
        </tbody>
      </ScDataTable>
      <aside v-if="showDetail && selectedRecord" class="planner-drawer" :aria-label="labels.details">
        <header><strong>{{ selectedEntry?.node.code }} {{ selectedEntry?.node.label }}</strong><ScIconButton :label="labels.close_details" @click="showDetail = false"><ScIcon name="close" :size="16" /></ScIconButton></header>
        <div class="planner-drawer-body">
          <section v-for="section in detailSections" :key="section.title">
            <h3>{{ section.title }}</h3>
            <dl><template v-for="field in section.fields" :key="field.field"><dt>{{ field.label }}</dt><dd>{{ displayValue(selectedRecord[field.field], field) }}</dd></template></dl>
          </section>
        </div>
      </aside>
    </main>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import {
  executeHierarchyCommand,
  loadHierarchyRows,
  loadHierarchyTree,
  type HierarchyCommand,
  type HierarchyLevelConfig,
  type HierarchyTreeNode,
} from '../../app/action_runtime/hierarchyCollectionDataSource';
import { formatDisplayValue } from '../../utils/display';
import ScButton from '../design-system/ScButton.vue';
import ScDataTable from '../design-system/ScDataTable.vue';
import ScEmptyState from '../design-system/ScEmptyState.vue';
import ScIcon from '../design-system/ScIcon.vue';
import ScIconButton from '../design-system/ScIconButton.vue';
import ProductListHeader from '../product-list/ProductListHeader.vue';

type Dict = Record<string, unknown>;
type Column = { field: string; label: string; type?: string; ttype?: string; selection?: Array<[string, string]> };
type SurfaceAction = { key: string; label: string; action_id: number; menu_id: number; variant: string; route: string };
type OutlineEntry = { node: HierarchyTreeNode; record: Dict; depth: number };
type DetailSection = { title: string; fields: Column[] };
type GovernanceFact = { key: string; label: string; value: string };

const props = withDefaults(defineProps<{ config: Dict; preferenceScope?: string }>(), { preferenceScope: 'default' });
const emit = defineEmits<{ 'open-record': [row: Dict]; 'open-action': [action: SurfaceAction] }>();
const defaultLabels: Record<string, string> = {
  surface_aria: 'hierarchy planner', search_label: 'Search', search_placeholder: '', total_prefix: '', total_suffix: '',
  loading: 'Loading…', refresh: 'Refresh', load_error: 'Unable to load data', open: 'Open', expand_all: 'Expand all', collapse_all: 'Collapse all', more: 'More', view: 'View', details: 'Details', close_details: 'Close details', selected_prefix: 'Selected', select_hint: 'Select a record', operation_success: 'Completed',
};
const labels = computed(() => ({ ...defaultLabels, ...(props.config.labels && typeof props.config.labels === 'object' ? props.config.labels as Dict : {}) }) as Record<string, string>);
const title = computed(() => String(props.config.title || labels.value.surface_aria));
const createConfig = computed(() => {
  const raw = props.config.create && typeof props.config.create === 'object' ? props.config.create as Dict : {};
  return { enabled: raw.enabled === true && Boolean(String(raw.label || '').trim()), label: String(raw.label || '') };
});
const actions = computed<SurfaceAction[]>(() => (Array.isArray(props.config.actions) ? props.config.actions : []).map((row) => row as SurfaceAction));
const commands = computed<HierarchyCommand[]>(() => (Array.isArray(props.config.commands) ? props.config.commands : []).map((row) => row as HierarchyCommand));
const toolbarCommands = computed(() => commands.value.filter((command) => command.placement !== 'overflow'));
const overflowCommands = computed(() => commands.value.filter((command) => command.placement === 'overflow'));
const detailSections = computed<DetailSection[]>(() => {
  const raw = props.config.detail && typeof props.config.detail === 'object' ? props.config.detail as Dict : {};
  return (Array.isArray(raw.sections) ? raw.sections : []).map((row) => row as DetailSection);
});
const governanceFacts = computed<GovernanceFact[]>(() => {
  const raw = props.config.governance && typeof props.config.governance === 'object' ? props.config.governance as Dict : {};
  return (Array.isArray(raw.facts) ? raw.facts : []).map((row) => row as GovernanceFact);
});
const levels = computed<HierarchyLevelConfig[]>(() => {
  const tree = props.config.tree && typeof props.config.tree === 'object' ? props.config.tree as Dict : {};
  return (Array.isArray(tree.levels) ? tree.levels : []).map((raw) => {
    const row = raw as Dict;
    return {
      key: String(row.key || ''), model: String(row.model || ''), fields: Array.isArray(row.fields) ? row.fields.map(String) : [],
      label_field: String(row.label_field || ''), code_field: String(row.code_field || ''), parent_key: String(row.parent_key || ''),
      parent_field: String(row.parent_field || ''), self_parent_field: String(row.self_parent_field || ''), order: String(row.order || 'id asc'),
      domain: Array.isArray(row.domain) ? row.domain : [],
    };
  });
});
const listConfig = computed(() => {
  const raw = props.config.list && typeof props.config.list === 'object' ? props.config.list as Dict : {};
  const requestedPageSize = Number(raw.page_size || 5000);
  return {
    model: String(raw.model || ''), fields: Array.isArray(raw.fields) ? raw.fields.map(String) : [], bindings: raw.bindings && typeof raw.bindings === 'object' ? raw.bindings as Dict : {},
    order: String(raw.order || 'id asc'),
    pageSize: Number.isFinite(requestedPageSize) ? Math.max(1, Math.min(20000, requestedPageSize)) : 5000,
    domain: Array.isArray(raw.domain) ? raw.domain : [],
  };
});
const columns = computed<Column[]>(() => {
  const raw = props.config.list && typeof props.config.list === 'object' ? props.config.list as Dict : {};
  return (Array.isArray(raw.columns) ? raw.columns : []).map((row) => row as Column);
});
const planner = computed(() => props.config.planner && typeof props.config.planner === 'object' ? props.config.planner as Dict : {});
const defaultExpandDepth = computed(() => {
  const value = Number(planner.value.default_expand_depth);
  return Number.isFinite(value) ? Math.max(0, Math.min(20, value)) : null;
});
const nodeLevelKey = computed(() => String(planner.value.node_level_key || ''));
const outlineField = computed(() => String(planner.value.outline_field || columns.value[0]?.field || ''));
const codeField = computed(() => String(planner.value.code_field || ''));
const roots = ref<HierarchyTreeNode[]>([]);
const records = ref(new Map<number, Dict>());
const expandedKeys = ref(new Set<string>());
const selectedRecord = ref<Dict | null>(null);
const selectedEntry = computed(() => visibleEntries.value.find((entry) => Number(entry.record.id) === Number(selectedRecord.value?.id)) || null);
const showDetail = ref(false);
const activeMenu = ref<'' | 'more' | 'view'>('');
const plannerElement = ref<HTMLElement | null>(null);
const keyword = ref('');
const loading = ref(false);
const commandBusy = ref(false);
const errorMessage = ref('');
const successMessage = ref('');
const indentSize = 20;
const allPlannerNodes = computed(() => {
  const output: HierarchyTreeNode[] = [];
  const visited = new Set<string>();
  const visit = (node: HierarchyTreeNode) => {
    if (visited.has(node.key)) return;
    visited.add(node.key);
    if (node.levelKey === nodeLevelKey.value) output.push(node);
    node.children.forEach(visit);
  };
  roots.value.forEach(visit);
  return output;
});
const plannerRoots = computed(() => {
  const childKeys = new Set<string>();
  allPlannerNodes.value.forEach((node) => node.children.forEach((child) => childKeys.add(child.key)));
  return allPlannerNodes.value.filter((node) => !childKeys.has(node.key));
});
const visibleEntries = computed<OutlineEntry[]>(() => {
  const output: OutlineEntry[] = [];
  const term = keyword.value.trim().toLowerCase();
  const matches = (node: HierarchyTreeNode): boolean => {
    const row = records.value.get(node.id) || {};
    return !term || [node.code, node.label, ...Object.values(row).map(String)].join(' ').toLowerCase().includes(term) || node.children.some(matches);
  };
  const visit = (node: HierarchyTreeNode, depth: number) => {
    if (node.levelKey !== nodeLevelKey.value || !matches(node)) return;
    const record = records.value.get(node.id);
    if (record) output.push({ node, record, depth });
    if ((term || expandedKeys.value.has(node.key)) && node.children.length) node.children.forEach((child) => visit(child, depth + 1));
  };
  plannerRoots.value.forEach((node) => visit(node, 0));
  return output;
});
const displayedTotal = computed(() => keyword.value.trim() ? visibleEntries.value.length : allPlannerNodes.value.length);
const tableStyle = computed(() => ({ minWidth: `${Math.max(900, columns.value.length * 150)}px` }));
const headerLayoutStyle = computed(() => ({ gridTemplateColumns: 'minmax(240px, auto) 0 minmax(320px, 1fr) 0 max-content' }));

function displayValue(value: unknown, column: Column): string { return formatDisplayValue(value, column); }
function columnStyle(column: Column): Record<string, string> { return { width: column.field === outlineField.value ? 'min(36vw, 520px)' : '150px' }; }
function onSearchInput(event: Event): void { keyword.value = String((event.target as HTMLInputElement | null)?.value || ''); }
function selectEntry(entry: OutlineEntry): void { selectedRecord.value = entry.record; }
function openRecord(record: Dict): void { if (Number(record.id || 0)) emit('open-record', record); }
function openSelected(): void { if (selectedRecord.value) openRecord(selectedRecord.value); }
function createRecord(): void { emit('open-record', { id: 'new' }); }
function commandEnabled(command: HierarchyCommand): boolean {
  if (!selectedRecord.value) return false;
  const field = String(command.availability_field || '');
  return !field || selectedRecord.value[field] === true;
}
function toggleMenu(menu: 'more' | 'view'): void { activeMenu.value = activeMenu.value === menu ? '' : menu; }
function closeMenus(): void { activeMenu.value = ''; }
function closeMenusFromOutside(event: MouseEvent): void {
  const target = event.target;
  if (!(target instanceof Element) || !plannerElement.value?.contains(target) || !target.closest('.planner-menu')) closeMenus();
}
function closeMenusFromKeyboard(event: KeyboardEvent): void { if (event.key === 'Escape') closeMenus(); }
function toggle(node: HierarchyTreeNode): void { const next = new Set(expandedKeys.value); if (next.has(node.key)) next.delete(node.key); else next.add(node.key); expandedKeys.value = next; }
function expandAll(): void { expandedKeys.value = new Set(allPlannerNodes.value.map((node) => node.key)); }
function collapseAll(): void { expandedKeys.value = new Set(); }
function defaultExpandedNodeKeys(): Set<string> {
  if (defaultExpandDepth.value === null) return new Set(allPlannerNodes.value.map((node) => node.key));
  const keys = new Set<string>();
  const visit = (node: HierarchyTreeNode, depth: number) => {
    if (depth < defaultExpandDepth.value!) keys.add(node.key);
    node.children.forEach((child) => visit(child, depth + 1));
  };
  plannerRoots.value.forEach((node) => visit(node, 0));
  return keys;
}
async function reload(): Promise<void> {
  loading.value = true; errorMessage.value = '';
  try {
    roots.value = await loadHierarchyTree(levels.value);
    const result = await loadHierarchyRows({ config: listConfig.value, selectedNode: null, keyword: '', offset: 0 });
    records.value = new Map(result.rows.map((row) => [Number(row.id), row]));
    const nodeKeys = new Set(allPlannerNodes.value.map((node) => node.key));
    expandedKeys.value = expandedKeys.value.size ? new Set([...expandedKeys.value].filter((key) => nodeKeys.has(key))) : defaultExpandedNodeKeys();
    if (selectedRecord.value) selectedRecord.value = records.value.get(Number(selectedRecord.value.id)) || null;
  } catch (error) { errorMessage.value = error instanceof Error ? error.message : labels.value.load_error; }
  finally { loading.value = false; }
}
async function runCommand(command: HierarchyCommand): Promise<void> {
  if (!commandEnabled(command) || !selectedRecord.value || commandBusy.value) return;
  commandBusy.value = true; errorMessage.value = '';
  successMessage.value = '';
  try {
    await executeHierarchyCommand({ model: listConfig.value.model, recordId: Number(selectedRecord.value.id), command });
    closeMenus();
    await reload();
    successMessage.value = `${command.label}：${labels.value.operation_success}`;
  }
  catch (error) { errorMessage.value = error instanceof Error ? error.message : labels.value.load_error; }
  finally { commandBusy.value = false; }
}
onMounted(() => { document.addEventListener('click', closeMenusFromOutside); document.addEventListener('keydown', closeMenusFromKeyboard); void reload(); });
onBeforeUnmount(() => { document.removeEventListener('click', closeMenusFromOutside); document.removeEventListener('keydown', closeMenusFromKeyboard); });
</script>

<style scoped>
.hierarchy-planner { display: grid; gap: 0; min-width: 0; color: var(--sc-app-text-primary); }
.planner-head { min-height: var(--sc-product-toolbar-height); padding: 0; border: 1px solid var(--sc-app-border); border-radius: var(--sc-component-toolbar-radius) var(--sc-component-toolbar-radius) 0 0; background: var(--sc-app-panel); box-shadow: none; }
.planner-head :deep(.product-list-header__tools) { min-height: var(--sc-product-toolbar-height); }
.planner-head :deep(.product-list-header__search) { padding-block: var(--sc-space-2xs); }
.planner-head :deep(.product-list-header__actions) { padding: var(--sc-space-xs) var(--sc-surface-padding); }
.planner-governance { display: flex; flex-wrap: wrap; gap: var(--sc-space-md); min-height: 38px; margin: 0; padding: var(--sc-space-xs) var(--sc-surface-padding); border-inline: 1px solid var(--sc-app-border); border-bottom: 1px solid var(--sc-app-border); background: var(--sc-app-panel); }
.planner-governance div { display: flex; align-items: baseline; gap: var(--sc-space-xs); }
.planner-governance dt { color: var(--sc-app-text-secondary); font-size: var(--sc-product-text-sm); }.planner-governance dd { margin: 0; font-weight: 600; }
.planner-title { display: flex; align-items: baseline; gap: var(--sc-space-sm); padding-inline: var(--sc-surface-padding); white-space: nowrap; }
.planner-title span { color: var(--sc-app-text-secondary); font-size: var(--sc-product-text-sm); }
.planner-canvas { position: relative; min-width: 0; min-height: calc(var(--sc-component-hierarchy-browser-min-height) * 1px); overflow: hidden; border: 1px solid var(--sc-app-border); border-top: 0; border-radius: 0 0 var(--sc-component-panel-radius) var(--sc-component-panel-radius); background: var(--sc-app-panel); }
.planner-toolbar { display: flex; align-items: center; justify-content: space-between; gap: var(--sc-toolbar-group-gap); min-height: var(--sc-product-list-toolbar-height); padding: var(--sc-space-xs) var(--sc-surface-padding); border-bottom: 1px solid var(--sc-app-border); }
.planner-selection { display: flex; align-items: baseline; gap: var(--sc-space-sm); white-space: nowrap; }
.planner-selection span { color: var(--sc-app-text-secondary); font-size: var(--sc-product-text-sm); }
.planner-commands { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: var(--sc-toolbar-gap); }
.planner-menu { position: relative; }
.planner-menu-popover { position: absolute; z-index: 5; top: calc(100% + var(--sc-space-2xs)); right: 0; display: grid; min-width: 140px; padding: var(--sc-space-xs); border: 1px solid var(--sc-app-border); background: var(--sc-app-panel); box-shadow: var(--sc-app-shadow-md); }
.planner-grid { max-height: calc(100vh - 260px); border: 0; border-radius: 0; box-shadow: none; }
.planner-grid :deep(.sc-product-table) { width: 100%; border-collapse: collapse; font-size: var(--sc-product-text-body); }
.planner-grid :deep(th), .planner-grid :deep(td) { height: var(--sc-product-table-row-height); padding: calc(var(--sc-component-table-cell-padding-y) * 1px) calc(var(--sc-component-table-cell-padding-x) * 1px); border-bottom: 1px solid var(--sc-table-divider); text-align: left; white-space: nowrap; }
.planner-grid :deep(th) { position: sticky; top: 0; z-index: 1; height: calc(var(--sc-component-table-header-height) * 1px); background: var(--sc-table-header-bg); color: var(--sc-app-text-secondary); }
.planner-grid :deep(tbody tr) { cursor: pointer; }
.planner-grid :deep(tbody tr:hover) { background: var(--sc-app-hover-bg); }
.planner-grid :deep(tbody tr.selected) { background: var(--sc-app-selected-bg); }
.planner-grid :deep(tbody tr.parent td) { font-weight: 600; }
.outline-cell, .code-cell { display: flex; align-items: center; min-width: 0; }
.tree-elbow { align-self: stretch; width: var(--sc-space-sm); margin-inline-end: var(--sc-space-xs); border-bottom: 1px solid var(--sc-app-border-strong); border-left: 1px solid var(--sc-app-border-strong); }
.outline-toggle, .outline-toggle-spacer { flex: 0 0 var(--sc-touch-target-min); width: var(--sc-touch-target-min); min-height: var(--sc-touch-target-min); }
.outline-toggle { display: inline-grid; border: 0; background: transparent; color: var(--sc-app-text-secondary); cursor: pointer; place-items: center; }
.outline-toggle :deep(.sc-icon) { transition: transform var(--sc-motion-fast, 120ms) ease; }
.outline-toggle :deep(.sc-icon.is-expanded) { transform: rotate(90deg); }
.planner-state { display: grid; min-height: 420px; place-content: center; color: var(--sc-app-text-secondary); }
.planner-error { padding: var(--sc-space-xs) var(--sc-space-sm); border: 1px solid var(--sc-app-danger-border); background: var(--sc-app-danger-bg); color: var(--sc-app-danger-text); }
.planner-success { padding: var(--sc-space-xs) var(--sc-space-sm); border: 1px solid var(--sc-app-success-border); background: var(--sc-app-success-bg); color: var(--sc-app-success-text); }
.planner-drawer { position: absolute; z-index: 4; inset-block: 0; right: 0; display: grid; grid-template-rows: auto minmax(0, 1fr); width: min(420px, 42vw); border-left: 1px solid var(--sc-app-border); background: var(--sc-app-panel); box-shadow: var(--sc-app-shadow-lg); }
.planner-drawer header { display: flex; align-items: center; justify-content: space-between; gap: var(--sc-space-sm); min-height: var(--sc-product-list-toolbar-height); padding: var(--sc-space-xs) var(--sc-surface-padding); border-bottom: 1px solid var(--sc-app-border); }
.planner-drawer-body { overflow: auto; padding: var(--sc-surface-padding); }
.planner-drawer-body section + section { margin-top: var(--sc-space-md); padding-top: var(--sc-space-md); border-top: 1px solid var(--sc-app-border); }
.planner-drawer-body h3 { margin: 0 0 var(--sc-space-sm); font-size: var(--sc-product-text-body); }
.planner-drawer-body dl { display: grid; grid-template-columns: minmax(90px, auto) 1fr; gap: var(--sc-space-xs) var(--sc-space-sm); margin: 0; font-size: var(--sc-product-text-sm); }
.planner-drawer-body dt { color: var(--sc-app-text-secondary); }.planner-drawer-body dd { margin: 0; }
@media (max-width: 900px) { .planner-toolbar { align-items: stretch; flex-direction: column; } .planner-commands { justify-content: flex-start; } .planner-grid { max-height: none; } }
</style>
