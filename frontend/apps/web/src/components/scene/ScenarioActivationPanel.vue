<template>
  <section id="enterprise-scenario-activation" class="scenario-activation-panel" data-semantic-component="ScenarioActivationPanel" :data-state="state">
    <header class="scenario-activation-panel__header">
      <div>
        <h3>{{ catalogPresentation?.title }}</h3>
        <p v-if="actor && targetScope" class="scenario-activation-panel__scope">
          操作者：{{ actor.name || actor.login }} · 目标公司：{{ targetScope.company_name || targetScope.company_id }}
          <span v-if="actor.platform_admin">· 平台管理员</span>
        </p>
        <p v-if="catalogPresentation" class="scenario-activation-panel__scope">{{ catalogPresentation.summary }}</p>
      </div>
      <ScButton size="small" variant="ghost" type="button" :disabled="busy" @click="refresh">刷新</ScButton>
    </header>
    <ScInlineState
      v-if="readback"
      state="success"
      :label="`已回读：${readback.readback.enabled ? '已启用' : '已停用'} · 公司 ${readback.readback.company_id} · ${readback.readback.source} · 未授予用户访问权限`"
    />
    <ScInlineState
      v-if="centerReadback"
      state="success"
      :label="`已启用 ${centerReadback.center_keys.length} 个业务中心、${centerReadback.enabled_scene_count} 个业务场景 · 公司 ${centerReadback.company_id} · 未授予用户访问权限`"
    />
    <ScInlineState v-if="state === 'loading'" state="loading" label="正在读取场景目录…" />
    <ScInlineState v-else-if="state === 'error'" state="error" :label="errorMessage" />
    <template v-else>
      <ScInlineState v-if="!rows.length || !businessCenters.length" state="empty" :label="catalogEmptyLabel" />
      <template v-else>
        <section class="scenario-activation-panel__centers" data-center-selector>
          <header class="scenario-activation-panel__section-head">
            <div>
              <h4>{{ centerActivation?.title }}</h4>
              <p>{{ centerActivation?.description }}</p>
            </div>
            <span class="scenario-activation-panel__selection-count">
              {{ centerActivation?.selection_label }}：{{ selectedCenters.length }}
              {{ centerActivation?.selection_count_label }} · {{ selectedSceneCount }}
              {{ centerActivation?.scene_count_label }}
            </span>
          </header>
          <div class="scenario-activation-panel__center-grid">
            <article
              v-for="center in businessCenters"
              :key="center.key"
              class="scenario-activation-panel__center"
              :data-center-key="center.key"
              :data-center-status="center.status"
            >
              <div class="scenario-activation-panel__center-title">
                <ScCheckbox
                  :checked="selectedCenterKeys.includes(center.key)"
                  :disabled="busy || !center.enable_allowed"
                  :label="center.name"
                  @update:checked="toggleCenter(center.key)"
                />
                <span v-if="center.default_selected" class="scenario-activation-panel__recommended">推荐</span>
              </div>
              <p class="scenario-activation-panel__center-meta">
                {{ center.scene_count }} 个业务场景 · {{ center.status_label }}
                <template v-if="center.status === 'partial'">
                  （{{ center.enabled_scene_count }}/{{ center.scene_count }}）
                </template>
              </p>
            </article>
          </div>
          <div class="scenario-activation-panel__center-actions">
            <p>推荐选中只代表本次准备启用的范围，提交前不会改变企业当前状态。</p>
            <ScButton
              variant="primary"
              type="button"
              :disabled="busy || !selectedCenters.length || selectedCenters.some(center => !center.enable_allowed)"
              @click="applyCenters"
            >
              {{ centerActivation?.apply_label }}
            </ScButton>
          </div>
        </section>
        <ScDisclosure
          class="scenario-activation-panel__advanced"
          :title="centerActivation?.advanced_label || ''"
        >
          <ul class="scenario-activation-panel__list">
            <li v-for="row in rows" :key="row.scene_key" class="scenario-activation-panel__row">
              <div class="scenario-activation-panel__row-main">
                <span class="scenario-activation-panel__name">{{ row.name }}</span>
                <span class="scenario-activation-panel__state">{{ row.release_label }}</span>
                <span class="scenario-activation-panel__enabled">{{ row.status_label }}</span>
              </div>
              <p class="scenario-activation-panel__qualification">
                产品资格：{{ row.product_qualification.label }}
                · 生效版本：{{ qualificationVersion(row) }}
              </p>
              <p v-if="row.enablement_blockers.length" class="scenario-activation-panel__blockers">
                启用阻断：{{ row.enablement_blockers.join(' · ') }}
              </p>
              <ScButton
                v-for="action in row.actions"
                :key="action.key"
                size="small"
                variant="ghost"
                type="button"
                :disabled="busy"
                :title="row.enablement_blockers.join(' · ') || action.key + ' 至 ' + String(action.enabled)"
                @click="execute(row, action)"
              >
                {{ action.label }}
              </ScButton>
            </li>
          </ul>
        </ScDisclosure>
      </template>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import ScButton from '../design-system/ScButton.vue';
