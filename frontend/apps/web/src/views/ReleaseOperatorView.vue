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
            :title="syncPolicyAction.reason_code || ''"
            @click="syncPolicy"
          >
            {{ copy.sync_policy_action_label || '同步已实现能力' }}
          </ScButton>
          <ScButton
            variant="primary"
            :disabled="busyKey === 'freeze' || !freezeAction.enabled"
            :title="freezeAction.reason_code || ''"
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

        <ScSection title="操作身份与影响范围">
          <ScDescriptions :items="operationScopeItems" :column="descriptionColumns" bordered />
          <ScInlineState
            v-if="operationReadback"
            state="success"
            :label="`权威回读：${operationReadback.product_key || '-'} · ${activeSnapshot.version || '无生效版本'} · 回滚目标 ${operationReadback.rollback_target_snapshot_id || '无'}`"
          />
        </ScSection>

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

        <ScSection
          title="业务场景组合"
          description="分别核对当前维护草稿、冻结候选和当前生效版本中的业务场景与原生入口。"
        >
          <template #actions>
            <ScButton
              variant="secondary"
              :disabled="!businessScenarioMaintenance.enabled"
              :title="businessScenarioMaintenance.reason_code || ''"
              @click="openBusinessScenarioMaintenance"
            >
              维护共享业务场景定义
            </ScButton>
          </template>
          <ScInlineState
            v-if="businessScenarioMaintenance.enabled"
            state="info"
            :label="`${businessScenarioMaintenance.scope.label}；将进入后冻结到 ${businessScenarioMaintenance.future_freeze_product_key}。该定义不是当前产品私有草案或当前企业配置。`"
          />
          <ScInlineState
            v-else
            state="error"
            :label="`共享业务场景维护入口不可用：${businessScenarioMaintenance.reason_code || '契约未声明'}${businessScenarioMaintenance.blockers.length ? `（${businessScenarioMaintenance.blockers.join('、')}）` : ''}`"
          />
          <div class="release-operator__composition-states">
            <ScCard
              v-for="state in compositionStateCards"
              :key="state.key"
              appearance="section"
              :title="state.title"
            >
              <ScDescriptions :items="state.items" :column="1" bordered />
              <ScInlineState
                v-if="state.state.empty"
                state="info"
                label="该状态存在组合载体，但当前没有业务场景。"
              />
              <ScInlineState
                v-else-if="!state.state.available"
                state="info"
                :label="state.state.reason_code"
              />
            </ScCard>
          </div>
          <ScForm layout="inline" :prevent-submit-default="true">
            <ScFormItem label="查看组合">
              <ScSelect
                v-model="selectedCompositionKey"
                :options="compositionStateOptions"
                aria-label="选择查看的业务组合状态"
              />
            </ScFormItem>
          </ScForm>
          <ScDescriptions
            class="release-operator__summary"
            :items="selectedCompositionItems"
            :column="compactDescriptionColumns"
            bordered
          />
          <ScDescriptions
            class="release-operator__summary"
            :items="compositionComparisonItems"
            :column="compactDescriptionColumns"
            bordered
          />
          <ScCard v-if="compositionEntryRows.length" appearance="table">
            <ScTable
              class="release-operator__table"
              label="业务场景组合入口"
              :data="compositionEntryRows"
              :columns="compositionEntryColumns"
              row-key="__rowKey"
              size="small"
            />
          </ScCard>
          <ScEmptyState
            v-else
            density="compact"
            :heading-level="4"
            title="当前查看状态没有业务场景入口"
          />
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
          <ScCard appearance="section" title="发布后回读">
            <ScDescriptions :items="operationReadbackItems" :column="compactDescriptionColumns" bordered />
          </ScCard>
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
                :title="updatePolicyAction.reason_code || ''"
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
          v-if="productCenterEditor"
          title="产品中心草案"
          description="中心名称、顺序和入口归属先保存为产品草案；发布产品版本后才影响正式导航。"
        >
          <template #actions>
            <span class="release-operator__section-meta">
              已发布 {{ productCenterEditor.published.version || '无版本' }} · 快照 {{ productCenterEditor.published.snapshot_id || '无' }}
            </span>
          </template>
          <ScInlineState
            state="info"
            :label="`当前操作范围：${String(productCenterEditor.operation_scope.product_key || productCenterEditor.product_key)} 的产品草案；企业场景启停仍按当前公司单独生效。`"
          />
          <ScForm layout="inline" :prevent-submit-default="true" class="release-operator__policy">
            <ScFormItem label="选择中心" name="product_center">
              <ScSelect
                :model-value="selectedCenterKey"
                :options="productCenterOptions"
                aria-label="选择产品中心"
                @update:model-value="selectCenter"
              />
            </ScFormItem>
            <ScFormItem label="中心名称" name="product_center_label">
              <ScInput
                v-model="centerLabelDraft"
                type="text"
                :maxlength="centerLabelMaxLength"
                :disabled="!selectedCenterKey || !centerLabelEditable"
                aria-label="产品中心名称"
              />
            </ScFormItem>
            <ScFormItem label="显示顺序" name="product_center_sequence">
              <ScInput
                v-model="centerSequenceDraft"
                type="number"
                :min="centerSequenceMinimum"
                :max="centerSequenceMaximum"
                :disabled="!selectedCenterKey || !centerSequenceEditable"
                aria-label="产品中心显示顺序"
              />
            </ScFormItem>
            <ScFormItem>
              <ScButton
                variant="primary"
                type="button"
                :disabled="centerSaveDisabled"
                :title="centerSaveReason"
                @click="saveProductCenterDraft"
              >
                保存产品中心草案
              </ScButton>
            </ScFormItem>
          </ScForm>
          <ScDescriptions
            class="release-operator__summary"
            :items="centerChangeItems"
            :column="compactDescriptionColumns"
            bordered
          />
          <ScCard v-if="selectedCenterEntries.length" appearance="table">
            <ScTable
              class="release-operator__table"
              label="入口所属中心"
              :data="centerEntryTableRows"
              :columns="centerEntryColumns"
              row-key="menu_xmlid"
              size="small"
            />
          </ScCard>
          <ScEmptyState
            v-else
            title="当前中心没有已发布入口"
            :heading-level="3"
            density="compact"
          />
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
              :title="rollbackAction.reason_code || ''"
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
    <IntentConfirmationDialog ref="promotionConfirmationRef" />
  </ScPage>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import StatusPanel from '../components/StatusPanel.vue';
