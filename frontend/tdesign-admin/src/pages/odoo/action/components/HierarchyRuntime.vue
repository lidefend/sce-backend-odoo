<template>
  <section class="hierarchy-runtime">
    <aside class="hierarchy-nav">
      <div class="hierarchy-nav__title">
        <strong>{{ navigationTitle }}</strong>
        <t-button size="small" variant="text" @click="selectNode(null)">全部</t-button>
      </div>
      <t-input v-model="keyword" clearable placeholder="搜索层级或记录">
        <template #suffix-icon><t-icon name="search" /></template>
      </t-input>
      <div class="hierarchy-tree">
        <t-tree
          v-if="filteredTree.length"
          :data="filteredTree"
          :keys="{ value: 'key', label: 'label', children: 'children' }"
          :expand-all="true"
          hover
          activable
          @click="({ node }) => selectNode((node?.data || null) as HierarchyNode | null)"
        />
        <t-empty v-else description="暂无层级数据" />
      </div>
    </aside>
    <main class="hierarchy-content">
      <header class="hierarchy-toolbar">
        <div>
          <strong>{{ selectedNode?.label || '全部记录' }}</strong>
          <span>共 {{ visibleRows.length }} 条</span>
        </div>
        <t-space>
          <t-button size="small" variant="outline" :loading="loading" @click="load">刷新</t-button>
          <t-button v-if="canCreate" size="small" theme="primary" @click="emit('create-record')">
            {{ createLabel }}
          </t-button>
        </t-space>
      </header>
      <t-alert v-if="error" theme="error" :message="error" />
      <t-table
        :data="visibleRows"
        :columns="columns"
        :loading="loading"
        :row-class-name="rowClassName"
        row-key="id"
        bordered
        stripe
        hover
        max-height="calc(100vh - 330px)"
        @row-click="({ row }) => selectRecord(row)"
      >
        <template #tree-cell="{ row }">
          <div class="tree-cell" :style="{ paddingLeft: `${Number(row.__depth || 0) * 18}px` }">
            <t-icon v-if="Number(row.__depth || 0)" name="branch" />
            <span>{{ formatValue(row[treeField]) }}</span>
          </div>
        </template>
        <template #operation="{ row }">
          <t-space size="small">
            <t-link theme="primary" @click="emit('open-record', row)">详情</t-link>
            <t-dropdown
              v-if="availableCommands(row).length"
              :options="availableCommands(row).map((item) => ({ content: item.label, value: item.key }))"
              @click="runCommand(row, $event.value)"
            >
              <t-link theme="warning">层级操作</t-link>
            </t-dropdown>
          </t-space>
        </template>
        <template #empty><t-empty description="当前层级没有记录" /></template>
      </t-table>
      <section v-if="isWorksheet && detailTabs.length" class="worksheet-detail">
        <t-tabs v-model="activeDetailTab">
          <t-tab-panel v-for="tab in detailTabs" :key="tab.key" :value="tab.key" :label="tab.label">
            <t-descriptions v-if="selectedRecord" :column="2" bordered>
              <t-descriptions-item v-for="field in tab.fields" :key="field" :label="fieldLabel(field)">
                {{ formatValue(selectedRecord[field]) }}
              </t-descriptions-item>
            </t-descriptions>
            <t-empty v-else :description="String(worksheet.labels?.select_hint || '请选择一条记录查看详情')" />
          </t-tab-panel>
        </t-tabs>
      </section>
    </main>
  </section>
</template>
<script setup lang="ts">
import type { PrimaryTableCol } from 'tdesign-vue-next';
import { MessagePlugin } from 'tdesign-vue-next';
import { computed, onMounted, ref, watch } from 'vue';

import { executeButton, listData } from '@/api/odoo';

type Dict = Record<string, any>;
interface HierarchyNode {
  key: string;
  id: number;
  label: string;
  code: string;
  levelKey: string;
  depth: number;
  raw: Dict;
  children: HierarchyNode[];
  recordIds?: number[];
}

const props = defineProps<{
  model: string;
  config: Dict;
  fields: Array<{ code: string; label: string; type: string; relation?: string }>;
  domain?: unknown[];
  canCreate?: boolean;
}>();
const emit = defineEmits<{ 'open-record': [row: Dict]; 'create-record': [] }>();
const loading = ref(false);
const error = ref('');
const roots = ref<HierarchyNode[]>([]);
const records = ref<Dict[]>([]);
const selectedNode = ref<HierarchyNode | null>(null);
const selectedRecord = ref<Dict | null>(null);
const activeDetailTab = ref('');
const keyword = ref('');

