<template>
  <main v-if="pageSectionsReady" class="release-operator" :style="pageSectionStyle('root')" :data-contract-sections="pageSectionsFingerprint">
    <section class="release-operator__header">
      <div>
        <p class="eyebrow">{{ copy.eyebrow || 'Release Operator Surface' }}</p>
        <h1>{{ copy.title || '发布控制台' }}</h1>
        <p>{{ copy.description || '查看当前发布状态、候选快照、待审批动作与回滚目标。' }}</p>
      </div>
      <div class="release-operator__actions">
        <ScSelect v-model="selectedProduct" class="release-operator__select" :options="productOptions" @change="loadSurface" />
        <ScButton variant="ghost" :disabled="loading" @click="loadSurface">{{ copy.action_refresh || '刷新' }}</ScButton>
        <ScButton
          v-for="action in pageGlobalActions"
          :key="action.key"
          variant="ghost"
          :disabled="action.disabled"
          @click="executeGlobalPageAction(action.key)"
        >
          {{ action.label }}
        </ScButton>
        <ScButton
          variant="ghost"
          :disabled="busyKey === 'sync_policy' || !syncPolicyAction.enabled"
          @click="syncPolicy"
        >
          {{ copy.sync_policy_action_label || '同步已实现能力' }}
        </ScButton>
        <ScButton
          variant="primary"
          :disabled="busyKey === 'freeze' || !freezeAction.enabled"
          @click="freeze"
        >
          {{ copy.freeze_action_label || '冻结候选快照' }}
        </ScButton>
      </div>
    </section>

    <StatusPanel
      v-if="loading && !surface"
      title="正在加载发布控制台..."
      variant="info"
    />
    <StatusPanel
      v-else-if="error"
      :title="copy.error_title || '加载失败'"
      :message="error"
      variant="error"
      :on-retry="loadSurface"
    />

    <template v-else-if="surface">
      <section class="release-operator__metrics">
        <article class="release-operator__metric">
          <span>{{ copy.metric_current_product || '当前产品' }}</span>
          <strong>{{ identity.product_key || '-' }}</strong>
        </article>
        <article class="release-operator__metric">
          <span>{{ copy.metric_active_snapshot || 'Active Released Snapshot' }}</span>
          <strong>{{ activeSnapshot.version || activeSnapshot.id || '-' }}</strong>
        </article>
        <article class="release-operator__metric">
          <span>{{ copy.metric_latest_action || 'Latest Action' }}</span>
          <strong>{{ runtimeSummary.latest_action_type || '-' }}</strong>
        </article>
        <article class="release-operator__metric">
          <span>{{ copy.metric_approval_state || 'Approval State' }}</span>
          <strong>{{ runtimeSummary.latest_action_approval_state || '-' }}</strong>
        </article>
      </section>

      <section class="release-operator__section">
        <div class="release-operator__section-head">
          <h2>{{ copy.section_product_delivery_console || '产品交付控制台' }}</h2>
          <p>{{ productProfile.label || productConsole.product_key || '-' }}</p>
        </div>
        <div class="release-operator__product-grid">
          <article>
            <span>产品包</span>
            <strong>{{ productBundle.name || '-' }}</strong>
            <small>{{ productBundle.default_dashboard || '-' }}</small>
          </article>
          <article>
            <span>授权层级</span>
            <strong>{{ productLicense.level || '-' }}</strong>
                  <small>{{ productLicense.customer_visible === false ? '平台可见' : '交付可见' }}</small>
          </article>
          <article>
            <span>交付就绪</span>
            <strong>{{ readinessLabel(productReadiness.status) }}</strong>
            <small>阻断 {{ productReadiness.blocking_count ?? 0 }} / 警告 {{ productReadiness.warn_count ?? 0 }}</small>
          </article>
          <article>
            <span>受控页面</span>
            <strong>{{ productReadiness.controlled_page_count ?? 0 }}</strong>
            <small>已发布 {{ productReadiness.released_page_count ?? 0 }}</small>
          </article>
        </div>
        <div class="release-operator__delivery-lists">
          <article>
            <h3>能力包</h3>
            <div class="release-operator__tag-list">
              <span v-for="capability in productCapabilities" :key="productItemKey(capability)">
                {{ capability.label || capability.key || '-' }}
              </span>
            </div>
          </article>
          <article>
            <h3>场景包</h3>
            <div class="release-operator__tag-list">
              <span v-for="scene in productScenes" :key="productItemKey(scene)">
                {{ scene.name || scene.code || '-' }}
              </span>
            </div>
          </article>
          <article>
            <h3>交付资产</h3>
            <div class="release-operator__asset-list">
              <span v-for="asset in acceptanceAssets" :key="asset">{{ asset }}</span>
            </div>
          </article>
        </div>
        <p v-if="productLicense.upgrade_hint" class="release-operator__upgrade-hint">
          {{ productLicense.upgrade_hint }}
        </p>
      </section>

      <section class="release-operator__section">
        <div class="release-operator__section-head">
          <h2>产品配置发布线</h2>
          <p>草案、检查、候选、发布、生效</p>
        </div>
        <div class="release-operator__pipeline">
          <article v-for="stage in pipelineStages" :key="pipelineKey(stage)">
            <span :class="['release-operator__stage-dot', `release-operator__stage-dot--${stage.status || 'pending'}`]"></span>
            <strong>{{ stage.label || stage.key || '-' }}</strong>
            <small>{{ stage.count ?? 0 }}</small>
          </article>
        </div>
        <div class="release-operator__summary-grid">
          <article>
            <span>当前发布页</span>
            <strong>{{ changeSummary.active_page_count ?? 0 }}</strong>
          </article>
          <article>
            <span>草案发布页</span>
            <strong>{{ changeSummary.draft_page_count ?? 0 }}</strong>
          </article>
          <article>
            <span>差异</span>
            <strong>{{ changeSummary.page_count_delta ?? 0 }}</strong>
          </article>
          <article>
            <span>预览/下线</span>
            <strong>{{ changeSummary.preview_page_count ?? 0 }} / {{ changeSummary.hidden_page_count ?? 0 }}</strong>
          </article>
        </div>
        <div class="release-operator__checks">
          <article v-for="check in preflightChecks" :key="pipelineKey(check)" :class="`release-operator__check--${check.status || 'pass'}`">
            <strong>{{ check.label || check.key || '-' }}</strong>
            <span>{{ check.message || '-' }}</span>
          </article>
        </div>
        <div class="release-operator__audience">
          <strong>生效试算</strong>
          <span>公司 {{ audienceSimulation.company_count ?? 0 }} 个，订阅 {{ audienceSimulation.subscription_count ?? 0 }} 个，角色 {{ audienceRoles }}</span>
        </div>
      </section>

      <section class="release-operator__section">
        <div class="release-operator__section-head">
          <h2>{{ copy.section_control_scope || '受控内容' }}</h2>
          <p>{{ controlScope.policy_state || '-' }} / {{ controlScope.access_level || '-' }}</p>
        </div>
        <div class="release-operator__policy-control">
          <label>
            <span>{{ copy.policy_state_label || '发布状态' }}</span>
            <ScSelect v-model="policyState" class="release-operator__select" :options="policyStateOptions" />
          </label>
          <label>
            <span>{{ copy.policy_access_label || '访问级别' }}</span>
            <ScSelect v-model="policyAccessLevel" class="release-operator__select" :options="policyAccessOptions" />
          </label>
          <ScButton
            variant="ghost"
            :disabled="busyKey === 'update_policy' || !updatePolicyAction.enabled"
            @click="savePolicy"
          >
            {{ copy.save_policy_action_label || '保存策略' }}
          </ScButton>
        </div>
        <div v-if="controlDefinitions.length" class="release-operator__definition-grid">
          <article v-for="item in controlDefinitions" :key="definitionKey(item)">
            <strong>{{ item.label || item.key || '-' }}</strong>
            <span>{{ item.meaning || '-' }}</span>
          </article>
        </div>
        <div class="release-operator__scope-grid">
          <article>
            <span>{{ copy.metric_controlled_menus || '受控菜单' }}</span>
            <strong>{{ controlScope.menu_count ?? 0 }}</strong>
          </article>
          <article>
            <span>{{ copy.metric_controlled_pages || '受控页面' }}</span>
            <strong>{{ controlScope.page_count ?? controlScope.menu_count ?? 0 }}</strong>
          </article>
          <article>
            <span>{{ copy.metric_controlled_capabilities || '受控能力' }}</span>
            <strong>{{ controlScope.capability_count ?? 0 }}</strong>
          </article>
        </div>
        <div v-if="controlledPages.length" class="release-operator__table-wrap release-operator__page-table">
          <ScTable class="release-operator__table" label="受控页面" :data="controlledPageTableRows" :columns="controlledPageColumns" row-key="__rowKey" size="small" />
        </div>
      </section>

      <section class="release-operator__section">
        <div class="release-operator__section-head">
          <h2>{{ copy.section_candidate || '可 Promote 候选' }}</h2>
          <p>{{ copy.hint_candidate || '仅展示当前产品下 candidate / approved 状态的候选快照。' }}</p>
        </div>
        <div v-if="candidateSnapshots.length" class="release-operator__table-wrap">
          <ScTable class="release-operator__table" label="可发布候选" :data="candidateTableRows" :columns="candidateColumns" row-key="id" size="small" />
        </div>
        <p v-else class="release-operator__empty">{{ copy.empty_candidate || '当前没有可 Promote 的候选快照。' }}</p>
      </section>

      <section class="release-operator__section">
        <div class="release-operator__section-head">
          <h2>{{ copy.section_pending || '待审批动作' }}</h2>
          <p>{{ copy.hint_pending_count_prefix || '当前数量：' }}{{ pendingActions.length }}</p>
        </div>
        <div v-if="pendingActions.length" class="release-operator__table-wrap">
          <ScTable class="release-operator__table" label="待审批动作" :data="pendingTableRows" :columns="pendingActionColumns" row-key="id" size="small" />
        </div>
        <p v-else class="release-operator__empty">{{ copy.empty_pending || '当前没有待审批动作。' }}</p>
      </section>

      <section class="release-operator__section release-operator__section--split">
        <div>
          <h2>{{ copy.section_rollback || '回滚' }}</h2>
          <p>{{ copy.hint_rollback || '仅当当前 active released snapshot 存在 rollback target 时可执行。' }}</p>
        </div>
        <ScButton
          variant="ghost"
          :disabled="!rollbackAction.enabled || busyKey === 'rollback'"
          @click="rollback"
        >
          {{ copy.rollback_action_label || '执行回滚' }}
        </ScButton>
      </section>

      <section class="release-operator__section">
        <div class="release-operator__section-head">
          <h2>{{ copy.section_history || '发布历史' }}</h2>
          <p>{{ copy.hint_history || '最近 action 与 snapshot。' }}</p>
        </div>
        <div class="release-operator__history">
          <div>
            <h3>{{ copy.history_snapshots_title || 'Snapshots' }}</h3>
            <ul>
              <li v-for="snapshot in historySnapshots" :key="`history-snapshot-${snapshot.id}`">
                <strong>{{ snapshot.version || snapshot.id }}</strong>
                <span>{{ snapshot.state || '-' }}</span>
              </li>
            </ul>
          </div>
          <div>
            <h3>{{ copy.history_actions_title || 'Actions' }}</h3>
            <ul>
              <li v-for="action in historyActions" :key="`history-action-${action.id}`">
                <strong>{{ action.action_type || action.id }}</strong>
                <span>{{ action.state || '-' }} / {{ action.approval_state || '-' }}</span>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import StatusPanel from '../components/StatusPanel.vue';
