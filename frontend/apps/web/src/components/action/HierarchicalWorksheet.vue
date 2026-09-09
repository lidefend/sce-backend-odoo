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
      @search-clear="clearSearch"
    >
      <template #actions>
        <ScButton v-for="action in actions" :key="action.key" :variant="action.variant === 'primary' ? 'primary' : 'secondary'" @click="emit('open-action', action)">{{ action.label }}</ScButton>
      </template>
    </ProductListHeader>
    <div v-if="errorMessage" class="worksheet-error" role="alert">{{ errorMessage }}</div>
    <div class="worksheet-layout" :style="layoutStyle">
      <aside :id="navigationPaneId" class="worksheet-navigation">
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
      <div class="worksheet-resizer worksheet-resizer-navigation" role="separator" aria-orientation="vertical" :aria-label="labels.resize_navigation" :aria-controls="navigationPaneId" :aria-valuemin="NAVIGATION_MIN" :aria-valuemax="NAVIGATION_MAX" :aria-valuenow="navigationWidth" tabindex="0" @keydown="resizeNavigationFromKeyboard" @pointerdown="startNavigationResize" />
      <main class="worksheet-main" :style="mainStyle">
        <section class="worksheet-grid-pane">
          <div class="worksheet-grid-toolbar">
            <ScButton
              v-if="compactViewport"
              class="worksheet-scope-trigger"
              variant="secondary"
              size="large"
              :aria-expanded="mobileNavigationOpen"
              aria-haspopup="dialog"
              @click="mobileNavigationOpen = true"
            >{{ labels.scope || '当前范围' }}：{{ currentScopeTitle }}</ScButton>
            <div class="worksheet-grid-title">
              <strong>{{ currentScopeTitle }}</strong><span>{{ labels.total_prefix }} {{ visibleLeafCount }} {{ labels.total_suffix }}</span>
              <div v-if="domainTabs.length" class="worksheet-domain-tabs" role="tablist" :aria-label="labels.domain_tabs || '数据域切换'">
                <ScButton
                  v-for="tab in domainTabs"
                  :key="tab.key"
                  variant="ghost"
                  size="small"
                  appearance="section-tab"
                  role="tab"
                  :aria-selected="activeDomainTab === tab.key"
                  :class="{ active: activeDomainTab === tab.key }"
                  :disabled="loading"
                  @click="selectDomainTab(tab.key)"
                >{{ tab.label }}</ScButton>
              </div>
            </div>
            <div v-if="!sourceOrderMode" class="worksheet-grid-actions">
              <ScButton @click="expandAll">{{ labels.expand_all }}</ScButton>
              <ScButton @click="collapseAll">{{ labels.collapse_all }}</ScButton>
            </div>
          </div>
          <div v-if="patchNotice" class="worksheet-patch-notice" :class="`patch-${patchNotice.kind}`" role="status" aria-live="polite">
            <span>{{ patchNotice.text }}</span>
            <ScButton variant="ghost" size="small" @click="patchNotice = null">{{ labels.dismiss || '关闭' }}</ScButton>
          </div>
          <div v-if="loading" class="worksheet-state" role="status">{{ labels.loading }}</div>
          <ScEmptyState
            v-else-if="!visibleRows.length"
            class="worksheet-state"
            density="compact"
            :heading-level="3"
            :title="keyword.trim() ? (labels.empty_filtered || '没有符合当前条件的记录') : labels.empty"
            :description="selectedNavigationNode ? `${labels.scope || '当前范围'}：${currentScopeTitle}` : ''"
          >
            <template v-if="keyword.trim() || selectedNavigationNode" #actions>
              <ScButton v-if="keyword.trim()" variant="secondary" @click="clearSearch">{{ labels.clear_search || '清除搜索' }}</ScButton>
              <ScButton v-if="selectedNavigationNode" variant="ghost" @click="selectNavigation(null)">{{ labels.clear_scope || '清除范围' }}</ScButton>
            </template>
          </ScEmptyState>
          <div v-else ref="tableScroll" class="worksheet-table-scroll">
            <ScTable
              appearance="worksheet"
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
        <div class="worksheet-resizer worksheet-resizer-detail" role="separator" aria-orientation="horizontal" :aria-label="labels.resize_detail" :aria-controls="detailPaneId" :aria-valuemin="DETAIL_MIN" :aria-valuemax="DETAIL_MAX" :aria-valuenow="detailHeight" tabindex="0" @keydown="resizeDetailFromKeyboard" @pointerdown="startDetailResize" />
        <section :id="detailPaneId" class="worksheet-detail">
          <nav class="worksheet-tabs" aria-label="detail tabs">
            <ScButton v-for="tab in detailTabs" :key="tab.key" variant="ghost" size="small" appearance="section-tab" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.label }}</ScButton>
            <ScButton
              v-if="selectedRecord"
              class="worksheet-open-record"
              variant="secondary"
              data-semantic-action="record.open"
              @click="openSelectedRecord(selectedRecord)"
            >{{ labels.open || '打开记录' }}</ScButton>
          </nav>
          <div v-if="!selectedRecord" class="worksheet-detail-empty">{{ labels.select_hint }}</div>
          <dl v-else class="worksheet-detail-fields">
            <template v-for="field in activeTabFields" :key="field.field">
              <dt>{{ field.label }}</dt><dd :data-detail-field="field.field" :data-field-type="field.type">{{ formatValue(selectedRecord[field.field], field, selectedRecord) }}</dd>
            </template>
          </dl>
        </section>
      </main>
    </div>
    <ScDrawer
      :open="mobileNavigationOpen"
      :title="navigationTitle || (labels.scope || '选择范围')"
      :description="`${labels.scope || '当前范围'}：${currentScopeTitle}`"
      appearance="workspace"
      @close="mobileNavigationOpen = false"
    >
      <nav class="worksheet-mobile-navigation" :aria-label="navigationTitle || (labels.scope || '选择范围')">
        <ScButton class="navigation-all" appearance="tree-item" variant="ghost" :class="{ active: !selectedNavigationNode }" @click="selectMobileNavigation(null)">{{ labels.all }}</ScButton>
        <HierarchyTreeNode
          v-for="node in navigationRoots"
          :key="`mobile:${node.key}`"
          :node="node"
          :selected-key="selectedNavigationNode?.key || ''"
          :expanded-keys="navigationExpandedKeys"
          empty-children-label=""
          @select="selectMobileNavigation"
          @toggle="toggleNavigation"
        />
      </nav>
    </ScDrawer>
  </section>
