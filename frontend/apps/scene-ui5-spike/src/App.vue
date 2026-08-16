<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import {
  SCENE_UI_KITS,
  SCENE_DESIGN_TOKEN_PROFILES,
  SceneCollectionSurface,
  SceneHierarchySurface,
  SceneObjectPage,
  SceneUiProvider,
  adaptReadonlyNormalizedCollection,
  loadSceneUiDriver,
  type SceneCollectionContract,
  type SceneUiDriverLoader,
  type SceneUiDensity,
  type SceneUiKitId,
  type SceneUiPreferenceResolution,
  type SceneDesignTokenProfileId,
} from '@sc/ui';
import { costHierarchyScene, paymentCollectionScene } from './fixtures/collectionScenes';
import { paymentRequestScene } from './fixtures/paymentRequestScene';
import { normalizedCompanyDirectorySnapshot } from './fixtures/normalizedCompanyDirectory';
import { readDriverPreference, readTokenProfile, writeDriverPreference, writeTokenProfile } from './driverPreference';

type LabSceneId = 'object' | 'list' | 'hierarchy';
const initialPreference = readDriverPreference();
const kit = ref<SceneUiKitId>(initialPreference.kit);
const preferenceSource = ref<SceneUiPreferenceResolution['source']>(initialPreference.source);
const density = ref<SceneUiDensity>('compact');
const tokenProfile = ref<SceneDesignTokenProfileId>(readTokenProfile());
const reviewPanelOpen = ref(false);
const initialQuery = new URLSearchParams(window.location.search);
const requestedScene = initialQuery.get('scene');
const scene = ref<LabSceneId>(requestedScene === 'list' || requestedScene === 'hierarchy' ? requestedScene : 'object');
const selectedRowIds = ref<string[]>([]);
const expandedNodeIds = ref<string[]>(['company-a', 'project-east', 'cost-civil']);
const injectedFailureKit = new URLSearchParams(window.location.search).get('failDriver');
const requestedPilot = initialQuery.get('pilot') === 'normalized-collection';
const labFeatureFlags = new Set(
  String(import.meta.env.VITE_FEATURE_FLAGS || '')
    .split(',')
    .map((flag) => flag.trim())
    .filter(Boolean),
);
const normalizedPilotFeatureEnabled = labFeatureFlags.has('scene_collection_pilot');
const normalizedPilotActive = requestedPilot && normalizedPilotFeatureEnabled;
let normalizedPilotFailure = '';
let normalizedPilotContract: SceneCollectionContract | null = null;
try {
  normalizedPilotContract = adaptReadonlyNormalizedCollection(normalizedCompanyDirectorySnapshot);
} catch (error) {
  normalizedPilotFailure = error instanceof Error ? error.message : 'unknown normalized collection error';
}
const collectionContract = computed(() => {
  if (!requestedPilot) return paymentCollectionScene;
  return normalizedPilotActive ? normalizedPilotContract : null;
});
const driverLoader: SceneUiDriverLoader = async (requestedKit) => {
  if (requestedKit === injectedFailureKit) {
    throw new Error('injected isolated-lab driver failure');
  }
  return loadSceneUiDriver(requestedKit);
};
const descriptor = computed(() => SCENE_UI_KITS[kit.value]);
const fieldValues = reactive<Record<string, string>>(
  Object.fromEntries(paymentRequestScene.task.groups.flatMap((group) => group.fields.map((field) => [field.id, field.value]))),
);

function selectKit(next: SceneUiKitId): void {
  kit.value = next;
  preferenceSource.value = 'user';
  writeDriverPreference(next);
}

function selectScene(next: LabSceneId): void {
  scene.value = next;
  const url = new URL(window.location.href);
  url.searchParams.set('scene', next);
  window.history.replaceState(null, '', url);
}

function selectDensity(next: SceneUiDensity): void {
  density.value = next;
}

function selectTokenProfile(next: SceneDesignTokenProfileId): void {
  tokenProfile.value = next;
  writeTokenProfile(next);
}

function onTokenProfileChange(event: Event): void {
  selectTokenProfile((event.target as HTMLSelectElement).value as SceneDesignTokenProfileId);
}

function updateField(fieldId: string, value: string): void {
  fieldValues[fieldId] = value;
}

