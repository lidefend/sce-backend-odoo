<template>
  <main class="release-page">
    <header class="page-heading">
      <div>
        <p class="eyebrow">产品治理</p>
        <h1>{{ copy.title || '发布控制台' }}</h1>
        <p>{{ copy.description || '查看发布状态、候选快照、待审批动作与回滚目标。' }}</p>
      </div>
      <t-space>
        <t-select v-model="productKey" :options="productOptions" style="width: 230px" @change="load" />
        <t-button variant="outline" :loading="loading" @click="load"
          ><template #icon><t-icon name="refresh" /></template>刷新</t-button
        >
        <t-button
          variant="outline"
          :disabled="!action('sync_policy').enabled"
          :loading="busy === 'sync'"
          @click="run('release.operator.sync_policy', action('sync_policy').params, 'sync')"
          >同步能力</t-button
        >
        <t-button
          theme="primary"
          :disabled="!action('freeze').enabled"
          :loading="busy === 'freeze'"
          @click="run('release.operator.freeze', action('freeze').params, 'freeze')"
          >冻结候选</t-button
        >
      </t-space>
    </header>

    <t-alert v-if="error" theme="error" :message="error" close @close="error = ''" />
    <t-loading :loading="loading && !surface" size="small">
      <template v-if="surface">
        <section class="metric-grid">
          <t-card v-for="metric in metrics" :key="metric.label" bordered class="metric-card"
            ><span>{{ metric.label }}</span
            ><strong>{{ metric.value }}</strong></t-card
          >
        </section>

        <section class="panel">
          <div class="section-title">
            <div>
              <h2>产品配置发布线</h2>
              <p>草案、检查、候选、发布、生效</p>
            </div>
          </div>
          <div class="pipeline">
            <div v-for="stage in pipelineStages" :key="itemKey(stage)" class="pipeline__stage">
              <t-tag :theme="stageTheme(stage.status)" variant="light">{{ stage.label || stage.key || '阶段' }}</t-tag
              ><strong>{{ stage.count ?? 0 }}</strong>
            </div>
          </div>
          <div class="checks">
            <t-alert
              v-for="check in preflightChecks"
              :key="itemKey(check)"
              :theme="checkTheme(check.status)"
              :message="String(check.label || check.key || '检查')"
              :description="String(check.message || '')"
            />
          </div>
        </section>

        <section class="panel">
          <div class="section-title">
            <div>
              <h2>受控页面</h2>
              <p>按产品发布阶段与访问范围管理页面。</p>
            </div>
            <t-space
              ><t-select v-model="policyState" :options="policyStates" style="width: 120px" /><t-select
                v-model="policyAccess"
                :options="policyAccesses"
                style="width: 130px"
              /><t-button :disabled="!action('update_policy').enabled" :loading="busy === 'policy'" @click="savePolicy"
                >保存策略</t-button
              ></t-space
            >
          </div>
          <t-table :data="controlledPages" :columns="pageColumns" row-key="page_key" size="small">
            <template #release_state="{ row }"
              ><t-tag
                :theme="stageTheme(row.release_state || (row.enabled === false ? 'hidden' : 'released'))"
                variant="light"
                >{{ releaseLabel(row) }}</t-tag
              ></template
            >
            <template #operations="{ row }"
              ><t-space size="small"
                ><t-button
                  size="small"
                  variant="text"
                  theme="primary"
                  :loading="busy === `page:${itemKey(row)}:released`"
                  @click="updatePage(row, { release_state: 'released', enabled: true })"
                  >发布</t-button
                ><t-button
                  size="small"
                  variant="text"
                  theme="warning"
                  :loading="busy === `page:${itemKey(row)}:preview`"
                  @click="updatePage(row, { release_state: 'preview', enabled: true })"
                  >预览</t-button
                ><t-button
                  size="small"
                  variant="text"
                  theme="danger"
                  :loading="busy === `page:${itemKey(row)}:hidden`"
                  @click="updatePage(row, { release_state: 'hidden', enabled: false })"
                  >下线</t-button
                ></t-space
              ></template
            >
          </t-table>
        </section>

        <section class="two-columns">
          <section class="panel">
            <div class="section-title">
              <div>
                <h2>可发布候选</h2>
                <p>只显示后端给出的候选快照。</p>
              </div>
            </div>
            <t-table :data="candidateSnapshots" :columns="snapshotColumns" row-key="id" size="small"
              ><template #operations="{ row }"
                ><t-button
                  size="small"
                  theme="primary"
                  :disabled="!candidateReady(row)"
                  :loading="busy === `promote:${row.id}`"
                  @click="promote(row)"
                  >发布</t-button
                ></template
              ></t-table
            >
          </section>
          <section class="panel">
            <div class="section-title">
              <div>
                <h2>待审批动作</h2>
                <p>由后端权限决定是否可审批。</p>
              </div>
            </div>
            <t-table :data="pendingActions" :columns="approvalColumns" row-key="id" size="small"
              ><template #operations="{ row }"
                ><t-button
                  size="small"
                  theme="primary"
                  :disabled="row.can_approve === false"
                  :loading="busy === `approve:${row.id}`"
                  @click="approve(row)"
                  >审批并执行</t-button
                ></template
              ></t-table
            >
          </section>
        </section>

        <section class="panel rollback">
          <div>
            <h2>回滚</h2>
            <p>{{ copy.hint_rollback || '仅当后端提供回滚目标并且当前账号具有权限时可执行。' }}</p>
          </div>
          <t-popconfirm
            content="确认执行发布回滚？"
            @confirm="run('release.operator.rollback', action('rollback').params, 'rollback')"
            ><t-button
              theme="danger"
              variant="outline"
              :disabled="!action('rollback').enabled"
              :loading="busy === 'rollback'"
              >执行回滚</t-button
            ></t-popconfirm
          >
        </section>
        <section class="two-columns">
          <section class="panel">
            <div class="section-title">
              <div>
                <h2>受控菜单</h2>
                <p>当前产品发布策略覆盖的菜单入口。</p>
              </div>
            </div>
            <t-table :data="controlledMenus" :columns="scopeColumns" row-key="key" size="small" />
          </section>
          <section class="panel">
            <div class="section-title">
              <div>
                <h2>受控能力</h2>
                <p>当前产品发布策略覆盖的能力。</p>
              </div>
            </div>
            <t-table :data="controlledCapabilities" :columns="scopeColumns" row-key="key" size="small" />
          </section>
        </section>
        <section class="two-columns">
          <section class="panel">
            <div class="section-title">
              <div>
                <h2>历史快照</h2>
                <p>后端返回的最近发布快照。</p>
              </div>
            </div>
            <t-table :data="historySnapshots" :columns="snapshotColumns" row-key="id" size="small" />
          </section>
          <section class="panel">
            <div class="section-title">
              <div>
                <h2>历史动作</h2>
                <p>发布、审批和回滚动作记录。</p>
              </div>
            </div>
            <t-table :data="historyActions" :columns="historyActionColumns" row-key="id" size="small" />
          </section>
        </section>
      </template>
      <t-empty v-else-if="!loading" description="暂无发布控制台数据" />
    </t-loading>
  </main>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import type { ReleaseOperatorSurface } from '@/api/odoo';
