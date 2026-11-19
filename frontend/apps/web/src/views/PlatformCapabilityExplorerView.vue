<template>
  <ScPage
    class="capability-explorer"
    content-layout="data-grid"
    data-semantic-component="PlatformCapabilityExplorerView"
    :data-state="loading && !catalog ? 'loading' : error ? 'error' : rows.length ? 'ready' : 'empty'"
  >
    <header v-if="pageSectionEnabled('header', true)" class="capability-explorer__header">
      <div>
        <p class="capability-explorer__eyebrow">{{ pageText('eyebrow', '') }}</p>
        <h1>{{ pageText('title', '') }}</h1>
        <p>{{ pageText('description', '') }}</p>
      </div>
      <div class="capability-explorer__header-actions">
        <span v-if="catalog" class="capability-explorer__token" :title="catalog.meta.catalog_token">
          目录 {{ shortToken(catalog.meta.catalog_token) }}
        </span>
        <ScButton type="button" variant="secondary" :loading="loading" @click="reloadFromCurrentPage">刷新目录</ScButton>
      </div>
    </header>

    <ScInlineState
      v-if="staleNotice"
      state="info"
      label="运行时目录已变化，旧 token 已失效；页面正在重新读取同一逻辑快照。"
    />
    <ScInlineState v-if="error" state="error" :label="error">
      <template #actions><ScButton type="button" variant="secondary" @click="reloadFromFirstPage">重新加载</ScButton></template>
    </ScInlineState>

    <section
      v-if="pageSectionEnabled('metrics', true)"
      class="capability-explorer__metrics"
      aria-label="当前能力目录概览"
    >
      <ScCard appearance="metric">
        <p class="capability-explorer__metric-label">当前原生入口</p>
        <strong class="capability-explorer__metric-value">{{ catalog?.meta.total ?? '—' }}</strong>
      </ScCard>
      <ScCard appearance="metric">
        <p class="capability-explorer__metric-label">已有场景绑定</p>
        <strong class="capability-explorer__metric-value">{{ catalog?.facets.scene_status.bound ?? '—' }}</strong>
      </ScCard>
      <ScCard appearance="metric">
        <p class="capability-explorer__metric-label">尚未场景化</p>
        <strong class="capability-explorer__metric-value">{{ catalog?.facets.scene_status.unbound ?? '—' }}</strong>
      </ScCard>
      <ScCard appearance="metric">
        <p class="capability-explorer__metric-label">原生业务中心</p>
        <strong class="capability-explorer__metric-value">{{ catalog?.facets.centers.length ?? '—' }}</strong>
      </ScCard>
    </section>

    <section
      v-if="pageSectionEnabled('filters', true)"
      class="capability-explorer__toolbar"
      aria-label="能力入口筛选"
    >
      <ScInput
        v-model="queryDraft"
        type="search"
        appearance="collection-search"
        clearable
        aria-label="搜索业务入口"
        placeholder="搜索名称、模块、模型、Action 或场景"
        @keydown="onSearchKeydown"
      />
      <ScSelect v-model="confidenceFilter" :options="confidenceOptions" aria-label="业务领域分类" />
      <ScSelect v-model="sceneFilter" :options="sceneOptions" aria-label="场景状态" />
      <ScSelect v-model="releaseFilter" :options="releaseOptions" aria-label="发布状态" />
      <ScSelect v-model="draftFilter" :options="draftOptions" aria-label="技术可选性" />
      <ScButton type="button" variant="ghost" :disabled="!hasFilters" @click="clearFilters">清除筛选</ScButton>
    </section>

    <div
      v-if="pageSectionEnabled('catalog', true)"
      class="capability-explorer__workspace"
    >
      <aside class="capability-explorer__centers" aria-labelledby="capability-centers-title">
        <div class="capability-explorer__section-heading">
          <h2 id="capability-centers-title">{{ pageText('centers_title', '') }}</h2>
          <span>原生中心</span>
        </div>
        <div
          class="capability-explorer__center"
          :class="{ 'is-active': !centerFilter }"
        >
          <ScButton type="button" variant="ghost" appearance="tree-item" @click="selectCenter('')">
            <span>全部中心</span>
            <strong>{{ catalog?.meta.total ?? 0 }}</strong>
          </ScButton>
        </div>
        <div
          v-for="center in catalog?.facets.centers || []"
          :key="center.key"
          class="capability-explorer__center"
          :class="{ 'is-active': centerFilter === center.key }"
        >
          <ScButton type="button" variant="ghost" appearance="tree-item" @click="selectCenter(center.key)">
            <span>{{ center.label }}</span>
            <strong>{{ center.count }}</strong>
          </ScButton>
        </div>
      </aside>

      <main class="capability-explorer__catalog" aria-labelledby="capability-entry-list-title">
        <div class="capability-explorer__section-heading">
          <h2 id="capability-entry-list-title">{{ pageText('entries_title', '') }}</h2>
          <span>{{ filteredTotal }} 项</span>
        </div>
        <ScInlineState v-if="loading && !catalog" state="loading" label="正在读取 Odoo 原生能力目录。" />
        <ScEmptyState
          v-else-if="!loading && !rows.length"
          title="当前筛选下没有业务入口"
          description="请调整搜索或筛选条件。空结果不代表能力不存在。"
        />
        <template v-else>
          <ScTable
            class="capability-explorer__table"
            :data="tableRows"
            :columns="columns"
            row-key="id"
            :loading="loading"
            :row-class-name="rowClassName"
            :row-attributes="rowAttributes"
            label="平台原生业务入口"
            @row-click="onTableRowClick"
          />

          <div class="capability-explorer__mobile-list" aria-label="平台原生业务入口">
            <ScMobileRecordCard
              v-for="row in rows"
              :key="entryKey(row)"
              as="button"
              class="capability-explorer__mobile-row"
              :class="{ 'is-active': selectedKey === entryKey(row) }"
              @click="openEntry(row)"
            >
              <template #identity>
                <span class="capability-explorer__mobile-identity">
                  <strong class="capability-explorer__mobile-title">{{ row.label }}</strong>
                  <span>{{ row.center.label || '未识别中心' }}</span>
                  <span>{{ row.origin.model || row.origin.module || '—' }}</span>
                </span>
              </template>
              <template #status>
                <ScStatusBadge v-bind="businessDomainPresentation(row)" value="business_domain" />
              </template>
              <span class="capability-explorer__mobile-badges">
                <ScStatusBadge v-bind="sceneUsagePresentation(row)" value="scene_usage" />
                <ScStatusBadge v-bind="technicalEligibilityPresentation(row)" value="draft_selectable" />
              </span>
              <span v-if="row.draft_eligibility.blockers.length" class="capability-explorer__blockers">
                {{ blockerLabel(row.draft_eligibility.blockers) }}
              </span>
            </ScMobileRecordCard>
          </div>

          <ScPagination
            v-if="filteredTotal > 0"
            :current="currentPage"
            :page-size="pageSize"
            :total="filteredTotal"
            :disabled="loading"
            @update:current="goToPage"
          />
        </template>
      </main>
    </div>

    <ScDrawer
      v-if="pageSectionEnabled('detail', true)"
      :open="drawerOpen"
      :title="pageText('detail_title', '')"
      :description="pageText('detail_description', '')"
      size="wide"
      @close="closeDrawer"
    >
      <ScInlineState v-if="detailLoading || diagnoseLoading" state="loading" label="正在读取入口详情并执行诊断。" />
      <ScInlineState v-if="detailError" state="error" :label="detailError">
        <template #actions><ScButton type="button" variant="secondary" @click="reloadFromFirstPage">刷新目录</ScButton></template>
      </ScInlineState>
      <template v-if="detail">
        <header class="capability-explorer__detail-head">
          <div>
            <p class="capability-explorer__eyebrow">{{ detail.origin.module }}</p>
            <h2>{{ detail.label }}</h2>
            <p>{{ detail.entry_ref.menu_xmlid }}</p>
            <p>{{ detail.entry_ref.action_xmlid }}</p>
          </div>
          <ScStatusBadge
            :value="detail.diagnostics.native_valid ? 'valid' : 'blocked'"
            :label="detail.diagnostics.native_valid ? '原生身份有效' : '原生身份存在阻断'"
            :semantic="detail.diagnostics.native_valid ? 'success' : 'danger'"
          />
        </header>

        <ScSection title="最终可用性">
          <div class="capability-explorer__availability-head">
            <ScStatusBadge
              :value="detail.visibility.can_use ? 'available' : 'denied'"
              :label="detail.visibility.can_use ? '当前用户可用' : '当前用户不可用'"
              :semantic="detail.visibility.can_use ? 'success' : 'danger'"
            />
            <code>{{ detail.visibility.reason_code }}</code>
          </div>
          <ScDescriptions :items="availabilityItems" :column="1" bordered />
          <ScInlineState
            v-if="detail.visibility.blockers.length"
            state="error"
            :label="`不可用原因：${blockerLabel(detail.visibility.blockers)}`"
          />
          <ScInlineState
            v-else
            state="success"
            label="原生来源、产品资格、版本、企业启用和当前用户权限均未返回阻断。"
          />
        </ScSection>

        <ScSection title="事实分层">
          <div class="capability-explorer__fact-layers">
            <article v-for="layer in detail.fact_layers" :key="layer.key">
              <div>
                <strong>{{ layer.label }}</strong>
                <span>{{ layer.reason_code }}</span>
              </div>
              <ScStatusBadge
                :value="layer.status"
                :label="factLayerPresentation(layer).label"
                :semantic="factLayerPresentation(layer).semantic"
              />
            </article>
          </div>
        </ScSection>

        <ScSection title="技术来源">
          <ScDescriptions :items="technicalItems" :column="1" bordered />
        </ScSection>

        <ScSection title="场景使用">
          <ScEmptyState
            v-if="!detail.scenario_usage.scenarios.length"
            title="尚无权威场景绑定"
            description="未绑定不代表该入口无效；它仍可能作为原生中心入口存在。"
            density="compact"
          />
          <div v-else class="capability-explorer__scenario-list">
            <article v-for="scenario in detail.scenario_usage.scenarios" :key="scenario.scenario_key">
              <strong>{{ scenario.scenario_name }}</strong>
              <span>{{ scenario.scenario_key }}</span>
              <span>{{ scenario.intent }} · 顺序 {{ scenario.sequence }}</span>
            </article>
          </div>
        </ScSection>

        <ScSection title="发布与资格">
          <ScDescriptions :items="qualificationItems" :column="1" bordered />
          <div class="capability-explorer__qualification-evidence">
            <article
              v-for="evidence in detail.qualification.evidence"
              :key="evidence.product_key"
            >
              <ScStatusBadge
                :value="evidence.status"
                :label="qualificationPresentation(evidence.status).label"
                :semantic="qualificationPresentation(evidence.status).semantic"
              />
              <strong>{{ evidence.product_key }}</strong>
              <span>{{ evidence.version || '无生效版本' }} · snapshot {{ evidence.snapshot_id || '—' }}</span>
              <span>{{ evidence.reason_code }}</span>
            </article>
          </div>
          <ScInlineState
            v-if="detail.release.blockers.length"
            state="error"
            :label="`发布归属存在阻断：${blockerLabel(detail.release.blockers)}`"
          />
        </ScSection>

        <ScSection title="诊断">
          <div class="capability-explorer__diagnosis-head">
            <ScStatusBadge
              :value="diagnosis?.draft_selectable ? 'selectable' : 'blocked'"
              :label="diagnosis?.draft_selectable ? '技术可进入场景草稿' : '技术不可进入场景草稿'"
              :semantic="diagnosis?.draft_selectable ? 'success' : 'danger'"
            />
            <ScButton type="button" variant="secondary" :loading="diagnoseLoading" @click="reDiagnose">重新诊断</ScButton>
          </div>
          <ScInlineState
            v-if="diagnosis?.blockers.length"
            state="error"
            :label="blockerLabel(diagnosis.blockers)"
          />
          <ScInlineState v-else state="success" label="当前诊断没有阻断原因。" />
          <p class="capability-explorer__qualification-note">
            技术可选不等于 Preview 或 Standard 产品资格；资格状态以后端返回为准。
          </p>
        </ScSection>
      </template>
    </ScDrawer>
  </ScPage>
