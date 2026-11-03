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
