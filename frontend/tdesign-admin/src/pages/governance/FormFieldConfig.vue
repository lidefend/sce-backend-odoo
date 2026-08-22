<template>
  <div class="field-config-page">
    <header class="page-heading">
      <div>
        <span>低代码配置</span>
        <h1>表单字段配置</h1>
        <p>基于当前动态菜单的真实表单 contract 调整字段显隐、顺序、分组和布局。</p>
      </div>
      <t-space size="small">
        <t-button variant="outline" :loading="loading" @click="loadContract">
          <template #icon><t-icon name="refresh" /></template>
          刷新
        </t-button>
        <t-button theme="primary" :disabled="!fields.length" @click="customFieldVisible = true">
          <template #icon><t-icon name="add" /></template>
          自定义字段
        </t-button>
      </t-space>
    </header>

    <t-alert v-if="error" theme="error" :message="error" />

    <section class="panel scope-panel">
      <div class="scope-field scope-field--wide">
        <label>业务表单</label>
        <t-select
          v-model="selectedTarget"
          :options="targetOptions"
          filterable
          placeholder="选择当前角色可访问的业务表单"
          @change="loadContract"
        />
      </div>
      <div class="scope-field">
        <label>表单列数</label>
        <t-radio-group v-model="formColumns" variant="default-filled">
          <t-radio-button :value="1">单列</t-radio-button>
          <t-radio-button :value="2">双列</t-radio-button>
          <t-radio-button :value="3">三列</t-radio-button>
        </t-radio-group>
      </div>
      <div class="scope-actions">
        <t-button variant="outline" :disabled="!fields.length" :loading="busy === 'order'" @click="saveOrder">
          保存顺序
        </t-button>
        <t-button theme="primary" :disabled="!fields.length" :loading="busy === 'batch'" @click="saveAll">
          保存全部配置
        </t-button>
      </div>
    </section>

    <section class="designer-layout">
      <section class="panel table-panel">
        <header class="panel-header">
          <div>
            <h2>{{ activeTarget?.label || '字段列表' }}</h2>
            <p>{{ activeTarget?.model || '请选择业务表单' }}</p>
          </div>
          <t-tag v-if="fields.length" variant="light">{{ fields.length }} 个字段</t-tag>
        </header>
        <t-table
          :data="fields"
          :columns="columns"
          row-key="name"
          :loading="loading"
          size="small"
          stripe
          hover
          drag-sort="row"
          @drag-sort="onDragSort"
        >
          <template #label="{ row }">
            <div class="field-name">
              <strong>{{ row.label }}</strong
              ><small>{{ row.name }}</small>
            </div>
          </template>
          <template #visible="{ row }"><t-switch v-model="row.visible" /></template>
          <template #group="{ row }"><t-input v-model="row.group" clearable placeholder="基本信息" /></template>
          <template #tab="{ row }"><t-input v-model="row.tab" clearable placeholder="主表单" /></template>
          <template #size="{ row }">
            <t-select v-model="row.size" :options="sizeOptions" clearable placeholder="默认" />
          </template>
          <template #operations="{ row, rowIndex }">
            <t-space size="small">
              <t-button
                shape="square"
                variant="text"
                :disabled="rowIndex === 0"
                title="上移"
                @click="move(rowIndex, -1)"
              >
                <template #icon><t-icon name="arrow-up" /></template>
              </t-button>
              <t-button
                shape="square"
                variant="text"
                :disabled="rowIndex === fields.length - 1"
                title="下移"
                @click="move(rowIndex, 1)"
              >
                <template #icon><t-icon name="arrow-down" /></template>
              </t-button>
              <t-button
                size="small"
                variant="text"
                theme="primary"
                :loading="busy === `field:${row.name}`"
                @click="saveField(row)"
              >
                保存
              </t-button>
            </t-space>
          </template>
        </t-table>
        <t-empty v-if="!loading && !fields.length" description="请选择一个包含表单 contract 的动态菜单" />
      </section>
      <aside class="panel preview-panel">
        <header class="panel-header">
          <div>
            <h2>实时预览</h2>
            <p>按当前 Notebook、分区、顺序和列数预览。</p>
          </div>
        </header>
        <t-tabs v-model="previewTab"
          ><t-tab-panel v-for="tab in previewTabs" :key="tab.key" :value="tab.key" :label="tab.label"
        /></t-tabs>
        <section v-for="group in previewGroups" :key="group.key" class="preview-group">
          <h3>{{ group.label }}</h3>
          <div class="preview-grid" :style="{ gridTemplateColumns: `repeat(${formColumns}, minmax(0, 1fr))` }">
            <div v-for="field in group.fields" :key="field.name" class="preview-field">
              <label>{{ field.label }}</label
              ><t-input :placeholder="field.type" disabled />
            </div>
          </div>
        </section>
        <t-empty v-if="!previewGroups.length" description="当前页签没有可见字段" />
      </aside>
    </section>

    <t-dialog v-model:visible="customFieldVisible" header="新增租户自定义字段" width="620px" :footer="false">
      <t-form label-align="top">
        <div class="form-grid">
          <t-form-item label="字段名称" required
            ><t-input v-model="customField.label" placeholder="例如：现场联系人"
          /></t-form-item>
          <t-form-item label="稳定业务键"
            ><t-input v-model="customField.extension_key" placeholder="例如：site_contact"
          /></t-form-item>
          <t-form-item label="字段类型" required
            ><t-select v-model="customField.ttype" :options="typeOptions"
          /></t-form-item>
          <t-form-item label="所属分组"
            ><t-input v-model="customField.group_title" placeholder="业务配置字段"
          /></t-form-item>
          <t-form-item label="帮助说明" class="form-grid__wide"
            ><t-textarea v-model="customField.help" autosize
          /></t-form-item>
          <t-form-item label="是否必填"><t-switch v-model="customField.required" /></t-form-item>
        </div>
        <t-alert v-if="previewResult" theme="info" :message="previewResult" />
        <div class="dialog-actions">
          <t-button variant="outline" :loading="busy === 'preview'" @click="previewCustomField">校验配置</t-button>
          <t-button theme="primary" :loading="busy === 'create'" @click="createCustomField">确认创建</t-button>
        </div>
      </t-form>
    </t-dialog>
  </div>