import ScCheckbox from '../design-system/ScCheckbox.vue';
import ScDisclosure from '../design-system/ScDisclosure.vue';
import ScInlineState from '../design-system/ScInlineState.vue';
import { useScenarioActivation, type BusinessScenario } from '../../composables/useScenarioActivation';

const {
  rows, businessCenters, centerActivation, selectedCenterKeys, catalogPresentation, catalogStatus,
  actor,
  targetScope,
  readback,
  centerReadback,
  state,
  errorMessage,
  busy,
  refresh,
  execute,
  toggleCenter,
  applyCenters,
} = useScenarioActivation();

const selectedCenters = computed(() => businessCenters.value.filter(center => selectedCenterKeys.value.includes(center.key)));
const selectedSceneCount = computed(() => new Set(selectedCenters.value.flatMap(center => center.scene_keys)).size);

const catalogEmptyLabel = computed(() => {
  if (!rows.value.length) {
    return catalogPresentation.value?.empty_label || '';
  }
  return catalogStatus.value === 'ready' ? '' : `目录状态：${catalogStatus.value}。`;
});

function qualificationVersion(row: BusinessScenario) {
  const evidence = row.product_qualification.evidence;
  if (typeof evidence.version === 'string' && evidence.version) return evidence.version;
  const products = Array.isArray(evidence.products) ? evidence.products : [];
  const standard = products.find((item) => item.product_key === 'construction.standard');
  return typeof standard?.version === 'string' && standard.version ? standard.version : '未返回';
}
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
.scenario-activation-panel__scope { margin: 4px 0 0; color: var(--sc-app-text-secondary); font-size: 12px; }
.scenario-activation-panel__centers {
  margin-top: 16px;
  padding: 16px;
  border: 1px solid var(--sc-app-border);
  border-radius: 10px;
  background: var(--sc-app-subtle-bg);
}
.scenario-activation-panel__section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.scenario-activation-panel__section-head h4 { margin: 0; font-size: 15px; }
.scenario-activation-panel__section-head p {
  margin: 6px 0 0;
  color: var(--sc-app-text-secondary);
  font-size: 13px;
}
.scenario-activation-panel__selection-count {
  color: var(--sc-app-text-secondary);
  font-size: 12px;
  white-space: nowrap;
}
.scenario-activation-panel__center-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
  gap: 10px;
  margin-top: 14px;
}
.scenario-activation-panel__center {
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  background: var(--sc-app-panel);
}
.scenario-activation-panel__center:has(.sc-checkbox[data-checked='true']) {
  border-color: var(--sc-app-primary);
  box-shadow: inset 0 0 0 1px var(--sc-app-primary);
}
.scenario-activation-panel__center-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.scenario-activation-panel__recommended {
  flex: none;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--sc-app-selected-bg);
  color: var(--sc-app-selected-text);
  font-size: 11px;
}
.scenario-activation-panel__center-meta {
  margin: 8px 0 0;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}
.scenario-activation-panel__center-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--sc-app-border);
}
.scenario-activation-panel__center-actions p {
  margin: 0;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}
.scenario-activation-panel__advanced {
  margin-top: 14px;
  border-top: 1px solid var(--sc-app-border);
  padding-top: 12px;
}
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
.scenario-activation-panel__qualification, .scenario-activation-panel__blockers {
  margin: 6px 0;
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}
.scenario-activation-panel__blockers { color: var(--sc-app-danger-text); }
.scenario-activation-panel__detail { display: grid; gap: 8px; font-size: 13px; }
.scenario-activation-panel__detail :deep(button) { justify-self: start; }
.scenario-activation-panel__status { padding: 16px 0; color: var(--sc-app-text-secondary); }
.scenario-activation-panel__status--error { color: var(--sc-app-danger-text); }
</style>