const isWorksheet = computed(() => Boolean(props.config.hierarchical_worksheet));
const worksheet = computed(() => (props.config.hierarchical_worksheet || {}) as Dict);
const levels = computed(() => (Array.isArray(props.config.hierarchy_levels) ? props.config.hierarchy_levels : []));
const treeField = computed(() =>
  String(
    worksheet.value.tree_column ||
      props.fields.find((field) => field.code === 'name')?.code ||
      props.fields[0]?.code ||
      'name',
  ),
);
const navigationTitle = computed(() =>
  String(
    worksheet.value.navigation_title ||
      levels.value.map((item: Dict) => item.label || item.field).join(' / ') ||
      '层级导航',
  ),
);
const createLabel = computed(() => String((props.config.hierarchy_create || {}).label || '新建'));
const commands = computed(() =>
  Array.isArray(props.config.hierarchy_commands) ? props.config.hierarchy_commands : [],
);
const detailTabs = computed(() =>
  (Array.isArray(worksheet.value.tabs) ? worksheet.value.tabs : []).map((tab: Dict, index: number) => ({
    key: String(tab.key || `tab-${index}`),
    label: String(tab.label || tab.key || `详情 ${index + 1}`),
    fields: Array.isArray(tab.fields) ? tab.fields.map(String) : [],
  })),
);