</template>

<script setup lang="ts">
import { computed, h, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import ScButton from '../components/design-system/ScButton.vue';
import ScCard from '../components/design-system/ScCard.vue';
import ScDescriptions from '../components/design-system/ScDescriptions.vue';
import ScDrawer from '../components/design-system/ScDrawer.vue';
import ScEmptyState from '../components/design-system/ScEmptyState.vue';
import ScInlineState from '../components/design-system/ScInlineState.vue';
import ScInput from '../components/design-system/ScInput.vue';
import ScMobileRecordCard from '../components/design-system/ScMobileRecordCard.vue';
import ScPage from '../components/design-system/ScPage.vue';
import ScPagination from '../components/design-system/ScPagination.vue';
import ScSection from '../components/design-system/ScSection.vue';
import ScSelect from '../components/design-system/ScSelect.vue';
import ScStatusBadge from '../components/design-system/ScStatusBadge.vue';
import ScTable from '../components/design-system/ScTable.vue';
import {
  fetchCapabilityExplorerDetail,
  fetchCapabilityExplorerDiagnose,
  fetchCapabilityExplorerList,
  type CapabilityExplorerDetailEntry,
  type CapabilityExplorerDiagnosisResponse,
  type CapabilityExplorerListResponse,
  type CapabilityExplorerRow,
} from '../api/platformCapabilityExplorer';
import {
  blockerLabel,
  buildListFilters,
  businessDomainPresentation,
  capabilityEntryKey,
  factLayerPresentation,
  isCatalogStaleError,
  qualificationPresentation,
  releaseStatePresentation,
  sceneUsagePresentation,
  technicalEligibilityPresentation,
} from '../app/platformCapabilityExplorerPresentation';
import { createCapabilityExplorerRequestGate } from '../app/platformCapabilityExplorerRequestGate';
import { usePageContract } from '../app/pageContract';

const pageContract = usePageContract('platform_capability_explorer');
const pageText = pageContract.text;
const pageSectionEnabled = pageContract.sectionEnabled;
const catalog = ref<CapabilityExplorerListResponse | null>(null);
const loading = ref(false);
const error = ref('');
const staleNotice = ref(false);
const queryDraft = ref('');
const appliedQuery = ref('');
const centerFilter = ref('');
const confidenceFilter = ref('');
const sceneFilter = ref('');
const releaseFilter = ref('');
const draftFilter = ref('');
const currentOffset = ref(0);
const pageSize = ref(0);
const requestSequence = ref(0);
const drawerOpen = ref(false);
const selectedKey = ref('');
const detail = ref<CapabilityExplorerDetailEntry | null>(null);
const diagnosis = ref<CapabilityExplorerDiagnosisResponse | null>(null);
const detailLoading = ref(false);
const diagnoseLoading = ref(false);
const detailError = ref('');
const detailRequestGate = createCapabilityExplorerRequestGate();
let searchTimer: ReturnType<typeof setTimeout> | null = null;

const rows = computed(() => catalog.value?.rows || []);
const filteredTotal = computed(() => catalog.value?.meta.filtered_total || 0);
const currentPage = computed(() => pageSize.value > 0 ? Math.floor(currentOffset.value / pageSize.value) + 1 : 1);
const hasFilters = computed(() => Boolean(
  queryDraft.value || centerFilter.value || confidenceFilter.value || sceneFilter.value || releaseFilter.value || draftFilter.value,
));

const confidenceOptions = [
  { value: '', label: '全部分类' },
  { value: 'authoritative_scene_binding', label: '权威场景绑定' },
  { value: 'center_only', label: '仅原生中心' },
  { value: 'unclassified', label: '未分类' },
];
const sceneOptions = [
  { value: '', label: '全部场景状态' },
  { value: 'bound', label: '已场景化' },
  { value: 'unbound', label: '尚未场景化' },
];
const draftOptions = [
  { value: '', label: '全部技术状态' },
  { value: 'true', label: '技术可选' },
  { value: 'false', label: '存在阻断' },
];
const releaseOptions = computed(() => [
  { value: '', label: '全部发布状态' },
  ...Object.keys(catalog.value?.facets.release_states || {})
    .filter(Boolean)
    .map((state) => ({ value: state, label: releaseStatePresentation(state).label })),
]);

const tableRows = computed(() => rows.value.map((row) => ({
  id: entryKey(row),
  ...row,
})));
const columns = computed(() => [
  {
    colKey: 'label',
    title: '业务入口',
    minWidth: 220,
    cell: (_h: unknown, { row }: { row: Record<string, unknown> }) => h('div', { class: 'capability-explorer__entry-cell' }, [
      h('strong', String(row.label || '')),
      h('span', String((row.origin as Record<string, unknown>)?.module || '')),
      h('span', String((row.origin as Record<string, unknown>)?.model || '')),
    ]),
  },
  {
    colKey: 'center',
    title: '原生中心',
    minWidth: 140,
    cell: (_h: unknown, { row }: { row: Record<string, unknown> }) => String((row.center as Record<string, unknown>)?.label || '未识别中心'),
  },
  {
    colKey: 'business_domain',
    title: '业务领域',
    minWidth: 180,
    cell: (_h: unknown, { row }: { row: Record<string, unknown> }) => {
      const presentation = businessDomainPresentation(row as unknown as CapabilityExplorerRow);
      return h(ScStatusBadge, { ...presentation, value: 'business_domain' });
    },
  },
  {
    colKey: 'scene_usage',
    title: '场景',
    minWidth: 150,
    cell: (_h: unknown, { row }: { row: Record<string, unknown> }) => {
      const presentation = sceneUsagePresentation(row as unknown as CapabilityExplorerRow);
      return h(ScStatusBadge, { ...presentation, value: 'scene_usage' });
    },
  },
  {
    colKey: 'release_state',
    title: '发布',
    minWidth: 130,
    cell: (_h: unknown, { row }: { row: Record<string, unknown> }) => {
      const presentation = releaseStatePresentation(String(row.release_state || ''));
      return h(ScStatusBadge, { ...presentation, value: String(row.release_state || '') });
    },
  },
  {
    colKey: 'draft_eligibility',
    title: '技术资格',
    minWidth: 140,
    cell: (_h: unknown, { row }: { row: Record<string, unknown> }) => {
      const presentation = technicalEligibilityPresentation(row as unknown as CapabilityExplorerRow);
      return h(ScStatusBadge, { ...presentation, value: 'draft_selectable' });
    },
  },
]);

const technicalItems = computed(() => {
  if (!detail.value) return [];
  const facts = detail.value.native_facts;
  return [
    { key: 'menu', label: 'Menu XMLID', value: facts.menu.xmlid },
    { key: 'action', label: 'Action XMLID', value: facts.action.xmlid },
    { key: 'action_type', label: 'Action 类型', value: facts.action.type },
    { key: 'module', label: '模块', value: `${facts.module.name} · ${facts.module.state} · ${facts.module.version || '—'}` },
    { key: 'model', label: '模型', value: facts.model.name || '—' },
    { key: 'view', label: 'View', value: `${facts.views.count} 个关联视图` },
    { key: 'acl', label: 'ACL 摘要', value: `${facts.acl.row_count} 条 · ${facts.acl.group_xmlids.join('、') || '未声明授权组'}` },
    { key: 'rules', label: 'Record Rules', value: `${facts.record_rules.count} 条` },
  ];
});
const qualificationItems = computed(() => {
  if (!detail.value) return [];
  const standard = detail.value.qualification.evidence.find((item) => item.product_key === 'construction.standard');
  return [
    { key: 'native', label: '原生有效性', value: detail.value.diagnostics.native_valid ? '有效' : '存在阻断' },
    { key: 'scene', label: '场景可选性', value: detail.value.scene_assignment.assignable ? '可选' : '不可选' },
    { key: 'release', label: '入口发布', value: releaseStatePresentation(detail.value.release.state).label },
    { key: 'preview', label: 'Preview 资格', value: qualificationPresentation(detail.value.qualification.preview).label },
    { key: 'standard', label: 'Standard 资格', value: qualificationPresentation(detail.value.qualification.standard).label },
    { key: 'version', label: '生效产品版本', value: standard?.version || '未返回生效版本' },
    { key: 'snapshot', label: '生效快照', value: standard?.snapshot_id ? String(standard.snapshot_id) : '未返回快照身份' },
    { key: 'authority', label: '资格依据', value: standard?.qualification_authority || detail.value.qualification.reason_code },
  ];
});

const availabilityItems = computed(() => {
  if (!detail.value) return [];
  const actor = detail.value.visibility.actor;
  const enterprise = detail.value.enterprise_enablement;
  return [
    { key: 'actor', label: '操作者身份', value: `${actor.name || actor.login || '—'} (${actor.login || actor.user_id})` },
    { key: 'actor_company', label: '操作者公司', value: actor.company_name || String(actor.company_id || '—') },
    { key: 'target_company', label: '本次目标公司', value: enterprise.company_name || String(enterprise.company_id || '—') },
    { key: 'enterprise', label: '企业启用', value: `${enterprise.status} · ${enterprise.reason_code}` },
    { key: 'group', label: '入口组权限', value: detail.value.current_user_access.entry_groups_allowed ? '满足' : '不满足' },
    { key: 'acl', label: '模型读取', value: detail.value.current_user_access.model_read_allowed ? '满足' : '不满足' },
    { key: 'record', label: '记录范围', value: detail.value.current_user_access.record_scope },
  ];
});

function entryKey(row: Pick<CapabilityExplorerRow, 'entry_ref'>): string {
  return capabilityEntryKey(row);
}

async function loadList(options: { readonly offset?: number; readonly clearToken?: boolean } = {}) {
  const sequence = ++requestSequence.value;
  loading.value = true;
  error.value = '';
  const offset = options.offset ?? currentOffset.value;
  try {
    const response = await fetchCapabilityExplorerList({
      query: appliedQuery.value || undefined,
      filters: buildListFilters({
        centerKey: centerFilter.value,
        confidence: confidenceFilter.value,
        sceneStatus: sceneFilter.value,
        releaseState: releaseFilter.value,
        draftSelectable: draftFilter.value,
      }),
      offset: offset || undefined,
      limit: pageSize.value || undefined,
      ...(!options.clearToken && catalog.value?.meta.catalog_token
        ? { expected_catalog_token: catalog.value.meta.catalog_token }
        : {}),
    });
    if (sequence !== requestSequence.value) return;
    catalog.value = response;
    pageSize.value = response.meta.limit;
    currentOffset.value = response.meta.offset;
    staleNotice.value = false;
  } catch (err) {
    if (sequence !== requestSequence.value) return;
    if (isCatalogStaleError(err)) {
      await recoverFromStale();
      return;
    }
    error.value = err instanceof Error ? err.message : '能力目录读取失败。';
  } finally {
    if (sequence === requestSequence.value) loading.value = false;
  }
}

async function recoverFromStale() {
  staleNotice.value = true;
  closeDrawer();
  catalog.value = null;
  currentOffset.value = 0;
  await loadList({ offset: 0, clearToken: true });
}

function reloadFromCurrentPage() {
  void loadList({ offset: currentOffset.value, clearToken: true });
}

function reloadFromFirstPage() {
  void loadList({ offset: 0, clearToken: true });
}

function applyQuery() {
  appliedQuery.value = queryDraft.value.trim();
  currentOffset.value = 0;
  void loadList({ offset: 0 });
}

function onSearchKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter') return;
  event.preventDefault();
  if (searchTimer) clearTimeout(searchTimer);
  applyQuery();
}

