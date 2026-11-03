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