import ScButton from '../components/design-system/ScButton.vue';
import ScStatusBadge from '../components/design-system/ScStatusBadge.vue';
import ScSelect from '../components/design-system/ScSelect.vue';
import ScTable from '../components/design-system/ScTable.vue';
import { intentRequest } from '../api/intents';
import { usePageContract } from '../app/pageContract';
import { executePageContractAction } from '../app/pageContractActionRuntime';

type AnyRecord = Record<string, unknown>;

interface ProductRow {
  product_key: string;
  label?: string;
}

interface SnapshotRow {
  id: number;
  version?: string;
  state?: string;
  channel?: string;
  frozen_at?: string;
  release_draft?: AnyRecord;
  release_diff?: AnyRecord;
  preflight_checks?: AnyRecord[];
}

interface ReleaseActionRow {
  id: number;
  action_type?: string;
  product_key?: string;
  state?: string;
  approval_state?: string;
  requested_at?: string;
  can_approve?: boolean;
}

interface ReleaseOperatorSurface {
  copy?: AnyRecord;
  identity?: AnyRecord;
  products?: ProductRow[];
  product_delivery_console?: AnyRecord;
  control_scope?: AnyRecord;
  release_pipeline?: AnyRecord;
  release_state?: AnyRecord;
  pending_approval?: { actions?: ReleaseActionRow[] };
  candidate_snapshots?: SnapshotRow[];
  release_history?: { actions?: ReleaseActionRow[]; snapshots?: SnapshotRow[] };
  available_actions?: AnyRecord;
}

