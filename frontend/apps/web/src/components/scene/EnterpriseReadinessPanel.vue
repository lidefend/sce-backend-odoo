<template>
  <section class="enterprise-readiness-panel" data-semantic-component="EnterpriseReadinessPanel" :data-state="state">
    <header class="enterprise-readiness-panel__header">
      <h3>企业业务配置诊断</h3>
      <ScButton size="small" variant="ghost" type="button" :disabled="busy" @click="load">
        刷新
      </ScButton>
    </header>

    <div v-if="state === 'loading'" class="enterprise-readiness-panel__status">正在读取企业配置状态…</div>
    <div v-else-if="state === 'error'" class="enterprise-readiness-panel__status enterprise-readiness-panel__status--error">
      {{ errorMessage }}
    </div>
    <ul v-else class="enterprise-readiness-panel__list">
      <li v-for="rule in rules" :key="rule.rule_key" class="enterprise-readiness-panel__row">
        <div class="enterprise-readiness-panel__row-main">
          <span class="enterprise-readiness-panel__label">{{ labelFor(rule.rule_key) }}</span>
          <span class="enterprise-readiness-panel__state" :class="`is-${rule.status.toLowerCase()}`">
            {{ statusLabel(rule) }}
          </span>
          <span v-if="!rule.applicability" class="enterprise-readiness-panel__not-applicable">不适用</span>
        </div>
        <div class="enterprise-readiness-panel__detail">
          <span v-if="rule.failure_reason">原因：{{ rule.failure_reason }}</span>
          <span v-if="rule.affected_scenarios?.length">影响：{{ rule.affected_scenarios.join('、') }}</span>
          <span v-if="rule.suggested_responsible_party">建议处理：{{ rule.suggested_responsible_party }}</span>
          <ScButton
            v-if="actionableKey(rule.remediation_entry)"
            size="small"
            variant="ghost"
            type="button"
            @click="$emit('remediate', actionableKey(rule.remediation_entry))"
          >
            去处理
          </ScButton>
          <span v-else-if="rule.remediation_entry">处理入口：{{ remediationLabel(rule.remediation_entry) }}</span>
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { intentRequest } from '../../api/intents';
import ScButton from '../design-system/ScButton.vue';

type ReadinessRule = {
  rule_key: string;
  evaluation_layer: string;
  applicability: boolean;
  status: string;
  authoritative_source: string;
  evidence: Record<string, unknown>;
  failure_reason: string;
  affected_scenarios: string[];
  remediation_entry: string;
  suggested_responsible_party: string;
};

type ReadinessEnvelope = {
  company_id: number;
  company_name: string;
  checked_at: string;
  rules: ReadinessRule[];
};

defineEmits<{ (e: 'remediate', entryKey: string): void }>();
const rules = ref<ReadinessRule[]>([]);
const state = ref<'loading' | 'ready' | 'error'>('loading');
const errorMessage = ref('');
const busy = ref(false);

const LABELS: Record<string, string> = {
  'enterprise.identity': '企业身份',
  'enterprise.organization': '组织架构',
  'enterprise.positions': '岗位体系',
  'enterprise.users': '用户身份',
  'enterprise.employees': '员工档案',
  'enterprise.user_employee_link': '用户与员工关联',
  'enterprise.user_org_position': '用户与部门、岗位关系',
  'enterprise.roles': '系统角色',
  'enterprise.project_responsibility': '项目成员责任',
  'enterprise.scenario_enablement': '企业场景启用',
  'enterprise.scenario_dependencies': '场景依赖',
  'enterprise.role_delivery': '角色工作空间交付',
};

const REMEDIATION_ACTION_KEYS: Record<string, string> = {
  'enterprise.info': 'company',
  'organization.department': 'department',
  'job.management': 'post',
  'user.management': 'user',
};

function labelFor(ruleKey: string) {
  return LABELS[ruleKey] || ruleKey;
}

function remediationLabel(entry: string) {
  return entry || '—';
}

function actionableKey(entry: string) {
  return REMEDIATION_ACTION_KEYS[entry] || '';
}

function statusLabel(rule: ReadinessRule) {
  if (!rule.applicability) return '不适用';
  if (rule.status === 'VERIFIED') return '已验证';
  if (rule.status === 'CONFIGURED') return '待验证';
  if (rule.status === 'NOT_CONFIGURED') return '未配置';
  return rule.status || '未知';
}

async function load() {
  state.value = 'loading';
  errorMessage.value = '';
  try {
    const data = await intentRequest<ReadinessEnvelope>({
      intent: 'enterprise.readiness.diagnosis.get',
      params: {},
    });
    rules.value = Array.isArray(data?.rules) ? data.rules : [];
    state.value = 'ready';
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : '诊断读取失败';
    state.value = 'error';
  }
}

onMounted(load);
</script>
