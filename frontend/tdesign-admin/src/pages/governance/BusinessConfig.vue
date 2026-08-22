<template>
  <div class="governance-page">
    <div class="page-heading">
      <div>
        <p class="eyebrow">低代码治理</p>
        <h1>业务配置</h1>
        <p>读取正式业务 contract、覆盖率和配置发布状态。</p>
      </div>
      <t-space size="small">
        <t-button variant="outline" @click="router.push('/governance/form-field-config')">字段配置</t-button>
        <t-button variant="outline" :loading="loading" @click="load">刷新</t-button>
      </t-space>
    </div>
    <t-alert v-if="error" theme="error" :message="error" /><t-card :bordered="false" class="panel"
      ><t-descriptions v-if="summary" :column="3" bordered
        ><t-descriptions-item v-for="(value, key) in summary" :key="String(key)" :label="String(key)">{{
          display(value)
        }}</t-descriptions-item></t-descriptions
      ><t-empty v-else description="暂无业务配置数据" /></t-card
    ><t-card :bordered="false" class="panel"
      ><template #title>配置分区</template><t-table :data="sections" :columns="columns" row-key="key"
    /></t-card>
    <t-card :bordered="false" class="panel">
      <template #title>配置变更集</template>
      <div class="action-bar">
        <t-input v-model="changeSetName" clearable placeholder="变更集名称" />
        <t-button :loading="busy === 'open'" @click="openChangeSet">新建变更集</t-button>
        <t-input v-model="changeSetToken" clearable placeholder="变更集 Token" />
        <t-button
          variant="outline"
          :disabled="!changeSetToken"
          :loading="busy === 'validate'"
          @click="runChangeSet('validate')"
          >校验</t-button
        >
        <t-button
          variant="outline"
          :disabled="!changeSetToken"
          :loading="busy === 'preview'"
          @click="runChangeSet('preview')"
          >预览</t-button
        >
        <t-popconfirm content="确认发布当前变更集？" @confirm="runChangeSet('publish')"
          ><t-button theme="primary" :disabled="!changeSetToken" :loading="busy === 'publish'"
            >发布</t-button
          ></t-popconfirm
        >
        <t-popconfirm content="确认回滚当前变更集？" @confirm="runChangeSet('rollback')"
          ><t-button theme="danger" variant="outline" :disabled="!changeSetToken" :loading="busy === 'rollback'"
            >回滚</t-button
          ></t-popconfirm
        >
        <t-button
          variant="text"
          :disabled="!changeSetToken"
          :loading="busy === 'discard'"
          @click="runChangeSet('discard')"
          >丢弃</t-button
        >
      </div>
      <t-descriptions v-if="Object.keys(changeSetResult).length" :column="3" bordered>
        <t-descriptions-item v-for="(value, key) in changeSetResult" :key="String(key)" :label="String(key)">{{
          display(value)
        }}</t-descriptions-item>
      </t-descriptions>
      <t-table
        v-if="changePreviewRows.length"
        class="result-spacing"
        :data="changePreviewRows"
        :columns="changePreviewColumns"
        row-key="key"
        size="small"
        bordered
      />
      <t-alert v-if="lifecycleVerification" class="result-spacing" theme="success" :message="lifecycleVerification" />
      <t-collapse v-if="changeSetToken" class="stage-editor">
        <t-collapse-panel value="stage" header="添加配置变更项">
          <t-form label-align="top">
            <div class="stage-grid">
              <t-form-item label="配置类型" required>
                <t-select v-model="stageForm.config_type" :options="configTypeOptions" />
              </t-form-item>
              <t-form-item label="目标模型" required><t-input v-model="stageForm.model" /></t-form-item>
              <t-form-item label="视图类型"
                ><t-input v-model="stageForm.view_type" placeholder="form / list / search"
              /></t-form-item>
              <t-form-item label="目标标识" required><t-input v-model="stageForm.target_key" /></t-form-item>
              <t-form-item label="Action ID"
                ><t-input-number v-model="stageForm.action_id" theme="normal"
              /></t-form-item>
              <t-form-item label="View ID"><t-input-number v-model="stageForm.view_id" theme="normal" /></t-form-item>
            </div>
            <t-form-item label="配置 Contract JSON" required>
              <t-textarea v-model="stageForm.draft_payload" :autosize="{ minRows: 8, maxRows: 18 }" />
            </t-form-item>
            <t-form-item label="差异说明 JSON">
              <t-textarea v-model="stageForm.diff_summary" :autosize="{ minRows: 3, maxRows: 8 }" />
            </t-form-item>
            <t-button :loading="busy === 'stage'" @click="stageChangeSetItem">加入变更集</t-button>
          </t-form>
        </t-collapse-panel>
      </t-collapse>
    </t-card>
    <div class="governance-grid">
      <t-card :bordered="false" class="panel">
        <template #title>覆盖率检查</template>
        <div class="section-tools">
          <t-input v-model="coverageModel" clearable placeholder="按模型扫描（可选）" />
          <t-button size="small" variant="outline" :loading="busy === 'coverage'" @click="loadCoverage">扫描</t-button>
          <t-popconfirm content="将从运行态视图生成并发布缺失配置，确认继续？" @confirm="bootstrapCoverage">
            <t-button size="small" theme="warning" :loading="busy === 'bootstrap'">补全缺失配置</t-button>
          </t-popconfirm>
        </div>
        <pre class="result-json">{{ display(coverage) }}</pre>
      </t-card>
      <t-card :bordered="false" class="panel">
        <template #title>配置版本</template>
        <div class="section-tools">
          <t-input v-model="versionModel" clearable placeholder="目标模型（可选）" />
          <t-button size="small" variant="outline" :loading="busy === 'versions'" @click="loadVersions">查询</t-button>
        </div>
        <pre class="result-json">{{ display(versions) }}</pre>
        <t-table
          v-if="publishHistoryRows.length"
          :data="publishHistoryRows"
          :columns="publishHistoryColumns"
          row-key="key"
          size="small"
          bordered
        />
      </t-card>
    </div>
    <t-card :bordered="false" class="panel">
      <template #title>管理员配置审计</template>
      <div class="section-tools">
        <t-input v-model="adminAuditModel" clearable placeholder="业务模型，例如 sc.general.contract" />
        <t-input-number v-model="adminAuditActionId" theme="normal" placeholder="Action ID（可选）" />
        <t-button variant="outline" :loading="busy === 'list-search-audit'" @click="runAdminConfigAudit('list-search')"
          >列表/搜索审计</t-button
        >
        <t-button variant="outline" :loading="busy === 'analysis-audit'" @click="runAdminConfigAudit('analysis')"
          >分析视图审计</t-button
        >
        <t-dropdown
          :options="[
            { content: '生成表单配置', value: 'form' },
            { content: '生成列表/搜索配置', value: 'list-search' },
            { content: '生成分析配置', value: 'analysis' },
          ]"
          @click="(option) => bootstrapAdminConfig(String(option.value))"
        >
          <t-button theme="warning" variant="outline" :loading="busy.startsWith('bootstrap-admin')">引导生成</t-button>
        </t-dropdown>
      </div>
      <t-alert
        v-if="adminAuditResult.source_authority || adminAuditResult.boundary"
        theme="info"
        :message="`数据来源：${display(adminAuditResult.source_authority || adminAuditResult.boundary)}`"
      />
      <pre class="result-json">{{ display(adminAuditResult) }}</pre>
    </t-card>
    <div class="governance-grid">
      <t-card :bordered="false" class="panel">
        <template #title>配置快照比较</template>
        <div class="section-tools">
          <t-button size="small" variant="outline" :loading="busy === 'snapshot-export'" @click="exportSnapshot"
            >导出当前快照</t-button
          >
          <t-button size="small" :loading="busy === 'snapshot-compare'" @click="compareSnapshot"
            >与当前配置比较</t-button
          >
        </div>
        <t-textarea
          v-model="snapshotJson"
          placeholder="粘贴历史快照 JSON，或先导出当前快照"
          :autosize="{ minRows: 7, maxRows: 14 }"
        />
        <pre v-if="Object.keys(snapshotComparison).length" class="result-json result-spacing">{{
          display(snapshotComparison)
        }}</pre>
        <t-table
          v-if="snapshotDiffRows.length"
          :data="snapshotDiffRows"
          :columns="snapshotDiffColumns"
          row-key="path"
          size="small"
          bordered
        />
      </t-card>
      <t-card :bordered="false" class="panel">
        <template #title>审批策略</template>
        <div class="section-tools">
          <t-input v-model="approvalModel" clearable placeholder="业务模型，例如 sc.payment.request" />
          <t-button size="small" variant="outline" :loading="busy === 'approval-load'" @click="loadApproval"
            >读取</t-button
          >
        </div>
        <t-form v-if="approvalLoaded" label-align="top">
          <div class="approval-grid">
            <t-form-item label="启用审批">
              <t-switch v-model="approvalForm.approval_required" />
            </t-form-item>
            <t-form-item label="审批方式">
              <t-select v-model="approvalForm.mode" :options="approvalModeOptions" />
            </t-form-item>
            <t-form-item label="触发时机">
              <t-select v-model="approvalForm.trigger" :options="approvalTriggerOptions" />
            </t-form-item>
            <t-form-item label="负责人范围">
              <t-select v-model="approvalForm.manager_scope_key" :options="approvalScopeOptions" clearable />
            </t-form-item>
          </div>
          <div class="subsection-heading">
            <span>审批步骤</span>
            <t-button size="small" variant="text" @click="addApprovalStep">新增步骤</t-button>
          </div>
          <div v-for="(step, index) in approvalForm.steps" :key="step.client_key" class="approval-step">
            <t-input v-model="step.name" placeholder="步骤名称" />
            <t-select v-model="step.approval_scope_key" :options="approvalScopeOptions" placeholder="审批岗位" />
            <t-input-number v-model="step.amount_min" theme="normal" placeholder="金额下限" />
            <t-input-number v-model="step.amount_max" theme="normal" placeholder="金额上限" />
            <t-input v-model="step.condition_note" placeholder="条件说明" />
            <t-button theme="danger" variant="text" @click="approvalForm.steps.splice(index, 1)">删除</t-button>
          </div>
          <t-space>
            <t-button :loading="busy === 'approval-save'" @click="saveApproval">保存策略</t-button>
            <t-button
              variant="outline"
              :disabled="!approvalForm.approval_required"
              :loading="busy === 'approval-steps'"
              @click="saveApprovalSteps"
              >保存步骤</t-button
            >
          </t-space>
        </t-form>
        <t-empty v-else description="请输入业务模型并读取审批配置" />
      </t-card>
    </div>
  </div>