import { executeReleaseOperatorAction, fetchReleaseOperatorSurface } from '@/api/odoo';

type Row = Record<string, any>;
const loading = ref(false);
const error = ref('');
const busy = ref('');
const surface = ref<ReleaseOperatorSurface | null>(null);
const productKey = ref('');
const policyState = ref('stable');
const policyAccess = ref('public');
const policyStates = ['draft', 'preview', 'stable', 'archived'].map((value) => ({ value, label: value }));
const policyAccesses = ['public', 'internal', 'role_restricted'].map((value) => ({ value, label: value }));
const copy = computed<Row>(() => surface.value?.copy || {});
const productOptions = computed(() =>
  (surface.value?.products || []).map((item) => ({ value: item.product_key, label: item.label || item.product_key })),
);
const releaseState = computed<Row>(() => surface.value?.release_state || {});
const pipeline = computed<Row>(() => surface.value?.release_pipeline || {});
const scope = computed<Row>(() => surface.value?.control_scope || {});
const pipelineStages = computed<Row[]>(() => (Array.isArray(pipeline.value.stages) ? pipeline.value.stages : []));
const preflightChecks = computed<Row[]>(() =>
  Array.isArray(pipeline.value.preflight_checks) ? pipeline.value.preflight_checks : [],
);
const controlledPages = computed<Row[]>(() => (Array.isArray(scope.value.pages) ? scope.value.pages : []));
const controlledMenus = computed<Row[]>(() => (Array.isArray(scope.value.menus) ? scope.value.menus : []));
const controlledCapabilities = computed<Row[]>(() =>
  Array.isArray(scope.value.capabilities) ? scope.value.capabilities : [],
);
const candidateSnapshots = computed<Row[]>(() =>
  Array.isArray(surface.value?.candidate_snapshots) ? surface.value!.candidate_snapshots! : [],
);
const pendingActions = computed<Row[]>(() =>
  Array.isArray(surface.value?.pending_approval?.actions) ? surface.value!.pending_approval!.actions! : [],
);
const historySnapshots = computed<Row[]>(() =>
  Array.isArray(surface.value?.release_history?.snapshots) ? surface.value!.release_history!.snapshots! : [],
);
const historyActions = computed<Row[]>(() =>
  Array.isArray(surface.value?.release_history?.actions) ? surface.value!.release_history!.actions! : [],
);
const metrics = computed(() => [
  { label: '当前产品', value: String(surface.value?.identity?.product_key || '—') },
  {
    label: '生效快照',
    value: String(releaseState.value.active_snapshot?.version || releaseState.value.active_snapshot?.id || '—'),
  },
  { label: '最近动作', value: String(releaseState.value.runtime_summary?.latest_action_type || '—') },
  { label: '审批状态', value: String(releaseState.value.runtime_summary?.latest_action_approval_state || '—') },
]);
const pageColumns = [
  { colKey: 'page_label', title: '页面', minWidth: 150 },
  { colKey: 'route', title: '路由', minWidth: 180 },
  { colKey: 'release_state', title: '发布阶段', minWidth: 100 },
  { colKey: 'access_level', title: '访问范围', minWidth: 100 },
  { colKey: 'operations', title: '操作', width: 180 },
];
const snapshotColumns = [
  { colKey: 'version', title: '版本', minWidth: 100 },
  { colKey: 'state', title: '状态', minWidth: 90 },
  { colKey: 'channel', title: '通道', minWidth: 90 },
  { colKey: 'frozen_at', title: '冻结时间', minWidth: 150 },
  { colKey: 'operations', title: '操作', width: 80 },
];
const approvalColumns = [
  { colKey: 'action_type', title: '动作', minWidth: 120 },
  { colKey: 'product_key', title: '产品', minWidth: 110 },
  { colKey: 'approval_state', title: '审批', minWidth: 100 },
  { colKey: 'requested_at', title: '请求时间', minWidth: 150 },
  { colKey: 'operations', title: '操作', width: 110 },
];
const scopeColumns = [
  { colKey: 'label', title: '名称', minWidth: 150 },
  { colKey: 'key', title: '标识', minWidth: 180 },
  { colKey: 'release_state', title: '状态', width: 100 },
];
const historyActionColumns = [
  { colKey: 'action_type', title: '动作', minWidth: 120 },
  { colKey: 'state', title: '状态', width: 90 },
  { colKey: 'approval_state', title: '审批', width: 90 },
  { colKey: 'requested_at', title: '时间', minWidth: 150 },
];