const route = useRoute();
const router = useRouter();
const pageContract = usePageContract('release_operator');
const pageSectionEnabled = pageContract.sectionEnabled;
const pageSectionStyle = pageContract.sectionStyle;
const pageSectionTagIs = pageContract.sectionTagIs;
const pageActionIntent = pageContract.actionIntent;
const pageActionTarget = pageContract.actionTarget;
const pageGlobalActions = pageContract.globalActions;
const pageSectionsReady = computed(() => (
  pageSectionEnabled('root', true)
  && pageSectionEnabled('hero', true)
  && pageSectionEnabled('release_state', true)
  && pageSectionEnabled('candidate_snapshots', true)
  && pageSectionEnabled('pending_approvals', true)
  && pageSectionEnabled('rollback', true)
  && pageSectionTagIs('root', 'section')
  && pageSectionTagIs('hero', 'header')
  && pageSectionTagIs('release_state', 'section')
  && pageSectionTagIs('candidate_snapshots', 'section')
  && pageSectionTagIs('pending_approvals', 'section')
  && pageSectionTagIs('rollback', 'section')
));
const pageSectionsFingerprint = computed(() => JSON.stringify([
  pageSectionStyle('hero'),
  pageSectionStyle('release_state'),
  pageSectionStyle('candidate_snapshots'),
  pageSectionStyle('pending_approvals'),
  pageSectionStyle('rollback'),
]));

