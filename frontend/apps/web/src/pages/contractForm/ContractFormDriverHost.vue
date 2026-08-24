<template>
  <section
    v-if="error || !renderModel"
    class="sc-form-driver-error"
    role="alert"
    data-contract-form-driver-error
  >
    <strong>页面契约无法渲染</strong>
    <span>{{ error || 'CANONICAL_FORM_RENDER_MODEL_MISSING' }}</span>
  </section>
  <section
    v-else
    class="sc-form-driver-host"
    :data-contract-form-driver="renderKit"
    :data-contract-form-driver-source="driverConfig?.resolutionSource || 'safe-default'"
    :data-contract-form-driver-reason="driverConfig?.reasonCode || ''"
    :data-source-contract-sha="renderModel.identity.sourceContractSha256"
    :data-render-model-fields="String(fieldCount)"
    :data-render-model-actions="String(renderModel.actionBar.length)"
  >
    <div v-if="allowUserOverride" class="sc-form-driver-chooser">
      <label for="contract-form-driver-kit">界面风格</label>
      <select id="contract-form-driver-kit" :value="activeKit" data-contract-form-driver-chooser @change="changeKit">
        <option v-for="kit in allowedKits" :key="kit" :value="kit">{{ kitLabel(kit) }}</option>
      </select>
    </div>
    <SceneUiProvider :kit="renderKit" fallback-kit="sc-native" density="compact">
      <TaskFormPattern v-if="renderModel.identity.presentationMode === 'task'" :render-profile="renderModel.identity.mode">
      <ObjectTaskPage
        :summary-nodes="floorplan.summaryNodes"
        :task-nodes="floorplan.taskNodes"
        :core-input-nodes="floorplan.coreInputNodes"
        :condition-input-nodes="floorplan.conditionInputNodes"
        :pre-execution-input-nodes="floorplan.preExecutionInputNodes"
        :pre-execution-input-title="floorplan.preExecutionInputTitle"
        :supplementary-input-nodes="floorplan.supplementaryInputNodes"
        :context-nodes="floorplan.contextNodes"
        :overflow-context-nodes="floorplan.overflowContextNodes"
        :risk-nodes="floorplan.riskNodes"
        :audit-nodes="floorplan.auditNodes"
        :audit-events="auditEvents"
        :has-audit="floorplan.auditDeclared"
        :relation-nodes="floorplan.relationNodes"
        :subordinate-nodes="floorplanSubordinateNodes"
        :decision-mode="true"
        :relation-adapter="relationAdapter"
        :has-collaboration="hasCollaboration"
        @field-change="emit('field-change', $event)"
      >
        <template v-if="floorplan.blockedActions.length" #blocking>
          <section class="canonical-form-blocking-notice" role="status" data-canonical-blocking-notice>
            <strong>当前操作暂不可用</strong>
            <span v-for="action in floorplan.blockedActions" :key="action.key">{{ action.label }}暂不可执行</span>
          </section>
        </template>
        <template v-if="hasCollaboration" #collaboration>
          <NativeCollaborationPanel
            v-if="showCollaborationPanel"
            v-bind="collaborationPanelProps"
            readonly
            v-on="collaborationPanelListeners"
          />
          <p v-else class="canonical-form-activity-empty">暂无活动记录</p>
        </template>
        <template v-if="showProductActions && !actionsInHeader" #actions>
          <nav class="canonical-product-edit-actions" aria-label="表单业务动作" data-canonical-action-bar>
            <SceneButton
              v-if="localSavePrimary"
              tier="primary"
              :disabled="busy"
              data-action-ref="form.save"
              data-action-tier="primary"
              data-action-enabled="true"
              @activate="emit('save')"
            >{{ renderModel.identity.mode === 'create' ? '保存草稿' : '保存修改' }}</SceneButton>
            <CanonicalActionBar
              v-else
              :direct-actions="floorplan.directActions"
              :overflow-actions="floorplan.overflowActions"
              :effective-primary-key="floorplan.effectivePrimaryKey"
              @action-ref="emit('action-ref', $event)"
            />
          </nav>
        </template>
      </ObjectTaskPage>
      </TaskFormPattern>
      <WorkspaceFormPattern v-else :render-profile="renderModel.identity.mode">
      <article class="sc-native-contract-page" data-native-contract-structure>
        <main class="sc-native-contract-tree" data-canonical-zone="primary">
          <NativeFormTreeRenderer
            v-if="nativeBridge"
            :nodes="nativeBridge.primaryNodes"
            :field-schemas-for-nodes="nativeBridge.fieldSchemasForNodes"
            :is-node-visible="nativeBridge.nodeVisible"
            :relation-adapter="relationAdapter"
            :native-action-handler="runNativeCanonicalAction"
            :native-action-state-resolver="nativeBridge.actionStateForNode"
            @field-change="emit('field-change', $event)"
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
            @field-change="emit('field-change', $event)"
          />
        </section>
        <section v-if="showCollaborationPanel && hasCollaborationNode" class="sc-native-contract-collaboration">
          <NativeCollaborationPanel
            v-bind="collaborationPanelProps"
            v-on="collaborationPanelListeners"
          />
        </section>
        <CanonicalActionBar
          v-if="visibleActions.length && !actionsInHeader"
          :direct-actions="directActions"
          :overflow-actions="overflowActions"
          :effective-primary-key="floorplan.effectivePrimaryKey"
          @action-ref="emit('action-ref', $event)"
        />
      </article>
      </WorkspaceFormPattern>
    </SceneUiProvider>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { SCENE_UI_KITS, SceneButton, SceneUiProvider, type SceneUiKitId } from '@sc/ui/form';
