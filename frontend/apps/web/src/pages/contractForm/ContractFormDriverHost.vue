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
      <nav v-if="visibleActions.length" class="canonical-form-action-bar" aria-label="表单业务动作" data-canonical-action-bar>
        <button
          v-for="action in visibleActions"
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
      </nav>
      <div class="canonical-form-zones" data-canonical-form-zones>
        <section class="canonical-form-zone canonical-form-zone--primary" data-canonical-zone="primary">
          <CanonicalFormNodeRenderer
            v-for="node in primaryNodes"
            :key="node.nodeId"
            :node="node"
            :relation-adapter="relationAdapter"
            @field-change="emit('field-change', $event)"
          />
        </section>
        <section
          v-if="subordinateNodes.length || showCollaborationPanel"
          class="canonical-form-zone canonical-form-zone--subordinate"
          data-canonical-zone="subordinate"
        >
          <CanonicalFormNodeRenderer
            v-for="node in subordinateNodes"
            :key="node.nodeId"
            :node="node"
            :relation-adapter="relationAdapter"
            @field-change="emit('field-change', $event)"
          />
          <NativeCollaborationPanel
            v-if="showCollaborationPanel && hasCollaborationNode"
            v-bind="collaborationPanelProps"
            v-on="collaborationPanelListeners"
          />
        </section>
      </div>
    </SceneUiProvider>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { SCENE_UI_KITS, SceneUiProvider, type SceneUiKitId } from '@sc/ui/form';
import type { ContractV2ActionRule } from '../../app/contracts/v2/types';
import type { CanonicalFormAction, CanonicalFormNode, CanonicalFormRenderModel } from '../../app/presentation/canonicalFormRenderModel';
import type { FormSectionFieldChange } from '../../components/template/formSection.types';
import type { RelationFieldAdapter } from '../../components/template/relationField.types';
import CanonicalFormNodeRenderer from './CanonicalFormNodeRenderer.vue';
import NativeCollaborationPanel, {
  type NativeCollaborationPanelListeners,
  type NativeCollaborationPanelProps,
} from './NativeCollaborationPanel.vue';
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
const visibleActions = computed(() => props.renderModel?.actionBar.filter((action) => action.visible) || []);
const primaryNodes = computed(() => props.renderModel?.zones.primary.filter(canonicalNodeHasContent) || []);
const subordinateNodes = computed(() => props.renderModel?.zones.subordinate
  .filter((node) => !collaborationKind(node.kind))
  .filter(canonicalNodeHasContent) || []);
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
.canonical-form-action-bar {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 24px;
  border-bottom: 1px solid var(--sc-app-border);
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
  border-color: var(--sc-app-primary);
  background: var(--sc-app-primary);
  color: var(--sc-app-on-primary, #fff);
}
.canonical-form-action.is-danger { color: var(--sc-app-danger-text); }
.canonical-form-action:disabled { cursor: not-allowed; opacity: 0.55; }
.canonical-form-zones { display: grid; gap: 20px; min-width: 0; }
.canonical-form-zone { min-width: 0; }
.canonical-form-zone--subordinate {
  padding-top: 16px;
  border-top: 1px solid var(--sc-app-border);
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