async function executeGlobalPageAction(actionKey: string) {
  await executePageContractAction({
    actionKey,
    router,
    actionIntent: pageActionIntent,
    actionTarget: pageActionTarget,
    query: route.query,
    onRefresh: loadSurface,
  });
}

const initialProduct = String(route.query.product_key || '').trim();
const surface = ref<ReleaseOperatorSurface | null>(null);
const selectedProduct = ref(initialProduct);
const loading = ref(false);
const error = ref('');
const busyKey = ref('');
const policyState = ref('stable');
const policyAccessLevel = ref('public');

const copy = computed<Record<string, string>>(() => {
  const raw = surface.value?.copy || {};
  return Object.fromEntries(
    Object.entries(raw).map(([key, value]) => [key, String(value || '')]),
  );
});
const identity = computed(() => surface.value?.identity || {});
const products = computed(() => surface.value?.products || []);
const productOptions = computed(() => products.value.map((product) => ({
  value: product.product_key,
  label: `${product.label || product.product_key} · ${product.product_key}`,
})));
const policyStateOptions = [
  { value: 'draft', label: 'draft' },
  { value: 'preview', label: 'preview' },
  { value: 'stable', label: 'stable' },
  { value: 'archived', label: 'archived' },
];
const policyAccessOptions = [
  { value: 'public', label: 'public' },
  { value: 'internal', label: 'internal' },
  { value: 'role_restricted', label: 'role_restricted' },
];
const productConsole = computed(() => surface.value?.product_delivery_console || {});
const productProfile = computed(() => (productConsole.value.profile || {}) as AnyRecord);
const productBundle = computed(() => (productConsole.value.bundle || {}) as AnyRecord);
const productLicense = computed(() => (productConsole.value.license || {}) as AnyRecord);
const productReadiness = computed(() => (productConsole.value.readiness || {}) as AnyRecord);
const productCapabilities = computed(() => {
  const items = productBundle.value.capabilities;
  return Array.isArray(items) ? items as AnyRecord[] : [];
});
const productScenes = computed(() => {
  const items = productBundle.value.scenes;
  return Array.isArray(items) ? items as AnyRecord[] : [];
});
const acceptanceAssets = computed(() => {
  const items = productConsole.value.acceptance_assets;
  return Array.isArray(items) ? items.map((item) => String(item || '')).filter(Boolean) : [];
});
const controlScope = computed(() => surface.value?.control_scope || {});
const releasePipeline = computed(() => surface.value?.release_pipeline || {});
const pipelineStages = computed(() => {
  const stages = releasePipeline.value.stages;
  return Array.isArray(stages) ? stages as AnyRecord[] : [];
});
const changeSummary = computed(() => (releasePipeline.value.change_summary || {}) as AnyRecord);
const preflightChecks = computed(() => {
  const checks = releasePipeline.value.preflight_checks;
  return Array.isArray(checks) ? checks as AnyRecord[] : [];
});
const audienceSimulation = computed(() => (releasePipeline.value.audience_simulation || {}) as AnyRecord);
const audienceRoles = computed(() => {
  const roles = audienceSimulation.value.role_scope;
  return Array.isArray(roles) && roles.length ? roles.join(', ') : '-';
});
const controlledPages = computed(() => {
  const pages = controlScope.value.pages;
  return Array.isArray(pages) ? pages as AnyRecord[] : [];
});
const controlDefinitions = computed(() => {
  const items = controlScope.value.control_definition;
  return Array.isArray(items) ? items as AnyRecord[] : [];
});
const releaseState = computed(() => surface.value?.release_state || {});
const activeSnapshot = computed(() => (releaseState.value.active_snapshot || {}) as AnyRecord);
const runtimeSummary = computed(() => (releaseState.value.runtime_summary || {}) as AnyRecord);
const candidateSnapshots = computed(() => surface.value?.candidate_snapshots || []);
const pendingActions = computed(() => surface.value?.pending_approval?.actions || []);
const historySnapshots = computed(() => surface.value?.release_history?.snapshots || []);
const historyActions = computed(() => surface.value?.release_history?.actions || []);
const rollbackAction = computed(() => {
  const actions = surface.value?.available_actions || {};
  return (actions.rollback || {}) as { enabled?: boolean; params?: AnyRecord };
});
const syncPolicyAction = computed(() => {
  const actions = surface.value?.available_actions || {};
  return (actions.sync_policy || {}) as { enabled?: boolean; params?: AnyRecord };
});
const updatePolicyAction = computed(() => {
  const actions = surface.value?.available_actions || {};
  return (actions.update_policy || {}) as { enabled?: boolean; params?: AnyRecord };
});
const updatePagePolicyAction = computed(() => {
  const actions = surface.value?.available_actions || {};
  return (actions.update_page_policy || {}) as { enabled?: boolean; params?: AnyRecord };
});
const controlledPageTableRows = computed(() => controlledPages.value.map((page) => ({ ...page, __rowKey: pageKey(page) })));
const candidateTableRows = computed(() => candidateSnapshots.value.map((snapshot) => ({ ...snapshot })));
const pendingTableRows = computed(() => pendingActions.value.map((action) => ({ ...action })));

