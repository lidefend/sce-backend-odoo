<template>
  <ScPage
    v-if="pageSectionsReady"
    class="release-operator sc-product-workspace-stack"
    content-layout="data-grid"
    data-product-page-mode="dashboard"
    data-semantic-component="ReleaseOperatorView"
    :data-contract-sections="pageSectionsFingerprint"
    :style="pageSectionStyle('root')"
  >
    <ProductPageHeader
      :title="copy.title || '发布控制台'"
      :subtitle="copy.description || '查看当前发布状态、候选快照、待审批动作与回滚目标。'"
      :eyebrow="copy.eyebrow || '发布运营'"
      presentation-mode="dashboard"
      render-profile="readonly"
      :style="pageSectionStyle('hero')"
    >
      <template #actions>
        <ScActionBar label="发布控制台操作">
          <ScSelect
            v-model="selectedProduct"
            class="release-operator__product-select"
            :options="productOptions"
            :aria-label="copy.metric_current_product || '当前产品'"
            @change="loadSurface"
          />
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
        </ScActionBar>
      </template>
    </ProductPageHeader>

    <DashboardPattern>
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
        <section class="release-operator__metrics" aria-label="发布摘要" :style="pageSectionStyle('release_state')">
          <ScCard
            v-for="metric in summaryMetrics"
            :key="metric.key"
            class="release-operator__metric"
            appearance="metric"
            :data-metric-key="metric.key"
          >
            <h3>{{ metric.label }}</h3>
            <p>{{ metric.value }}</p>
          </ScCard>
        </section>

        <ScSection :title="copy.section_product_delivery_console || '产品交付控制台'">
          <template #actions>
            <span class="release-operator__section-meta">{{ productProfile.label || productConsole.product_key || '-' }}</span>
          </template>
          <ScDescriptions :items="productFacts" :column="descriptionColumns" bordered />
          <div class="release-operator__delivery">
            <ScCard
              v-for="group in deliveryGroups"
              :key="group.key"
              appearance="section"
              :title="group.title"
            >
              <ScList v-if="group.items.length" :items="group.items" :split="true">
                <template #item="{ item }">
                  <span class="release-operator__list-row">
                    <span class="release-operator__list-label">{{ item.label }}</span>
                    <span v-if="item.meta" class="release-operator__list-meta">{{ item.meta }}</span>
                  </span>
                </template>
              </ScList>
              <ScEmptyState v-else density="compact" :heading-level="4" title="暂无数据" />
            </ScCard>
          </div>
          <ScInlineState v-if="productLicense.upgrade_hint" state="info" :label="String(productLicense.upgrade_hint)" />
        </ScSection>

        <ScSection title="产品配置发布线">
          <template #actions>
            <span class="release-operator__section-meta">草案、检查、候选、发布、生效</span>
          </template>
          <ScList :items="pipelineItems" class="release-operator__stage-list">
            <template #item="{ item }">
              <span class="release-operator__stage">
                <ScStatusBadge :value="String(item.status || '')" :label="stageStatusLabel(String(item.status || ''))" :semantic="stageStatusSemantic(String(item.status || ''))" />
                <span class="release-operator__list-label">{{ item.label }}</span>
                <strong class="release-operator__list-meta">{{ item.count }}</strong>
              </span>
            </template>
          </ScList>
          <ScDescriptions class="release-operator__summary" :items="changeSummaryItems" :column="descriptionColumns" bordered />
          <ScList :items="preflightItems" class="release-operator__check-list">
            <template #item="{ item }">
              <span class="release-operator__check">
                <ScStatusBadge :value="String(item.status || '')" :label="checkStatusLabel(String(item.status || ''))" :semantic="checkStatusSemantic(String(item.status || ''))" />
                <span class="release-operator__list-label">{{ item.label }}</span>
                <span class="release-operator__list-meta">{{ item.message }}</span>
              </span>
            </template>
          </ScList>
          <ScCard appearance="section" title="生效试算">
            <ScDescriptions :items="audienceItems" :column="compactDescriptionColumns" bordered />
          </ScCard>
        </ScSection>

        <ScSection :title="copy.section_control_scope || '受控内容'">
          <template #actions>
            <span class="release-operator__section-meta">{{ controlScope.policy_state || '-' }} / {{ controlScope.access_level || '-' }}</span>
          </template>
          <ScForm layout="inline" :prevent-submit-default="true" class="release-operator__policy">
            <ScFormItem :label="copy.policy_state_label || '发布状态'" name="policy_state">
              <ScSelect v-model="policyState" :options="policyStateOptions" />
            </ScFormItem>
            <ScFormItem :label="copy.policy_access_label || '访问级别'" name="policy_access_level">
              <ScSelect v-model="policyAccessLevel" :options="policyAccessOptions" />
            </ScFormItem>
            <ScFormItem>
              <ScButton
                variant="ghost"
                type="button"
                :disabled="busyKey === 'update_policy' || !updatePolicyAction.enabled"
                @click="savePolicy"
              >
                {{ copy.save_policy_action_label || '保存策略' }}
              </ScButton>
            </ScFormItem>
          </ScForm>
          <ScList v-if="controlDefinitionItems.length" :items="controlDefinitionItems">
            <template #item="{ item }">
              <span class="release-operator__list-row">
                <span class="release-operator__list-label">{{ item.label }}</span>
                <span class="release-operator__list-meta release-operator__list-meta--wrap">{{ item.meta }}</span>
              </span>
            </template>
          </ScList>
          <ScDescriptions class="release-operator__summary" :items="scopeItems" :column="compactDescriptionColumns" bordered />
          <ScCard v-if="controlledPages.length" class="release-operator__table-card" appearance="table">
            <ScTable
              class="release-operator__table"
              label="受控页面"
              :data="controlledPageTableRows"
              :columns="controlledPageColumns"
              row-key="__rowKey"
              size="small"
            />
          </ScCard>
        </ScSection>

        <ScSection
          :title="copy.section_candidate || '可晋升候选'"
          :description="copy.hint_candidate || '仅展示当前产品下 candidate / approved 状态的候选快照。'"
          :style="pageSectionStyle('candidate_snapshots')"
        >
          <ScCard v-if="candidateSnapshots.length" appearance="table">
            <ScTable
              class="release-operator__table"
              label="可发布候选"
              :data="candidateTableRows"
              :columns="candidateColumns"
              row-key="id"
              size="small"
            />
          </ScCard>
          <ScEmptyState v-else :title="copy.empty_candidate || '当前没有可晋升的候选快照。'" :heading-level="3" density="compact" />
        </ScSection>

        <ScSection
          :title="copy.section_pending || '待审批动作'"
          :description="`${copy.hint_pending_count_prefix || '当前数量：'}${pendingActions.length}`"
          :style="pageSectionStyle('pending_approvals')"
        >
          <ScCard v-if="pendingActions.length" appearance="table">
            <ScTable
              class="release-operator__table"
              label="待审批动作"
              :data="pendingTableRows"
              :columns="pendingActionColumns"
              row-key="id"
              size="small"
            />
          </ScCard>
          <ScEmptyState v-else :title="copy.empty_pending || '当前没有待审批动作。'" :heading-level="3" density="compact" />
        </ScSection>

        <ScSection
          :title="copy.section_rollback || '回滚'"
          :description="copy.hint_rollback || '仅当当前 active released snapshot 存在 rollback target 时可执行。'"
          :style="pageSectionStyle('rollback')"
        >
          <template #actions>
            <ScButton
              variant="ghost"
              :disabled="!rollbackAction.enabled || busyKey === 'rollback'"
              @click="rollback"
            >
              {{ copy.rollback_action_label || '执行回滚' }}
            </ScButton>
          </template>
        </ScSection>

        <ScSection
          :title="copy.section_history || '发布历史'"
          :description="copy.hint_history || '最近 action 与 snapshot。'"
        >
          <div class="release-operator__history">
            <ScCard appearance="section" :title="copy.history_snapshots_title || '发布快照'">
              <ScList v-if="historySnapshotItems.length" :items="historySnapshotItems">
                <template #item="{ item }">
                  <span class="release-operator__list-row">
                    <span class="release-operator__list-label">{{ item.label }}</span>
                    <span class="release-operator__list-meta">{{ item.meta }}</span>
                  </span>
                </template>
              </ScList>
              <ScEmptyState v-else density="compact" :heading-level="4" title="暂无数据" />
            </ScCard>
            <ScCard appearance="section" :title="copy.history_actions_title || '发布动作'">
              <ScList v-if="historyActionItems.length" :items="historyActionItems">
                <template #item="{ item }">
                  <span class="release-operator__list-row">
                    <span class="release-operator__list-label">{{ item.label }}</span>
                    <span class="release-operator__list-meta">{{ item.meta }}</span>
                  </span>
                </template>
              </ScList>
              <ScEmptyState v-else density="compact" :heading-level="4" title="暂无数据" />
            </ScCard>
          </div>
        </ScSection>
      </template>
    </DashboardPattern>
  </ScPage>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import StatusPanel from '../components/StatusPanel.vue';