function relationId(value: unknown) {
  return Array.isArray(value) ? Number(value[0] || 0) : Number(value || 0);
}
function displayValue(value: unknown) {
  if (Array.isArray(value)) return String(value[1] ?? value[0] ?? '');
  if (value === false || value === null || value === undefined) return '';
  return String(value);
}
function formatValue(value: unknown) {
  return displayValue(value) || '—';
}
function unique(values: string[]) {
  return values.filter((value, index) => value && values.indexOf(value) === index);
}
async function loadAll(model: string, fields: string[], domain: unknown[] = [], order = '') {
  const result: Dict[] = [];
  const limit = 5000;
  for (let offset = 0; ; offset += limit) {
    const payload = await listData({ model, fields: unique(['id', ...fields]), domain, order, offset, limit });
    const rows = (payload.records || payload.rows || []) as Dict[];
    result.push(...rows);
    if (rows.length < limit) return result;
  }
}
function setDepth(nodes: HierarchyNode[], depth = 0) {
  nodes.forEach((node) => {
    node.depth = depth;
    setDepth(node.children, depth + 1);
  });
}
async function loadWorksheet() {
  const groups = Array.isArray(worksheet.value.navigation_groups) ? worksheet.value.navigation_groups : [];
  const sheetFields = unique([
    ...props.fields.map((field) => field.code),
    ...groups.map((group: Dict) => String(group.field || '')),
    ...detailTabs.value.flatMap((tab) => tab.fields),
    String(worksheet.value.row_kind_field || ''),
    String(worksheet.value.binding_field || ''),
  ]);
  records.value = await loadAll(
    props.model,
    sheetFields,
    (worksheet.value.sheet_domain || props.domain || []) as unknown[],
    String(worksheet.value.sheet_order || ''),
  );
  let virtualId = -1;
  const rootsOut: HierarchyNode[] = [];
  const nodes = new Map<string, HierarchyNode>();
  records.value.forEach((record) => {
    let parent: HierarchyNode | null = null;
    let path = '';
    groups.forEach((group: Dict, depth: number) => {
      const field = String(group.field || '');
      const label = displayValue(record[field]) || String(group.empty_label || '未分类');
      path += `/${field}:${label}`;
      let node = nodes.get(path);
      if (!node) {
        node = {
          key: path,
          id: virtualId--,
          label,
          code: '',
          levelKey: field,
          depth,
          raw: {},
          children: [],
          recordIds: [],
        };
        nodes.set(path, node);
        if (parent) parent.children.push(node);
        else rootsOut.push(node);
      }
      const id = Number(record.id || 0);
      if (id && !node.recordIds?.includes(id)) node.recordIds?.push(id);
      parent = node;
    });
  });
  roots.value = rootsOut;
  selectedRecord.value = records.value[0] || null;
  activeDetailTab.value = activeDetailTab.value || detailTabs.value[0]?.key || '';
}
async function loadHierarchy() {
  const maps = new Map<string, Map<number, HierarchyNode>>();
  let rootNodes: HierarchyNode[] = [];
  for (const raw of levels.value) {
    const level = raw as Dict;
    const fieldSpec = props.fields.find((field) => field.code === String(level.field || '')) as Dict | undefined;
    const model = String(level.model || fieldSpec?.relation || '');
    const field = String(level.field || '');
    if (!model || !field) continue;
    const required = unique([
      String(level.label_field || 'display_name'),
      String(level.code_field || ''),
      String(level.parent_field || ''),
      String(level.self_parent_field || ''),
    ]);
    const rows = await loadAll(model, required, (level.domain || []) as unknown[], String(level.order || ''));
    const map = new Map<number, HierarchyNode>();
    rows.forEach((row) => {
      const id = Number(row.id || 0);
      if (!id) return;
      const label = displayValue(row[String(level.label_field || 'display_name')]);
      const code = displayValue(row[String(level.code_field || '')]);
      map.set(id, {
        key: `${field}:${id}`,
        id,
        label: [code, label].filter(Boolean).join(' '),
        code,
        levelKey: field,
        depth: 0,
        raw: row,
        children: [],
      });
    });
    maps.set(field, map);
    const nested = new Set<number>();
    if (level.self_parent_field) {
      rows.forEach((row) => {
        const node = map.get(Number(row.id));
        const parent = map.get(relationId(row[String(level.self_parent_field)]));
        if (node && parent && node !== parent) {
          parent.children.push(node);
          nested.add(node.id);
        }
      });
    }
    if (!level.parent_key && maps.size === 1) {
      rootNodes = [...map.values()].filter((node) => !nested.has(node.id));
    } else {
      const previous = levels.value[Math.max(0, levels.value.indexOf(raw) - 1)] as Dict;
      const parents = maps.get(String(level.parent_key || previous?.field || ''));
      rows.forEach((row) => {
        const node = map.get(Number(row.id));
        const parent = parents?.get(relationId(row[String(level.parent_field || '')]));
        if (node && parent && !nested.has(node.id)) parent.children.push(node);
      });
    }
  }
  setDepth(rootNodes);
  roots.value = rootNodes;
  records.value = await loadAll(
    props.model,
    unique([
      ...props.fields.map((field) => field.code),
      ...commands.value.map((command: Dict) => String(command.availability_field || '')),
      ...levels.value.map((level: Dict) => String(level.field || '')),
    ]),
    props.domain || [],
  );
}
async function load() {
  loading.value = true;
  error.value = '';
  try {
    if (isWorksheet.value) await loadWorksheet();
    else await loadHierarchy();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '层级数据加载失败';
  } finally {
    loading.value = false;
  }
}
function selectNode(node: HierarchyNode | null) {
  selectedNode.value = node;
}
function collectNodeIds(node: HierarchyNode) {
  const ids = new Set<number>();
  const visit = (item: HierarchyNode) => {
    ids.add(item.id);
    item.children.forEach(visit);
  };
  visit(node);
  return ids;
}
const filteredTree = computed(() => {
  const term = keyword.value.trim().toLowerCase();
  if (!term) return roots.value;
  const filter = (node: HierarchyNode): HierarchyNode | null => {
    const children = node.children.map(filter).filter(Boolean) as HierarchyNode[];
    return node.label.toLowerCase().includes(term) || children.length ? { ...node, children } : null;
  };
  return roots.value.map(filter).filter(Boolean) as HierarchyNode[];
});
const visibleRows = computed(() => {
  const term = keyword.value.trim().toLowerCase();
  let values = records.value;
  if (selectedNode.value) {
    if (isWorksheet.value) {
      const ids = new Set(selectedNode.value.recordIds || []);
      values = values.filter((row) => ids.has(Number(row.id)));
    } else {
      const ids = collectNodeIds(selectedNode.value);
      const level = levels.value.find((item: Dict) => String(item.field) === selectedNode.value?.levelKey) as Dict;
      const operator = String(level?.domain_operator || '=');
      const field = String(level?.field || selectedNode.value.levelKey);
      values = values.filter((row) => {
        const id = relationId(row[field]);
        return operator === 'child_of' ? ids.has(Number(row.id)) || ids.has(id) : id === selectedNode.value?.id;
      });
    }
  }
  if (term)
    values = values.filter((row) => Object.values(row).map(displayValue).join(' ').toLowerCase().includes(term));
  if (!isWorksheet.value) {
    const selfParent = levels.value.find((item: Dict) => item.self_parent_field) as Dict;
    if (selfParent) {
      const byId = new Map(values.map((row) => [Number(row.id), row]));
      const depths = new Map<number, number>();
      const depthOf = (row: Dict): number => {
        const id = Number(row.id);
        if (depths.has(id)) return Number(depths.get(id));
        const parent = byId.get(relationId(row[String(selfParent.self_parent_field)]));
        const depth = parent && parent !== row ? depthOf(parent) + 1 : 0;
        depths.set(id, depth);
        return depth;
      };
      return values.map((row) => ({ ...row, __depth: depthOf(row) }));
    }
  }
  return values;
});
const columns = computed<PrimaryTableCol[]>(() => [
  ...props.fields.map((field) => ({
    colKey: field.code,
    title: field.label || field.code,
    ellipsis: true,
    minWidth: field.code === treeField.value ? 220 : 120,
    cell:
      field.code === treeField.value
        ? 'tree-cell'
        : (_h: unknown, { row }: { row: Dict }) => formatValue(row[field.code]),
  })),
  { colKey: 'operation', title: '操作', width: 130, fixed: 'right' as const },
]);
function availableCommands(row: Dict) {
  return commands.value.filter(
    (command: Dict) => !command.availability_field || row[command.availability_field] === true,
  );
}
function selectRecord(row: Dict) {
  selectedRecord.value = row;
}
function fieldLabel(field: string) {
  return props.fields.find((item) => item.code === field)?.label || field;
}
function rowClassName({ row }: { row: Dict }) {
  if (!isWorksheet.value) return '';
  const kind = String(row[String(worksheet.value.row_kind_field || '')] || '');
  if ((worksheet.value.heading_values || []).includes(kind)) return 'worksheet-row--heading';
  if ((worksheet.value.summary_values || []).includes(kind)) return 'worksheet-row--summary';
  return '';
}
async function runCommand(row: Dict, key: unknown) {
  const command = commands.value.find((item: Dict) => String(item.key) === String(key)) as Dict | undefined;
  if (!command?.method) return;
  try {
    await executeButton({
      model: props.model,
      recordId: Number(row.id),
      button: { name: command.method, type: 'object' },
    });
    MessagePlugin.success(`${command.label || '层级操作'}已完成`);
    await load();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '层级操作失败');
  }
}

