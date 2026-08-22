<template>
  <div class="governance-page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">系统治理</p>
        <h1>菜单配置</h1>
        <p>配置只提交到后端 contract，不直接修改前端动态路由。</p>
      </div>
      <div class="heading-actions">
        <t-button
          variant="outline"
          @click="
            auditDialogVisible = true;
            loadAudit();
          "
          >审计/版本</t-button
        ><t-button variant="outline" @click="createDialogVisible = true">新建菜单</t-button
        ><t-button variant="outline" :loading="loading" @click="load">刷新</t-button
        ><t-button theme="primary" :loading="saving" @click="save">保存配置</t-button>
      </div>
    </div>
    <t-alert v-if="error" theme="error" :message="error" />
    <t-card :bordered="false" class="panel"
      ><t-table
        :data="rows"
        :columns="columns"
        :loading="loading"
        row-key="menu_id"
        drag-sort="row"
        @drag-sort="onDragSort"
        ><template #custom_label="{ row }"
          ><t-input v-model="row.custom_label" :placeholder="row.name || '显示名称'" clearable /></template
        ><template #parent="{ row }"
          ><t-select
            v-model="row.target_parent_menu_id"
            :options="parentOptions.filter((option) => option.value !== row.menu_id)"
            clearable
            filterable
            placeholder="沿用原父级" /></template
        ><template #roles="{ row }"
          ><t-select
            v-model="row.role_group_ids"
            :options="groupOptions"
            multiple
            filterable
            clearable
            collapse-tags
            placeholder="全部角色" /></template
        ><template #visible="{ row }"><t-switch v-model="row.visible" /></template
        ><template #sequence="{ row }"><t-input-number v-model="row.sequence_override" theme="normal" /></template
        ><template #runtime="{ row }"
          ><t-tag :theme="row.runtime_visible === false ? 'danger' : 'success'" variant="light">{{
            row.runtime_visible === false ? '隐藏' : '可见'
          }}</t-tag></template
        ><template #operation="{ row }"
          ><t-space size="small"
            ><t-button size="small" variant="text" theme="primary" @click="openCopy(row)">复制</t-button
            ><t-popconfirm content="确认删除该菜单配置？" @confirm="remove(row)"
              ><t-button size="small" variant="text" theme="danger">删除</t-button></t-popconfirm
            ></t-space
          ></template
        ></t-table
      ><t-empty v-if="!loading && !rows.length" description="暂无菜单配置"
    /></t-card>
    <t-dialog
      v-model:visible="createDialogVisible"
      header="新建菜单"
      :confirm-btn="{ content: '创建', loading: busy === 'create' }"
      @confirm="create"
    >
      <t-form label-align="top"
        ><t-form-item label="菜单名称" required><t-input v-model="createForm.name" /></t-form-item
        ><t-form-item label="上级菜单"
          ><t-select v-model="createForm.parent_menu_id" :options="parentOptions" clearable filterable /></t-form-item
        ><t-form-item label="排序"><t-input-number v-model="createForm.sequence" theme="normal" /></t-form-item
        ><t-form-item label="备注"><t-textarea v-model="createForm.note" /></t-form-item
      ></t-form>
    </t-dialog>
    <t-dialog
      v-model:visible="copyDialogVisible"
      header="复制菜单"
      :confirm-btn="{ content: '复制', loading: busy === 'copy' }"
      @confirm="copyMenu"
      ><t-form label-align="top"
        ><t-form-item label="新菜单名称" required><t-input v-model="copyForm.name" /></t-form-item
        ><t-form-item label="上级菜单"
          ><t-select v-model="copyForm.parent_menu_id" :options="parentOptions" filterable /></t-form-item
        ><t-form-item label="排序"><t-input-number v-model="copyForm.sequence" theme="normal" /></t-form-item></t-form
    ></t-dialog>
    <t-drawer v-model:visible="auditDialogVisible" header="菜单审计与版本" size="min(760px, 92vw)">
      <t-space style="margin-bottom: 12px"
        ><t-button variant="outline" :loading="busy === 'audit'" @click="loadAudit">刷新审计</t-button
        ><t-popconfirm content="确认回滚到选中版本？" @confirm="rollback"
          ><t-button theme="danger" variant="outline" :disabled="!rollbackVersion" :loading="busy === 'rollback'"
            >回滚版本</t-button
          ></t-popconfirm
        ><t-select v-model="rollbackVersion" :options="versionOptions" clearable placeholder="选择版本"
      /></t-space>
      <t-tabs
        ><t-tab-panel value="audit" label="审计">
          <pre class="result-json">{{ display(audit) }}</pre></t-tab-panel
        ><t-tab-panel value="versions" label="版本">
          <pre class="result-json">{{ display(versions) }}</pre>
        </t-tab-panel></t-tabs
      >
    </t-drawer>
  </div>
