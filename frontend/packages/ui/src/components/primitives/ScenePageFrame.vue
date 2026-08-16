<script setup lang="ts">
import { computed } from 'vue';
import { useSceneUiKit } from '../../kits/context';

const { runtime } = useSceneUiKit();
const componentModel = computed(() => runtime.value?.componentModel || 'native');
</script>

<template>
  <ui5-dynamic-page v-if="componentModel === 'web-components'" class="scene-page-frame" hide-pin-button>
    <ui5-dynamic-page-title slot="titleArea">
      <div slot="heading"><slot name="heading" /></div>
      <div slot="actionsBar"><slot name="actions" /></div>
      <slot name="snapped" />
    </ui5-dynamic-page-title>
    <ui5-dynamic-page-header slot="headerArea"><slot name="header" /></ui5-dynamic-page-header>
    <slot />
  </ui5-dynamic-page>

  <section v-else class="scene-page-frame scene-native-page-frame">
    <header class="scene-native-page-title">
      <slot name="heading" />
      <div class="scene-native-page-actions"><slot name="actions" /></div>
      <div class="scene-native-page-snapped"><slot name="snapped" /></div>
    </header>
    <div class="scene-native-page-header"><slot name="header" /></div>
    <div class="scene-native-page-content"><slot /></div>
  </section>
</template>

<style scoped>
.scene-page-frame {
  width: 100%;
  height: 100%;
}

.scene-native-page-frame {
  overflow: auto;
  background: white;
}

.scene-native-page-title {
  position: sticky;
  z-index: 4;
  top: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px 24px;
  align-items: center;
  padding: 14px 24px;
  border-bottom: 1px solid #dfe5ec;
  background: rgba(255, 255, 255, 0.97);
  backdrop-filter: blur(8px);
}

.scene-native-page-actions {
  display: flex;
  gap: 8px;
}

.scene-native-page-snapped {
  grid-column: 1 / -1;
}

.scene-native-page-header {
  padding: 12px 24px 15px;
  border-bottom: 1px solid #dfe5ec;
}

@media (max-width: 640px) {
  .scene-native-page-title {
    grid-template-columns: minmax(0, 1fr);
    padding: 12px 16px;
  }

  .scene-native-page-actions,
  .scene-native-page-snapped {
    display: none;
  }

  .scene-native-page-header {
    padding: 8px 16px 12px;
  }
}
</style>
