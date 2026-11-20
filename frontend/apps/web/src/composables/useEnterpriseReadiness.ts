import { onActivated, onDeactivated, onScopeDispose, ref, watch } from 'vue';
import { intentRequest } from '../api/intents';
import { currentContextEpoch, isCurrentContextEpoch } from '../app/contextEpoch';
import { contractGapError } from '../app/contract/contractGap';
import { useSessionStore } from '../stores/session';

export type ReadinessRemediation = { kind: 'handling_entry' | 'anchor'; key: string; label: string };
export type ReadinessRule = {
  rule_key: string; label: string; section_key: string; section_label: string; section_sequence: number;
  applicability: boolean; status: string; status_label: string; failure_reason: string;
  suggested_responsible_party: string; remediation: ReadinessRemediation | null;
};
export type ReadinessSummary = {
  rule_count: number;
  applicable_count: number;
  verified_count: number;
  configured_count: number;
  needs_attention_count: number;
  pending_business_validation_count: number;
  not_applicable_count: number;
};
export type ReadinessMaintenanceScope = {
  kind: 'enterprise_configuration';
  company_id: number;
  company_name: string;
  enterprise_managed: string[];
  platform_managed: string[];
  business_validation_required: string[];
};
type ReadinessEnvelope = {
  contract_version: string;
  company_id: number;
  company_name: string;
  maintenance_scope: ReadinessMaintenanceScope;
  summary: ReadinessSummary;
  rules: ReadinessRule[];
};

const summaryKeys: Array<keyof ReadinessSummary> = [
  'rule_count', 'applicable_count', 'verified_count', 'configured_count',
  'needs_attention_count', 'pending_business_validation_count', 'not_applicable_count',
];

function textList(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(item => typeof item === 'string' && Boolean(item.trim()));
}

export function requireReadiness(value: ReadinessEnvelope): ReadinessEnvelope {
  const summary = value?.summary;
  const scope = value?.maintenance_scope;
  if (!value || value.contract_version !== 'enterprise_readiness.v2' || !Number.isInteger(value.company_id)
    || value.company_id <= 0 || !Array.isArray(value.rules) || value.rules.some(row => !row
      || typeof row.rule_key !== 'string' || !row.rule_key || typeof row.label !== 'string' || !row.label
      || typeof row.section_key !== 'string' || !row.section_key
      || typeof row.section_label !== 'string' || !row.section_label
      || !Number.isInteger(row.section_sequence) || row.section_sequence <= 0
      || typeof row.status_label !== 'string' || !row.status_label || typeof row.status !== 'string'
      || typeof row.applicability !== 'boolean' || typeof row.failure_reason !== 'string'
      || typeof row.suggested_responsible_party !== 'string'
      || (row.remediation !== null && (!row.remediation || !['handling_entry', 'anchor'].includes(row.remediation.kind)
        || typeof row.remediation.key !== 'string' || !row.remediation.key
        || typeof row.remediation.label !== 'string' || !row.remediation.label)))
    || typeof value.company_name !== 'string' || !value.company_name.trim()
    || !scope || scope.kind !== 'enterprise_configuration'
    || scope.company_id !== value.company_id || scope.company_name !== value.company_name
    || !textList(scope.enterprise_managed) || !textList(scope.platform_managed)
    || !textList(scope.business_validation_required)
    || !summary || summaryKeys.some(key => !Number.isInteger(summary[key]) || summary[key] < 0)
    || summary.rule_count !== value.rules.length
    || summary.applicable_count !== summary.verified_count + summary.configured_count
      + summary.needs_attention_count + summary.pending_business_validation_count
    || summary.rule_count !== summary.applicable_count + summary.not_applicable_count) {
    throw contractGapError({ kind: 'contract_defect', missing: 'enterprise_readiness.v2',
      requiredDeclarationLayer: 'P1:smart_construction_scene:enterprise.readiness.diagnosis.get' }, '企业配置诊断契约不完整');
  }
  return value;
}

export function useEnterpriseReadiness() {
  const session = useSessionStore();
  const rules = ref<ReadinessRule[]>([]);
  const companyName = ref('');
  const maintenanceScope = ref<ReadinessMaintenanceScope | null>(null);
  const summary = ref<ReadinessSummary | null>(null);
  const state = ref<'loading' | 'ready' | 'error'>('loading');
  const errorMessage = ref('');
  const busy = ref(false);
  let sequence = 0;
  let disposed = false;
  let deactivated = false;
  const contextKey = () => JSON.stringify([session.token, session.recordContext?.company_id,
    session.recordContext?.selected?.company_id]);

  async function load() {
    const request = ++sequence;
    const key = contextKey();
    const epoch = currentContextEpoch();
    const current = () => !disposed && !deactivated && request === sequence
      && key === contextKey() && isCurrentContextEpoch(epoch) && session.initStatus === 'ready';
    rules.value = [];
    companyName.value = '';
    maintenanceScope.value = null;
    summary.value = null;
    state.value = 'loading';
    busy.value = false;
    errorMessage.value = '';
    if (!session.token || deactivated) return;
    if (session.initStatus === 'error') {
      state.value = 'error';
      errorMessage.value = session.initError || '会话初始化失败，请刷新重试';
      return;
    }
    if (session.initStatus !== 'ready') return;
    const company = session.recordContext?.company_id ?? session.recordContext?.selected?.company_id;
    busy.value = true;
    try {
      const result = await intentRequest<ReadinessEnvelope>({ intent: 'enterprise.readiness.diagnosis.get',
        params: company ? { company_id: company } : {} });
      if (!current()) return;
      const data = requireReadiness(result);
      if (company && data.company_id !== company) throw new Error('诊断公司与当前上下文不一致');
      rules.value = data.rules;
      companyName.value = data.company_name;
      maintenanceScope.value = data.maintenance_scope;
      summary.value = data.summary;
      state.value = 'ready';
    } catch (error) {
      if (!current()) return;
      state.value = 'error';
      errorMessage.value = error instanceof Error ? error.message : '诊断读取失败';
    } finally {
      if (request === sequence) busy.value = false;
    }
  }
  watch(() => [contextKey(), session.initStatus], () => { void load(); }, { immediate: true });
  onDeactivated(() => {
    deactivated = true;
    sequence += 1;
    rules.value = [];
    companyName.value = '';
    maintenanceScope.value = null;
    summary.value = null;
    busy.value = false;
  });
  onActivated(() => { if (deactivated) { deactivated = false; void load(); } });
  onScopeDispose(() => { disposed = true; sequence += 1; });
  return { rules, companyName, maintenanceScope, summary, state, errorMessage, busy, load };
}
