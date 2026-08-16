<script setup lang="ts">
import { computed, watchEffect } from 'vue';
import type { SceneNotice } from '../../contracts/sceneObjectPage';
import { useSceneUiKit } from '../../kits/context';

const props = defineProps<{ notice: SceneNotice }>();
const { kit, runtime } = useSceneUiKit();
const componentModel = computed(() => runtime.value?.componentModel || 'native');
const driverAlert = computed(() => runtime.value?.components.alert);
const tdesignTheme = computed(() => ({
  Critical: 'warning',
  Information: 'info',
  Negative: 'error',
  Neutral: 'info',
  Positive: 'success',
}[props.notice.tone]));

watchEffect(() => {
  if (componentModel.value === 'web-components') void runtime.value?.ensurePrimitive?.('alert');
});
</script>

<template>
  <div class="scene-notice" :data-notice-id="notice.id" :data-notice-driver="kit">
    <ui5-message-strip
      v-if="componentModel === 'web-components'"
      :design="notice.tone"
      hide-close-button
    >
      <strong>{{ notice.title }}</strong>
      <span>{{ notice.detail }}</span>
    </ui5-message-strip>

    <component
      :is="driverAlert"
      v-else-if="componentModel === 'vue' && driverAlert"
      :theme="tdesignTheme"
      :title="notice.title"
      :message="notice.detail"
      :close="false"
    />

    <div v-else class="scene-native-notice" :data-tone="notice.tone" role="status">
      <strong>{{ notice.title }}</strong>
      <span>{{ notice.detail }}</span>
    </div>
  </div>
</template>

<style scoped>
.scene-notice,
.scene-notice :deep(ui5-message-strip) {
  width: 100%;
}

.scene-notice :deep(ui5-message-strip) span {
  margin-left: 8px;
}

.scene-native-notice {
  display: flex;
  gap: 10px;
  align-items: baseline;
  padding: 11px 13px;
  border: 1px solid #d5dee8;
  border-left: 4px solid #6d8094;
  border-radius: 7px;
  background: #f8fafc;
  color: #26394c;
  font-size: 13px;
}

.scene-native-notice[data-tone='Critical'] {
  border-left-color: var(--sc-scene-warning);
  background: #fff8e8;
}

.scene-native-notice[data-tone='Positive'] {
  border-left-color: var(--sc-scene-success);
  background: #f1f9f4;
}

.scene-native-notice span {
  color: var(--sc-scene-muted);
}

@media (max-width: 640px) {
  .scene-native-notice {
    align-items: flex-start;
    flex-direction: column;
    gap: 3px;
  }
}
</style>