function selectCenter(key: string) {
  centerFilter.value = key;
  currentOffset.value = 0;
  void loadList({ offset: 0 });
}

function clearFilters() {
  queryDraft.value = '';
  appliedQuery.value = '';
  centerFilter.value = '';
  confidenceFilter.value = '';
  sceneFilter.value = '';
  releaseFilter.value = '';
  draftFilter.value = '';
  currentOffset.value = 0;
  void loadList({ offset: 0 });
}

function goToPage(page: number) {
  currentOffset.value = Math.max(0, (page - 1) * pageSize.value);
  void loadList({ offset: currentOffset.value });
}

function onTableRowClick(context: unknown) {
  if (!context || typeof context !== 'object') return;
  const id = Reflect.get(context, 'row') && typeof Reflect.get(context, 'row') === 'object'
    ? String(Reflect.get(Reflect.get(context, 'row') as Record<string, unknown>, 'id') || '')
    : '';
  const row = rows.value.find((candidate) => entryKey(candidate) === id);
  if (row) void openEntry(row);
}

function rowClassName(context: unknown): string {
  const row = context && typeof context === 'object' ? Reflect.get(context, 'row') as Record<string, unknown> : null;
  return row && String(row.id || '') === selectedKey.value ? 'is-selected' : '';
}

