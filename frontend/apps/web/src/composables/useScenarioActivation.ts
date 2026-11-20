import { onScopeDispose, ref, watch } from 'vue';
import { intentRequest } from '../api/intents';
import { currentContextEpoch, isCurrentContextEpoch } from '../app/contextEpoch';
import { contractGapError } from '../app/contract/contractGap';
import { useSessionStore } from '../stores/session';

export type ScenarioAction = { key: string; label: string; enabled: boolean };
export type ScenarioActor = {
  user_id: number;
  login: string;
  name: string;
  can_manage_enterprise_configuration: boolean;
  platform_admin: boolean;
  source: string;
};
export type ScenarioTargetScope = {
  kind: string;
  company_id: number;
  company_name: string;
  is_global_product_release: boolean;
  source: string;
  target_role_scope: {
    mode: string;
    target_role_key: string;
    reason_code: string;
    meaning: string;
  };
};
export type ScenarioProductQualification = {
  status: string;
  reason_code: string;
  evidence: {
    product_key?: string;
    qualified?: boolean;
    snapshot_id?: number;
    version?: string;
    fingerprint?: string;
    applied?: boolean;
    source?: string;
    qualification_authority?: string;
    products?: Array<Record<string, unknown>>;
    [key: string]: unknown;
  };
};
export type BusinessScenario = {
  scene_key: string; name: string; enablement_scope: string;
  status_label: string; release_label: string;
  product_qualification: ScenarioProductQualification;
  enablement_blockers: string[];
  enable_allowed: boolean;
  actions: ScenarioAction[];
};
export type ScenarioCatalogRow = {
  scene_key: string;
  name: string;
  release_state: string;
  product_released: boolean;
  tenant_enabled: boolean;
  product_qualification: {
    status: string;
    reason_code: string;
    evidence: Record<string, unknown>;
  };
  enablement_blockers: string[];
  enable_allowed: boolean;
};
export type ScenarioReadback = {
  scene_key: string;
  stored_scene_key: string;
  enablement_scope: string;
  enabled: boolean;
  target_scope: ScenarioTargetScope;
  readback: {
    enabled: boolean;
    company_id: number;
    requested_scene_key: string;
    stored_scene_key: string;
    enablement_scope: string;
    target_state: boolean;
    source: string;
    storage_key: string;
    write_committed: boolean;
    access_granted: boolean;
  };
};
type Catalog = {
  contract_version: string;
  rows: ScenarioCatalogRow[];
  row_count: number;
  company_id: number;
  actor: ScenarioActor;
  target_scope: ScenarioTargetScope;
  business_scenarios: BusinessScenario[];
};

function requireCatalog(value: Catalog): Catalog {
  if (!value || value.contract_version !== 'scenario_activation_catalog.v1'
    || !Array.isArray(value.rows)
    || value.rows.some(row => !row || typeof row.scene_key !== 'string' || !row.scene_key
      || typeof row.name !== 'string' || !row.name
      || typeof row.release_state !== 'string'
      || typeof row.product_released !== 'boolean'
      || typeof row.tenant_enabled !== 'boolean'
      || !row.product_qualification
      || typeof row.product_qualification.status !== 'string'
      || typeof row.product_qualification.reason_code !== 'string'
      || !row.product_qualification.evidence
      || typeof row.product_qualification.evidence !== 'object'
      || !Array.isArray(row.enablement_blockers)
      || row.enablement_blockers.some((item: unknown) => typeof item !== 'string')
      || typeof row.enable_allowed !== 'boolean')
    || !Number.isInteger(value.row_count) || value.row_count !== value.rows.length
    || !Number.isInteger(value.company_id) || value.company_id <= 0
    || !value.actor || !Number.isInteger(value.actor.user_id) || value.actor.user_id <= 0
    || typeof value.actor.can_manage_enterprise_configuration !== 'boolean'
    || !value.target_scope || value.target_scope.company_id !== value.company_id
    || value.target_scope.is_global_product_release !== false
    || typeof value.target_scope.target_role_scope?.mode !== 'string'
    || !Array.isArray(value.business_scenarios)
    || value.business_scenarios.some(row => !row || ['scene_key', 'name', 'enablement_scope', 'status_label', 'release_label']
      .some(key => typeof row[key as keyof BusinessScenario] !== 'string' || !row[key as keyof BusinessScenario])
      || !Array.isArray(row.actions) || row.actions.some(action => !action
        || typeof action.key !== 'string' || !action.key || typeof action.label !== 'string' || !action.label
        || typeof action.enabled !== 'boolean')
      || !row.product_qualification || typeof row.product_qualification.status !== 'string'
      || typeof row.product_qualification.reason_code !== 'string'
      || !row.product_qualification.evidence || typeof row.product_qualification.evidence !== 'object'
      || !Array.isArray(row.enablement_blockers)
      || row.enablement_blockers.some((item: unknown) => typeof item !== 'string')
      || typeof row.enable_allowed !== 'boolean')) {
    throw contractGapError({ kind: 'contract_defect', missing: 'business_scenarios',
      requiredDeclarationLayer: 'P1:smart_construction_scene:scenario.activation.catalog.get' }, '业务场景目录契约不完整');
  }
  return value;
}