function tableText(value: unknown) { return String(value ?? '').trim() || '-'; }
function statusNode(value: string, label: string, semantic: 'default'|'info'|'success'|'warning'|'danger' = 'default') {
  return h(ScStatusBadge, { value, label, semantic });
}
function actionNode(label: string, disabled: boolean, onClick: () => void, variant: 'primary'|'ghost' = 'ghost') {
  return h(ScButton, { variant, size: 'small', disabled, onClick }, () => label);
}
const controlledPageColumns = computed(() => [
  { colKey: 'visible_menu_path', title: '用户菜单', cell: (_h: unknown, { row }: { row: AnyRecord }) => tableText(row.visible_menu_path || row.group_label) },
  { colKey: 'page_label', title: '页面', cell: (_h: unknown, { row }: { row: AnyRecord }) => tableText(row.page_label || row.label || row.page_key) },
  { colKey: 'route', title: '路由', ellipsis: true, cell: (_h: unknown, { row }: { row: AnyRecord }) => tableText(row.route) },
  { colKey: 'release_state', title: '发布阶段', cell: (_h: unknown, { row }: { row: AnyRecord }) => {
    const state = String(row.release_state || (row.enabled === false ? 'hidden' : 'released'));
    return statusNode(state, releaseStateLabel(row), state === 'released' ? 'success' : state === 'preview' ? 'warning' : 'default');
  } },
  { colKey: 'access_level', title: '可见范围', cell: (_h: unknown, { row }: { row: AnyRecord }) => accessLevelLabel(row) },
  { colKey: 'source', title: '来源', ellipsis: true, cell: (_h: unknown, { row }: { row: AnyRecord }) => sourceLabel(row) },
  { colKey: 'actions', title: '操作', width: 260, cell: (_h: unknown, { row }: { row: AnyRecord }) => h('div', { class: 'release-operator__row-actions' }, [
    actionNode('发布', busyKey.value === `page:${pageKey(row)}:released` || !updatePagePolicyAction.value.enabled, () => updatePagePolicy(row, { release_state: 'released', enabled: true })),
    actionNode('预览', busyKey.value === `page:${pageKey(row)}:preview` || !updatePagePolicyAction.value.enabled, () => updatePagePolicy(row, { release_state: 'preview', enabled: true })),
    actionNode('下线', busyKey.value === `page:${pageKey(row)}:hidden` || !updatePagePolicyAction.value.enabled, () => updatePagePolicy(row, { release_state: 'hidden', enabled: false })),
    actionNode(row.access_level === 'internal' ? '转公开' : '内部', busyKey.value === `page:${pageKey(row)}:internal` || !updatePagePolicyAction.value.enabled, () => updatePagePolicy(row, { access_level: row.access_level === 'internal' ? 'public' : 'internal' })),
  ]) },
]);
const candidateColumns = computed(() => [
  { colKey: 'version', title: '版本', cell: (_h: unknown, { row }: { row: SnapshotRow }) => tableText(row.version) },
  { colKey: 'state', title: '状态', cell: (_h: unknown, { row }: { row: SnapshotRow }) => statusNode(String(row.state || ''), tableText(row.state), 'info') },
  { colKey: 'channel', title: '通道', cell: (_h: unknown, { row }: { row: SnapshotRow }) => tableText(row.channel) },
  { colKey: 'draft', title: '草案范围', cell: (_h: unknown, { row }: { row: SnapshotRow }) => snapshotDraftLabel(row) },
  { colKey: 'diff', title: '差异', cell: (_h: unknown, { row }: { row: SnapshotRow }) => snapshotDiffLabel(row) },
  { colKey: 'gate', title: '门禁', cell: (_h: unknown, { row }: { row: SnapshotRow }) => statusNode(candidateReady(row) ? 'ready' : 'refreeze', candidateReady(row) ? '可发布' : '需重新冻结', candidateReady(row) ? 'success' : 'warning') },
  { colKey: 'frozen_at', title: '冻结时间', cell: (_h: unknown, { row }: { row: SnapshotRow }) => tableText(row.frozen_at) },
  { colKey: 'actions', title: '操作', width: 96, cell: (_h: unknown, { row }: { row: SnapshotRow }) => actionNode('发布', busyKey.value === `promote:${row.id}` || !candidateReady(row), () => promote(row), 'primary') },
]);
const pendingActionColumns = computed(() => [
  { colKey: 'action_type', title: '动作', cell: (_h: unknown, { row }: { row: ReleaseActionRow }) => tableText(row.action_type) },
  { colKey: 'product_key', title: '产品', cell: (_h: unknown, { row }: { row: ReleaseActionRow }) => tableText(row.product_key) },
  { colKey: 'approval_state', title: '审批', cell: (_h: unknown, { row }: { row: ReleaseActionRow }) => statusNode(String(row.approval_state || ''), tableText(row.approval_state), 'warning') },
  { colKey: 'requested_at', title: '请求时间', cell: (_h: unknown, { row }: { row: ReleaseActionRow }) => tableText(row.requested_at) },
  { colKey: 'actions', title: '操作', width: 128, cell: (_h: unknown, { row }: { row: ReleaseActionRow }) => actionNode(copy.value.approve_action_label || '审批并执行', busyKey.value === `approve:${row.id}` || row.can_approve === false, () => approve(row), 'primary') },
]);

