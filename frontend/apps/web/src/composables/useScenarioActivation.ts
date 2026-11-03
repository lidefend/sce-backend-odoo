import { onScopeDispose, ref, watch } from 'vue';
import { intentRequest } from '../api/intents';
import { currentContextEpoch, isCurrentContextEpoch } from '../app/contextEpoch';
import { contractGapError } from '../app/contract/contractGap';
import { useSessionStore } from '../stores/session';

export type ScenarioAction = { key: string; label: string; enabled: boolean };
export type BusinessScenario = {
  scene_key: string; name: string; enablement_scope: string;
  status_label: string; release_label: string; actions: ScenarioAction[];
};
type Catalog = { company_id: number; business_scenarios: BusinessScenario[] };

function requireCatalog(value: Catalog): Catalog {
  if (!value || !Number.isInteger(value.company_id) || value.company_id <= 0
    || !Array.isArray(value.business_scenarios)
    || value.business_scenarios.some(row => !row || ['scene_key', 'name', 'enablement_scope', 'status_label', 'release_label']
      .some(key => typeof row[key as keyof BusinessScenario] !== 'string' || !row[key as keyof BusinessScenario])
      || !Array.isArray(row.actions) || row.actions.some(action => !action
        || typeof action.key !== 'string' || !action.key || typeof action.label !== 'string' || !action.label
        || typeof action.enabled !== 'boolean'))) {
    throw contractGapError({ kind: 'contract_defect', missing: 'business_scenarios',
      requiredDeclarationLayer: 'P1:smart_construction_scene:scenario.activation.catalog.get' }, '业务场景目录契约不完整');
  }
  return value;
}

export function useScenarioActivation() {
  const session = useSessionStore();
  const rows = ref<BusinessScenario[]>([]);
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
      rows.value = catalog.business_scenarios;
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
    try {
      await intentRequest({ intent: 'scenario.activation.set', params: { company_id: companyId,
        scene_key: row.scene_key, enablement_scope: row.enablement_scope, enabled: action.enabled } });
      if (!current(key, epoch) || operation !== mutation) return;
      refreshRequired = true;
      await session.loadAppInit({ force: true });
      if (current(key, epoch) && operation === mutation) {
        refreshRequired = false;
        await load();
      }
    } catch (error) {
      if (!current(key, epoch) || operation !== mutation) return;
      rows.value = [];
      state.value = 'error';
      const message = error instanceof Error ? error.message : '场景操作失败';
      errorMessage.value = refreshRequired ? `场景状态已保存，但导航刷新失败。请点击刷新恢复：${message}` : message;
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

  watch(contextKey, () => { mutation += 1; busy.value = false; refreshRequired = false; });
  watch(() => [contextKey(), session.initStatus], () => {
    if (busy.value) {
      sequence += 1;
      rows.value = [];
      state.value = 'loading';
      return;
    }
    // A successful independent bootstrap also satisfies the pending refresh.
    if (session.initStatus === 'ready') refreshRequired = false;
    void load();
  }, { immediate: true });
  onScopeDispose(() => { disposed = true; sequence += 1; mutation += 1; });
  return { rows, state, errorMessage, busy, load, refresh, execute };
}