import ScButton from '../components/design-system/ScButton.vue';
import ScEmptyState from '../components/design-system/ScEmptyState.vue';
import ScStatusBadge from '../components/design-system/ScStatusBadge.vue';
import ScSelect from '../components/design-system/ScSelect.vue';
import ScTable from '../components/design-system/ScTable.vue';
import ScPage from '../components/design-system/ScPage.vue';
import ScSection from '../components/design-system/ScSection.vue';
import ScCard from '../components/design-system/ScCard.vue';
import ScDescriptions from '../components/design-system/ScDescriptions.vue';
import ScList from '../components/design-system/ScList.vue';
import ScActionBar from '../components/design-system/ScActionBar.vue';
import ScForm from '../components/design-system/ScForm.vue';
import ScFormItem from '../components/design-system/ScFormItem.vue';
import ScInlineState from '../components/design-system/ScInlineState.vue';
import ProductPageHeader from '../components/product-page-header/ProductPageHeader.vue';
import DashboardPattern from '../components/product-page-patterns/DashboardPattern.vue';
import { useNarrowViewport } from '../composables/useNarrowViewport';
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

type DescriptionItem = { key: string; label: string; value: string };
type ListRow = { key: string; label: string; meta: string };
type StageRow = { key: string; label: string; count: string; status: string };
type CheckRow = { key: string; label: string; message: string; status: string };