watch(() => [props.model, props.config], load, { deep: true });
onMounted(load);
</script>
<style scoped>
.hierarchy-runtime {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  min-height: 560px;
  overflow: hidden;
  border: 1px solid var(--td-border-level-1-color);
}
.hierarchy-nav {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 10px;
  min-width: 0;
  padding: 14px;
  border-right: 1px solid var(--td-border-level-1-color);
  background: var(--td-bg-color-secondarycontainer);
}
.hierarchy-nav__title,
.hierarchy-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.hierarchy-tree {
  min-height: 0;
  overflow: auto;
}
.hierarchy-content {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  min-width: 0;
}
.worksheet-detail {
  max-height: 260px;
  padding: 0 14px 14px;
  overflow: auto;
  border-top: 1px solid var(--td-border-level-1-color);
}
.hierarchy-content :deep(.worksheet-row--heading > td) {
  background: var(--td-bg-color-secondarycontainer);
  font-weight: 600;
}
.hierarchy-content :deep(.worksheet-row--summary > td) {
  background: var(--td-brand-color-light);
  font-weight: 600;
}
.hierarchy-toolbar {
  min-height: 54px;
  padding: 0 14px;
  border-bottom: 1px solid var(--td-border-level-1-color);
}
.hierarchy-toolbar > div {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.hierarchy-toolbar span {
  color: var(--td-text-color-secondary);
  font-size: 12px;
}
.tree-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}
@media (width <= 900px) {
  .hierarchy-runtime {
    grid-template-columns: minmax(0, 1fr);
  }
  .hierarchy-nav {
    max-height: 280px;
    border-right: 0;
    border-bottom: 1px solid var(--td-border-level-1-color);
  }
}
</style>
