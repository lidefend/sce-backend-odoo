<template>
  <section
    v-if="error || !renderModel"
    class="contract-form-driver-error"
    role="alert"
    data-contract-form-driver-error
  >
    <strong>页面契约无法渲染</strong>
    <span>{{ error || 'CANONICAL_FORM_RENDER_MODEL_MISSING' }}</span>
  </section>
  <section
    v-else
    class="contract-form-driver-host"
    :data-contract-form-driver="activeKit"
    :data-contract-form-driver-source="driverConfig?.resolutionSource || 'safe-default'"
    :data-contract-form-driver-reason="driverConfig?.reasonCode || ''"
  >
    <div v-if="allowUserOverride" class="contract-form-driver-chooser">
      <label for="contract-form-driver-kit">界面风格</label>
      <select id="contract-form-driver-kit" :value="activeKit" data-contract-form-driver-chooser @change="changeKit">
        <option v-for="kit in allowedKits" :key="kit" :value="kit">{{ kitLabel(kit) }}</option>
      </select>
    </div>
    <SceneUiProvider v-if="activeKit !== 'sc-native'" :kit="activeKit" fallback-kit="sc-native" density="compact">
      <ContractFormNativeCanvas
        v-bind="$attrs"
        :data-source-contract-sha="renderModel.identity.sourceContractSha256"
        :data-render-model-fields="String(fieldCount)"
        :data-render-model-actions="String(renderModel.actionBar.length)"
      />
    </SceneUiProvider>
    <ContractFormNativeCanvas
      v-else
      v-bind="$attrs"
      :data-source-contract-sha="renderModel.identity.sourceContractSha256"
      :data-render-model-fields="String(fieldCount)"
      :data-render-model-actions="String(renderModel.actionBar.length)"
    />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { SCENE_UI_KITS, SceneUiProvider, type SceneUiKitId } from '@sc/ui/form';
import type { CanonicalFormNode, CanonicalFormRenderModel } from '../../app/presentation/canonicalFormRenderModel';
import ContractFormNativeCanvas from './ContractFormNativeCanvas.vue';

defineOptions({ inheritAttrs: false });
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
}>();
const emit = defineEmits<{ 'driver-change': [kit: SceneUiKitId] }>();

function countFields(nodes: CanonicalFormNode[]): number {
  return nodes.reduce((total, node) => total + node.fields.length + countFields(node.children), 0);
}

const fieldCount = computed(() => props.renderModel
  ? countFields([...props.renderModel.zones.primary, ...props.renderModel.zones.subordinate])
  : 0);
const activeKit = computed<SceneUiKitId>(() => props.driverConfig?.activeKit || 'sc-native');
const allowedKits = computed<SceneUiKitId[]>(() => props.driverConfig?.allowedKits?.length ? props.driverConfig.allowedKits : ['sc-native']);
const allowUserOverride = computed(() => props.driverConfig?.allowUserOverride === true && allowedKits.value.length > 1);

function kitLabel(kit: SceneUiKitId) {
  return SCENE_UI_KITS[kit]?.label || kit;
}

function changeKit(event: Event) {
  const kit = String((event.target as HTMLSelectElement).value || '') as SceneUiKitId;
  if (allowedKits.value.includes(kit)) emit('driver-change', kit);
}
</script>

<style scoped>
.contract-form-driver-error {
  display: grid;
  gap: 6px;
  padding: 20px;
  border: 1px solid var(--sc-app-danger-border);
  border-radius: 8px;
  background: var(--sc-app-danger-bg);
  color: var(--sc-app-danger-text);
}
.contract-form-driver-host { min-width: 0; }
.contract-form-driver-chooser {
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
.contract-form-driver-chooser select {
  min-height: 32px;
  padding: 0 30px 0 10px;
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  background: var(--sc-app-panel);
  color: var(--sc-app-text-primary);
}
</style>