function pageKey(page: AnyRecord) {
  return String(page.page_key || page.scene_key || page.menu_key || page.capability_key || '').trim();
}
function definitionKey(item: AnyRecord) {
  return String(item.key || item.label || '').trim();
}
function pipelineKey(item: AnyRecord) {
  return String(item.key || item.label || '').trim();
}
function productItemKey(item: AnyRecord) {
  return String(item.key || item.code || item.name || item.label || '').trim();
}
function readinessLabel(value: unknown) {
  const status = String(value || '').trim();
  const labels: Record<string, string> = {
    ready: '可交付',
    warn: '需关注',
    blocked: '有阻断',
  };
  return labels[status] || status || '-';
}
function releaseStateLabel(page: AnyRecord) {
  const state = String(page.release_state || (page.enabled === false ? 'hidden' : 'released'));
  const labels: Record<string, string> = {
    released: '正式发布',
    preview: '预览',
    hidden: '未发布',
    retired: '已下线',
  };
  return labels[state] || state || '-';
}
function releaseStateClass(page: AnyRecord) {
  const state = String(page.release_state || (page.enabled === false ? 'hidden' : 'released'));
  if (state === 'preview') return 'release-operator__pill--preview';
  if (state === 'hidden' || state === 'retired' || page.enabled === false) return 'release-operator__pill--muted';
  return '';
}
function accessLevelLabel(page: AnyRecord) {
  const level = String(page.access_level || 'public');
  const labels: Record<string, string> = {
    public: '授权用户',
    internal: '内部可见',
    role_restricted: '按角色',
  };
  return labels[level] || level;
}
function sourceLabel(page: AnyRecord) {
  const menu = String(page.menu_xmlid || '').trim();
  const model = String(page.res_model || '').trim();
  if (menu && model) return `${menu} / ${model}`;
  return menu || model || String(page.source_kind || '').trim() || '-';
}
function snapshotDraftLabel(snapshot: SnapshotRow) {
  const draft = (snapshot.release_draft || {}) as AnyRecord;
  const pageCount = Number(draft.page_count || 0);
  const totalCount = Number(draft.total_page_count || 0);
  if (!draft.fingerprint) return '无草案指纹';
  return `${pageCount}/${totalCount} 页`;
}
function snapshotDiffLabel(snapshot: SnapshotRow) {
  const diff = (snapshot.release_diff || {}) as AnyRecord;
  return `新增 ${Number(diff.added_page_count || 0)} / 变更 ${Number(diff.changed_page_count || 0)} / 移除 ${Number(diff.removed_page_count || 0)}`;
}
function candidateReady(snapshot: SnapshotRow) {
  const draft = (snapshot.release_draft || {}) as AnyRecord;
  return Boolean(draft.fingerprint) && Number(draft.blocking_issue_count || 0) === 0;
}
const freezeAction = computed(() => {
  const actions = surface.value?.available_actions || {};
  return (actions.freeze || {}) as { enabled?: boolean; params?: AnyRecord };
});

function hydratePolicyControls(payload: ReleaseOperatorSurface) {
  const scope = payload.control_scope || {};
  policyState.value = String(scope.policy_state || 'stable');
  policyAccessLevel.value = String(scope.access_level || 'public');
}

