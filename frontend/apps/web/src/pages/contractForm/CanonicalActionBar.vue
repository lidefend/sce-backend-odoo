<template>
  <nav v-if="directActions.length || overflowActions.length" class="canonical-action-bar" aria-label="表单业务动作" data-canonical-action-bar>
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
      :data-action-allowed="String(action.actionRef.allowed === true)"
      :data-visible-profiles="action.visibleProfiles.join(',')"
      @activate="action.enabled && emit('action-ref', action.actionRef)"
    >
      <span v-if="canonicalFormActionIconClass(action.icon)" :class="['canonical-action-bar__icon', canonicalFormActionIconClass(action.icon)]" aria-hidden="true" />
      <span>{{ action.label }}</span>
    </SceneButton>
    <details v-if="overflowActions.length" class="canonical-action-bar__overflow">
      <summary>更多操作</summary>
      <div class="canonical-action-bar__overflow-panel">
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
          :data-action-allowed="String(action.actionRef.allowed === true)"
          :data-visible-profiles="action.visibleProfiles.join(',')"
          @activate="action.enabled && emit('action-ref', action.actionRef)"
        >
          <span v-if="canonicalFormActionIconClass(action.icon)" :class="['canonical-action-bar__icon', canonicalFormActionIconClass(action.icon)]" aria-hidden="true" />
          <span>{{ action.label }}</span>
        </SceneButton>
      </div>
    </details>
  </nav>
</template>

<script setup lang="ts">
import { SceneButton } from '@sc/ui/form';
import type { ContractV2ActionRule } from '../../app/contracts/v2/types';
import type { CanonicalFormAction } from '../../app/presentation/canonicalFormRenderModel';
import { canonicalFormActionIconClass } from './canonicalFormActionIcon';

defineProps<{
  directActions: CanonicalFormAction[];
  overflowActions: CanonicalFormAction[];
  effectivePrimaryKey: string;
}>();
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
.canonical-action-bar__overflow > summary { cursor: pointer; color: var(--sc-app-text-primary); }
.canonical-action-bar__overflow-panel {
  position: absolute;
  z-index: 20;
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
