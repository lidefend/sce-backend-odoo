<template>
  <nav
    v-if="directActions.length || overflowActions.length"
    class="canonical-action-bar"
    aria-label="表单业务动作"
    data-canonical-action-bar
    data-semantic-component="CanonicalActionBar"
    data-state="ready"
    data-professional-workflow-component="action-bar"
    :data-workflow-action-count="authority.actionCount"
    :data-workflow-disabled-count="authority.disabledCount"
    :data-workflow-primary-key="authority.primaryKey"
  >
    <ActionReasonTrigger
      v-for="action in directActions"
      :key="action.key"
      :reason="workflowDisabledReason(action)"
      :trigger-key="action.key"
    >
      <SceneButton
        :tier="action.key === effectivePrimaryKey ? 'primary' : 'secondary'"
        :disabled="actionControlState(action).disabled"
        :loading="actionControlState(action).loading"
        :loading-label="`${action.label}处理中`"
        :aria-busy="actionControlState(action).loading || undefined"
        :data-action-ref="action.actionRef.actionId"
        :data-action-key="action.actionRef.actionKey || ''"
        :data-action-method="action.actionRef.button?.name || action.actionRef.button?.method || ''"
        :data-backend-identity="action.actionRef.backendIdentity"
        :data-action-tier="action.key === effectivePrimaryKey ? 'primary' : action.tier"
        :data-normalized-action-tier="action.tier"
        :data-action-enabled="String(action.enabled)"
        :data-action-loading="actionControlState(action).loading || undefined"
        :data-disabled-reason="workflowDisabledReason(action) || undefined"
        :title="workflowDisabledReason(action) || undefined"
        :data-action-allowed="String(action.actionRef.allowed === true)"
        :data-visible-profiles="action.visibleProfiles.join(',')"
        @activate="!actionControlState(action).disabled && emit('action-ref', action.actionRef)"
      >
        <ScIcon v-if="canonicalFormActionIconClass(action.icon)" class="canonical-action-bar__icon" :name="canonicalFormActionIconClass(action.icon) || 'check'" :size="16" />
        <span>{{ action.label }}</span>
      </SceneButton>
    </ActionReasonTrigger>
    <ScDropdown
      v-if="overflowActions.length"
      class="canonical-action-bar__overflow"
      :data-overflow-count="overflowActions.length"
      :items="overflowActions.map((action) => ({
        value: action.key,
        label: action.label,
        disabled: actionControlState(action).disabled,
        loading: actionControlState(action).loading,
        reasonMessage: workflowDisabledReason(action),
      }))"
      @select="selectOverflowAction"
    >
      <template #trigger><ScButton variant="secondary" aria-label="展开更多表单操作">更多操作</ScButton></template>
    </ScDropdown>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { SceneButton } from '@sc/ui/form';
import type { ContractV2ActionRule } from '../../app/contracts/v2/types';
import type { CanonicalFormAction } from '../../app/presentation/canonicalFormRenderModel';
import ScIcon from '../../components/design-system/ScIcon.vue';
import ScButton from '../../components/design-system/ScButton.vue';
import ScDropdown, { type ScDropdownItem } from '../../components/design-system/ScDropdown.vue';
import ActionReasonTrigger from './ActionReasonTrigger.vue';
import { canonicalFormActionIconClass } from './canonicalFormActionIcon';
import { resolveWorkflowActionBarAuthority, workflowDisabledReason } from './professionalWorkflowModel';
import { resolveActionInteractionState, useActionExecutionIdentity } from './actionInteractionState';

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
const actionExecutionIdentity = useActionExecutionIdentity();
function actionControlState(action: CanonicalFormAction) {
  return resolveActionInteractionState(action, actionExecutionIdentity.value);
}
function selectOverflowAction(item: ScDropdownItem) {
  const action = props.overflowActions.find((candidate) => candidate.key === String(item.value));
  if (action && !actionControlState(action).disabled) emit('action-ref', action.actionRef);
}
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
.canonical-action-bar__overflow { align-self: center; }
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
