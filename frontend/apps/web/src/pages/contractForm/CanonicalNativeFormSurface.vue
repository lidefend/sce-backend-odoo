<template>
  <article class="sc-native-contract-page" data-native-contract-structure>
    <FormSectionNavigation
      v-if="sectionLinks.length > 1"
      :items="sectionLinks"
      root-selector="[data-native-contract-structure]"
    />
    <main class="sc-native-contract-tree" data-canonical-zone="primary">
      <NativeFormTreeRenderer
        v-if="nativeBridge"
        :nodes="nativeBridge.primaryNodes"
        :field-schemas-for-nodes="nativeBridge.fieldSchemasForNodes"
        :is-node-visible="nativeBridge.nodeVisible"
        :relation-adapter="relationAdapter"
        :native-action-handler="runNativeCanonicalAction"
        :native-action-state-resolver="nativeBridge.actionStateForNode"
        :prefer-readonly-facts="renderMode === 'readonly'"
        :authoritative-business-section-mode="nativeBridge.authoritativeBusinessSectionMode"
        @field-change="emit('field-change', $event)"
        @field-action="emit('field-action', $event)"
      />
    </main>
    <section v-if="nativeBridge?.subordinateNodes.length" class="sc-native-contract-subordinate" data-canonical-zone="subordinate">
      <NativeFormTreeRenderer
        :nodes="nativeBridge.subordinateNodes"
        :field-schemas-for-nodes="nativeBridge.fieldSchemasForNodes"
        :is-node-visible="nativeBridge.nodeVisible"
        :relation-adapter="relationAdapter"
        :native-action-handler="runNativeCanonicalAction"
        :native-action-state-resolver="nativeBridge.actionStateForNode"
        :prefer-readonly-facts="renderMode === 'readonly'"
        :authoritative-business-section-mode="nativeBridge.authoritativeBusinessSectionMode"
        @field-change="emit('field-change', $event)"
        @field-action="emit('field-action', $event)"
      />
    </section>
    <section
      v-if="showCollaborationPanel"
      class="sc-native-contract-collaboration"
      data-form-semantic-role="activity"
      data-form-section-target="surface:activity"
      data-section-content-kind="collaboration-panel"
      data-section-source-identity="collaboration-panel"
    >
      <NativeCollaborationPanel
        v-bind="collaborationPanelProps"
        :show-audit-timeline="true"
        v-on="collaborationPanelListeners || {}"
      />
    </section>
    <CanonicalActionBar
      v-if="visibleActions.length && !actionsInHeader"
      :direct-actions="directActions"
      :overflow-actions="overflowActions"
      :effective-primary-key="effectivePrimaryKey"
      @action-ref="emit('action-ref', $event)"
    />
  </article>
</template>

<script setup lang="ts">
import type { CanonicalFormAction, CanonicalFormRenderMode } from '../../app/presentation/canonicalFormRenderModel';
import type { ContractV2ActionRule } from '../../app/contracts/v2/types';
import NativeFormTreeRenderer from '../../components/template/NativeFormTreeRenderer.vue';
import type { FormSectionFieldActionPayload, FormSectionFieldChange } from '../../components/template/formSection.types';
import type { RelationFieldAdapter } from '../../components/template/relationField.types';
import CanonicalActionBar from './CanonicalActionBar.vue';
import FormSectionNavigation from './FormSectionNavigation.vue';
import NativeCollaborationPanel, {
  type NativeCollaborationPanelListeners,
  type NativeCollaborationPanelProps,
} from './NativeCollaborationPanel.vue';
import type { CanonicalNativeFormBridge } from './canonicalNativeFormBridge';
import type { WorkspaceSectionNavigationItem } from './nativeSectionNavigation';

const props = defineProps<{
  nativeBridge: CanonicalNativeFormBridge | null;
  sectionLinks: WorkspaceSectionNavigationItem[];
  renderMode: CanonicalFormRenderMode;
  relationAdapter?: RelationFieldAdapter;
  showCollaborationPanel?: boolean;
  collaborationPanelProps?: NativeCollaborationPanelProps;
  collaborationPanelListeners?: NativeCollaborationPanelListeners;
  visibleActions: CanonicalFormAction[];
  directActions: CanonicalFormAction[];
  overflowActions: CanonicalFormAction[];
  effectivePrimaryKey: string;
  actionsInHeader?: boolean;
}>();
const emit = defineEmits<{
  'field-change': [payload: FormSectionFieldChange];
  'field-action': [payload: FormSectionFieldActionPayload];
  'action-ref': [action: ContractV2ActionRule];
}>();

function runNativeCanonicalAction(payload: Record<string, unknown>) {
  const action = props.nativeBridge?.actionForPayload(payload);
  if (action) emit('action-ref', action);
}
</script>

<style scoped>
.sc-native-contract-page :deep([data-form-section-target]) {
  scroll-margin-top: calc(var(--sc-form-command-bar-height, 72px) + var(--sc-form-section-nav-height, 0px) + var(--sc-form-sticky-gap, 8px) * 2);
}
.sc-native-contract-page,
.sc-native-contract-tree,
.sc-native-contract-subordinate,
.sc-native-contract-collaboration {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}
</style>