const narrowViewport = useNarrowViewport(900);
const descriptionColumns = computed(() => (narrowViewport.value ? 1 : 4));
const compactDescriptionColumns = computed(() => (narrowViewport.value ? 1 : 3));

const summaryMetrics = computed(() => [
  {
    key: 'current_product',
    label: copy.value.metric_current_product || '当前产品',
    value: String(identity.value.label || identity.value.product_key || '-'),
  },
  {
    key: 'active_snapshot',
    label: copy.value.metric_active_snapshot || '当前生效快照',
    value: String(activeSnapshot.value.version || activeSnapshot.value.id || '-'),
  },
  {
    key: 'latest_action',
    label: copy.value.metric_latest_action || '最近发布动作',
    value: String(runtimeSummary.value.latest_action_type || '-'),
  },
  {
    key: 'approval_state',
    label: copy.value.metric_approval_state || '审批状态',
    value: String(runtimeSummary.value.latest_action_approval_state || '-'),
  },
]);

const productFacts = computed<DescriptionItem[]>(() => [
  {
    key: 'bundle',
    label: '产品包',
    value: String(productBundle.value.name || '-'),
  },
  {
    key: 'license',
    label: '授权层级',
    value: `${String(productLicense.value.level || '-')}${productLicense.value.customer_visible === false ? '（平台可见）' : ''}`,
  },
  {
    key: 'readiness',
    label: '交付就绪',
    value: `${readinessLabel(productReadiness.value.status)}（阻断 ${Number(productReadiness.value.blocking_count ?? 0)} / 警告 ${Number(productReadiness.value.warn_count ?? 0)}${productReadiness.value.unconfigured_count ? ` / 未配置 ${Number(productReadiness.value.unconfigured_count)}` : ''}）`,
  },
  {
    key: 'controlled_pages',
    label: '受控页面',
    value: `${Number(productReadiness.value.controlled_page_count ?? 0)}（已发布 ${Number(productReadiness.value.released_page_count ?? 0)}）`,
  },
]);