function rowAttributes(context: unknown): Record<string, unknown> {
  const row = context && typeof context === 'object' ? Reflect.get(context, 'row') as Record<string, unknown> : null;
  const candidate = rows.value.find((item) => entryKey(item) === String(row?.id || ''));
  if (!candidate) return {};
  return {
    tabindex: 0,
    onKeydown: (event: KeyboardEvent) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
      void openEntry(candidate);
    },
  };
}

async function openEntry(row: CapabilityExplorerRow) {
  const rowKey = entryKey(row);
  const token = catalog.value?.meta.catalog_token;
  if (!token) {
    await recoverFromStale();
    return;
  }
  const requestSequence = detailRequestGate.begin();
  selectedKey.value = rowKey;
  drawerOpen.value = true;
  detail.value = null;
  diagnosis.value = null;
  detailError.value = '';
  detailLoading.value = true;
  diagnoseLoading.value = true;
  try {
    const [detailResult, diagnosisResult] = await Promise.all([
      fetchCapabilityExplorerDetail({ entry_ref: row.entry_ref, expected_catalog_token: token }),
      fetchCapabilityExplorerDiagnose({ entry_ref: row.entry_ref, expected_catalog_token: token }),
    ]);
    if (!detailRequestGate.isCurrent(requestSequence) || selectedKey.value !== rowKey) return;
    detail.value = detailResult.entry;
    diagnosis.value = diagnosisResult;
  } catch (err) {
    if (!detailRequestGate.isCurrent(requestSequence) || selectedKey.value !== rowKey) return;
    if (isCatalogStaleError(err)) {
      await recoverFromStale();
      return;
    }
    detailError.value = err instanceof Error ? err.message : '入口详情读取失败。';
  } finally {
    if (detailRequestGate.isCurrent(requestSequence) && selectedKey.value === rowKey) {
      detailLoading.value = false;
      diagnoseLoading.value = false;
    }
  }
}