async function loadSurface() {
  loading.value = true;
  error.value = '';
  try {
    const payload = await intentRequest<ReleaseOperatorSurface>({
      intent: 'release.operator.surface',
      params: {
        product_key: selectedProduct.value,
        action_limit: 20,
      },
    });
    surface.value = payload;
    hydratePolicyControls(payload);
    const resolvedProduct = String(payload.identity?.product_key || '').trim();
    if (resolvedProduct) {
      selectedProduct.value = resolvedProduct;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '发布控制台不可用';
  } finally {
    loading.value = false;
  }
}

async function runWrite(intent: string, params: AnyRecord, key: string) {
  busyKey.value = key;
  error.value = '';
  try {
    const result = await intentRequest<{ surface?: ReleaseOperatorSurface }>({ intent, params });
    if (result.surface) {
      surface.value = result.surface;
      hydratePolicyControls(result.surface);
      const resolvedProduct = String(result.surface.identity?.product_key || '').trim();
      if (resolvedProduct) selectedProduct.value = resolvedProduct;
    } else {
      await loadSurface();
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '发布动作执行失败';
  } finally {
    busyKey.value = '';
  }
}

function promote(snapshot: SnapshotRow) {
  void runWrite(
    'release.operator.promote',
    {
      product_key: selectedProduct.value,
      snapshot_id: snapshot.id,
      replace_active: true,
    },
    `promote:${snapshot.id}`,
  );
}

function approve(action: ReleaseActionRow) {
  void runWrite('release.operator.approve', { action_id: action.id }, `approve:${action.id}`);
}

function freeze() {
  const params = freezeAction.value.params || { product_key: selectedProduct.value };
  void runWrite('release.operator.freeze', params, 'freeze');
}

function syncPolicy() {
  const params = syncPolicyAction.value.params || { product_key: selectedProduct.value };
  void runWrite('release.operator.sync_policy', params, 'sync_policy');
}

function savePolicy() {
  const params = updatePolicyAction.value.params || { product_key: selectedProduct.value };
  void runWrite(
    'release.operator.update_policy',
    {
      ...params,
      product_key: selectedProduct.value,
      state: policyState.value,
      access_level: policyAccessLevel.value,
    },
    'update_policy',
  );
}

function updatePagePolicy(page: AnyRecord, updates: AnyRecord) {
  const key = pageKey(page);
  if (!key) return;
  const params = updatePagePolicyAction.value.params || { product_key: selectedProduct.value };
  const state = String(updates.release_state || updates.access_level || 'update');
  void runWrite(
    'release.operator.update_page_policy',
    {
      ...params,
      product_key: selectedProduct.value,
      page_key: key,
      ...updates,
    },
    `page:${key}:${state}`,
  );
}

function rollback() {
  const params = rollbackAction.value.params || {};
  void runWrite('release.operator.rollback', params, 'rollback');
}

onMounted(() => {
  void loadSurface();
});
</script>

<style scoped>
.release-operator {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px;
}

.release-operator__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.release-operator__header h1 {
  margin: 2px 0 8px;
  font-size: 28px;
  line-height: 1.2;
}

.release-operator__header p {
  margin: 0;
  color: var(--sc-semantic-text-muted);
}

.release-operator__actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.release-operator__select {
  min-width: 190px;
  height: 38px;
  border: 1px solid var(--sc-app-border-strong);
  border-radius: var(--sc-component-input-radius);
  background: var(--sc-app-input-bg);
  color: var(--sc-app-text-primary);
  padding: 0 10px;
}

.release-operator__metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.release-operator__metric,
.release-operator__section {
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-component-panel-radius);
  background: var(--sc-app-panel);
}

.release-operator__metric {
  padding: 14px;
}

.release-operator__metric span {
  display: block;
  margin-bottom: 8px;
  color: var(--sc-semantic-text-muted);
  font-size: 12px;
}

.release-operator__metric strong {
  display: block;
  overflow-wrap: anywhere;
  color: var(--sc-app-text-primary);
  font-size: 18px;
}

.release-operator__scope-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.release-operator__product-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.release-operator__product-grid article {
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-component-panel-radius);
  padding: 12px;
}

.release-operator__product-grid span,
.release-operator__product-grid small {
  display: block;
  color: var(--sc-semantic-text-muted);
  font-size: 12px;
}

.release-operator__product-grid strong {
  display: block;
  margin: 7px 0;
  overflow-wrap: anywhere;
  color: var(--sc-app-text-primary);
  font-size: 18px;
}

.release-operator__delivery-lists {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.release-operator__delivery-lists article {
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-component-panel-radius);
  padding: 12px;
}

.release-operator__delivery-lists h3 {
  margin: 0 0 10px;
  font-size: 14px;
}

.release-operator__tag-list,
.release-operator__asset-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.release-operator__tag-list span,
.release-operator__asset-list span {
  border: 1px solid var(--sc-app-border);
  border-radius: 6px;
  padding: 5px 8px;
  color: var(--sc-app-text-primary);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.release-operator__asset-list span {
  max-width: 100%;
}

.release-operator__upgrade-hint {
  margin-top: 12px;
  color: var(--sc-semantic-text-muted);
}

.release-operator__pipeline,
.release-operator__summary-grid,
.release-operator__checks {
  display: grid;
  gap: 10px;
}

.release-operator__pipeline {
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.release-operator__pipeline article,
.release-operator__summary-grid article,
.release-operator__checks article,
.release-operator__audience {
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-component-panel-radius);
  padding: 10px;
}

.release-operator__pipeline article {
  display: grid;
  gap: 6px;
}

.release-operator__pipeline strong,
.release-operator__summary-grid strong,
.release-operator__checks strong,
.release-operator__audience strong {
  color: var(--sc-app-text-primary);
  font-size: 13px;
}

.release-operator__pipeline small,
.release-operator__summary-grid span,
.release-operator__checks span,
.release-operator__audience span {
  color: var(--sc-semantic-text-muted);
  font-size: 12px;
}

.release-operator__stage-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--sc-app-border-strong);
}

