<script setup lang="ts">
import { computed, provide, ref, shallowRef, watch, type CSSProperties } from 'vue';
import { sceneUiKitKey } from '../kits/context';
import { loadSceneUiDriver, type SceneUiDriverLoader } from '../kits/registry';
import type { SceneUiDensity, SceneUiDriverRuntime, SceneUiKitId } from '../kits/types';
import { SCENE_DESIGN_TOKEN_PROFILES, type SceneDesignTokenProfileId } from '../kits/tokens';

const props = withDefaults(
  defineProps<{
    kit: SceneUiKitId;
    density?: SceneUiDensity;
    fallbackKit?: SceneUiKitId;
    driverLoader?: SceneUiDriverLoader;
    tokenProfile?: SceneDesignTokenProfileId;
  }>(),
  { density: 'compact', fallbackKit: 'sc-native', tokenProfile: 'enterprise-neutral' },
);

const runtime = shallowRef<SceneUiDriverRuntime | null>(null);
const loadFailure = ref<{ requestedKit: SceneUiKitId; fallbackKit: SceneUiKitId; message: string } | null>(null);
const ready = computed(() => Boolean(runtime.value));
const resolvedKit = computed(() => runtime.value?.id || props.fallbackKit);
let requestSerial = 0;
const tokenStyle = computed<CSSProperties>(() => {
  const tokens = SCENE_DESIGN_TOKEN_PROFILES[props.tokenProfile].tokens;
  return {
    '--sc-scene-bg': tokens.background,
    '--sc-scene-surface': tokens.surface,
    '--sc-scene-border': tokens.border,
    '--sc-scene-muted': tokens.mutedText,
    '--sc-scene-text': tokens.text,
    '--sc-scene-brand': tokens.brand,
    '--sc-scene-accent-soft': tokens.accentSoft,
    '--sc-scene-warning': tokens.warning,
    '--sc-scene-success': tokens.success,
    '--sc-scene-focus': tokens.focus,
    '--sc-scene-control-radius': tokens.controlRadius,
    '--sc-scene-surface-radius': tokens.surfaceRadius,
  } as CSSProperties;
});

async function ensureDriver(kit: SceneUiKitId): Promise<void> {
  const serial = ++requestSerial;
  runtime.value = null;
  loadFailure.value = null;
  try {
    const loaded = await (props.driverLoader || loadSceneUiDriver)(kit);
    if (serial === requestSerial) runtime.value = loaded;
  } catch (error) {
    if (serial !== requestSerial) return;
    const fallback = await loadSceneUiDriver(props.fallbackKit);
    if (serial !== requestSerial) return;
    loadFailure.value = {
      requestedKit: kit,
      fallbackKit: fallback.id,
      message: error instanceof Error ? error.message : 'unknown driver load error',
    };
    runtime.value = fallback;
  }
}

watch(
  () => props.kit,
  (kit) => void ensureDriver(kit),
  { immediate: true },
);

provide(sceneUiKitKey, {
  kit: resolvedKit,
  requestedKit: computed(() => props.kit),
  density: computed(() => props.density),
  runtime,
  ready,
});
</script>

<template>
  <div
    class="scene-ui-provider"
    :data-scene-ui-kit="resolvedKit"
    :data-scene-ui-requested-kit="kit"
    :data-scene-density="density"
    :data-scene-token-profile="tokenProfile"
    :data-scene-driver-fallback="loadFailure ? 'true' : 'false'"
    :style="tokenStyle"
  >
    <div v-if="!ready" class="scene-ui-provider__loading" role="status">正在加载组件驱动…</div>
    <template v-else>
      <div v-if="loadFailure" class="scene-ui-provider__fallback" role="alert" data-driver-fallback-notice>
        <strong>已切换到安全组件</strong>
        <span>{{ loadFailure.requestedKit }} 加载失败，当前使用 {{ loadFailure.fallbackKit }}。</span>
      </div>
      <slot />
    </template>
  </div>
</template>

<style>
.scene-ui-provider {
  min-width: 0;
  min-height: 100%;
}

.scene-ui-provider__loading {
  display: grid;
  min-height: 70vh;
  place-items: center;
  color: #52667a;
  font: 14px/1.5 "Segoe UI", sans-serif;
}

.scene-ui-provider__fallback {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 9px 16px;
  border-bottom: 1px solid #e3c980;
  background: #fff8df;
  color: #704d00;
  font: 12px/1.4 "Segoe UI", sans-serif;
}

.scene-ui-provider[data-scene-density='cozy'] {
  --sc-scene-control-height: 44px;
  --sc-scene-field-gap: 19px;
}

.scene-ui-provider[data-scene-density='compact'] {
  --sc-scene-control-height: 36px;
  --sc-scene-field-gap: 15px;
}

.scene-ui-provider :where(button, [role='button'], input, select, textarea, ui5-button, ui5-input, ui5-select, ui5-date-picker, ui5-textarea):focus-visible {
  outline: 3px solid var(--sc-scene-focus);
  outline-offset: 2px;
}
</style>