</template>
<script setup lang="ts">
import { MessagePlugin } from 'tdesign-vue-next';
import { computed, onMounted, ref } from 'vue';

import {
  createMenuConfigurationEntry,
  deleteMenuConfigurationEntry,
  loadMenuConfigurationAudit,
  loadMenuConfigurationPanel,
  loadMenuConfigurationVersions,
  rollbackMenuConfiguration,
  saveMenuConfigurationPanel,
} from '@/api/odoo';

type Dict = Record<string, any>;
const loading = ref(false);
const saving = ref(false);
const error = ref('');
const rows = ref<Dict[]>([]);
const groupOptions = ref<Array<{ value: number; label: string }>>([]);
const busy = ref('');
const createDialogVisible = ref(false);
const copyDialogVisible = ref(false);
const auditDialogVisible = ref(false);
const audit = ref<Dict>({});
const versions = ref<Dict>({});
const rollbackVersion = ref<number>();
const createForm = ref({ name: '', parent_menu_id: undefined as number | undefined, sequence: 10, note: '' });
const copyForm = ref({ source_menu_id: 0, name: '', parent_menu_id: undefined as number | undefined, sequence: 10 });
const columns = [
  { colKey: 'complete_name', title: '菜单路径', ellipsis: true },
  { colKey: 'custom_label', title: '显示名称', width: 190 },
  { colKey: 'parent', title: '上级菜单', width: 220 },
  { colKey: 'roles', title: '可见角色', width: 260 },
  { colKey: 'visible', title: '显示', width: 100 },
  { colKey: 'sequence', title: '顺序', width: 140 },
  { colKey: 'runtime', title: '运行时状态', width: 120 },
  { colKey: 'operation', title: '操作', width: 90, fixed: 'right' as const },
];
function onDragSort(event: { currentIndex: number; targetIndex: number }) {
  const from = Number(event.currentIndex);
  const to = Number(event.targetIndex);
  if (!Number.isInteger(from) || !Number.isInteger(to) || from === to) return;
  const next = [...rows.value];
  const [moved] = next.splice(from, 1);
  if (!moved) return;
  next.splice(to, 0, moved);
  rows.value = next.map((row, index) => ({ ...row, sequence_override: (index + 1) * 10 }));
}
const parentOptions = computed(() =>
  rows.value.map((row) => ({
    value: Number(row.menu_id),
    label: String(row.complete_name || row.custom_label || row.name || row.menu_id),
  })),
);
const versionOptions = computed(() => {
  const values = versions.value.items || versions.value.versions || [];
  return Array.isArray(values)
    ? values.map((row: Dict) => ({
        value: Number(row.version_no || row.version),
        label: `版本 ${row.version_no || row.version}`,
      }))
    : [];
});
function display(value: unknown) {
  return typeof value === 'string' ? value : JSON.stringify(value || {}, null, 2);
}
async function load() {
  loading.value = true;
  error.value = '';
  try {
    const payload = await loadMenuConfigurationPanel();
    const policyMap = payload.policies && typeof payload.policies === 'object' ? (payload.policies as Dict) : {};
    const menus = Array.isArray(payload.menus) ? (payload.menus as Dict[]) : [];
    const groups = Array.isArray(payload.groups) ? (payload.groups as Dict[]) : [];
    const runtime = (payload.runtime || {}) as Dict;
    const states = (runtime.states || {}) as Dict;
    groupOptions.value = groups.map((group) => ({
      value: Number(group.id),
      label: String(group.display_name || group.name || group.id),
    }));
    rows.value = menus.map((menu) => {
      const menuId = Number(menu.menu_id || menu.id);
      const policy = (policyMap[String(menuId)] || {}) as Dict;
      return {
        ...menu,
        ...policy,
        menu_id: menuId,
        policy_id: Number(policy.id || 0) || undefined,
        custom_label: String(policy.custom_label || ''),
        target_parent_menu_id: Number(policy.target_parent_menu_id || menu.parent_id || 0) || undefined,
        sequence_override: Number(policy.sequence_override || menu.sequence || 0),
        visible: policy.visible !== false,
        active: policy.active !== false,
        role_group_ids: Array.isArray(policy.role_group_ids) ? policy.role_group_ids.map(Number) : [],
        runtime_visible: (states[String(menuId)] as Dict | undefined)?.runtime_visible,
      };
    });
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '菜单配置加载失败';
  } finally {
    loading.value = false;
  }
}
async function save() {
  saving.value = true;
  try {
    await saveMenuConfigurationPanel(
      rows.value.map((row) => ({
        policy_id: row.policy_id,
        menu_id: row.menu_id,
        target_parent_menu_id: row.target_parent_menu_id,
        custom_label: row.custom_label,
        sequence_override: row.sequence_override,
        visible: row.visible,
        active: row.active,
        role_group_ids: row.role_group_ids,
        note: row.note,
      })),
    );
    MessagePlugin.success('菜单配置已保存');
    await load();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '菜单配置保存失败');
  } finally {
    saving.value = false;
  }
}
async function create() {
  if (!createForm.value.name.trim()) return;
  busy.value = 'create';
  try {
    await createMenuConfigurationEntry(createForm.value);
    MessagePlugin.success('菜单已创建');
    createDialogVisible.value = false;
    createForm.value = { name: '', parent_menu_id: undefined, sequence: 10, note: '' };
    await load();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '菜单创建失败');
  } finally {
    busy.value = '';
  }
}
function openCopy(row: Dict) {
  copyForm.value = {
    source_menu_id: Number(row.menu_id),
    name: `${row.custom_label || row.name || '菜单'} 副本`,
    parent_menu_id: Number(row.target_parent_menu_id || row.parent_id || 0) || undefined,
    sequence: Number(row.sequence_override || row.sequence || 10) + 1,
  };
  copyDialogVisible.value = true;
}
async function copyMenu() {
  if (!copyForm.value.source_menu_id || !copyForm.value.name.trim()) return;
  busy.value = 'copy';
  try {
    await createMenuConfigurationEntry(copyForm.value);
    MessagePlugin.success('菜单已复制');
    copyDialogVisible.value = false;
    await load();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '菜单复制失败');
  } finally {
    busy.value = '';
  }
}
async function remove(row: Dict) {
  busy.value = `delete:${row.menu_id}`;
  try {
    await deleteMenuConfigurationEntry(Number(row.menu_id));
    MessagePlugin.success('菜单已删除');
    await load();
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '菜单删除失败');
  } finally {
    busy.value = '';
  }
}
async function loadAudit() {
  busy.value = 'audit';
  try {
    [audit.value, versions.value] = await Promise.all([loadMenuConfigurationAudit(), loadMenuConfigurationVersions()]);
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '审计信息加载失败');
  } finally {
    busy.value = '';
  }
}
async function rollback() {
  if (!rollbackVersion.value) return;
  busy.value = 'rollback';
  try {
    await rollbackMenuConfiguration(rollbackVersion.value);
    MessagePlugin.success('菜单版本已回滚');
    await Promise.all([load(), loadAudit()]);
  } catch (cause) {
    MessagePlugin.error(cause instanceof Error ? cause.message : '菜单回滚失败');
  } finally {
    busy.value = '';
  }
}
onMounted(load);
</script>
<style scoped>
.governance-page {
  display: grid;
  gap: 16px;
}
.page-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}
.heading-actions {
  display: flex;
  gap: 8px;
}
.page-heading h1 {
  margin: 4px 0 8px;
  font-size: 28px;
}
.page-heading p {
  margin: 0;
  color: var(--td-text-color-secondary);
}
.eyebrow {
  color: var(--td-brand-color) !important;
  font-size: 13px;
}
.panel {
  border: 1px solid var(--td-border-level-1-color);
}
.result-json {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  color: var(--td-text-color-secondary);
  font:
    12px/1.6 ui-monospace,
    SFMono-Regular,
    Consolas,
    monospace;
}
@media (width<=720px) {
  .page-heading {
    flex-direction: column;
  }
  .heading-actions {
    width: 100%;
  }
  .heading-actions .t-button {
    flex: 1;
  }
}
</style>
