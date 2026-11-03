<template>
  <section id="enterprise-scenario-activation" class="scenario-activation-panel" data-semantic-component="ScenarioActivationPanel" :data-state="state">
    <header class="scenario-activation-panel__header">
      <h3>企业业务场景管理</h3>
      <ScButton size="small" variant="ghost" type="button" :disabled="busy" @click="refresh">刷新</ScButton>
    </header>
    <div v-if="state === 'loading'" class="scenario-activation-panel__status">正在读取场景目录…</div>
    <div v-else-if="state === 'error'" class="scenario-activation-panel__status scenario-activation-panel__status--error">
      {{ errorMessage }}
    </div>
    <div v-else-if="!rows.length" class="scenario-activation-panel__status">暂无场景目录。</div>
    <ul v-else class="scenario-activation-panel__list">
      <li v-for="row in rows" :key="row.scene_key" class="scenario-activation-panel__row">
        <div class="scenario-activation-panel__row-main">
          <span class="scenario-activation-panel__name">{{ row.name }}</span>
          <span class="scenario-activation-panel__state">{{ row.release_label }}</span>
          <span class="scenario-activation-panel__enabled">{{ row.status_label }}</span>
        </div>
        <ScButton
          v-for="action in row.actions"
          :key="action.key"
          size="small"
          variant="ghost"
          type="button"
          :disabled="busy"
          @click="execute(row, action)"
        >
          {{ action.label }}
        </ScButton>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import ScButton from '../design-system/ScButton.vue';
import { useScenarioActivation } from '../../composables/useScenarioActivation';

const { rows, state, errorMessage, busy, refresh, execute } = useScenarioActivation();
</script>

<style scoped>
.scenario-activation-panel {
  margin-top: 20px;
  padding: 16px;
  border: 1px solid var(--sc-app-border);
  border-radius: 12px;
  background: var(--sc-app-panel);
  color: var(--sc-app-text-primary);
  scroll-margin-top: 20px;
}
.scenario-activation-panel__header, .scenario-activation-panel__row-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.scenario-activation-panel__header h3 { margin: 0; font-size: 16px; }
.scenario-activation-panel__list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 310px), 1fr));
  gap: 12px;
  padding: 0;
  margin: 16px 0 0;
  list-style: none;
}
.scenario-activation-panel__row {
  padding: 14px;
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  min-width: 0;
}
.scenario-activation-panel__row-main { margin-bottom: 8px; }
.scenario-activation-panel__label, .scenario-activation-panel__name { font-weight: 600; }
.scenario-activation-panel__state, .scenario-activation-panel__enabled {
  font-size: 12px;
  color: var(--sc-app-text-secondary);
}
.scenario-activation-panel__detail { display: grid; gap: 8px; font-size: 13px; }
.scenario-activation-panel__detail :deep(button) { justify-self: start; }
.scenario-activation-panel__status { padding: 16px 0; color: var(--sc-app-text-secondary); }
.scenario-activation-panel__status--error { color: var(--sc-app-danger-text); }
</style>