function action(key: string) {
  return surface.value?.available_actions?.[key] || {};
}
function itemKey(row: Row) {
  return String(row.page_key || row.key || row.id || row.label || 'item');
}
function stageTheme(value: unknown) {
  const state = String(value || '').toLowerCase();
  return state.includes('fail') || state.includes('block') || state.includes('hidden')
    ? 'danger'
    : state.includes('warn') || state.includes('preview')
      ? 'warning'
      : state.includes('pending') || state.includes('draft')
        ? 'default'
        : 'success';
}
function checkTheme(value: unknown) {
  return stageTheme(value) === 'danger' ? 'error' : stageTheme(value) === 'warning' ? 'warning' : 'success';
}
function releaseLabel(row: Row) {
  const state = String(row.release_state || (row.enabled === false ? 'hidden' : 'released'));
  return ({ released: '已发布', preview: '预览', hidden: '已下线', retired: '已下线' } as Row)[state] || state;
}
function candidateReady(row: Row) {
  const draft = row.release_draft || {};
  return Boolean(draft.fingerprint) && Number(draft.blocking_issue_count || 0) === 0;
}

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const result = await fetchReleaseOperatorSurface(productKey.value);
    surface.value = result;
    const resolved = String(result.identity?.product_key || '');
    if (resolved) productKey.value = resolved;
    policyState.value = String(result.control_scope?.policy_state || 'stable');
    policyAccess.value = String(result.control_scope?.access_level || 'public');
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '发布控制台加载失败';
  } finally {
    loading.value = false;
  }
}
async function run(
  name: Parameters<typeof executeReleaseOperatorAction>[0],
  params: Record<string, unknown> = {},
  key: string,
) {
  busy.value = key;
  try {
    const result = await executeReleaseOperatorAction(name, { ...params, product_key: productKey.value });
    if (result.surface) {
      surface.value = result.surface;
    } else {
      await load();
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '发布操作失败';
  } finally {
    busy.value = '';
  }
}
function promote(row: Row) {
  void run('release.operator.promote', { snapshot_id: row.id, replace_active: true }, `promote:${row.id}`);
}
function approve(row: Row) {
  void run('release.operator.approve', { action_id: row.id }, `approve:${row.id}`);
}
function updatePage(row: Row, updates: Row) {
  const key = itemKey(row);
  void run(
    'release.operator.update_page_policy',
    { ...action('update_page_policy').params, page_key: key, ...updates },
    `page:${key}:${updates.release_state}`,
  );
}
function savePolicy() {
  void run(
    'release.operator.update_policy',
    { ...action('update_policy').params, state: policyState.value, access_level: policyAccess.value },
    'policy',
  );
}
onMounted(load);
</script>
<style scoped>
.release-page {
  display: grid;
  gap: 18px;
}
.page-heading,
.section-title,
.rollback {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.page-heading h1,
.section-title h2,
.rollback h2 {
  margin: 4px 0 8px;
}
.page-heading h1 {
  font-size: 28px;
}
.page-heading p,
.section-title p,
.rollback p {
  margin: 0;
  color: var(--td-text-color-secondary);
}
.eyebrow {
  color: var(--td-brand-color) !important;
  font-size: 13px;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.metric-card span {
  display: block;
  color: var(--td-text-color-secondary);
  font-size: 12px;
}
.metric-card strong {
  display: block;
  margin-top: 8px;
  font-size: 20px;
  overflow-wrap: anywhere;
}
.panel {
  padding: 20px;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 8px;
  background: var(--td-bg-color-container);
}
.pipeline {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
  margin: 16px 0;
}
.pipeline__stage {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--td-border-level-1-color);
  border-radius: 6px;
}
.pipeline__stage strong {
  font-size: 22px;
}
.checks {
  display: grid;
  gap: 8px;
}
.two-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}
.rollback {
  align-items: center;
}
@media (max-width: 900px) {
  .page-heading,
  .section-title,
  .rollback {
    flex-direction: column;
  }
  .metric-grid,
  .two-columns {
    grid-template-columns: 1fr;
  }
}
</style>