</template>
<script setup lang="ts">
import { MessagePlugin } from 'tdesign-vue-next';
import { computed, onMounted, reactive, ref } from 'vue';

import { batchSetFormFieldConfig, createFormCustomField, setFormFieldOrder, setFormFieldPolicy } from '@/api/odoo';
import { loadFormContract } from '@/runtime/contract';
import { normalizeFieldType } from '@/runtime/fieldType';
import { useUserStore } from '@/store';

type Dict = Record<string, any>;
interface TargetOption {
  value: string;
  label: string;
  model: string;
  actionId?: number;
  menuId?: number;
}
interface FieldRow {
  name: string;
  label: string;
  type: string;
  visible: boolean;
  group: string;
  tab: string;
  size: string;
}

const userStore = useUserStore();
const loading = ref(false);
const busy = ref('');
const error = ref('');
const selectedTarget = ref('');
const fields = ref<FieldRow[]>([]);
const formColumns = ref(2);
const previewTab = ref('main');
const customFieldVisible = ref(false);
const previewResult = ref('');
const customField = reactive({
  label: '',
  extension_key: '',
  ttype: 'char',
  group_title: '业务配置字段',
  help: '',
  required: false,
});
const targetOptions = computed<TargetOption[]>(() => collectTargets(userStore.navigation));
const activeTarget = computed(() => targetOptions.value.find((item) => item.value === selectedTarget.value));
const columns = [
  { colKey: 'label', title: '字段', minWidth: 190 },
  { colKey: 'type', title: '类型', width: 110 },
  { colKey: 'visible', title: '显示', width: 90 },
  { colKey: 'group', title: '分组', minWidth: 160 },
  { colKey: 'tab', title: 'Notebook', minWidth: 140 },
  { colKey: 'size', title: '尺寸', width: 130 },
  { colKey: 'operations', title: '操作', width: 170, fixed: 'right' as const },
];
const previewTabs = computed(() => {
  const names = [...new Set(fields.value.map((field) => field.tab || '主表单'))];
  return names.map((label, index) => ({ key: index === 0 ? 'main' : label, label }));
});
const previewGroups = computed(() => {
  const activeLabel =
    previewTabs.value.find((tab) => tab.key === previewTab.value)?.label || previewTabs.value[0]?.label;
  const groups = new Map<string, FieldRow[]>();
  fields.value
    .filter((field) => field.visible && (field.tab || '主表单') === activeLabel)
    .forEach((field) =>
      groups.set(field.group || '基本信息', [...(groups.get(field.group || '基本信息') || []), field]),
    );
  return [...groups].map(([label, groupFields]) => ({ key: label, label, fields: groupFields }));
});
const sizeOptions = [
  { value: 'small', label: '紧凑' },
  { value: 'medium', label: '标准' },
  { value: 'large', label: '宽字段' },
  { value: 'full', label: '整行' },
];
const typeOptions = [
  { value: 'char', label: '单行文本' },
  { value: 'text', label: '多行文本' },
  { value: 'integer', label: '整数' },
  { value: 'float', label: '小数' },
  { value: 'monetary', label: '金额' },
  { value: 'boolean', label: '是/否' },
  { value: 'date', label: '日期' },
  { value: 'datetime', label: '日期时间' },
  { value: 'selection', label: '选项' },
];