async function reDiagnose() {
  const token = catalog.value?.meta.catalog_token;
  if (!detail.value || !token) {
    await recoverFromStale();
    return;
  }
  const rowKey = entryKey(detail.value);
  const requestSequence = detailRequestGate.begin();
  diagnoseLoading.value = true;
  try {
    const result = await fetchCapabilityExplorerDiagnose({
      entry_ref: detail.value.entry_ref,
      expected_catalog_token: token,
    });
    if (!detailRequestGate.isCurrent(requestSequence) || selectedKey.value !== rowKey) return;
    diagnosis.value = result;
  } catch (err) {
    if (!detailRequestGate.isCurrent(requestSequence) || selectedKey.value !== rowKey) return;
    if (isCatalogStaleError(err)) {
      await recoverFromStale();
      return;
    }
    detailError.value = err instanceof Error ? err.message : '诊断读取失败。';
  } finally {
    if (detailRequestGate.isCurrent(requestSequence) && selectedKey.value === rowKey) {
      diagnoseLoading.value = false;
    }
  }
}

function closeDrawer() {
  detailRequestGate.invalidate();
  drawerOpen.value = false;
  selectedKey.value = '';
  detail.value = null;
  diagnosis.value = null;
  detailError.value = '';
  detailLoading.value = false;
  diagnoseLoading.value = false;
}