const deliveryGroups = computed(() => [
  {
    key: 'capabilities',
    title: '能力包',
    items: productCapabilities.value.map((item, index) => ({
      key: productItemKey(item) || `capability-${index + 1}`,
      label: String(item.label || item.key || '-'),
      meta: String(item.tier || ''),
    })),
  },
  {
    key: 'scenes',
    title: '场景包',
    items: productScenes.value.map((item, index) => ({
      key: productItemKey(item) || `scene-${index + 1}`,
      label: String(item.name || item.code || '-'),
      meta: String(item.tier || ''),
    })),
  },
  {
    key: 'assets',
    title: '交付资产',
    items: acceptanceAssets.value.map((asset, index) => ({
      key: `asset-${index + 1}-${asset}`,
      label: asset,
      meta: '',
    })),
  },
]);

const pipelineItems = computed<StageRow[]>(() => pipelineStages.value.map((stage, index) => ({
  key: pipelineKey(stage) || `stage-${index + 1}`,
  label: String(stage.label || stage.key || '-'),
  count: String(stage.count ?? 0),
  status: String(stage.status || 'pending'),
})));

const changeSummaryItems = computed<DescriptionItem[]>(() => [
  { key: 'active_pages', label: '当前发布页', value: String(changeSummary.value.active_page_count ?? 0) },
  { key: 'draft_pages', label: '草案发布页', value: String(changeSummary.value.draft_page_count ?? 0) },
  { key: 'delta', label: '差异', value: String(changeSummary.value.page_count_delta ?? 0) },
  {
    key: 'preview_hidden',
    label: '预览/下线',
    value: `${Number(changeSummary.value.preview_page_count ?? 0)} / ${Number(changeSummary.value.hidden_page_count ?? 0)}`,
  },
]);

const preflightItems = computed<CheckRow[]>(() => preflightChecks.value.map((check, index) => ({
  key: pipelineKey(check) || `check-${index + 1}`,
  label: String(check.label || check.key || '-'),
  message: String(check.message || '-'),
  status: String(check.status || 'pass'),
})));

const audienceItems = computed<DescriptionItem[]>(() => [
  { key: 'companies', label: '公司', value: String(audienceSimulation.value.company_count ?? 0) },
  { key: 'subscriptions', label: '订阅', value: String(audienceSimulation.value.subscription_count ?? 0) },
  { key: 'roles', label: '角色', value: audienceRoles.value },
]);

const controlDefinitionItems = computed<ListRow[]>(() => controlDefinitions.value.map((item, index) => ({
  key: definitionKey(item) || `definition-${index + 1}`,
  label: String(item.label || item.key || '-'),
  meta: String(item.meaning || '-'),
})));

const scopeItems = computed<DescriptionItem[]>(() => [
  {
    key: 'menus',
    label: copy.value.metric_controlled_menus || '受控菜单',
    value: String(controlScope.value.menu_count ?? 0),
  },
  {
    key: 'pages',
    label: copy.value.metric_controlled_pages || '受控页面',
    value: String(controlScope.value.page_count ?? controlScope.value.menu_count ?? 0),
  },
  {
    key: 'capabilities',
    label: copy.value.metric_controlled_capabilities || '受控能力',
    value: String(controlScope.value.capability_count ?? 0),
  },
]);

const historySnapshotItems = computed<ListRow[]>(() => historySnapshots.value.map((snapshot) => ({
  key: `history-snapshot-${snapshot.id}`,
  label: String(snapshot.version || snapshot.id),
  meta: String(snapshot.state || '-'),
})));