function asDict(value: unknown): Dict {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Dict) : {};
}

function collectTargets(nodes: Array<Record<string, unknown>>, parents: string[] = []): TargetOption[] {
  const result: TargetOption[] = [];
  nodes.forEach((raw) => {
    const node = raw as Dict;
    const label = String(node.label || node.name || node.title || '未命名菜单');
    const nextParents = [...parents, label];
    const model = String(node.model || asDict(node.meta).model || asDict(node.entry_target).model || '');
    const actionId =
      Number(node.action_id || asDict(node.meta).action_id || asDict(node.entry_target).action_id || 0) || undefined;
    const menuId = Number(node.menu_id || node.id || asDict(node.meta).menu_id || 0) || undefined;
    if (model && actionId) {
      result.push({
        value: `${actionId}:${menuId || 0}:${model}`,
        label: nextParents.join(' / '),
        model,
        actionId,
        menuId,
      });
    }
    result.push(...collectTargets((node.children as Array<Record<string, unknown>>) || [], nextParents));
  });
  return result.filter((item, index, rows) => rows.findIndex((row) => row.value === item.value) === index);
}

async function loadContract() {
  const target = activeTarget.value;
  if (!target) {
    fields.value = [];
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    const contract = await loadFormContract({ model: target.model, actionId: target.actionId, menuId: target.menuId });
    fields.value = extractFields(contract);
    const layout = asDict(contract.layoutContract || contract.layout_contract || contract.layout);
    formColumns.value = Number(layout.columns || asDict(layout.config).columns || 2) || 2;
  } catch (cause) {
    fields.value = [];
    error.value = cause instanceof Error ? cause.message : '表单 contract 加载失败';
  } finally {
    loading.value = false;
  }
}