</template>

<script setup lang="ts">
import { computed, h, nextTick, onActivated, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue';
import { formatDisplayValue } from '../../utils/display';
import { formatMonetaryDisplayValue, normalizeMonetaryDigits, resolveCurrencyDisplayLabel } from '../template/formSection.mapper';
import {
  applyWorksheetDomainTab,
  collectNodeIds,
  loadHierarchicalWorksheet,
  relationId,
  resolveWorksheetDomainTabs,
  type WorksheetDict,
  type WorksheetHierarchyConfig,
  type WorksheetNode,
  type WorksheetSheetConfig,
} from '../../app/action_runtime/hierarchicalWorksheetDataSource';
import {
  clampWorksheetPaneSize,
  resizeWorksheetPaneFromKeyboard,
  resolveVisibleWorksheetRecordId,
  shouldOpenWorksheetRecordFromKeyboard,
} from '../../app/action_runtime/hierarchicalWorksheetInteraction';
import { ApiError } from '../../api/client';
import { buildBoqLinePatchIdempotencyKey, patchBoqLineQuantity } from '../../api/boqLinePatch';
import {
  beginBoqLinePatchSession,
  BOQ_LINE_PATCH_SESSION_EDITING,
  describeBoqLinePatchSuccess,
  isBoqLinePatchEditableRow,
  markBoqLinePatchError,
  markBoqLinePatchSaving,
  resolveBoqLinePatchEditableFields,
  updateBoqLinePatchDraft,
  validateDraftQuantity,
  type BoqLinePatchSession,
} from '../../app/presentation/boqLinePatch';
import ScButton from '../design-system/ScButton.vue';
import ScDrawer from '../design-system/ScDrawer.vue';
import ScEmptyState from '../design-system/ScEmptyState.vue';
import ScInput from '../design-system/ScInput.vue';
import ScTable from '../design-system/ScTable.vue';
import ProductListHeader from '../product-list/ProductListHeader.vue';
import HierarchyTreeNode from './HierarchyTreeNode.vue';

type Dict = Record<string, unknown>;
type DisplayField = { field: string; label: string; type: string; selection: Array<[string, string]>; precision?: number; digits?: [number, number]; currency_field?: string };
type Column = DisplayField & { align: string; width: number };
type DetailField = DisplayField;
type DetailTab = { key: string; label: string; fields: DetailField[] };
type SurfaceAction = { key: string; label: string; action_id: number; menu_id: number; route: string; variant: string };
type VisibleEntry = { key: string; node: WorksheetNode; record: WorksheetDict | null; ordinal: number; rowKind: string };
type NavigationTreeNode = { key: string; id: number; levelKey?: string; code: string; label: string; children: NavigationTreeNode[] };

const props = withDefaults(defineProps<{ config: Dict; preferenceScope?: string }>(), { preferenceScope: 'default' });
const emit = defineEmits<{ 'open-record': [row: WorksheetDict]; 'open-action': [action: SurfaceAction] }>();
const componentId = useId();
const navigationPaneId = `worksheet-navigation-${componentId}`;
const detailPaneId = `worksheet-detail-${componentId}`;

function openRecordFromKeyboard(event: KeyboardEvent, record: WorksheetDict | null): void {
  if (shouldOpenWorksheetRecordFromKeyboard(event, record)) openSelectedRecord(record as WorksheetDict);
}
const hierarchyConfig = computed(() => props.config.hierarchy as unknown as WorksheetHierarchyConfig);
const sheetConfig = computed(() => props.config.sheet as unknown as WorksheetSheetConfig);
const labels = computed(() => props.config.labels as Record<string, string>);
/** 数据域 tab（G7.3）：后端未下发 domain_tabs 时为空数组，工作表行为与旧契约一致 */
const domainTabs = computed(() => resolveWorksheetDomainTabs(sheetConfig.value));
const activeDomainTab = ref('');
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
const mobileNavigationOpen = ref(false);
const tableScroll = ref<HTMLElement | null>(null);
/** G7.2 内联编辑：编辑会话（行级单例）+ 结果通知 + 窄屏禁用 */
const patchSession = ref<BoqLinePatchSession | null>(null);
const patchNotice = ref<{ kind: 'success' | 'error'; text: string } | null>(null);
const compactViewport = ref(false);
let viewportMedia: MediaQueryList | null = null;
const editableFields = computed(() => resolveBoqLinePatchEditableFields(sheetConfig.value.editable_fields));
let resizeMode: '' | 'navigation' | 'detail' = '';
let resizeStart = 0;
let resizeStartSize = 0;
let retainedTableScroll = { left: 0, top: 0 };
const NAVIGATION_MIN = 200;
const NAVIGATION_MAX = 480;
const DETAIL_MIN = 140;
const DETAIL_MAX = 420;

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

watch(visibleRows, (entries) => {
  const records = entries.filter((entry): entry is VisibleEntry & { record: WorksheetDict } => Boolean(entry.record));
  const visibleIds = records.map((entry) => Number(entry.record.id || 0)).filter(Boolean);
  const selectedId = selectedRecord.value ? Number(selectedRecord.value.id || 0) : null;
  const nextId = resolveVisibleWorksheetRecordId(visibleIds, selectedId);
  const nextEntry = nextId ? records.find((entry) => Number(entry.record.id || 0) === nextId) : null;
  selectedNode.value = nextEntry?.node || null;
  selectedRecord.value = nextEntry?.record || null;
}, { flush: 'sync' });

function worksheetCell(entry: VisibleEntry, column: Column) {
  if (isEditablePatchCell(entry, column)) return renderPatchCell(entry, column);
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

/** G7.2 内联编辑：可编辑 cell 判定（字段写入面 + 叶子记录行 + 非窄屏） */
function isEditablePatchCell(entry: VisibleEntry, column: Column): boolean {
  if (compactViewport.value) return false;
  if (!editableFields.value.has(column.field)) return false;
  return isBoqLinePatchEditableRow({
    hasRecord: Boolean(entry.record),
    rowKind: entry.rowKind,
    itemValues: itemValues.value,
  });
}

function renderPatchCell(entry: VisibleEntry, column: Column) {
  const record = entry.record;
  const lineId = Number(record?.id || 0);
  const session = patchSession.value;
  if (!session || session.lineId !== lineId) {
    return h('span', {
      class: 'patch-cell',
      title: '双击编辑工程量',
      onDblclick: (event: MouseEvent) => { event.stopPropagation(); beginPatchEdit(lineId, record as WorksheetDict); },
    }, displayCell(entry, column));
  }
  return h('div', {
    class: 'patch-cell-editing',
    onKeydown: (event: KeyboardEvent) => {
      if (event.key === 'Enter') { event.preventDefault(); void commitPatchEdit(); }
      else if (event.key === 'Escape') { event.preventDefault(); cancelPatchEdit(); }
    },
  }, [
    h(ScInput, {
      modelValue: session.draft,
      type: 'number',
      size: 'small',
      appearance: 'numeric-entry',
      status: session.state === 'error' ? 'error' : 'default',
      min: 0,
      step: 'any',
      align: 'right',
      'aria-label': '工程量（Enter 提交 / Esc 取消）',
      'aria-invalid': session.state === 'error' || undefined,
      disabled: session.state !== BOQ_LINE_PATCH_SESSION_EDITING,
      'onUpdate:modelValue': (value: string) => { patchSession.value = updateBoqLinePatchDraft(session, value); },
      onBlur: () => { void commitPatchEdit(); },
      onVnodeMounted: (vnode: { el?: HTMLElement }) => {
        const input = vnode.el?.querySelector('input');
        if (input) { input.focus(); input.select(); }
      },
    }),
    session.errorMessage ? h('div', { class: 'patch-cell-error', role: 'alert' }, session.errorMessage) : null,
  ]);
}

function beginPatchEdit(lineId: number, record: WorksheetDict) {
  if (!lineId) return;
  const expected = Number(record.quantity ?? 0);
  patchNotice.value = null;
  patchSession.value = beginBoqLinePatchSession({
    lineId,
    expectedQuantity: Number.isFinite(expected) ? expected : 0,
  });
}

function cancelPatchEdit() {
  patchSession.value = null;
}

async function commitPatchEdit() {
  const session = patchSession.value;
  if (!session || session.state !== BOQ_LINE_PATCH_SESSION_EDITING) return;
  const validation = validateDraftQuantity(session.draft, session.expectedQuantity);
  if (!validation.ok) {
    if (validation.code === 'NO_CHANGE') { patchSession.value = null; return; }
    patchSession.value = markBoqLinePatchError(session, 'INVALID_QUANTITY');
    return;
  }
  const idempotencyKey = buildBoqLinePatchIdempotencyKey(session.lineId);
  patchSession.value = markBoqLinePatchSaving(session, idempotencyKey);
  try {
    const result = await patchBoqLineQuantity({
      lineId: session.lineId,
      expectedQuantity: session.expectedQuantity,
      newQuantity: validation.newQuantity,
      idempotencyKey,
    });
    patchSession.value = null;
    patchNotice.value = { kind: 'success', text: describeBoqLinePatchSuccess(result) };
    await reloadWorksheet();
    window.setTimeout(() => { if (patchNotice.value?.kind === 'success') patchNotice.value = null; }, 4000);
  } catch (error) {
    const reasonCode = error instanceof ApiError ? (error.reasonCode || 'NETWORK_ERROR') : 'NETWORK_ERROR';
    const failed = markBoqLinePatchError(session, reasonCode);
    patchSession.value = failed;
    patchNotice.value = { kind: 'error', text: failed.errorMessage || '工程量更新失败，请重试。' };
    if (reasonCode === 'BASELINE_MISMATCH') await refreshPatchBaseline(session.lineId);
  }
}

/** BASELINE_MISMATCH：静默刷新整表并同步会话基线（草稿保留，供基于最新值重试） */
async function refreshPatchBaseline(lineId: number) {
  await reloadWorksheet();
  const fresh = findRecordById(lineId);
  if (fresh && patchSession.value) {
    const next = Number(fresh.quantity ?? patchSession.value.expectedQuantity);
    if (Number.isFinite(next)) patchSession.value = { ...patchSession.value, expectedQuantity: next };
  }
}

function findRecordById(recordId: number): WorksheetDict | null {
  const fromSource = sourceRows.value.find((record) => Number(record.id || 0) === recordId);
  if (fromSource) return fromSource;
  for (const record of recordsByNode.value.values()) {
    if (Number(record.id || 0) === recordId) return record;
  }
  return null;
}

/** 整表权威 reload（成功提交后与基线漂移后；金额链全由服务端重算，本地不形成事实） */
async function reloadWorksheet(): Promise<void> {
  const result = await loadHierarchicalWorksheet(
    hierarchyConfig.value,
    applyWorksheetDomainTab(sheetConfig.value, activeDomainTab.value),
  );
  roots.value = result.roots;
  nodesById.value = result.nodesById;
  recordsByNode.value = result.recordsByNode;
  sourceRows.value = result.sourceRows;
  recordCount.value = result.recordCount;
  if (selectedNode.value) selectedNode.value = nodesById.value.get(selectedNode.value.id) || selectedNode.value;
  if (selectedRecord.value) selectedRecord.value = findRecordById(Number(selectedRecord.value.id || 0));
}

/** 数据域 tab 切换（G7.3）：换 domain 权威重载，编辑会话/选中态复位避免悬空行 */
async function selectDomainTab(tabKey: string): Promise<void> {
  if (tabKey === activeDomainTab.value || loading.value) return;
  if (patchSession.value) cancelPatchEdit();
  activeDomainTab.value = tabKey;
  selectedNode.value = null;
  selectedRecord.value = null;
  loading.value = true;
  try {
    await reloadWorksheet();
    expandAll();
    const firstRecord = visibleRows.value.find((entry) => entry.record);
    if (firstRecord) selectEntry(firstRecord);
  } catch (error) { errorMessage.value = error instanceof Error ? error.message : String(error); }
  finally { loading.value = false; }
}

function worksheetRowAttributes({ row }: { row: VisibleEntry }) {
  return {
    tabindex: 0,
    'data-record-id': row.record ? String(row.record.id || '') : undefined,
    'aria-selected': row.record ? selectedRecord.value?.id === row.record.id : undefined,
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
  if (row?.record) openSelectedRecord(row.record);
}

function groupValue(node: WorksheetNode, field: string): unknown {
  const source = hierarchyConfig.value.group_field_map?.[field];
  const value = source ? node.raw[source] : '';
  return value === null || value === undefined || value === false ? '' : value;
}
function formatValue(value: unknown, field: DisplayField, record?: WorksheetDict | null): string {
  if (String(field.type || '').trim().toLowerCase() === 'monetary') {
    const explicitDigits = typeof field.precision === 'number'
      ? [Math.max(16, field.precision), field.precision] as [number, number]
      : normalizeMonetaryDigits(field.digits);
    const currencyLabel = field.currency_field && record
      ? resolveCurrencyDisplayLabel(record[field.currency_field])
      : '';
    return formatMonetaryDisplayValue(value, explicitDigits, currencyLabel);
  }
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
  if (entry.record) return formatValue(entry.record[column.field], column, entry.record);
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
function selectMobileNavigation(rawNode: NavigationTreeNode | null) {
  selectNavigation(rawNode);
  mobileNavigationOpen.value = false;
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
function clearSearch() { keyword.value = ''; }
function resolveTableScrollOwner(): HTMLElement | null {
  return tableScroll.value?.querySelector<HTMLElement>('[data-table-scroll-region="true"]') || tableScroll.value;
}
function captureTableScroll() {
  const owner = resolveTableScrollOwner();
  retainedTableScroll = { left: owner?.scrollLeft || 0, top: owner?.scrollTop || 0 };
}
async function restoreTableScroll() {
  await nextTick();
  await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
  const owner = resolveTableScrollOwner();
  if (owner) {
    owner.scrollLeft = retainedTableScroll.left;
    owner.scrollTop = retainedTableScroll.top;
  }
}
function openSelectedRecord(record: WorksheetDict) {
  captureTableScroll();
  emit('open-record', record);
}
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
function resizeNavigationFromKeyboard(event: KeyboardEvent) {
  const result = resizeWorksheetPaneFromKeyboard('navigation', navigationWidth.value, event.key);
  if (!result.handled) return;
  event.preventDefault();
  navigationWidth.value = result.value;
  persistLayout();
}
function resizeDetailFromKeyboard(event: KeyboardEvent) {
  const result = resizeWorksheetPaneFromKeyboard('detail', detailHeight.value, event.key);
  if (!result.handled) return;
  event.preventDefault();
  detailHeight.value = result.value;
  persistLayout();
}
function bindResize() { window.addEventListener('pointermove', resizeMove); window.addEventListener('pointerup', stopResize); }
function resizeMove(event: PointerEvent) {
  if (resizeMode === 'navigation') navigationWidth.value = clampWorksheetPaneSize('navigation', resizeStartSize + event.clientX - resizeStart);
  if (resizeMode === 'detail') detailHeight.value = clampWorksheetPaneSize('detail', resizeStartSize - (event.clientY - resizeStart));
}
function stopResize() { if (resizeMode) persistLayout(); resizeMode = ''; window.removeEventListener('pointermove', resizeMove); window.removeEventListener('pointerup', stopResize); }

function onViewportChange(event: MediaQueryListEvent) { compactViewport.value = event.matches; }

onMounted(async () => {
  restoreLayout();
  if (typeof window !== 'undefined' && window.matchMedia) {
    viewportMedia = window.matchMedia('(max-width: 960px)');
    compactViewport.value = viewportMedia.matches;
    viewportMedia.addEventListener('change', onViewportChange);
  }
  loading.value = true;
  try {
    activeDomainTab.value = domainTabs.value[0]?.key || '';
    await reloadWorksheet();
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
onActivated(() => { void restoreTableScroll(); });
onBeforeUnmount(() => {
  stopResize();
  viewportMedia?.removeEventListener('change', onViewportChange);
  viewportMedia = null;
});
</script>

<style scoped>
.worksheet { display: grid; min-width: 0; color: var(--sc-app-text-primary); }
.worksheet-head { min-height: var(--sc-product-toolbar-height); border: 0; border-radius: var(--sc-component-toolbar-radius) var(--sc-component-toolbar-radius) 0 0; background: var(--sc-app-panel); box-shadow: none; }
.worksheet-layout { display: grid; height: calc(100vh - 170px); min-height: 600px; overflow: hidden; border: 0; border-radius: 0 0 var(--sc-product-radius-panel) var(--sc-product-radius-panel); background: var(--sc-app-panel); }
.worksheet-navigation { min-width: 0; overflow: auto; padding: var(--sc-space-sm); }
.worksheet-navigation h3 { margin: 0 0 var(--sc-space-xs); color: var(--sc-app-text-secondary); font-size: var(--sc-product-text-body); }
.navigation-all { width: 100%; min-height: var(--sc-touch-target-min); padding: var(--sc-space-xs); text-align: left; }
.worksheet-resizer { position: relative; z-index: 2; background: var(--sc-app-border); }
.worksheet-resizer::after { position: absolute; content: ''; inset: -5px; }
.worksheet-resizer:hover { background: var(--sc-app-accent); }
.worksheet-resizer:focus-visible { outline: var(--sc-component-button-focus-ring-width) solid var(--sc-app-focus-ring); outline-offset: var(--sc-component-button-focus-offset); background: var(--sc-app-accent); }
.worksheet-resizer-navigation { cursor: col-resize; }
.worksheet-main { display: grid; min-width: 0; min-height: 0; overflow: hidden; }
.worksheet-grid-pane { display: grid; grid-template-rows: auto minmax(0, 1fr); min-height: 0; }
.worksheet-grid-toolbar { display: flex; align-items: center; justify-content: space-between; min-height: 48px; padding: 0 var(--sc-space-sm); border-bottom: 1px solid var(--sc-app-border); }
.worksheet-scope-trigger { display: none; max-width: 100%; }
.worksheet-grid-toolbar span { margin-left: var(--sc-space-sm); color: var(--sc-app-text-secondary); }
.worksheet-grid-title { display: flex; align-items: center; min-width: 0; flex-wrap: wrap; gap: var(--sc-space-xs); }
.worksheet-domain-tabs { display: inline-flex; align-items: center; gap: 2px; margin-left: var(--sc-space-sm); }
.worksheet-grid-actions { display: flex; gap: var(--sc-space-xs); }
.worksheet-state { display: grid; place-items: center; color: var(--sc-app-text-secondary); }
.worksheet-table-scroll { min-height: 0; overflow: auto; }
:deep(.align-right) { text-align: right; font-variant-numeric: tabular-nums; }
:deep(.variance-nonzero) { color: var(--sc-app-warning-text); font-weight: 600; }
:deep(.patch-cell) { cursor: text; border-bottom: 1px dashed transparent; }
:deep(.patch-cell:hover) { border-bottom-color: var(--sc-app-accent); }
:deep(.patch-cell-editing) { display: flex; flex-direction: column; gap: 2px; min-width: 104px; }
:deep(.patch-cell-error) { color: var(--sc-app-danger-text); font-size: 12px; line-height: 1.3; max-width: 180px; }
.worksheet-patch-notice { display: flex; align-items: center; gap: var(--sc-space-xs); padding: var(--sc-space-xs) var(--sc-space-sm); border-bottom: 1px solid var(--sc-app-border); }
.worksheet-patch-notice span { flex: 1; min-width: 0; }
.worksheet-patch-notice.patch-success { color: var(--sc-app-success-text); }
.worksheet-patch-notice.patch-error { color: var(--sc-app-danger-text); }
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
.worksheet-mobile-navigation { min-width: 0; max-height: calc(100vh - 160px); overflow: auto; }
@media (max-width: 960px) { .worksheet-layout { grid-template-columns: 1fr !important; height: auto; } .worksheet-navigation, .worksheet-resizer-navigation { display: none; } .worksheet-main { min-height: 680px; } .worksheet-grid-toolbar { align-items: stretch; flex-direction: column; gap: var(--sc-space-xs); padding-block: var(--sc-space-xs); } .worksheet-scope-trigger { display: inline-flex; justify-content: flex-start; min-height: var(--sc-touch-target-min); overflow: hidden; text-overflow: ellipsis; } }
@media (max-width: 640px) {
  .worksheet-detail-fields { grid-template-columns: max-content minmax(0, 1fr); }
}
</style>