export function requireScenarioReadback(
  value: ScenarioReadback,
  expected: {
    companyId: number;
    sceneKey: string;
    enablementScope: string;
    targetState: boolean;
  },
): ScenarioReadback {
  const readback = value?.readback;
  const valid = value
    && value.scene_key === expected.sceneKey
    && typeof value.stored_scene_key === 'string'
    && value.stored_scene_key.trim().length > 0
    && value.enablement_scope === expected.enablementScope
    && value.enabled === expected.targetState
    && value.target_scope
    && value.target_scope.kind === 'enterprise_scenario_enablement'
    && value.target_scope.company_id === expected.companyId
    && value.target_scope.is_global_product_release === false
    && typeof value.target_scope.target_role_scope?.mode === 'string'
    && readback
    && readback.company_id === expected.companyId
    && readback.requested_scene_key === expected.sceneKey
    && readback.stored_scene_key === value.stored_scene_key
    && readback.enablement_scope === expected.enablementScope
    && readback.enabled === expected.targetState
    && readback.target_state === expected.targetState
    && readback.source === 'ir.config_parameter'
    && typeof readback.storage_key === 'string'
    && readback.storage_key.trim().length > 0
    && readback.write_committed === true
    && readback.access_granted === false;
  if (!valid) {
    throw contractGapError({
      kind: 'contract_defect',
      missing: 'scenario.activation.set.readback',
      requiredDeclarationLayer: 'P1:smart_construction_scene:scenario.activation.set',
    }, '企业场景写入回读与本次公司、场景、作用域或目标状态不一致');
  }
  return value;
}

