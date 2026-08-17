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
    :data-contract-form-driver="activeKit"
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
    <SceneUiProvider :kit="activeKit" fallback-kit="sc-native" density="compact">
      <ObjectTaskPage
        :task-nodes="floorplan.taskNodes"
        :context-nodes="floorplan.contextNodes"
        :subordinate-nodes="subordinateNodes"
        :relation-adapter="relationAdapter"
        :has-collaboration="showCollaborationPanel && hasCollaborationNode"
        @field-change="emit('field-change', $event)"
      >
        <template v-if="floorplan.blockedActions.length" #blocking>
          <section class="canonical-form-blocking-notice" role="status" data-canonical-blocking-notice>
            <strong>当前办理暂不可执行</strong>
            <span v-for="action in floorplan.blockedActions" :key="action.key">
              {{ action.label }}：{{ action.reasonCode || 'ACTION_NOT_ALLOWED' }}
            </span>
          </section>
        </template>
        <template v-if="showCollaborationPanel && hasCollaborationNode" #collaboration>
          <NativeCollaborationPanel
            v-bind="collaborationPanelProps"
            v-on="collaborationPanelListeners"
          />
        </template>
        <template v-if="visibleActions.length" #actions>
          <nav class="canonical-form-action-bar" aria-label="表单业务动作" data-canonical-action-bar>
            <button
              v-for="action in directActions"
              :key="action.key"
              type="button"
              :class="['canonical-form-action', `canonical-form-action--${action.tier}`, { 'is-danger': actionDanger(action) }]"
              :disabled="!action.enabled"
              :title="action.reasonCode || undefined"
              :data-action-ref="action.actionRef.actionId"
              :data-backend-identity="action.actionRef.backendIdentity"
              :data-action-tier="action.tier"
              :data-action-enabled="String(action.enabled)"
              @click="action.enabled && emit('action-ref', action.actionRef)"
            >{{ action.label }}</button>
            <details v-if="overflowActions.length" class="canonical-form-action-overflow">
              <summary>更多操作</summary>
              <div class="canonical-form-action-overflow-panel">
                <button
                  v-for="action in overflowActions"
                  :key="action.key"
                  type="button"
                  class="canonical-form-action canonical-form-action--overflow"
                  :disabled="!action.enabled"
                  :title="action.reasonCode || undefined"
                  :data-action-ref="action.actionRef.actionId"
                  :data-backend-identity="action.actionRef.backendIdentity"
                  :data-action-tier="action.tier"
                  :data-action-enabled="String(action.enabled)"
                  @click="action.enabled && emit('action-ref', action.actionRef)"
                >{{ action.label }}</button>
              </div>
            </details>
          </nav>
        </template>
      </ObjectTaskPage>
    </SceneUiProvider>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { SCENE_UI_KITS, SceneUiProvider, type SceneUiKitId } from '@sc/ui/form';
import type { ContractV2ActionRule } from '../../app/contracts/v2/types';
import type { CanonicalFormAction, CanonicalFormNode, CanonicalFormRenderModel } from '../../app/presentation/canonicalFormRenderModel';
import { composeCanonicalFormFloorplan } from '../../app/presentation/canonicalFormFloorplan';
import type { FormSectionFieldChange } from '../../components/template/formSection.types';
import type { RelationFieldAdapter } from '../../components/template/relationField.types';
import NativeCollaborationPanel, {
  type NativeCollaborationPanelListeners,
  type NativeCollaborationPanelProps,
} from './NativeCollaborationPanel.vue';
import ObjectTaskPage from './ObjectTaskPage.vue';
import { canonicalNodeHasContent } from './canonicalFormRenderer';