import type { ContractV2ActionRule } from '../../app/contracts/v2/types';
import type { CanonicalAuditEvent, CanonicalFormNode, CanonicalFormRenderModel } from '../../app/presentation/canonicalFormRenderModel';
import { composeCanonicalFormFloorplan, type CanonicalFormFloorplan } from '../../app/presentation/canonicalFormFloorplan';
import NativeFormTreeRenderer from '../../components/template/NativeFormTreeRenderer.vue';
import type { FormSectionFieldChange } from '../../components/template/formSection.types';
import type { RelationFieldAdapter } from '../../components/template/relationField.types';
import { buildCanonicalNativeFormBridge } from './canonicalNativeFormBridge';
import CanonicalActionBar from './CanonicalActionBar.vue';
import NativeCollaborationPanel, {
  type NativeCollaborationPanelListeners,
  type NativeCollaborationPanelProps,
} from './NativeCollaborationPanel.vue';
import ObjectTaskPage from './ObjectTaskPage.vue';
import TaskFormPattern from '../../components/product-page-patterns/TaskFormPattern.vue';
import WorkspaceFormPattern from '../../components/product-page-patterns/WorkspaceFormPattern.vue';
import { canonicalNodeHasContent } from './canonicalFormRenderer';

const props = defineProps<{
  renderModel: CanonicalFormRenderModel | null;
  error?: string;
  driverConfig?: {
    activeKit: SceneUiKitId;
    allowedKits: SceneUiKitId[];
    allowUserOverride: boolean;
    showUserDriverChooser?: boolean;
    resolutionSource: string;
    reasonCode: string;
  };
  relationAdapter?: RelationFieldAdapter;
  showCollaborationPanel?: boolean;
  collaborationPanelProps?: NativeCollaborationPanelProps;
  collaborationPanelListeners?: NativeCollaborationPanelListeners;
  dirty?: boolean;
  busy?: boolean;
  actionsInHeader?: boolean;
}>();
const emit = defineEmits<{
  'driver-change': [kit: SceneUiKitId];
  'field-change': [payload: FormSectionFieldChange];
  'action-ref': [action: ContractV2ActionRule];
  save: [];
}>();

function countFields(nodes: CanonicalFormNode[]): number {
  return nodes.reduce((total, node) => total + node.fields.filter((field) => field.visible).length + countFields(node.children), 0);
}

const fieldCount = computed(() => props.renderModel
  ? countFields([...props.renderModel.zones.primary, ...props.renderModel.zones.subordinate])
  : 0);