function shortToken(token: string): string {
  return token.length > 20 ? `${token.slice(0, 15)}…${token.slice(-6)}` : token;
}

watch(queryDraft, () => {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    const normalized = queryDraft.value.trim();
    if (normalized === appliedQuery.value) return;
    applyQuery();
  }, 320);
});
watch([confidenceFilter, sceneFilter, releaseFilter, draftFilter], () => {
  currentOffset.value = 0;
  void loadList({ offset: 0 });
});

onMounted(() => {
  void loadList({ offset: 0, clearToken: true });
});
onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer);
});
</script>

<style scoped>
.capability-explorer { display: grid; gap: var(--sc-space-lg); }
.capability-explorer__header { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--sc-space-md); }
.capability-explorer__header h1, .capability-explorer__header p { margin: 0; }
.capability-explorer__header h1 { font: var(--sc-font-title-large); }
.capability-explorer__header > div > p:last-child { max-width: 72ch; margin-top: var(--sc-space-xs); color: var(--sc-app-text-secondary); }
.capability-explorer__eyebrow { color: var(--sc-app-text-muted); font: var(--sc-font-body-small); text-transform: uppercase; letter-spacing: .08em; }
.capability-explorer__header-actions { display: flex; align-items: center; gap: var(--sc-space-sm); flex-wrap: wrap; justify-content: flex-end; }
.capability-explorer__token { max-width: 220px; color: var(--sc-app-text-muted); font: var(--sc-font-body-small); overflow-wrap: anywhere; }
.capability-explorer__metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--sc-space-sm); }
.capability-explorer__metric-label { margin: 0; color: var(--sc-app-text-secondary); font: var(--sc-font-body-small); }
.capability-explorer__metric-value { display: block; margin-top: var(--sc-space-xs); font: var(--sc-font-title-large); }
.capability-explorer__toolbar { display: grid; grid-template-columns: minmax(260px, 2fr) repeat(4, minmax(150px, 1fr)) auto; gap: var(--sc-space-sm); align-items: center; }
.capability-explorer__workspace { display: grid; grid-template-columns: minmax(190px, 240px) minmax(0, 1fr); gap: var(--sc-space-lg); align-items: start; }
.capability-explorer__centers, .capability-explorer__catalog { min-width: 0; }
.capability-explorer__centers { display: grid; gap: var(--sc-space-xs); padding: var(--sc-space-md); border: 1px solid var(--sc-app-border); border-radius: var(--sc-radius-md); background: var(--sc-app-panel); }
.capability-explorer__section-heading { display: flex; align-items: center; justify-content: space-between; gap: var(--sc-space-sm); margin-bottom: var(--sc-space-sm); }
.capability-explorer__section-heading h2 { margin: 0; font: var(--sc-font-title-medium); }
.capability-explorer__section-heading span { color: var(--sc-app-text-muted); font: var(--sc-font-body-small); }
.capability-explorer__center { display: flex; align-items: center; justify-content: space-between; gap: var(--sc-space-sm); min-height: 44px; padding: var(--sc-space-xs) var(--sc-space-sm); border: 0; border-radius: var(--sc-radius-sm); color: var(--sc-app-text-primary); background: transparent; text-align: left; cursor: pointer; }
.capability-explorer__center:hover, .capability-explorer__center.is-active { background: var(--sc-app-info-bg); color: var(--sc-app-info-text); }
.capability-explorer__center strong { font-variant-numeric: tabular-nums; }
.capability-explorer__center :deep(.sc-btn) { width: 100%; justify-content: space-between; }
.capability-explorer__center :deep(.sc-btn__content) { display: flex; width: 100%; align-items: center; justify-content: space-between; gap: var(--sc-space-sm); }
.capability-explorer__catalog { display: grid; gap: var(--sc-space-sm); }
.capability-explorer__table { min-width: 0; }
.capability-explorer__entry-cell { display: grid; gap: 2px; min-width: 0; }
.capability-explorer__entry-cell strong, .capability-explorer__entry-cell span { overflow-wrap: anywhere; }
.capability-explorer__entry-cell span { color: var(--sc-app-text-secondary); font: var(--sc-font-body-small); }
.capability-explorer__mobile-list { display: none; }
.capability-explorer__mobile-row { display: grid; gap: var(--sc-space-xs); width: 100%; min-height: 44px; padding: var(--sc-space-md); border: 1px solid var(--sc-app-border); border-radius: var(--sc-radius-md); color: var(--sc-app-text-primary); background: var(--sc-app-panel); text-align: left; }
.capability-explorer__mobile-row.is-active { border-color: var(--sc-app-accent); background: var(--sc-app-info-bg); }
.capability-explorer__mobile-identity { display: grid; min-width: 0; gap: 2px; text-align: left; }
.capability-explorer__mobile-identity > span { color: var(--sc-app-text-secondary); font: var(--sc-font-body-small); overflow-wrap: anywhere; }
.capability-explorer__mobile-title { font: var(--sc-font-title-small); }
.capability-explorer__mobile-badges { display: flex; flex-wrap: wrap; gap: var(--sc-space-xs); }
.capability-explorer__blockers { color: var(--sc-app-danger-text); font: var(--sc-font-body-small); overflow-wrap: anywhere; }
.capability-explorer__detail-head { display: flex; justify-content: space-between; gap: var(--sc-space-md); margin-bottom: var(--sc-space-md); }
.capability-explorer__detail-head h2, .capability-explorer__detail-head p { margin: 0; }
.capability-explorer__detail-head h2 { font: var(--sc-font-title-large); }
.capability-explorer__detail-head p:not(.capability-explorer__eyebrow) { margin-top: 2px; color: var(--sc-app-text-secondary); font: var(--sc-font-body-small); overflow-wrap: anywhere; }
.capability-explorer__availability-head { display: flex; align-items: center; justify-content: space-between; gap: var(--sc-space-sm); margin-bottom: var(--sc-space-sm); }
.capability-explorer__availability-head code { color: var(--sc-app-text-muted); font: var(--sc-font-body-small); overflow-wrap: anywhere; }
.capability-explorer__fact-layers, .capability-explorer__qualification-evidence { display: grid; gap: var(--sc-space-xs); }
.capability-explorer__fact-layers article, .capability-explorer__qualification-evidence article { display: flex; align-items: center; justify-content: space-between; gap: var(--sc-space-sm); padding: var(--sc-space-sm); border: 1px solid var(--sc-app-border); border-radius: var(--sc-radius-sm); }
.capability-explorer__fact-layers article > div, .capability-explorer__qualification-evidence article { min-width: 0; }
.capability-explorer__fact-layers strong, .capability-explorer__fact-layers span, .capability-explorer__qualification-evidence strong, .capability-explorer__qualification-evidence span { overflow-wrap: anywhere; }
.capability-explorer__fact-layers span, .capability-explorer__qualification-evidence span { color: var(--sc-app-text-secondary); font: var(--sc-font-body-small); }
.capability-explorer__qualification-evidence article { display: grid; grid-template-columns: auto minmax(140px, 1fr) minmax(160px, 1fr) minmax(140px, 1fr); }
.capability-explorer__scenario-list { display: grid; gap: var(--sc-space-xs); }
.capability-explorer__scenario-list article { display: grid; gap: 2px; padding: var(--sc-space-sm); border: 1px solid var(--sc-app-border); border-radius: var(--sc-radius-sm); }
.capability-explorer__scenario-list span { color: var(--sc-app-text-secondary); font: var(--sc-font-body-small); overflow-wrap: anywhere; }
.capability-explorer__diagnosis-head { display: flex; align-items: center; justify-content: space-between; gap: var(--sc-space-sm); margin-bottom: var(--sc-space-sm); }
.capability-explorer__qualification-note { margin: var(--sc-space-sm) 0 0; color: var(--sc-app-text-muted); font: var(--sc-font-body-small); }
@media (max-width: 1100px) {
  .capability-explorer__metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .capability-explorer__toolbar { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .capability-explorer__toolbar > :first-child { grid-column: 1 / -1; }
}
@media (max-width: 760px) {
  .capability-explorer__header { display: grid; }
  .capability-explorer__header-actions { justify-content: flex-start; }
  .capability-explorer__toolbar { grid-template-columns: minmax(0, 1fr); }
  .capability-explorer__workspace { grid-template-columns: minmax(0, 1fr); }
  .capability-explorer__centers { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
  .capability-explorer__centers .capability-explorer__section-heading { grid-column: 1 / -1; }
  .capability-explorer__table { display: none; }
  .capability-explorer__mobile-list { display: grid; gap: var(--sc-space-sm); }
  .capability-explorer__detail-head { display: grid; }
  .capability-explorer__fact-layers article, .capability-explorer__qualification-evidence article { display: grid; justify-items: start; }
}
@media (max-width: 520px) {
  .capability-explorer__metrics { grid-template-columns: minmax(0, 1fr); }
}
</style>