const props = defineProps<{
  renderModel: CanonicalFormRenderModel | null;
  error?: string;
  driverConfig?: {
    activeKit: SceneUiKitId;
    allowedKits: SceneUiKitId[];
    allowUserOverride: boolean;
    resolutionSource: string;
    reasonCode: string;
  };
  relationAdapter?: RelationFieldAdapter;
  showCollaborationPanel?: boolean;
  collaborationPanelProps?: NativeCollaborationPanelProps;
  collaborationPanelListeners?: NativeCollaborationPanelListeners;
}>();
const emit = defineEmits<{
  'driver-change': [kit: SceneUiKitId];
  'field-change': [payload: FormSectionFieldChange];
  'action-ref': [action: ContractV2ActionRule];
}>();

function countFields(nodes: CanonicalFormNode[]): number {
  return nodes.reduce((total, node) => total + node.fields.filter((field) => field.visible).length + countFields(node.children), 0);
}

const fieldCount = computed(() => props.renderModel
  ? countFields([...props.renderModel.zones.primary, ...props.renderModel.zones.subordinate])
  : 0);
const activeKit = computed<SceneUiKitId>(() => props.driverConfig?.activeKit || 'sc-native');
const allowedKits = computed<SceneUiKitId[]>(() => props.driverConfig?.allowedKits?.length ? props.driverConfig.allowedKits : ['sc-native']);
const allowUserOverride = computed(() => props.driverConfig?.allowUserOverride === true && allowedKits.value.length > 1);
const floorplan = computed(() => props.renderModel ? composeCanonicalFormFloorplan(props.renderModel) : {
  taskNodes: [], contextNodes: [], subordinateNodes: [], blockedActions: [],
});
const visibleActions = computed(() => props.renderModel?.actionBar.filter((action) => action.visible) || []);
const directActions = computed(() => visibleActions.value.filter((action) => (
  action.enabled && !['overflow', 'configuration'].includes(action.tier)
)));
const overflowActions = computed(() => visibleActions.value.filter((action) => (
  !directActions.value.includes(action) && !floorplan.value.blockedActions.includes(action)
)));
const subordinateNodes = computed(() => floorplan.value.subordinateNodes
  .filter((node) => !collaborationKind(node.kind))
  .filter(canonicalNodeHasContent));
const hasCollaborationNode = computed(() => Boolean(props.renderModel?.zones.subordinate.some((node) => collaborationKind(node.kind))));

function collaborationKind(kind: string) {
  return ['chatter', 'activity'].includes(String(kind || '').trim().toLowerCase());
}

function actionDanger(action: CanonicalFormAction) {
  const classification = String(action.safety.classification || action.safety.level || '').trim().toLowerCase();
  return classification === 'danger' || action.safety.destructive === true;
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
.sc-form-driver-host { min-width: 0; }
.canonical-form-blocking-notice {
  display: grid;
  gap: 4px;
  padding: 12px 16px;
  border: 1px solid var(--sc-app-warning-border, #e8b44c);
  border-radius: 10px;
  background: var(--sc-app-warning-bg, #fff8e6);
  color: var(--sc-app-text-primary, #183247);
}
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
  border-color: var(--sc-semantic-surface-interactive, #2563eb);
  background: var(--sc-semantic-surface-interactive, #2563eb);
  color: var(--sc-semantic-text-on-interactive, #fff) !important;
}
.canonical-form-action.is-danger { color: var(--sc-app-danger-text); }
.canonical-form-action:disabled { cursor: not-allowed; opacity: 0.55; }
.canonical-form-action-overflow { position: relative; }
.canonical-form-action-overflow > summary { cursor: pointer; color: var(--sc-app-text-primary, #183247); }
.canonical-form-action-overflow-panel {
  position: absolute;
  z-index: 20;
  right: 0;
  display: grid;
  gap: 6px;
  min-width: 240px;
  padding: 10px;
  border: 1px solid var(--sc-app-border, #cbd5df);
  border-radius: 8px;
  background: var(--sc-app-panel, #fff);
  box-shadow: 0 10px 28px rgb(26 48 66 / 16%);
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