const activeKit = computed<SceneUiKitId>(() => props.driverConfig?.activeKit || 'tdesign-modern');
const emptyFloorplan: CanonicalFormFloorplan = {
    summaryNodes: [], taskNodes: [], coreInputNodes: [], conditionInputNodes: [], preExecutionInputNodes: [], preExecutionInputTitle: '', supplementaryInputNodes: [],
    contextNodes: [], overflowContextNodes: [], riskNodes: [], auditNodes: [], auditDeclared: false,
  relationNodes: [], subordinateNodes: [], blockedActions: [], directActions: [], overflowActions: [],
  effectivePrimaryKey: '', decisionMode: false,
};
const floorplan = computed(() => props.renderModel ? composeCanonicalFormFloorplan(props.renderModel) : emptyFloorplan);
const productWriteMode = computed(() => Boolean(
  floorplan.value.decisionMode && props.renderModel && props.renderModel.identity.mode !== 'readonly',
));
const localSavePrimary = computed(() => Boolean(
  productWriteMode.value && (props.renderModel?.identity.mode === 'create' || props.dirty),
));
const showProductActions = computed(() => Boolean(
  localSavePrimary.value || productWriteMode.value
  || floorplan.value.directActions.length || floorplan.value.overflowActions.length,
));
const renderKit = computed<SceneUiKitId>(() => floorplan.value.decisionMode ? 'tdesign-modern' : activeKit.value);
const allowedKits = computed<SceneUiKitId[]>(() => (
  props.driverConfig?.allowedKits?.length ? props.driverConfig.allowedKits : ['tdesign-modern', 'sc-native']
));
const allowUserOverride = computed(() => (
  !floorplan.value.decisionMode
  && props.driverConfig?.showUserDriverChooser === true
  && props.driverConfig?.allowUserOverride === true
  && allowedKits.value.length > 1
));
const visibleActions = computed(() => props.renderModel?.actionBar.filter((action) => action.visible) || []);
const directActions = computed(() => visibleActions.value.filter((action) => ['primary', 'secondary'].includes(action.tier)));
const overflowActions = computed(() => visibleActions.value.filter((action) => ['overflow', 'configuration'].includes(action.tier)));
const hasCollaborationNode = computed(() => Boolean(props.renderModel?.zones.subordinate.some((node) => collaborationKind(node.kind))));
const hasCollaboration = computed(() => props.showCollaborationPanel === true || hasCollaborationNode.value);
const auditEvents = computed<CanonicalAuditEvent[]>(() => (props.collaborationPanelProps?.timeline || []).flatMap((entry) => {
  if (entry.type !== 'audit' || !entry.audit) return [];
  const actor = String(entry.audit.actor || '').trim();
  const occurredAt = String(entry.audit.occurred_at || '').trim();
  const event = String(entry.audit.event || '').trim();
  const result = String(entry.audit.result || '').trim();
  if (!actor || !occurredAt || !event || !result) return [];
  return [{
    key: entry.key,
    actor,
    occurredAt,
    event,
    result,
    detail: String(entry.body || '').trim(),
  }];
}));
const nativeBridgeModel = computed<CanonicalFormRenderModel | null>(() => {
  const model = props.renderModel;
  if (!model || model.identity.mode !== 'create') return model;
  return {
    ...model,
    zones: {
      primary: floorplan.value.taskNodes,
      subordinate: floorplan.value.subordinateNodes,
    },
  };
});
const nativeBridge = computed(() => nativeBridgeModel.value ? buildCanonicalNativeFormBridge(nativeBridgeModel.value) : null);
const floorplanSubordinateNodes = computed(() => floorplan.value.subordinateNodes
  .filter((node) => !collaborationKind(node.kind))
  .filter(canonicalNodeHasContent));

function collaborationKind(kind: string) {
  return ['chatter', 'activity'].includes(String(kind || '').trim().toLowerCase());
}

function runNativeCanonicalAction(payload: Record<string, unknown>) {
  const action = nativeBridge.value?.actionForPayload(payload);
  if (action) emit('action-ref', action);
}

function kitLabel(kit: SceneUiKitId) {
  return SCENE_UI_KITS[kit]?.label || kit;
}

function changeKit(event: Event) {
  const kit = String((event.target as HTMLSelectElement).value || '') as SceneUiKitId;
  if (allowedKits.value.includes(kit)) emit('driver-change', kit);
}
</script>

<style scoped>
.sc-form-driver-error {
  display: grid;
  gap: 6px;
  padding: 20px;
  border: 1px solid var(--sc-app-danger-border);
  border-radius: 8px;
  background: var(--sc-app-danger-bg);
  color: var(--sc-app-danger-text);
}
.canonical-product-edit-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  min-width: 0;
}
@media (max-width: 560px) {
  .canonical-product-edit-actions { flex-wrap: nowrap; width: 100%; }
  .canonical-product-edit-actions :deep(button[data-action-tier='primary']) { flex: 1 1 auto; }
}
.sc-form-driver-host { min-width: 0; }
.canonical-form-action-icon { inline-size: 1em; text-align: center; }
.canonical-form-blocking-notice {
  display: grid;
  gap: 4px;
  padding: 12px 16px;
  border: 1px solid var(--sc-app-warning-border);
  border-radius: 10px;
  background: var(--sc-app-warning-bg);
  color: var(--sc-app-warning-text);
}
.canonical-form-activity-empty { margin: 0; color: var(--sc-app-text-secondary); }
.canonical-form-action-bar {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 24px;
  background: transparent;
}
.canonical-form-action {
  min-height: 36px;
  padding: 0 16px;
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  background: var(--sc-app-panel);
  color: var(--sc-app-text-primary);
  cursor: pointer;
}
.canonical-form-action--primary {
  border-color: var(--sc-semantic-surface-interactive);
  background: var(--sc-semantic-surface-interactive);
  color: var(--sc-semantic-text-on-interactive) !important;
}
.canonical-form-action.is-danger { color: var(--sc-app-danger-text); }
.canonical-form-action:disabled { cursor: not-allowed; opacity: 0.55; }
.canonical-form-action-overflow { position: relative; }
.canonical-form-action-overflow > summary { cursor: pointer; color: var(--sc-app-text-primary); }
.canonical-form-action-overflow-panel {
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
.sc-form-driver-chooser {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  align-items: center;
  padding: 8px 24px;
  border-bottom: 1px solid var(--sc-app-border);
  background: var(--sc-app-panel);
  color: var(--sc-app-text-secondary);
  font-size: 12px;
}
.sc-form-driver-chooser select {
  min-height: 32px;
  padding: 0 30px 0 10px;
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  background: var(--sc-app-panel);
  color: var(--sc-app-text-primary);
}
</style>
