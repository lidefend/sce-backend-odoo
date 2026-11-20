<template>
  <section
    class="enterprise-readiness-panel"
    data-semantic-component="EnterpriseReadinessPanel"
    :data-state="state"
    :data-company-id="maintenanceScope?.company_id || undefined"
  >
    <header class="enterprise-readiness-panel__header">
      <div>
        <h3>企业基础配置状态</h3>
        <p v-if="companyName" class="enterprise-readiness-panel__scope">
          当前企业：{{ companyName }} · 企业配置管理员维护本企业基础配置
        </p>
      </div>
      <ScButton size="small" variant="ghost" type="button" :disabled="busy" @click="load">
        刷新
      </ScButton>
    </header>

    <ScInlineState v-if="state === 'loading'" state="loading" label="正在读取企业配置状态…" />
    <ScInlineState v-else-if="state === 'error'" state="error" :label="errorMessage" />
    <ScInlineState v-else-if="!rules.length" state="empty" label="暂无企业业务配置诊断项。" />
    <template v-else>
      <div v-if="summary" class="enterprise-readiness-panel__summary" aria-label="企业基础配置状态汇总">
        <span><strong>{{ summary.needs_attention_count }}</strong> 项需处理</span>
        <span><strong>{{ summary.pending_business_validation_count }}</strong> 项待业务验证</span>
        <span><strong>{{ summary.configured_count }}</strong> 项已配置</span>
        <span><strong>{{ summary.verified_count }}</strong> 项已验证</span>
      </div>
      <p
        v-if="summary?.pending_business_validation_count"
        class="enterprise-readiness-panel__validation-note"
      >
        基础配置不会替代实际业务办理。请使用目标业务角色的账号验证工作入口和数据范围。
      </p>
      <p v-if="maintenanceScope" class="enterprise-readiness-panel__boundary">
        平台管理：{{ maintenanceScope.platform_managed.join('、') }}。
        企业维护：{{ maintenanceScope.enterprise_managed.join('、') }}。
      </p>
      <section
        v-for="group in groupedRules"
        :key="group.key"
        class="enterprise-readiness-panel__group"
        :data-section-key="group.key"
      >
        <header class="enterprise-readiness-panel__group-header">
          <h4>{{ group.label }}</h4>
          <span>{{ group.rules.length }} 项</span>
        </header>
        <ul class="enterprise-readiness-panel__list">
          <li v-for="rule in group.rules" :key="rule.rule_key" class="enterprise-readiness-panel__row">
            <div class="enterprise-readiness-panel__row-main">
              <span class="enterprise-readiness-panel__label">{{ rule.label }}</span>
              <span class="enterprise-readiness-panel__state" :class="`is-${rule.status.toLowerCase()}`">
                {{ rule.status_label }}
              </span>
            </div>
            <div class="enterprise-readiness-panel__detail">
              <span v-if="rule.failure_reason">原因：{{ rule.failure_reason }}</span>
              <span v-if="rule.suggested_responsible_party">建议处理：{{ rule.suggested_responsible_party }}</span>
              <ScButton
                v-if="rule.remediation"
                size="small"
                variant="ghost"
                type="button"
                @click="$emit('remediate', rule.remediation)"
              >
                {{ rule.remediation.label }}
              </ScButton>
            </div>
          </li>
        </ul>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import ScButton from '../design-system/ScButton.vue';
import ScInlineState from '../design-system/ScInlineState.vue';
import { useEnterpriseReadiness, type ReadinessRemediation } from '../../composables/useEnterpriseReadiness';
import { groupEnterpriseReadinessRules } from '../../app/enterpriseReadinessPresentation';

defineEmits<{ (e: 'remediate', target: ReadinessRemediation): void }>();
const {
  rules, companyName, maintenanceScope, summary, state, errorMessage, busy, load,
} = useEnterpriseReadiness();

const groupedRules = computed(() => groupEnterpriseReadinessRules(rules.value));
</script>

<style scoped>
.enterprise-readiness-panel {
  margin-top: 20px;
  padding: 16px;
  border: 1px solid var(--sc-app-border);
  border-radius: 12px;
  background: var(--sc-app-panel);
  color: var(--sc-app-text-primary);
  scroll-margin-top: 20px;
}
.enterprise-readiness-panel__header, .enterprise-readiness-panel__row-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.enterprise-readiness-panel__header h3 { margin: 0; font-size: 16px; }
.enterprise-readiness-panel__scope {
  margin: 4px 0 0;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}
.enterprise-readiness-panel__summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
  margin-top: 14px;
  padding: 10px 12px;
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}
.enterprise-readiness-panel__summary strong {
  color: var(--sc-app-text-primary);
  font-size: 15px;
}
.enterprise-readiness-panel__validation-note,
.enterprise-readiness-panel__boundary {
  margin: 10px 0 0;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  line-height: 1.6;
}
.enterprise-readiness-panel__validation-note {
  color: var(--sc-app-warning-text, var(--sc-app-text-secondary));
}
.enterprise-readiness-panel__group {
  margin-top: 16px;
}
.enterprise-readiness-panel__group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.enterprise-readiness-panel__group-header h4 {
  margin: 0;
  font-size: 14px;
}
.enterprise-readiness-panel__group-header span {
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}
.enterprise-readiness-panel__list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 310px), 1fr));
  gap: 12px;
  padding: 0;
  margin: 16px 0 0;
  list-style: none;
}
.enterprise-readiness-panel__row {
  padding: 14px;
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  min-width: 0;
}
.enterprise-readiness-panel__row-main { margin-bottom: 8px; }
.enterprise-readiness-panel__label, .enterprise-readiness-panel__name { font-weight: 600; }
.enterprise-readiness-panel__state, .enterprise-readiness-panel__enabled {
  font-size: 12px;
  color: var(--sc-app-text-secondary);
}
.enterprise-readiness-panel__detail { display: grid; gap: 8px; font-size: 13px; }
.enterprise-readiness-panel__detail :deep(button) { justify-self: start; }
.enterprise-readiness-panel__status { padding: 16px 0; color: var(--sc-app-text-secondary); }
.enterprise-readiness-panel__status--error { color: var(--sc-app-danger-text); }
</style>