.release-operator__stage-dot--done,
.release-operator__stage-dot--active,
.release-operator__stage-dot--preview {
  background: var(--sc-semantic-surface-interactive);
}

.release-operator__stage-dot--warn {
  background: var(--sc-app-warning-text);
}

.release-operator__stage-dot--blocked {
  background: var(--sc-app-danger-text);
}

.release-operator__summary-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-top: 10px;
}

.release-operator__summary-grid article {
  display: grid;
  gap: 6px;
}

.release-operator__summary-grid strong {
  font-size: 20px;
}

.release-operator__checks {
  grid-template-columns: repeat(5, minmax(0, 1fr));
  margin-top: 10px;
}

.release-operator__check--fail {
  border-color: var(--sc-app-danger-border);
  background: var(--sc-app-danger-bg);
}

.release-operator__check--warn {
  border-color: var(--sc-app-warning-border);
  background: var(--sc-app-warning-bg);
}

.release-operator__audience {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
}

.release-operator__policy-control {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 10px;
  margin-bottom: 12px;
}

.release-operator__policy-control label {
  display: grid;
  gap: 6px;
}

.release-operator__policy-control span {
  color: var(--sc-semantic-text-muted);
  font-size: 12px;
}

.release-operator__definition-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.release-operator__definition-grid article {
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-component-panel-radius);
  padding: 10px;
}

.release-operator__definition-grid strong,
.release-operator__definition-grid span {
  display: block;
}

.release-operator__definition-grid strong {
  margin-bottom: 5px;
  color: var(--sc-app-text-primary);
  font-size: 13px;
}

.release-operator__definition-grid span {
  color: var(--sc-semantic-text-muted);
  font-size: 12px;
  line-height: 1.5;
  white-space: normal;
}

.release-operator__scope-grid article {
  border: 1px solid var(--sc-app-border);
  border-radius: var(--sc-component-panel-radius);
  padding: 12px;
}

.release-operator__scope-grid span {
  display: block;
  margin-bottom: 8px;
  color: var(--sc-semantic-text-muted);
  font-size: 12px;
}

.release-operator__scope-grid strong {
  color: var(--sc-app-text-primary);
  font-size: 22px;
}

.release-operator__page-table {
  margin-top: 12px;
}

.release-operator__section {
  padding: 16px;
}

.release-operator__section--split {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.release-operator__section h2,
.release-operator__section h3 {
  margin: 0;
  color: var(--sc-app-text-primary);
}

.release-operator__section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.release-operator__section p {
  margin: 6px 0 0;
  color: var(--sc-semantic-text-muted);
}

.release-operator__table-wrap {
  overflow-x: auto;
}

.release-operator__table :deep(table) {
  width: 100%;
}

.release-operator__table :deep(th),
.release-operator__table :deep(td) {
  border-top: 1px solid var(--sc-app-border);
  padding: 10px 8px;
  text-align: left;
  white-space: nowrap;
}

.release-operator__table :deep(th) {
  color: var(--sc-semantic-text-muted);
  font-size: 12px;
  font-weight: 600;
}

.release-operator__pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  border-radius: 999px;
  background: var(--sc-app-info-bg);
  color: var(--sc-app-info-text);
  padding: 0 9px;
  font-size: 12px;
}

.release-operator__pill--muted {
  background: var(--sc-app-muted-bg);
  color: var(--sc-semantic-text-muted);
}

.release-operator__pill--preview {
  background: var(--sc-app-warning-bg);
  color: var(--sc-app-warning-text);
}

.release-operator__row-actions {
  display: flex;
  flex-wrap: nowrap;
  gap: 6px;
}

.release-operator__row-action {
  min-width: 52px;
}

.release-operator__empty {
  border-top: 1px solid var(--sc-app-border);
  padding-top: 12px;
}

.release-operator__history {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.release-operator__history ul {
  display: grid;
  gap: 8px;
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}

.release-operator__history li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-top: 1px solid var(--sc-app-border);
  padding-top: 8px;
}

.release-operator__history span {
  color: var(--sc-semantic-text-muted);
}

@media (max-width: 900px) {
  .release-operator {
    padding: 16px;
  }

  .release-operator__header,
  .release-operator__section-head,
  .release-operator__section--split {
    flex-direction: column;
    align-items: stretch;
  }

  .release-operator__metrics,
  .release-operator__scope-grid,
  .release-operator__product-grid,
  .release-operator__delivery-lists,
  .release-operator__pipeline,
  .release-operator__summary-grid,
  .release-operator__checks,
  .release-operator__definition-grid,
  .release-operator__history {
    grid-template-columns: 1fr;
  }

  .release-operator__audience {
    flex-direction: column;
  }

  .release-operator__actions {
    flex-wrap: wrap;
  }
}
</style>
