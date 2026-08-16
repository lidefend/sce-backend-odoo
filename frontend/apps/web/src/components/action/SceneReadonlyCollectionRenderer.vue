<template>
  <section
    class="scene-readonly-collection-renderer"
    data-scene-readonly-collection-renderer
    :data-scene-driver-source="resolutionSource"
  >
    <div v-if="allowUserOverride" class="scene-driver-chooser">
      <label for="scene-driver-kit">界面风格</label>
      <select
        id="scene-driver-kit"
        :value="activeKit"
        data-scene-driver-chooser
        @change="changeKit"
      >
        <option v-for="kit in allowedKits" :key="kit" :value="kit">
          {{ kitLabel(kit) }}
        </option>
      </select>
    </div>
    <SceneUiProvider :kit="activeKit" fallback-kit="sc-native" density="compact">
      <SceneCollectionSurface
        :contract="contract"
        :prototype-mode="true"
        @open-row="openRow"
      />
    </SceneUiProvider>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import {
  SCENE_UI_KITS,
  SceneCollectionSurface,
  SceneUiProvider,
  type SceneCollectionContract,
  type SceneUiKitId,
} from '@sc/ui/collection';
import { sceneCollectionRowToRecord } from '../../app/renderers/sceneReadonlyCollectionBridge';

type SceneReadonlyCollectionRendererConfig = {
  contract?: SceneCollectionContract;
  activeKit?: SceneUiKitId;
  allowedKits?: SceneUiKitId[];
  allowUserOverride?: boolean;
  resolutionSource?: string;
};

const props = defineProps<{ config: SceneReadonlyCollectionRendererConfig }>();
const emit = defineEmits<{
  'driver-change': [kit: SceneUiKitId];
  'open-record': [row: Record<string, unknown>];
}>();

const contract = computed(() => props.config.contract as SceneCollectionContract);
const activeKit = computed<SceneUiKitId>(() => props.config.activeKit || 'sc-native');
const allowedKits = computed<SceneUiKitId[]>(() => (
  Array.isArray(props.config.allowedKits) && props.config.allowedKits.length
    ? props.config.allowedKits
    : ['sc-native']
));
const allowUserOverride = computed(() => props.config.allowUserOverride === true);
const resolutionSource = computed(() => String(props.config.resolutionSource || 'safe-default'));

function kitLabel(kit: SceneUiKitId): string {
  return SCENE_UI_KITS[kit]?.label || kit;
}

function changeKit(event: Event): void {
  const kit = String((event.target as HTMLSelectElement).value || '') as SceneUiKitId;
  if (!allowedKits.value.includes(kit)) return;
  emit('driver-change', kit);
}

function openRow(row: { id: string; values: Record<string, string> }): void {
  emit('open-record', sceneCollectionRowToRecord(row));
}
</script>

<style scoped>
.scene-readonly-collection-renderer { min-width: 0; }
.scene-driver-chooser {
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
.scene-driver-chooser select {
  min-height: 32px;
  padding: 0 30px 0 10px;
  border: 1px solid var(--sc-app-border);
  border-radius: 8px;
  background: var(--sc-app-panel);
  color: var(--sc-app-text-primary);
}
</style>
