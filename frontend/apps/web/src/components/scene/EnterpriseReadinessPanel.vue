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

<script setup lang="ts">
import ScButton from '../design-system/ScButton.vue';
import { useEnterpriseReadiness, type ReadinessRemediation } from '../../composables/useEnterpriseReadiness';

defineEmits<{ (e: 'remediate', target: ReadinessRemediation): void }>();
const { rules, state, errorMessage, busy, load } = useEnterpriseReadiness();
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
