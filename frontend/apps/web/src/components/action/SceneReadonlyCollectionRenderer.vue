<template>
  <section
    class="scene-readonly-collection-renderer"
    data-scene-readonly-collection-renderer
    :data-scene-driver-source="resolutionSource"
  >
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
  'open-record': [row: Record<string, unknown>];
}>();

const contract = computed(() => props.config.contract as SceneCollectionContract);
const activeKit = computed<SceneUiKitId>(() => props.config.activeKit || 'tdesign-modern');
const resolutionSource = computed(() => String(props.config.resolutionSource || 'safe-default'));

function openRow(row: { id: string; values: Record<string, string> }): void {
  emit('open-record', sceneCollectionRowToRecord(row));
}
</script>

<style scoped>
.scene-readonly-collection-renderer { min-width: 0; }
</style>