function extractFields(contract: Dict): FieldRow[] {
  const layout = asDict(contract.layoutContract || contract.layout_contract || contract.layout);
  const roots = Array.isArray(layout.containerTree)
    ? layout.containerTree
    : Array.isArray(layout.container_tree)
      ? layout.container_tree
      : Array.isArray(layout.widgetList)
        ? layout.widgetList
        : [];
  const output: FieldRow[] = [];
  const seen = new Set<string>();
  const visit = (value: unknown, group = '') => {
    if (!value || typeof value !== 'object') return;
    if (Array.isArray(value)) {
      value.forEach((item) => visit(item, group));
      return;
    }
    const node = value as Dict;
    const kind = String(node.type || node.kind || '').toLowerCase();
    const nextGroup = ['group', 'section'].includes(kind)
      ? String(node.label || node.title || node.string || group)
      : group;
    const info = asDict(node.fieldInfo || node.field_info);
    const config = asDict(node.componentConfig || node.component_config);
    const name = String(node.fieldCode || node.field_code || info.name || (kind === 'field' ? node.name : '') || '');
    if (name && !seen.has(name)) {
      seen.add(name);
      output.push({
        name,
        label: String(node.label || node.string || info.label || info.string || name),
        type: normalizeFieldType(config.fieldType || info.type || node.fieldType || node.ttype || 'char'),
        visible: node.visible !== false && node.invisible !== true && config.invisible !== true,
        group: String(node.group_title || config.group_title || nextGroup || '基本信息'),
        tab: String(node.tab_title || config.tab_title || '主表单'),
        size: String(config.field_size || config.fieldSize || node.field_size || ''),
      });
    }
    ['children', 'widgetList', 'pages', 'tabs', 'nodes', 'items', 'fields', 'groups', 'sub_groups'].forEach((key) => {
      if (node[key]) visit(node[key], nextGroup);
    });
  };
  visit(roots);
  if (!output.length) visit(contract.fields || asDict(contract.dataContract).fields);
  return output;
}

function scopeParams() {
  const target = activeTarget.value;
  if (!target) throw new Error('请先选择业务表单');
  return { model: target.model, action_id: target.actionId, view_id: undefined };
}

function move(index: number, offset: number) {
  const target = index + offset;
  if (target < 0 || target >= fields.value.length) return;
  const next = [...fields.value];
  [next[index], next[target]] = [next[target], next[index]];
  fields.value = next;
}
function onDragSort(event: { currentIndex: number; targetIndex: number }) {
  const next = [...fields.value];
  const [moved] = next.splice(event.currentIndex, 1);
  if (moved) next.splice(event.targetIndex, 0, moved);
  fields.value = next;
}

async function saveField(row: FieldRow) {
  busy.value = `field:${row.name}`;
  error.value = '';
  try {
    await setFormFieldPolicy({
      ...scopeParams(),
      field_name: row.name,
      label: row.label,
      visible: row.visible,
      group_title: row.group,
      sequence: (fields.value.indexOf(row) + 1) * 10,
    });
    MessagePlugin.success(`${row.label}配置已保存`);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '字段配置保存失败';
  } finally {
    busy.value = '';
  }
}

async function saveOrder() {
  busy.value = 'order';
  error.value = '';
  try {
    await setFormFieldOrder({
      ...scopeParams(),
      field_order: fields.value.map((field) => field.name),
      field_groups: Object.fromEntries(fields.value.map((field) => [field.name, field.group])),
      field_tabs: Object.fromEntries(fields.value.map((field) => [field.name, field.tab])),
    });
    MessagePlugin.success('字段顺序已保存');
    await loadContract();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '字段顺序保存失败';
  } finally {
    busy.value = '';
  }
}

async function saveAll() {
  busy.value = 'batch';
  error.value = '';
  try {
    await batchSetFormFieldConfig({
      ...scopeParams(),
      field_order: fields.value.map((field) => field.name),
      field_visibility: Object.fromEntries(fields.value.map((field) => [field.name, field.visible])),
      field_groups: Object.fromEntries(fields.value.map((field) => [field.name, field.group])),
      field_sizes: Object.fromEntries(
        fields.value.filter((field) => field.size).map((field) => [field.name, field.size]),
      ),
      form_columns: formColumns.value,
    });
    MessagePlugin.success('表单字段配置已发布');
    await loadContract();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '表单字段配置保存失败';
  } finally {
    busy.value = '';
  }
}