export function useScenarioActivation() {
  const session = useSessionStore();
  const rows = ref<BusinessScenario[]>([]);
  const catalogRows = ref<ScenarioCatalogRow[]>([]);
  const catalogRowCount = ref(0);
  const actor = ref<ScenarioActor | null>(null);
  const targetScope = ref<ScenarioTargetScope | null>(null);
  const readback = ref<ScenarioReadback | null>(null);
  const state = ref<'loading' | 'ready' | 'error'>('loading');
  const errorMessage = ref('');
  const busy = ref(false);
  let companyId = 0;
  let catalogKey = '';
  let catalogEpoch = -1;
  let sequence = 0;
  let mutation = 0;
  let disposed = false;
  let refreshRequired = false;
  const contextKey = () => JSON.stringify([session.token, session.recordContext?.company_id,
    session.recordContext?.selected?.company_id]);
  const current = (key: string, epoch: number) => !disposed && contextKey() === key && isCurrentContextEpoch(epoch);

  async function load() {
    const request = ++sequence;
    rows.value = [];
    catalogRows.value = [];
    catalogRowCount.value = 0;
    actor.value = null;
    targetScope.value = null;
    companyId = 0;
    state.value = 'loading';
    errorMessage.value = '';
    if (!session.token) return;
    if (session.initStatus === 'error') {
      state.value = 'error';
      errorMessage.value = session.initError || '会话初始化失败，请刷新重试';
      return;
    }
    if (session.initStatus !== 'ready') return;
    const key = contextKey();
    const epoch = currentContextEpoch();
    const company = session.recordContext?.company_id ?? session.recordContext?.selected?.company_id;
    try {
      const response = await intentRequest<Catalog>({ intent: 'scenario.activation.catalog.get',
        params: company ? { company_id: company } : {} });
      if (!current(key, epoch) || request !== sequence) return;
      const catalog = requireCatalog(response);
      if (company && catalog.company_id !== company) throw new Error('场景目录公司与当前上下文不一致');
      catalogRows.value = catalog.rows;
      catalogRowCount.value = catalog.row_count;
      rows.value = catalog.business_scenarios;
      actor.value = catalog.actor;
      targetScope.value = catalog.target_scope;
      companyId = catalog.company_id;
      catalogKey = key;
      catalogEpoch = epoch;
      state.value = 'ready';
    } catch (error) {
      if (!current(key, epoch) || request !== sequence) return;
      errorMessage.value = error instanceof Error ? error.message : '场景目录读取失败';
      state.value = 'error';
    }
  }

  async function execute(row: BusinessScenario, action: ScenarioAction) {
    if (busy.value || refreshRequired || state.value !== 'ready' || session.initStatus !== 'ready'
      || !current(catalogKey, catalogEpoch) || !rows.value.includes(row) || !row.actions.includes(action)) return;
    const key = contextKey();
    const epoch = currentContextEpoch();
    const operation = ++mutation;
    busy.value = true;
    errorMessage.value = '';
    readback.value = null;
    let verifiedReadback: ScenarioReadback | null = null;
    try {
      const expected = { companyId, sceneKey: row.scene_key,
        enablementScope: row.enablement_scope, targetState: action.enabled };
      const response = await intentRequest<ScenarioReadback>({ intent: 'scenario.activation.set', params: { company_id: companyId,
        scene_key: row.scene_key, enablement_scope: row.enablement_scope, enabled: action.enabled } });
      if (!current(key, epoch) || operation !== mutation) return;
      refreshRequired = true;
      verifiedReadback = requireScenarioReadback(response, expected);
      readback.value = verifiedReadback;
      await session.loadAppInit({ force: true });
      if (current(key, epoch) && operation === mutation) {
        refreshRequired = false;
        await load();
      }
    } catch (error) {
      if (!current(key, epoch) || operation !== mutation) return;
      rows.value = [];
      catalogRows.value = [];
      catalogRowCount.value = 0;
      readback.value = verifiedReadback;
      state.value = 'error';
      const message = error instanceof Error ? error.message : '场景操作失败';
      errorMessage.value = refreshRequired && verifiedReadback
        ? `场景状态已保存，但导航刷新失败。请点击刷新恢复：${message}`
        : refreshRequired
          ? `场景写入结果尚未确认，请点击刷新只读恢复：${message}`
          : message;
    } finally {
      if (operation === mutation) busy.value = false;
    }
  }

  async function refresh() {
    if (busy.value) return;
    if (!session.token) { await load(); return; }
    const key = contextKey();
    const epoch = currentContextEpoch();
    const operation = ++mutation;
    busy.value = true;
    state.value = 'loading';
    rows.value = [];
    catalogRows.value = [];
    catalogRowCount.value = 0;
    try {
      // Read-only recovery: never replay scenario.activation.set after a
      // successful write whose following navigation refresh failed.
      if (refreshRequired || session.initStatus !== 'ready') await session.loadAppInit({ force: true });
      if (!current(key, epoch) || operation !== mutation) return;
      refreshRequired = false;
      await load();
    } catch (error) {
      if (!current(key, epoch) || operation !== mutation) return;
      state.value = 'error';
      errorMessage.value = error instanceof Error ? error.message : '场景刷新失败';
    } finally {
      if (operation === mutation) busy.value = false;
    }
  }

  watch(contextKey, () => {
    mutation += 1;
    busy.value = false;
    refreshRequired = false;
    readback.value = null;
    rows.value = [];
    catalogRows.value = [];
    catalogRowCount.value = 0;
    actor.value = null;
    targetScope.value = null;
  });
  watch(() => [contextKey(), session.initStatus], () => {
    if (busy.value) {
      sequence += 1;
      rows.value = [];
      catalogRows.value = [];
      catalogRowCount.value = 0;
      state.value = 'loading';
      return;
    }
    // A successful independent bootstrap also satisfies the pending refresh.
    if (session.initStatus === 'ready') refreshRequired = false;
    void load();
  }, { immediate: true });
  onScopeDispose(() => { disposed = true; sequence += 1; mutation += 1; });
  return {
    rows, catalogRows, catalogRowCount, actor, targetScope, readback, state, errorMessage, busy,
    load, refresh, execute,
  };
}