import ScButton from '../components/design-system/ScButton.vue';
import ScEmptyState from '../components/design-system/ScEmptyState.vue';
import ScInput from '../components/design-system/ScInput.vue';
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
import IntentConfirmationDialog from '../components/business/IntentConfirmationDialog.vue';
import ProductPageHeader from '../components/product-page-header/ProductPageHeader.vue';
import DashboardPattern from '../components/product-page-patterns/DashboardPattern.vue';
import { useNarrowViewport } from '../composables/useNarrowViewport';
import { intentRequest } from '../api/intents';
import { usePageContract } from '../app/pageContract';
import { executePageContractAction } from '../app/pageContractActionRuntime';
import { contractGapError } from '../app/contract/contractGap';
import { buildBusinessScenarioMaintenanceTarget } from '../app/businessScenarioNavigation';
import {
  buildConfiguredOperatorParams,
  decodeConfiguredActionResult,
  decodeReleaseOperatorSurface,
  decodeProductCenterWriteEnvelope,
  type BusinessSceneCompositionState,
  type BusinessSceneCompositionStates,
  type BusinessScenarioMaintenance,
  type OperatorAction,
  type ProductCenterEditor,
} from '../app/releaseOperatorActionContract';

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
  approve_action?: OperatorAction;
}

interface ReleaseOperatorSurface {
  copy?: AnyRecord;
  identity?: AnyRecord;
  products?: ProductRow[];
  product_delivery_console?: AnyRecord;
  control_scope?: AnyRecord;
  product_center_editor?: ProductCenterEditor;
  business_scene_composition_states?: BusinessSceneCompositionStates;
  business_scenario_maintenance?: BusinessScenarioMaintenance;
  release_pipeline?: AnyRecord;
  release_state?: AnyRecord;
  pending_approval?: { actions?: ReleaseActionRow[] };
  candidate_snapshots?: SnapshotRow[];
  release_history?: { actions?: ReleaseActionRow[]; snapshots?: SnapshotRow[] };
  actor_scope?: AnyRecord;
  available_actions?: AnyRecord;
  operation_readback?: {
    product_key?: string;
    active_snapshot?: AnyRecord;
    draft?: AnyRecord;
    change_summary?: AnyRecord;
    rollback_target_snapshot_id?: number;
    audience?: AnyRecord;
  };
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
const promotionConfirmationRef = ref<InstanceType<typeof IntentConfirmationDialog> | null>(null);

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
const actionSelectOptions = (action: OperatorAction | null | undefined, key: string) => (
  action?.editable_fields?.find((field) => field.key === key)?.options || []
);
const policyStateOptions = computed(() => (
  actionSelectOptions(updatePolicyAction.value, 'state')
));
const policyAccessOptions = computed(() => (
  actionSelectOptions(updatePolicyAction.value, 'access_level')
));
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
const productCenterEditor = computed(() => surface.value?.product_center_editor || null);
const businessSceneCompositionStates = computed(() => (
  surface.value?.business_scene_composition_states || null
));
const businessScenarioMaintenance = computed<BusinessScenarioMaintenance>(() => (
  surface.value?.business_scenario_maintenance
  || {
    contract_version: 'business_scenario_maintenance_entry.v1',
    product_key: String(identity.value.product_key || ''),
    applicable: false,
    provider: '',
    enabled: false,
    reason_code: 'SCENARIO_MAINTENANCE_CONTRACT_MISSING',
    blockers: ['SCENARIO_MAINTENANCE_CONTRACT_MISSING'],
    action: { xmlid: '', id: 0, name: '', res_model: '', view_mode: '' },
    menu: { xmlid: '', id: 0, name: '' },
    scope: {
      kind: 'not_applicable',
      label: '共享业务场景定义不可用',
      model: '',
      has_product_key: false,
      has_company_id: false,
      applies_to: '',
      filter_by_current_product: false,
    },
    future_freeze_product_key: String(identity.value.product_key || ''),
    access: { read_allowed: false, write_allowed: false },
    return_readback: {
      intent: '',
      product_key: String(identity.value.product_key || ''),
      fields: [],
    },
  }
));
const selectedCompositionKey = ref<'draft' | 'candidate' | 'active'>('draft');
const compositionStateOptions = [
  { value: 'draft', label: '当前维护草稿' },
  { value: 'candidate', label: '冻结候选' },
  { value: 'active', label: '当前生效版本' },
];
const selectedCompositionState = computed<BusinessSceneCompositionState | null>(() => (
  businessSceneCompositionStates.value?.[selectedCompositionKey.value] || null
));
const compositionStateCards = computed(() => {
  const states = businessSceneCompositionStates.value;
  if (!states) return [];
  return [
    { key: 'draft', title: '当前维护草稿', state: states.draft },
    { key: 'candidate', title: '冻结候选', state: states.candidate },
    { key: 'active', title: '当前生效版本', state: states.active },
  ].map((row) => ({
    ...row,
    items: [
      { key: 'status', label: '状态', value: row.state.status_label },
      {
        key: 'identity',
        label: '版本身份',
        value: row.state.identity.snapshot_id
          ? `快照 ${String(row.state.identity.snapshot_id)} · ${String(row.state.identity.version || '-')}`
          : `策略 ${String(row.state.identity.policy_id || '-')} · ${String(row.state.identity.version || '-')}`,
      },
      {
        key: 'counts',
        label: '组合规模',
        value: `${row.state.scenario_count} 个场景 / ${row.state.entry_count} 个入口`,
      },
      {
        key: 'digest',
        label: '组合摘要',
        value: row.state.digest || row.state.reason_code,
      },
    ],
  }));
});
const selectedCompositionItems = computed<DescriptionItem[]>(() => {
  const state = selectedCompositionState.value;
  if (!state) return [];
  return [
    { key: 'state', label: '查看状态', value: state.status_label },
    { key: 'reason', label: '状态说明', value: state.reason_code },
    { key: 'source_db', label: '组合来源库', value: state.source_db || '-' },
    { key: 'scope', label: '组合作用域', value: state.runtime_scope || '-' },
    { key: 'scenario_count', label: '场景数量', value: String(state.scenario_count) },
    { key: 'entry_count', label: '入口数量', value: String(state.entry_count) },
  ];
});
const compositionComparisonItems = computed<DescriptionItem[]>(() => {
  const comparisons = businessSceneCompositionStates.value?.comparisons;
  if (!comparisons) return [];
  const rows = [
    ['draft_vs_candidate', '草稿相对候选', comparisons.draft_vs_candidate],
    ['draft_vs_active', '草稿相对生效', comparisons.draft_vs_active],
    ['candidate_vs_active', '候选相对生效', comparisons.candidate_vs_active],
  ] as const;
  return rows.map(([key, label, diff]) => ({
    key,
    label,
    value: `${diff.state} · 变化 ${diff.change_count} 项 · 场景 ${diff.changed_scenario_keys.join('、') || '无'} · 入口 ${diff.changed_entry_keys.join('、') || '无'}`,
  }));
});
const compositionEntryRows = computed(() => {
  const rows: Array<AnyRecord & { __rowKey: string }> = [];
  for (const scenario of selectedCompositionState.value?.scenarios || []) {
    for (const entry of scenario.entries) {
      rows.push({
        ...entry,
        scenario_key: scenario.key,
        scenario_name: scenario.name,
        scenario_sequence: scenario.sequence,
        scenario_active: scenario.active,
        __rowKey: `${scenario.key}:${entry.entry_id}:${entry.menu_key}:${entry.intent}`,
      });
    }
  }
  return rows;
});
const selectedCenterKey = ref('');
const centerLabelDraft = ref('');
const centerSequenceDraft = ref('10');
const entryPlacementDraft = ref<Record<string, string>>({});
const productCenterOptions = computed(() => (productCenterEditor.value?.centers || []).map((center) => ({
  value: center.center_key,
  label: `${center.label} · ${Number(center.sequence)}`,
})));
const selectedCenter = computed(() => (
  productCenterEditor.value?.centers.find((center) => center.center_key === selectedCenterKey.value)
  || null
));
const selectedCenterEntries = computed(() => (
  (productCenterEditor.value?.entries || []).filter(
    (entry) => entry.center_key === selectedCenterKey.value,
  )
));
const centerField = (key: string) => (
  productCenterEditor.value?.editable_fields.find((field) => field.key === key) || null
);
const centerLabelField = computed(() => centerField('label'));
const centerSequenceField = computed(() => centerField('sequence'));
const centerLabelEditable = computed(() => Boolean(
  selectedCenter.value?.editable_fields.includes('label'),
));
const centerSequenceEditable = computed(() => Boolean(
  selectedCenter.value?.editable_fields.includes('sequence'),
));
const centerLabelMaxLength = computed(() => centerLabelField.value?.max_length || 1);
const centerSequenceMinimum = computed(() => centerSequenceField.value?.minimum ?? 0);
const centerSequenceMaximum = computed(() => centerSequenceField.value?.maximum ?? 0);
const changedCenterPlacements = computed(() => (
  (productCenterEditor.value?.entries || []).filter(
    (entry) => (entryPlacementDraft.value[entry.menu_xmlid] || entry.center_key) !== entry.center_key,
  )
));
const centerDraftChanged = computed(() => {
  const center = selectedCenter.value;
  if (!center) return false;
  return centerLabelDraft.value.trim() !== center.label
    || Number(centerSequenceDraft.value) !== Number(center.sequence);
});
const centerDraftValid = computed(() => {
  const sequence = Number(centerSequenceDraft.value);
  const label = centerLabelDraft.value.trim();
  return (!centerLabelField.value?.required || Boolean(label))
    && label.length <= centerLabelMaxLength.value
    && Number.isInteger(sequence)
    && sequence >= centerSequenceMinimum.value
    && sequence <= centerSequenceMaximum.value;
});
const centerSaveDisabled = computed(() => (
  busyKey.value === 'update_policy'
  || !productCenterEditor.value?.save_action.enabled
  || !selectedCenter.value
  || !centerDraftValid.value
  || (!centerDraftChanged.value && !changedCenterPlacements.value.length)
));
const centerSaveReason = computed(() => {
  if (!productCenterEditor.value) return '产品中心契约缺失';
  if (!selectedCenter.value) return '请选择中心';
  if (!centerDraftValid.value) {
    return `中心名称必须为 1–${centerLabelMaxLength.value} 个字符，显示顺序必须在 ${centerSequenceMinimum.value}–${centerSequenceMaximum.value} 之间`;
  }
  if (!productCenterEditor.value.save_action.enabled) {
    return productCenterEditor.value.save_action.reason_code || '保存动作不可用';
  }
  if (!centerDraftChanged.value && !changedCenterPlacements.value.length) return '没有待保存的中心修改';
  return '';
});
const centerChangeItems = computed<DescriptionItem[]>(() => {
  const editor = productCenterEditor.value;
  const summary = (editor?.change_summary || {}) as AnyRecord;
  const center = selectedCenter.value;
  return [
    {
      key: 'center_scope',
      label: '当前中心',
      value: center
        ? `${center.label} · ${center.center_key}`
        : '请选择中心',
    },
    {
      key: 'published_center',
      label: '已发布值',
      value: center
        ? `${center.published_label || '未发布'} · ${center.published_sequence || 0}`
        : '-',
    },
    {
      key: 'draft_changes',
      label: '草案差异',
      value: `中心 ${Number(summary.changed_center_count || 0)} 个 / 入口归属 ${Number(summary.changed_entry_placement_count || 0)} 个`,
    },
    {
      key: 'entry_count',
      label: '当前中心入口',
      value: `${selectedCenterEntries.value.length}`,
    },
  ];
});
const controlDefinitions = computed(() => {
  const items = controlScope.value.control_definition;
  return Array.isArray(items) ? items as AnyRecord[] : [];
});
const releaseState = computed(() => surface.value?.release_state || {});
const activeSnapshot = computed(() => (releaseState.value.active_snapshot || {}) as AnyRecord);
const actorScope = computed(() => surface.value?.actor_scope || {});
const operationReadback = computed(() => surface.value?.operation_readback ?? null);
const runtimeSummary = computed(() => (releaseState.value.runtime_summary || {}) as AnyRecord);
const candidateSnapshots = computed(() => surface.value?.candidate_snapshots || []);
const pendingActions = computed(() => surface.value?.pending_approval?.actions || []);
const historySnapshots = computed(() => surface.value?.release_history?.snapshots || []);
const historyActions = computed(() => surface.value?.release_history?.actions || []);
const rollbackAction = computed(() => {
  const actions = surface.value?.available_actions || {};
  return (actions.rollback || {}) as OperatorAction;
});
const syncPolicyAction = computed(() => {
  const actions = surface.value?.available_actions || {};
  return (actions.sync_policy || {}) as OperatorAction;
});
const updatePolicyAction = computed(() => {
  const actions = surface.value?.available_actions || {};
  return (actions.update_policy || {}) as OperatorAction;
});
const updatePagePolicyAction = computed(() => {
  const actions = surface.value?.available_actions || {};
  return (actions.update_page_policy || {}) as OperatorAction;
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

const freezeAction = computed(() => {
  const actions = surface.value?.available_actions || {};
  return (actions.freeze || {}) as OperatorAction;
});

const operationScopeItems = computed<DescriptionItem[]>(() => [
  {
    key: 'actor',
    label: '操作者',
    value: `${String(actorScope.value.name || actorScope.value.login || '—')} (${String(actorScope.value.login || actorScope.value.user_id || '—')})`,
  },
  {
    key: 'operator_kind',
    label: '操作者类型',
    value: String(actorScope.value.operator_kind || '—'),
  },
  {
    key: 'roles',
    label: '发布角色',
    value: Array.isArray(actorScope.value.roles) && actorScope.value.roles.length
      ? actorScope.value.roles.map(String).join(', ')
      : '未返回角色',
  },
  {
    key: 'target_scope',
    label: '目标范围',
    value: String(operationReadback.value?.product_key || identity.value.product_key || '—'),
  },
  {
    key: 'scope_meaning',
    label: '影响范围',
    value: String((freezeAction.value.target_scope || {}).meaning || '—'),
  },
]);

const operationReadbackItems = computed<DescriptionItem[]>(() => [
  {
    key: 'readback_product',
    label: '产品',
    value: String(operationReadback.value?.product_key || '—'),
  },
  {
    key: 'readback_version',
    label: '当前生效版本',
    value: String(operationReadback.value?.active_snapshot?.version || activeSnapshot.value.version || '无'),
  },
  {
    key: 'readback_state',
    label: '版本状态',
    value: String(operationReadback.value?.active_snapshot?.state || '—'),
  },
  {
    key: 'readback_rollback',
    label: '回滚目标',
    value: String(operationReadback.value?.rollback_target_snapshot_id || '无'),
  },
  {
    key: 'readback_draft',
    label: '草案页数',
    value: String(operationReadback.value?.draft?.page_count ?? '—'),
  },
  {
    key: 'readback_delta',
    label: '页面差异',
    value: String(operationReadback.value?.change_summary?.page_count_delta ?? '—'),
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
function actionNode(
  label: string,
  disabled: boolean,
  onClick: () => void,
  variant: 'primary'|'ghost' = 'ghost',
  title = '',
) {
  return h(ScButton, { variant, size: 'small', disabled, onClick, title }, () => label);
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
  { colKey: 'actions', title: '操作', width: 260, cell: (_h: unknown, { row }: { row: AnyRecord }) => {
    const releaseOptions = actionSelectOptions(updatePagePolicyAction.value, 'release_state');
    const accessOptions = actionSelectOptions(updatePagePolicyAction.value, 'access_level');
    const releaseOption = (value: string) => releaseOptions.find(option => option.value === value);
    const accessOption = (value: string) => accessOptions.find(option => option.value === value);
    const actions = [
      ...(releaseOption('released') ? [actionNode(releaseOption('released')!.label, busyKey.value === `page:${pageKey(row)}:released` || !updatePagePolicyAction.value.enabled, () => updatePagePolicy(row, { release_state: 'released', enabled: true }), 'ghost', updatePagePolicyAction.value.reason_code || '')] : []),
      ...(releaseOption('preview') ? [actionNode(releaseOption('preview')!.label, busyKey.value === `page:${pageKey(row)}:preview` || !updatePagePolicyAction.value.enabled, () => updatePagePolicy(row, { release_state: 'preview', enabled: true }), 'ghost', updatePagePolicyAction.value.reason_code || '')] : []),
      ...(releaseOption('hidden') ? [actionNode(releaseOption('hidden')!.label, busyKey.value === `page:${pageKey(row)}:hidden` || !updatePagePolicyAction.value.enabled, () => updatePagePolicy(row, { release_state: 'hidden', enabled: false }), 'ghost', updatePagePolicyAction.value.reason_code || '')] : []),
    ];
    const targetAccess = row.access_level === 'internal' ? 'public' : 'internal';
    if (accessOption(targetAccess)) {
      actions.push(actionNode(
        accessOption(targetAccess)!.label,
        busyKey.value === `page:${pageKey(row)}:${targetAccess}` || !updatePagePolicyAction.value.enabled,
        () => updatePagePolicy(row, { access_level: targetAccess }),
        'ghost',
        updatePagePolicyAction.value.reason_code || '',
      ));
    }
    return h('div', { class: 'release-operator__row-actions' }, actions);
  } },
]);
const centerEntryTableRows = computed(() => selectedCenterEntries.value.map((entry) => ({
  ...entry,
  target_center_key: entryPlacementDraft.value[entry.menu_xmlid] || entry.center_key,
})));
const centerEntryColumns = computed(() => [
  {
    colKey: 'label',
    title: '入口',
    ellipsis: true,
    cell: (_h: unknown, { row }: { row: AnyRecord }) => tableText(row.label || row.menu_xmlid),
  },
  {
    colKey: 'published',
    title: '已发布归属',
    cell: (_h: unknown, { row }: { row: AnyRecord }) => tableText(row.published_center_label || '未发布'),
  },
  {
    colKey: 'target',
    title: '草案归属',
    width: 220,
    cell: (_h: unknown, { row }: { row: AnyRecord }) => h(ScSelect, {
      modelValue: String(row.target_center_key || ''),
      options: productCenterOptions.value,
      'aria-label': `设置 ${String(row.label || row.menu_xmlid)} 所属中心`,
      'onUpdate:modelValue': (value: unknown) => {
        entryPlacementDraft.value = {
          ...entryPlacementDraft.value,
          [String(row.menu_xmlid)]: String(value || ''),
        };
      },
    }),
  },
  {
    colKey: 'changed',
    title: '状态',
    cell: (_h: unknown, { row }: { row: AnyRecord }) => {
      const changed = String(row.target_center_key || '') !== String(row.center_key || '');
      return statusNode(changed ? 'changed' : 'saved', changed ? '草案已改' : '与草案一致', changed ? 'warning' : 'default');
    },
  },
]);
const compositionEntryColumns = computed(() => [
  {
    colKey: 'scenario_name',
    title: '业务场景',
    cell: (_h: unknown, { row }: { row: AnyRecord }) => tableText(
      `${String(row.scenario_name || row.scenario_key)} · ${Number(row.scenario_sequence || 0)}`,
    ),
  },
  {
    colKey: 'scenario_active',
    title: '定义状态',
    cell: (_h: unknown, { row }: { row: AnyRecord }) => statusNode(
      row.scenario_active ? 'active' : 'inactive',
      row.scenario_active ? '启用' : '停用',
      row.scenario_active ? 'success' : 'default',
    ),
  },
  {
    colKey: 'menu_key',
    title: '原生入口',
    ellipsis: true,
    cell: (_h: unknown, { row }: { row: AnyRecord }) => tableText(row.menu_key),
  },
  {
    colKey: 'intent_label',
    title: '业务用途',
    cell: (_h: unknown, { row }: { row: AnyRecord }) => tableText(row.intent_label || row.intent),
  },
  {
    colKey: 'sequence',
    title: '入口顺序',
    cell: (_h: unknown, { row }: { row: AnyRecord }) => tableText(row.sequence),
  },
  {
    colKey: 'source_db',
    title: '来源库',
    cell: (_h: unknown, { row }: { row: AnyRecord }) => tableText(row.source_db),
  },
]);
const candidateColumns = computed(() => [
  { colKey: 'version', title: '版本', cell: (_h: unknown, { row }: { row: SnapshotRow }) => tableText(row.version) },
  { colKey: 'state', title: '状态', cell: (_h: unknown, { row }: { row: SnapshotRow }) => statusNode(String(row.state || ''), tableText(row.state), 'info') },
  { colKey: 'channel', title: '通道', cell: (_h: unknown, { row }: { row: SnapshotRow }) => tableText(row.channel) },
  { colKey: 'draft', title: '草案范围', cell: (_h: unknown, { row }: { row: SnapshotRow }) => snapshotDraftLabel(row) },
  { colKey: 'diff', title: '差异', cell: (_h: unknown, { row }: { row: SnapshotRow }) => snapshotDiffLabel(row) },
  { colKey: 'gate', title: '门禁', cell: (_h: unknown, { row }: { row: SnapshotRow }) => {
    const action = promoteActionFor(row);
    return statusNode(candidateReady(row) ? 'ready' : action?.reason_code || 'blocked', candidateReady(row) ? '可发布产品版本' : action?.reason_code || '后端未返回可发布动作', candidateReady(row) ? 'success' : 'danger');
  } },
  { colKey: 'contract', title: '发布契约', cell: (_h: unknown, { row }: { row: SnapshotRow }) => {
    const action = promoteActionFor(row);
    if (!action) return tableText('契约缺口');
    const confirmation = action.prerequisites.confirmation_required ? '需确认' : '无需确认';
    return tableText(`${action.actor.login} 至 ${action.target_scope.product_key} · ${confirmation}`);
  } },
  { colKey: 'frozen_at', title: '冻结时间', cell: (_h: unknown, { row }: { row: SnapshotRow }) => tableText(row.frozen_at) },
  { colKey: 'actions', title: '操作', width: 132, cell: (_h: unknown, { row }: { row: SnapshotRow }) => {
    const action = promoteActionFor(row);
    return actionNode(action?.label || '发布产品版本', busyKey.value === (action?.key || `promote:${row.id}`) || !candidateReady(row), () => promote(row), 'primary', action?.reason_code || '');
  } },
]);
const pendingActionColumns = computed(() => [
  { colKey: 'action_type', title: '动作', cell: (_h: unknown, { row }: { row: ReleaseActionRow }) => tableText(row.action_type) },
  { colKey: 'product_key', title: '产品', cell: (_h: unknown, { row }: { row: ReleaseActionRow }) => tableText(row.product_key) },
  { colKey: 'approval_state', title: '审批', cell: (_h: unknown, { row }: { row: ReleaseActionRow }) => statusNode(String(row.approval_state || ''), tableText(row.approval_state), 'warning') },
  { colKey: 'requested_at', title: '请求时间', cell: (_h: unknown, { row }: { row: ReleaseActionRow }) => tableText(row.requested_at) },
  { colKey: 'actions', title: '操作', width: 128, cell: (_h: unknown, { row }: { row: ReleaseActionRow }) => actionNode(copy.value.approve_action_label || '审批并执行', busyKey.value === `approve:${row.id}` || row.approve_action?.enabled !== true, () => approve(row), 'primary', row.approve_action?.reason_code || '') },
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
const promoteActions = computed<OperatorAction[]>(() => {
  const actions = surface.value?.available_actions || {};
  return Array.isArray(actions.promote) ? actions.promote as OperatorAction[] : [];
});
function promoteActionFor(snapshot: SnapshotRow) {
  return promoteActions.value.find((action) => (
    Number(action.params?.snapshot_id || 0) === Number(snapshot.id)
  ));
}
function candidateReady(snapshot: SnapshotRow) {
  return promoteActionFor(snapshot)?.enabled === true;
}
function hydratePolicyControls(payload: ReleaseOperatorSurface) {
  const scope = payload.control_scope || {};
  policyState.value = String(scope.policy_state || 'stable');
  policyAccessLevel.value = String(scope.access_level || 'public');
}

function hydrateProductCenterEditor(payload: ReleaseOperatorSurface) {
  const editor = payload.product_center_editor;
  if (!editor) {
    selectedCenterKey.value = '';
    centerLabelDraft.value = '';
    centerSequenceDraft.value = '10';
    entryPlacementDraft.value = {};
    return;
  }
  const centers = editor.centers || [];
  const selected = centers.find((center) => center.center_key === selectedCenterKey.value) || centers[0];
  selectedCenterKey.value = selected?.center_key || '';
  centerLabelDraft.value = selected?.label || '';
  centerSequenceDraft.value = String(selected?.sequence ?? 10);
  entryPlacementDraft.value = Object.fromEntries(
    (editor.entries || []).map((entry) => [entry.menu_xmlid, entry.center_key]),
  );
}

function selectCenter(value: unknown) {
  const key = String(value || '').trim();
  selectedCenterKey.value = key;
  const center = productCenterEditor.value?.centers.find((row) => row.center_key === key);
  centerLabelDraft.value = center?.label || '';
  centerSequenceDraft.value = String(center?.sequence ?? 10);
}

async function openBusinessScenarioMaintenance() {
  const entry = businessScenarioMaintenance.value;
  const target = buildBusinessScenarioMaintenanceTarget(entry, route.fullPath);
  if (target) await router.push(target);
}

async function syncResolvedProduct(decoded: ReleaseOperatorSurface) {
  const resolvedProduct = String(decoded.identity?.product_key || '').trim();
  if (!resolvedProduct) return;
  selectedProduct.value = resolvedProduct;
  const routeProduct = String(route.query.product_key || '').trim();
  if (resolvedProduct === routeProduct) return;
  await router.replace({
    query: {
      ...route.query,
      product_key: resolvedProduct,
    },
  });
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
    const decoded = decodeReleaseOperatorSurface(
      payload as unknown as AnyRecord,
    ) as unknown as ReleaseOperatorSurface;
    surface.value = decoded;
    hydratePolicyControls(decoded);
    hydrateProductCenterEditor(decoded);
    await syncResolvedProduct(decoded);
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
      const decoded = decodeReleaseOperatorSurface(
        result.surface as unknown as AnyRecord,
      ) as unknown as ReleaseOperatorSurface;
      surface.value = decoded;
      hydratePolicyControls(decoded);
      hydrateProductCenterEditor(decoded);
      await syncResolvedProduct(decoded);
    } else {
      await loadSurface();
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '发布动作执行失败';
  } finally {
    busyKey.value = '';
  }
}

async function runConfiguredAction(
  action: OperatorAction | null | undefined,
  overrides: AnyRecord,
  busy: string,
  confirmationMessage = '',
) {
  if (!action || !action.enabled) return;
  if (
    action.prerequisites.confirmation_required
  ) {
    const confirmed = await promotionConfirmationRef.value?.confirm({
      actionLabel: action.label,
      message: confirmationMessage || `确认执行平台动作“${action.label}”？`,
    });
    if (!confirmed) return;
  }
  busyKey.value = busy;
  error.value = '';
  try {
    const params = buildConfiguredOperatorParams(action, overrides);
    const result = await intentRequest<AnyRecord>({
      intent: action.intent,
      params,
    });
    const writeReadback = decodeConfiguredActionResult(
      result,
      action,
      action.target_scope.product_key,
    );
    const decoded = decodeReleaseOperatorSurface(
      writeReadback.surface,
    ) as unknown as ReleaseOperatorSurface;
    if (
      String(decoded.identity?.product_key || '')
      !== action.target_scope.product_key
    ) {
      throw contractGapError({
        kind: 'contract_defect',
        missing: `${action.key}.readback.product_key`,
        requiredDeclarationLayer: 'P0:smart_core:platform_management_action_contract',
      }, `平台动作 ${action.key} 的回读产品与执行对象不一致`);
    }
    surface.value = decoded;
    hydratePolicyControls(decoded);
    hydrateProductCenterEditor(decoded);
    await syncResolvedProduct(decoded);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '平台管理动作执行失败';
  } finally {
    busyKey.value = '';
  }
}

function centerWriteText(value: unknown, path: string): string {
  const result = String(value || '').trim();
  if (!result) {
    throw contractGapError({
      kind: 'contract_defect',
      missing: path,
      requiredDeclarationLayer: 'P0:smart_core:product_center_editor',
    }, `产品中心保存回读缺少 ${path}`);
  }
  return result;
}

function assertCenterWriteReadback(
  result: AnyRecord,
  editor: ProductCenterEditor,
  centerUpdates: AnyRecord[],
  entryPlacements: AnyRecord[],
) {
  const envelope = decodeProductCenterWriteEnvelope(result, editor);
  const { policy, readback } = envelope;
  if (String(policy.product_key || '') !== editor.product_key) {
    throw contractGapError({
      kind: 'contract_defect',
      missing: 'product_center_write.policy.product_key',
      requiredDeclarationLayer: 'P0:smart_core:product_center_editor',
    }, '产品中心保存回读的产品与本次提交不一致');
  }
  const groups = Array.isArray(policy.menu_groups) ? policy.menu_groups : [];
  for (const update of centerUpdates) {
    const group = groups.find((row) => (
      row && typeof row === 'object'
      && String((row as AnyRecord).center_key || (row as AnyRecord).group_key || '') === String(update.center_key)
    )) as AnyRecord | undefined;
    if (!group
      || String(group.group_label || group.label || '') !== String(update.label)
      || Number(group.sequence) !== Number(update.sequence)) {
      throw contractGapError({
        kind: 'contract_defect',
        missing: 'product_center_write.policy.center_update',
        requiredDeclarationLayer: 'P0:smart_core:product_center_editor',
      }, '产品中心保存回读未包含本次中心修改');
    }
  }
  for (const placement of entryPlacements) {
    const group = groups.find((row) => (
      row && typeof row === 'object'
      && Array.isArray((row as AnyRecord).menus)
      && ((row as AnyRecord).menus as unknown[]).some((menu) => (
        menu && typeof menu === 'object'
        && String((menu as AnyRecord).menu_xmlid || (menu as AnyRecord).menu_key || '') === String(placement.menu_xmlid)
      ))
    )) as AnyRecord | undefined;
    if (!group
      || String(group.center_key || group.group_key || '') !== String(placement.center_key)) {
      throw contractGapError({
        kind: 'contract_defect',
        missing: 'product_center_write.policy.entry_placement',
        requiredDeclarationLayer: 'P0:smart_core:product_center_editor',
      }, '产品中心保存回读未包含本次入口归属');
    }
  }
  if (String(readback.product_key || '') !== editor.product_key) {
    throw contractGapError({
      kind: 'contract_defect',
      missing: 'product_center_write.readback.product_key',
      requiredDeclarationLayer: 'P0:smart_core:product_center_editor',
    }, '产品中心保存回读的产品身份与本次提交不一致');
  }
  centerWriteText(readback.draft_policy_sha256, 'product_center_write.readback.draft_policy_sha256');
  centerWriteText(readback.draft_fingerprint, 'product_center_write.readback.draft_fingerprint');
  if (typeof readback.published_version !== 'string') {
    throw contractGapError({
      kind: 'contract_defect',
      missing: 'product_center_write.readback.published_version',
      requiredDeclarationLayer: 'P0:smart_core:product_center_editor',
    }, '产品中心保存回读缺少发布版本声明');
  }
}

async function runCenterWrite(
  editor: ProductCenterEditor,
  params: AnyRecord,
  centerUpdates: AnyRecord[],
  entryPlacements: AnyRecord[],
) {
  busyKey.value = 'update_policy';
  error.value = '';
  try {
    const result = await intentRequest<AnyRecord>({
      intent: editor.save_action.intent,
      params,
    });
    assertCenterWriteReadback(result, editor, centerUpdates, entryPlacements);
    const envelope = decodeProductCenterWriteEnvelope(result, editor);
    const decoded = decodeReleaseOperatorSurface(
      envelope.surface,
    ) as unknown as ReleaseOperatorSurface;
    if (String(decoded.identity?.product_key || '') !== editor.product_key) {
      throw contractGapError({
        kind: 'contract_defect',
        missing: 'product_center_write.surface.identity.product_key',
        requiredDeclarationLayer: 'P0:smart_core:product_center_editor',
      }, '产品中心保存返回的 surface 属于另一产品');
    }
    surface.value = decoded;
    hydratePolicyControls(decoded);
    hydrateProductCenterEditor(decoded);
    await syncResolvedProduct(decoded);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '产品中心保存失败';
  } finally {
    busyKey.value = '';
  }
}

async function promote(snapshot: SnapshotRow) {
  const action = promoteActionFor(snapshot);
  if (!action || !action.enabled) return;
  if (action.prerequisites.confirmation_required) {
    const confirmed = await promotionConfirmationRef.value?.confirm({
      actionLabel: action.label,
      message: `确认将候选快照 ${action.params.snapshot_id} 发布为产品版本？`
        + ` 操作者 ${action.actor.login}，影响产品 ${action.target_scope.product_key}。`,
    });
    if (!confirmed) return;
  }
  await runWrite(action.intent, action.params, action.key);
}

function approve(action: ReleaseActionRow) {
  void runConfiguredAction(
    action.approve_action,
    {},
    `approve:${action.id}`,
    `确认审批并执行发布申请 ${action.id}？`,
  );
}

function freeze() {
  void runConfiguredAction(freezeAction.value, {}, 'freeze');
}

function syncPolicy() {
  void runConfiguredAction(syncPolicyAction.value, {}, 'sync_policy');
}

function savePolicy() {
  void runConfiguredAction(
    updatePolicyAction.value,
    {
      state: policyState.value,
      access_level: policyAccessLevel.value,
    },
    'update_policy',
  );
}

async function saveProductCenterDraft() {
  const editor = productCenterEditor.value;
  const center = selectedCenter.value;
  if (!editor || !center || centerSaveDisabled.value) return;
  if (editor.save_action.confirmation_required) {
    const confirmed = await promotionConfirmationRef.value?.confirm({
      actionLabel: '保存产品中心草案',
      message: `确认将中心 ${center.label} 的修改保存为产品 ${editor.product_key} 的草案？`,
    });
    if (!confirmed) return;
  }
  const centerUpdates = centerDraftChanged.value
    ? [{
      center_key: center.center_key,
      label: centerLabelDraft.value.trim(),
      sequence: Number(centerSequenceDraft.value),
    }]
    : [];
  const entryPlacements = changedCenterPlacements.value.map((entry) => ({
    menu_xmlid: entry.menu_xmlid,
    center_key: entryPlacementDraft.value[entry.menu_xmlid],
  }));
  void runCenterWrite(
    editor,
    {
      ...editor.save_action.params,
      product_key: editor.product_key,
      center_updates: centerUpdates,
      entry_placements: entryPlacements,
    },
    centerUpdates,
    entryPlacements,
  );
}

function updatePagePolicy(page: AnyRecord, updates: AnyRecord) {
  const key = pageKey(page);
  if (!key) return;
  const state = String(updates.release_state || updates.access_level || 'update');
  void runConfiguredAction(
    updatePagePolicyAction.value,
    {
      page_key: key,
      ...updates,
    },
    `page:${key}:${state}`,
  );
}

function rollback() {
  void runConfiguredAction(
    rollbackAction.value,
    {},
    'rollback',
    `确认回滚产品 ${rollbackAction.value.target_scope.product_key} 到快照 ${rollbackAction.value.params.target_snapshot_id}？`,
  );
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

.release-operator__composition-states {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--sc-product-panel-gap);
  margin-block: var(--sc-product-space-3);
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
