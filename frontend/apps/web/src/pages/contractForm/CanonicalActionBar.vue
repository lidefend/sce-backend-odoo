<template>
  <nav
    v-if="directActions.length || overflowActions.length"
    class="canonical-action-bar"
    aria-label="表单业务动作"
    data-canonical-action-bar
    data-semantic-component="CanonicalActionBar"
    :data-state="busy ? 'loading' : 'ready'"
    data-professional-workflow-component="action-bar"
    :data-workflow-action-count="authority.actionCount"
    :data-workflow-disabled-count="authority.disabledCount"
    :data-workflow-primary-key="authority.primaryKey"
  >
    <SceneButton
      v-for="action in directActions"
      :key="action.key"
      :tier="action.key === effectivePrimaryKey ? 'primary' : 'secondary'"
      :disabled="!action.enabled"
      :data-action-ref="action.actionRef.actionId"
      :data-action-key="action.actionRef.actionKey || ''"
      :data-action-method="action.actionRef.button?.name || action.actionRef.button?.method || ''"
      :data-backend-identity="action.actionRef.backendIdentity"
      :data-action-tier="action.key === effectivePrimaryKey ? 'primary' : action.tier"
      :data-normalized-action-tier="action.tier"
      :data-action-enabled="String(action.enabled)"
      :data-disabled-reason="workflowDisabledReason(action) || undefined"
      :title="workflowDisabledReason(action) || undefined"
      :data-action-allowed="String(action.actionRef.allowed === true)"
      :data-visible-profiles="action.visibleProfiles.join(',')"
      @activate="action.enabled && emit('action-ref', action.actionRef)"
    >
      <ScIcon v-if="canonicalFormActionIconClass(action.icon)" class="canonical-action-bar__icon" :name="canonicalFormActionIconClass(action.icon) || 'check'" :size="16" />
      <span>{{ action.label }}</span>
    </SceneButton>
    <details v-if="overflowActions.length" class="canonical-action-bar__overflow" :data-overflow-count="overflowActions.length">
      <summary aria-label="展开更多表单操作">更多操作</summary>
      <div class="canonical-action-bar__overflow-panel" aria-label="更多表单操作">
        <SceneButton
          v-for="action in overflowActions"
          :key="action.key"
          tier="transparent"
          :disabled="!action.enabled"
          :data-action-ref="action.actionRef.actionId"
          :data-action-key="action.actionRef.actionKey || ''"
          :data-action-method="action.actionRef.button?.name || action.actionRef.button?.method || ''"
          :data-backend-identity="action.actionRef.backendIdentity"
          :data-action-tier="action.tier"
          :data-action-enabled="String(action.enabled)"
          :data-disabled-reason="workflowDisabledReason(action) || undefined"
          :title="workflowDisabledReason(action) || undefined"
          :data-action-allowed="String(action.actionRef.allowed === true)"
          :data-visible-profiles="action.visibleProfiles.join(',')"
          @activate="action.enabled && emit('action-ref', action.actionRef)"
        >
          <ScIcon v-if="canonicalFormActionIconClass(action.icon)" class="canonical-action-bar__icon" :name="canonicalFormActionIconClass(action.icon) || 'check'" :size="16" />
          <span>{{ action.label }}</span>
        </SceneButton>
      </div>
    </details>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { SceneButton } from '@sc/ui/form';
import type { ContractV2ActionRule } from '../../app/contracts/v2/types';
import type { CanonicalFormAction } from '../../app/presentation/canonicalFormRenderModel';
import ScIcon from '../../components/design-system/ScIcon.vue';
import { canonicalFormActionIconClass } from './canonicalFormActionIcon';
import { resolveWorkflowActionBarAuthority, workflowDisabledReason } from './professionalWorkflowModel';

const props = defineProps<{
  directActions: CanonicalFormAction[];
  overflowActions: CanonicalFormAction[];
  effectivePrimaryKey: string;
}>();
const authority = computed(() => resolveWorkflowActionBarAuthority(
  props.directActions,
  props.overflowActions,
  props.effectivePrimaryKey,
));
const emit = defineEmits<{ 'action-ref': [action: ContractV2ActionRule] }>();
</script>

<style scoped>
.canonical-action-bar {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  min-width: 0;
}
.canonical-action-bar__icon { inline-size: 1em; margin-inline-end: 6px; text-align: center; }
.canonical-action-bar__overflow { position: relative; align-self: center; }
.canonical-action-bar__overflow > summary { display: inline-flex; min-height: calc(var(--sc-component-button-height-md) * 1px); align-items: center; padding-inline: var(--sc-product-space-2); border: 1px solid var(--sc-app-border); border-radius: var(--sc-component-button-radius); background: var(--sc-app-panel); color: var(--sc-app-text-primary); cursor: pointer; list-style: none; }
.canonical-action-bar__overflow > summary::-webkit-details-marker { display: none; }
.canonical-action-bar__overflow-panel {
  position: absolute;
  z-index: var(--sc-component-button-overflow-z-index);
  top: calc(100% + var(--sc-product-space-1));
  right: 0;
  display: grid;
  gap: 6px;
  min-width: 240px;
  padding: 10px;
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  background: var(--sc-app-panel);
  box-shadow: var(--sc-app-shadow-popover);
}
.canonical-action-bar__overflow-panel :deep(button) { width: 100%; justify-content: flex-start; }
@media (max-width: 560px) {
  .canonical-action-bar {
    display: flex;
    flex-wrap: nowrap;
    align-items: center;
    width: 100%;
  }
  .canonical-action-bar :deep(button) {
    width: auto;
    min-height: 44px;
    white-space: nowrap;
  }
  .canonical-action-bar :deep(button[data-action-tier='primary']) {
    flex: 1 1 auto;
    width: 100%;
  }
  .canonical-action-bar__overflow > summary {
    display: inline-flex;
    min-height: 44px;
    align-items: center;
    white-space: nowrap;
  }
  .canonical-action-bar__overflow-panel {
    position: absolute;
    top: auto;
    right: 0;
    bottom: calc(100% + 10px);
    width: min(320px, calc(100vw - 24px));
    min-width: 0;
    max-height: min(60vh, 420px);
    overflow-y: auto;
  }
  .canonical-action-bar__overflow-panel :deep(button) { width: 100%; }
}
</style>