function toggleRow(rowId: string): void {
  selectedRowIds.value = selectedRowIds.value.includes(rowId)
    ? selectedRowIds.value.filter((id) => id !== rowId)
    : [...selectedRowIds.value, rowId];
}

function toggleNode(nodeId: string): void {
  expandedNodeIds.value = expandedNodeIds.value.includes(nodeId)
    ? expandedNodeIds.value.filter((id) => id !== nodeId)
    : [...expandedNodeIds.value, nodeId];
}
</script>

<template>
  <div class="scene-lab" data-component-lab>
    <aside class="scene-labbar" aria-label="组件驱动实验室">
      <div class="scene-labbar__identity">
        <strong>场景组件实验室</strong>
        <span>同一语义合同 · 可切换底层驱动</span>
      </div>

      <div class="scene-labbar__control" role="group" aria-label="组件驱动">
        <span>驱动</span>
        <button
          v-for="item in SCENE_UI_KITS"
          :key="item.id"
          type="button"
          :data-kit-choice="item.id"
          :aria-pressed="kit === item.id"
          @click="selectKit(item.id)"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="scene-labbar__control" role="group" aria-label="信息密度">
        <span>密度</span>
        <button type="button" data-density-choice="compact" :aria-pressed="density === 'compact'" @click="selectDensity('compact')">
          紧凑
        </button>
        <button type="button" data-density-choice="cozy" :aria-pressed="density === 'cozy'" @click="selectDensity('cozy')">
          舒适
        </button>
      </div>

      <div class="scene-labbar__control" role="group" aria-label="场景类型">
        <span>场景</span>
        <button type="button" data-scene-choice="object" :aria-pressed="scene === 'object'" @click="selectScene('object')">办理</button>
        <button type="button" data-scene-choice="list" :aria-pressed="scene === 'list'" @click="selectScene('list')">列表</button>
        <button type="button" data-scene-choice="hierarchy" :aria-pressed="scene === 'hierarchy'" @click="selectScene('hierarchy')">层级</button>
      </div>

      <label class="scene-labbar__select">
        <span>视觉</span>
        <select
          :value="tokenProfile"
          data-token-profile-choice
          aria-label="视觉 Token 配置"
          @change="onTokenProfileChange"
        >
          <option v-for="profile in SCENE_DESIGN_TOKEN_PROFILES" :key="profile.id" :value="profile.id">{{ profile.label }}</option>
        </select>
      </label>

      <div class="scene-labbar__inventory" data-component-inventory>
        <span :data-preference-source="preferenceSource">{{ descriptor.vendor }} · {{ preferenceSource }}</span>
        <i
          v-if="requestedPilot"
          :data-normalized-pilot="normalizedPilotActive && normalizedPilotContract ? 'active' : 'blocked'"
        >
          normalized collection · {{ normalizedPilotActive && normalizedPilotContract ? 'readonly' : 'blocked' }}
        </i>
        <i v-for="capability in descriptor.capabilities" :key="capability">{{ capability }}</i>
      </div>
    </aside>

    <SceneUiProvider :kit="kit" :density="density" :token-profile="tokenProfile" :driver-loader="driverLoader">
      <SceneObjectPage
        v-if="scene === 'object'"
        :contract="paymentRequestScene"
        :field-values="fieldValues"
        :review-panel-open="reviewPanelOpen"
        prototype-mode
        @field-change="updateField"
        @update:review-panel-open="reviewPanelOpen = $event"
      />
      <SceneCollectionSurface
        v-else-if="scene === 'list' && collectionContract"
        :contract="collectionContract"
        :selected-row-ids="selectedRowIds"
        prototype-mode
        @toggle-row="toggleRow"
      />
      <section
        v-else-if="scene === 'list'"
        class="scene-pilot-blocked"
        role="alert"
        data-normalized-pilot-failure
      >
        <strong>normalized collection 试点已失败关闭</strong>
        <span>{{ normalizedPilotFailure || 'scene_collection_pilot 特性开关未启用' }}</span>
      </section>
      <SceneHierarchySurface
        v-else
        :contract="costHierarchyScene"
        :expanded-node-ids="expandedNodeIds"
        prototype-mode
        @toggle-node="toggleNode"
      />
    </SceneUiProvider>
  </div>
</template>