</template>
<script setup lang="ts">
import { MessagePlugin } from 'tdesign-vue-next';
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import {
  auditBusinessAnalysisConfig,
  auditBusinessListSearchConfig,
  bootstrapBusinessAnalysisConfig,
  bootstrapBusinessConfigCoverage,
  bootstrapBusinessFormConfig,
  bootstrapBusinessListSearchConfig,
  compareBusinessConfigSnapshot,
  discardBusinessConfigChangeSet,
  exportBusinessConfigSnapshot,
  loadBusinessConfigApproval,
  loadBusinessConfigContractVersions,
  loadBusinessConfigSurface,
  openBusinessConfigChangeSet,
  previewBusinessConfigChangeSet,
  publishBusinessConfigChangeSet,
  rollbackBusinessConfigChangeSet,
  saveBusinessConfigApproval,
  saveBusinessConfigApprovalSteps,
  scanBusinessConfigCoverage,
  stageBusinessConfigChangeSetItem,
  validateBusinessConfigChangeSet,
} from '@/api/odoo';

type Dict = Record<string, any>;
const router = useRouter();
const loading = ref(false);
const error = ref('');
const payload = ref<Dict>({});
const busy = ref('');
const changeSetName = ref('');
const changeSetToken = ref('');
const changeSetResult = ref<Dict>({});
const lifecycleVerification = ref('');
const changePreviewColumns = [
  { colKey: 'target', title: '目标', minWidth: 220 },
  { colKey: 'operation', title: '操作', width: 100 },
  { colKey: 'summary', title: '影响摘要', ellipsis: true, minWidth: 260 },
  { colKey: 'status', title: '状态', width: 110 },
];
const publishHistoryColumns = [
  { colKey: 'version', title: '版本', width: 100 },
  { colKey: 'status', title: '状态', width: 100 },
  { colKey: 'actor', title: '操作人', width: 140 },
  { colKey: 'date', title: '时间', width: 180 },
  { colKey: 'summary', title: '说明', ellipsis: true, minWidth: 220 },
];
const coverage = ref<Dict>({});
const versions = ref<Dict>({});
const coverageModel = ref('');
const versionModel = ref('');
const adminAuditModel = ref('');
const adminAuditActionId = ref<number>();
const adminAuditResult = ref<Dict>({});
const snapshotJson = ref('');
const snapshotComparison = ref<Dict>({});
const snapshotDiffColumns = [
  { colKey: 'path', title: '配置路径', minWidth: 280 },
  { colKey: 'before', title: '历史值', ellipsis: true, minWidth: 220 },
  { colKey: 'after', title: '当前值', ellipsis: true, minWidth: 220 },
  { colKey: 'kind', title: '变化', width: 100 },
];
const approvalModel = ref('');
const approvalLoaded = ref(false);
const approvalModeOptions = ref<Array<{ value: string; label: string }>>([]);
const approvalTriggerOptions = ref<Array<{ value: string; label: string }>>([]);
const approvalScopeOptions = ref<Array<{ value: string; label: string }>>([]);
const approvalForm = ref({
  approval_required: false,
  mode: 'none',
  trigger: 'submit',
  manager_scope_key: '',
  steps: [] as Array<Dict>,
});
const changePreviewRows = computed(() => {
  const raw = changeSetResult.value.impacts || changeSetResult.value.preview || changeSetResult.value.items || [];
  return (Array.isArray(raw) ? raw : []).map((item: Dict, index) => ({
    key: String(item.id || item.key || index),
    target: String(item.target_key || item.target || item.model || '配置项'),
    operation: String(item.operation || item.action || item.kind || '修改'),
    summary: display(item.summary || item.diff || item.message || ''),
    status: String(item.status || item.state || '待处理'),
  }));
});
const publishHistoryRows = computed(() => {
  const raw =
    versions.value.items || versions.value.versions || payload.value.publish_history || payload.value.history || [];
  return (Array.isArray(raw) ? raw : []).map((item: Dict, index) => ({
    key: String(item.id || item.version_no || item.version || index),
    version: String(item.version_no || item.version || '—'),
    status: String(item.status || item.state || '—'),
    actor: String(item.actor_name || item.user_name || item.actor || '—'),
    date: String(item.published_at || item.created_at || item.date || '—'),
    summary: String(item.summary || item.reason || item.note || ''),
  }));
});
const snapshotDiffRows = computed(() => {
  const source = snapshotComparison.value;
  const raw = source.diff || source.changes || source.items || [];
  if (Array.isArray(raw)) {
    return raw.map((item: Dict, index) => ({
      path: String(item.path || item.key || item.field || `change.${index + 1}`),
      before: display(item.before ?? item.old ?? item.previous),
      after: display(item.after ?? item.new ?? item.current),
      kind: String(item.kind || item.change || '修改'),
    }));
  }
  return Object.entries(source).flatMap(([key, value]) => {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return [];
    const row = value as Dict;
    if (!('before' in row) && !('after' in row) && !('old' in row) && !('new' in row)) return [];
    return [
      {
        path: key,
        before: display(row.before ?? row.old),
        after: display(row.after ?? row.new),
        kind: String(row.kind || '修改'),
      },
    ];
  });
});
const configTypeOptions = ['form', 'list', 'search', 'analysis', 'menu'].map((value) => ({ value, label: value }));
const stageForm = ref({
  config_type: 'form',
  model: '',
  view_type: 'form',
  target_key: '',
  action_id: undefined as number | undefined,
  view_id: undefined as number | undefined,
  draft_payload: '{\n  \n}',
  diff_summary: '{\n  "summary": ""\n}',
});
const summary = computed(() => payload.value.snapshot_summary || payload.value.delivery_readiness || null);
const sections = computed(() => (Array.isArray(payload.value.sections) ? payload.value.sections : []));
const columns = [
  { colKey: 'label', title: '分区' },
  { colKey: 'contract_count', title: '契约数', width: 120 },
  { colKey: 'boundary', title: '边界' },
];
function display(value: any) {
  return typeof value === 'object' ? JSON.stringify(value) : String(value ?? '—');
}
async function load() {
  loading.value = true;
  error.value = '';
  try {
    payload.value = await loadBusinessConfigSurface();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '业务配置加载失败';
  } finally {
    loading.value = false;
  }
}
async function openChangeSet() {
  busy.value = 'open';
  try {
    const result = await openBusinessConfigChangeSet(changeSetName.value.trim());
    changeSetResult.value = result;
    changeSetToken.value = String(result.change_set_token || result.token || '');
    MessagePlugin.success('变更集已创建');
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '变更集创建失败';
  } finally {
    busy.value = '';
  }
}
async function runChangeSet(action: 'validate' | 'preview' | 'publish' | 'rollback' | 'discard') {
  if (!changeSetToken.value) return;
  busy.value = action;
  lifecycleVerification.value = '';
  try {
    const calls = {
      validate: validateBusinessConfigChangeSet,
      preview: previewBusinessConfigChangeSet,
      publish: publishBusinessConfigChangeSet,
      rollback: rollbackBusinessConfigChangeSet,
      discard: discardBusinessConfigChangeSet,
    };
    changeSetResult.value = await calls[action](changeSetToken.value);
    MessagePlugin.success(
      `变更集${{ validate: '校验', preview: '预览', publish: '发布', rollback: '回滚', discard: '丢弃' }[action]}完成`,
    );
    await load();
    if (action === 'publish' || action === 'rollback') {
      await Promise.all([loadCoverage(), loadVersions()]);
      const coverageState = String(coverage.value.status || coverage.value.state || '已刷新');
      const versionCount = Array.isArray(versions.value.items || versions.value.versions)
        ? (versions.value.items || versions.value.versions).length
        : 0;
      lifecycleVerification.value = `${action === 'publish' ? '发布' : '回滚'}后复验完成：覆盖率 ${coverageState}，版本记录 ${versionCount} 条。`;
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '变更集操作失败';
  } finally {
    busy.value = '';
  }
}
async function stageChangeSetItem() {
  if (!changeSetToken.value || !stageForm.value.model.trim() || !stageForm.value.target_key.trim()) {
    MessagePlugin.warning('请填写目标模型和目标标识');
    return;
  }
  busy.value = 'stage';
  try {
    const draftPayload = JSON.parse(stageForm.value.draft_payload || '{}') as Dict;
    const diffSummary = JSON.parse(stageForm.value.diff_summary || '{}') as Dict;
    changeSetResult.value = await stageBusinessConfigChangeSetItem({
      change_set_token: changeSetToken.value,
      config_type: stageForm.value.config_type,
      target_key: stageForm.value.target_key.trim(),
      model: stageForm.value.model.trim(),
      view_type: stageForm.value.view_type.trim() || undefined,
      action_id: stageForm.value.action_id,
      view_id: stageForm.value.view_id,
      draft_payload: draftPayload,
      diff_summary: diffSummary,
    });
    MessagePlugin.success('配置变更项已加入变更集');
  } catch (cause) {
    error.value =
      cause instanceof SyntaxError ? '配置 JSON 格式不正确' : cause instanceof Error ? cause.message : '变更项添加失败';
  } finally {
    busy.value = '';
  }
}
async function loadCoverage() {
  busy.value = 'coverage';
  try {
    coverage.value = await scanBusinessConfigCoverage(coverageModel.value.trim());
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '覆盖率扫描失败';
  } finally {
    busy.value = '';
  }
}
async function loadVersions() {
  busy.value = 'versions';
  try {
    versions.value = await loadBusinessConfigContractVersions(versionModel.value.trim());
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '版本查询失败';
  } finally {
    busy.value = '';
  }
}
async function bootstrapCoverage() {
  busy.value = 'bootstrap';
  try {
    coverage.value = await bootstrapBusinessConfigCoverage({
      model: coverageModel.value.trim() || undefined,
      batch_limit: 100,
    });
    MessagePlugin.success('缺失配置补全已执行');
    await Promise.all([load(), loadCoverage()]);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '缺失配置补全失败';
  } finally {
    busy.value = '';
  }
}
async function runAdminConfigAudit(kind: 'list-search' | 'analysis') {
  if (!adminAuditModel.value.trim()) {
    MessagePlugin.warning('请填写业务模型');
    return;
  }
  busy.value = kind === 'analysis' ? 'analysis-audit' : 'list-search-audit';
  try {
    const params = { model: adminAuditModel.value.trim(), action_id: adminAuditActionId.value || undefined };
    adminAuditResult.value =
      kind === 'analysis' ? await auditBusinessAnalysisConfig(params) : await auditBusinessListSearchConfig(params);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '配置审计失败';
  } finally {
    busy.value = '';
  }
}
async function bootstrapAdminConfig(kind: string) {
  if (!adminAuditModel.value.trim()) {
    MessagePlugin.warning('请填写业务模型');
    return;
  }
  busy.value = `bootstrap-admin-${kind}`;
  try {
    const params = {
      model: adminAuditModel.value.trim(),
      action_id: adminAuditActionId.value || undefined,
      publish: true,
    };
    adminAuditResult.value =
      kind === 'form'
        ? await bootstrapBusinessFormConfig(params)
        : kind === 'analysis'
          ? await bootstrapBusinessAnalysisConfig(params)
          : await bootstrapBusinessListSearchConfig(params);
    MessagePlugin.success('配置引导生成完成');
    await Promise.all([load(), loadCoverage(), loadVersions()]);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '配置引导生成失败';
  } finally {
    busy.value = '';
  }
}
async function exportSnapshot() {
  busy.value = 'snapshot-export';
  try {
    const result = await exportBusinessConfigSnapshot();
    snapshotJson.value = JSON.stringify(result, null, 2);
    snapshotComparison.value = {};
    MessagePlugin.success('当前配置快照已载入');
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '快照导出失败';
  } finally {
    busy.value = '';
  }
}
async function compareSnapshot() {
  busy.value = 'snapshot-compare';
  try {
    const snapshot = JSON.parse(snapshotJson.value || '{}') as Dict;
    snapshotComparison.value = await compareBusinessConfigSnapshot(snapshot);
  } catch (cause) {
    error.value =
      cause instanceof SyntaxError ? '快照 JSON 格式不正确' : cause instanceof Error ? cause.message : '快照比较失败';
  } finally {
    busy.value = '';
  }
}
function optionRows(value: unknown) {
  return Array.isArray(value)
    ? value.map((item: Dict) => ({ value: String(item.value || ''), label: String(item.label || item.value || '') }))
    : [];
}
function normalizeApprovalStep(step: Dict, index: number) {
  return {
    ...step,
    client_key: `${step.id || 'new'}:${index}:${Date.now()}`,
    amount_min: step.amount_min === false ? undefined : step.amount_min,
    amount_max: step.amount_max === false ? undefined : step.amount_max,
  };
}
async function loadApproval() {
  if (!approvalModel.value.trim()) {
    MessagePlugin.warning('请填写业务模型');
    return;
  }
  busy.value = 'approval-load';
  try {
    const result = await loadBusinessConfigApproval(approvalModel.value.trim());
    const policy = (result.policy || {}) as Dict;
    approvalModeOptions.value = optionRows(result.mode_options);
    approvalTriggerOptions.value = optionRows(result.trigger_options);
    approvalScopeOptions.value = optionRows(result.scope_options);
    approvalForm.value = {
      approval_required: Boolean(policy.approval_required),
      mode: String(policy.mode || 'none'),
      trigger: String(policy.trigger || 'submit'),
      manager_scope_key: String(policy.manager_scope_key || ''),
      steps: Array.isArray(policy.steps) ? policy.steps.map(normalizeApprovalStep) : [],
    };
    approvalLoaded.value = true;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '审批策略读取失败';
  } finally {
    busy.value = '';
  }
}
function addApprovalStep() {
  approvalForm.value.steps.push(
    normalizeApprovalStep(
      {
        name: '',
        approval_scope_key: '',
        amount_min: undefined,
        amount_max: undefined,
        condition_note: '',
        active: true,
      },
      approvalForm.value.steps.length,
    ),
  );
}
async function saveApproval() {
  busy.value = 'approval-save';
  try {
    await saveBusinessConfigApproval({
      model: approvalModel.value.trim(),
      approval_required: approvalForm.value.approval_required,
      mode: approvalForm.value.mode,
      trigger: approvalForm.value.trigger,
      manager_scope_key: approvalForm.value.manager_scope_key || undefined,
    });
    MessagePlugin.success('审批策略已保存');
    await loadApproval();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '审批策略保存失败';
  } finally {
    busy.value = '';
  }
}
async function saveApprovalSteps() {
  busy.value = 'approval-steps';
  try {
    await saveBusinessConfigApprovalSteps({
      model: approvalModel.value.trim(),
      steps: approvalForm.value.steps.map((step, index) => ({
        id: step.id || undefined,
        name: String(step.name || '').trim(),
        approval_scope_key: step.approval_scope_key,
        sequence: (index + 1) * 10,
        amount_min: step.amount_min,
        amount_max: step.amount_max,
        condition_note: String(step.condition_note || '').trim(),
        note: String(step.note || '').trim(),
        active: step.active !== false,
      })),
    });
    MessagePlugin.success('审批步骤已保存');
    await loadApproval();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '审批步骤保存失败';
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
.action-bar {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) auto minmax(220px, 1.4fr) repeat(6, auto);
  gap: 8px;
  margin-bottom: 16px;
}
.governance-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.section-tools {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.section-tools :deep(.t-input__wrap) {
  min-width: 0;
  flex: 1;
}
.result-spacing {
  margin-top: 12px;
}
.approval-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 12px;
}
.subsection-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 4px 0 8px;
  font-weight: 600;
}
.approval-step {
  display: grid;
  grid-template-columns: 1fr 1fr 120px 120px 1.2fr auto;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.stage-editor {
  margin-top: 16px;
}
.stage-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0 12px;
}
.result-json {
  max-height: 320px;
  margin: 0;
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  color: var(--td-text-color-secondary);
  font:
    12px/1.6 ui-monospace,
    SFMono-Regular,
    Consolas,
    monospace;
}
@media (width <= 1000px) {
  .action-bar,
  .governance-grid,
  .stage-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .approval-grid,
  .approval-step {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