async function submitCustomField(dryRun: boolean) {
  if (!customField.label.trim()) {
    MessagePlugin.warning('请填写字段名称');
    return;
  }
  busy.value = dryRun ? 'preview' : 'create';
  error.value = '';
  try {
    const result = await createFormCustomField({ ...scopeParams(), ...customField, dry_run: dryRun });
    if (dryRun) {
      previewResult.value = `校验通过，将创建 ${String(result.extension_key || customField.extension_key || customField.label)} 字段。`;
    } else {
      MessagePlugin.success('自定义字段已创建');
      customFieldVisible.value = false;
      previewResult.value = '';
      Object.assign(customField, {
        label: '',
        extension_key: '',
        ttype: 'char',
        group_title: '业务配置字段',
        help: '',
        required: false,
      });
      await loadContract();
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : dryRun ? '字段配置校验失败' : '自定义字段创建失败';
  } finally {
    busy.value = '';
  }
}

function previewCustomField() {
  void submitCustomField(true);
}
function createCustomField() {
  void submitCustomField(false);
}

onMounted(async () => {
  if (!userStore.navigation.length) await userStore.getUserInfo();
  selectedTarget.value = targetOptions.value[0]?.value || '';
  await loadContract();
});
</script>
<style scoped>
.field-config-page {
  display: grid;
  gap: 16px;
}
.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.page-heading span {
  color: var(--td-brand-color);
  font-size: 13px;
}
.page-heading h1,
.page-heading p {
  margin: 0;
}
.page-heading h1 {
  margin-top: 4px;
  font-size: 28px;
}
.page-heading p {
  margin-top: 8px;
  color: var(--td-text-color-secondary);
}
.panel {
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 8px;
  background: var(--td-bg-color-container);
}
.scope-panel {
  display: flex;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 16px;
  padding: 18px;
}
.scope-field {
  display: grid;
  gap: 7px;
}
.scope-field label {
  color: var(--td-text-color-secondary);
  font-size: 13px;
}
.scope-field--wide {
  flex: 1;
  min-width: min(420px, 100%);
}
.scope-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}
.table-panel {
  min-width: 0;
  padding: 18px;
  overflow: hidden;
}
.designer-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(340px, 0.9fr);
  gap: 16px;
  align-items: start;
}
.preview-panel {
  position: sticky;
  top: 64px;
  padding: 18px;
}
.preview-group {
  margin-top: 16px;
}
.preview-group h3 {
  margin: 0 0 10px;
  font-size: 15px;
}
.preview-grid {
  display: grid;
  gap: 12px;
}
.preview-field {
  min-width: 0;
}
.preview-field label {
  display: block;
  margin-bottom: 6px;
  color: var(--td-text-color-secondary);
  font-size: 12px;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.panel-header h2,
.panel-header p {
  margin: 0;
}
.panel-header h2 {
  font-size: 18px;
}
.panel-header p {
  margin-top: 4px;
  color: var(--td-text-color-secondary);
}
.field-name {
  display: grid;
  gap: 3px;
}
.field-name small {
  color: var(--td-text-color-secondary);
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}
.form-grid__wide {
  grid-column: 1 / -1;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
}
@media (width <= 720px) {
  .designer-layout {
    grid-template-columns: 1fr;
  }
  .preview-panel {
    position: static;
  }
  .preview-grid {
    grid-template-columns: 1fr !important;
  }
  .page-heading {
    flex-direction: column;
  }
  .scope-field--wide {
    min-width: 100%;
  }
  .scope-actions {
    width: 100%;
    margin-left: 0;
  }
  .form-grid {
    grid-template-columns: 1fr;
  }
  .form-grid__wide {
    grid-column: auto;
  }
}
</style>
