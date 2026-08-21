<template>
  <nav v-if="directActions.length || overflowActions.length" class="canonical-action-bar" aria-label="表单业务动作" data-canonical-action-bar>
    <SceneButton
      v-for="action in directActions"
      :key="action.key"
      :tier="action.key === effectivePrimaryKey ? 'primary' : 'secondary'"
      :disabled="!action.enabled"
      :data-action-ref="action.actionRef.actionId"
      :data-backend-identity="action.actionRef.backendIdentity"
      :data-action-tier="action.key === effectivePrimaryKey ? 'primary' : action.tier"
      :data-normalized-action-tier="action.tier"
      :data-action-enabled="String(action.enabled)"
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
          :data-backend-identity="action.actionRef.backendIdentity"
          :data-action-tier="action.tier"
          :data-action-enabled="String(action.enabled)"
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
  .canonical-action-bar { display: grid; grid-template-columns: minmax(0, 1fr); }
  .canonical-action-bar :deep(button) { width: 100%; }
  .canonical-action-bar__overflow-panel { position: static; min-width: 0; margin-top: 8px; }
}
</style>