const historyActionItems = computed<ListRow[]>(() => historyActions.value.map((action) => ({
  key: `history-action-${action.id}`,
  label: String(action.action_type || action.id),
  meta: `${action.state || '-'} / ${action.approval_state || '-'}`,
})));

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
    not_configured: '未配置',
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
function stageStatusLabel(status: string) {
  const labels: Record<string, string> = {
    done: '已完成',
    active: '进行中',
    preview: '预览',
    pending: '待处理',
    warn: '警告',
    blocked: '阻断',
  };
  return labels[status] || status || '-';
}

function stageStatusSemantic(status: string): 'default' | 'info' | 'success' | 'warning' | 'danger' {
  if (status === 'done') return 'success';
  if (status === 'active' || status === 'preview') return 'info';
  if (status === 'warn') return 'warning';
  if (status === 'blocked') return 'danger';
  return 'default';
}

function checkStatusLabel(status: string) {
  const labels: Record<string, string> = {
    pass: '通过',
    warn: '警告',
    fail: '失败',
  };
  return labels[status] || status || '-';
}

function checkStatusSemantic(status: string): 'default' | 'info' | 'success' | 'warning' | 'danger' {
  if (status === 'pass') return 'success';
  if (status === 'warn') return 'warning';
  if (status === 'fail') return 'danger';
  return 'default';
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
  gap: var(--sc-product-workspace-stack-gap);
}

.release-operator__product-select {
  min-width: 220px;
}

.release-operator__section-meta {
  color: var(--sc-semantic-text-muted);
  font-size: var(--sc-product-text-sm);
}

.release-operator__metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: var(--sc-product-panel-gap);
}

.release-operator__metric h3 {
  margin: 0;
  color: var(--sc-semantic-text-muted);
  font-size: var(--sc-product-text-sm);
  font-weight: 500;
}

.release-operator__metric p {
  margin: var(--sc-product-space-1) 0 0;
  color: var(--sc-app-text-primary);
  font-size: 24px;
  font-weight: 600;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.release-operator__delivery {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--sc-product-panel-gap);
  margin-top: var(--sc-product-panel-gap);
}

.release-operator__list-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sc-product-space-2);
  width: 100%;
  min-width: 0;
}

.release-operator__list-label {
  min-width: 0;
  overflow-wrap: anywhere;
}

.release-operator__list-meta {
  flex: 0 0 auto;
  color: var(--sc-semantic-text-muted);
  font-size: var(--sc-product-text-sm);
}

.release-operator__list-meta--wrap {
  flex: 1 1 auto;
  text-align: right;
  overflow-wrap: anywhere;
}

.release-operator__stage {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr) max-content;
  align-items: center;
  gap: var(--sc-product-space-2);
  width: 100%;
}

.release-operator__stage strong {
  font-variant-numeric: tabular-nums;
}

.release-operator__check {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr) minmax(0, 1.3fr);
  align-items: center;
  gap: var(--sc-product-space-2);
  width: 100%;
}

.release-operator__check .release-operator__list-meta {
  flex: none;
}

.release-operator__summary {
  margin-top: var(--sc-product-panel-gap);
}

.release-operator__policy {
  margin-bottom: var(--sc-product-panel-gap);
}

.release-operator__history {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--sc-product-panel-gap);
}

.release-operator__table-card {
  margin-top: var(--sc-product-panel-gap);
}

@media (max-width: 900px) {
  .release-operator__metrics,
  .release-operator__delivery,
  .release-operator__history {
    grid-template-columns: 1fr;
  }

  .release-operator__stage,
  .release-operator__check {
    grid-template-columns: max-content minmax(0, 1fr);
  }

  .release-operator__stage strong,
  .release-operator__check .release-operator__list-meta {
    grid-column: 2;
    justify-self: start;
    text-align: left;
  }

  .release-operator__product-select {
    width: 100%;
    min-width: 0;
  }
}
</style>
