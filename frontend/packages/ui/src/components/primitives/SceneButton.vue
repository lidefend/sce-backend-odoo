<script setup lang="ts">
import { computed } from 'vue';
import { useSceneUiKit } from '../../kits/context';

defineOptions({ inheritAttrs: false });

const props = withDefaults(
  defineProps<{
    tier?: 'primary' | 'secondary' | 'transparent';
    disabled?: boolean;
    loading?: boolean;
    loadingLabel?: string;
  }>(),
  { tier: 'secondary', disabled: false, loading: false, loadingLabel: '处理中' },
);

const emit = defineEmits<{ activate: [] }>();
const { runtime } = useSceneUiKit();
const componentModel = computed(() => runtime.value?.componentModel || 'native');
const driverButton = computed(() => runtime.value?.components.button);

function tdesignTheme(): 'primary' | 'default' {
  return props.tier === 'primary' ? 'primary' : 'default';
}

function activate() {
  if (props.disabled || props.loading) return;
  emit('activate');
}
</script>

<template>
  <component
    :is="driverButton"
    v-if="componentModel === 'vue' && driverButton"
    v-bind="$attrs"
    :theme="tdesignTheme()"
    :variant="tier === 'transparent' ? 'text' : 'base'"
    :loading="loading"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    :data-loading="loading || undefined"
    data-scene-driver-control="button"
    @click="activate"
  >
    <slot />
  </component>
  <button
    v-else
    v-bind="$attrs"
    type="button"
    class="scene-native-button"
    :data-tier="tier"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    :data-loading="loading || undefined"
    @click="activate"
  >
    <span v-if="loading" class="scene-native-button__spinner" aria-hidden="true"></span>
    <slot />
    <span v-if="loading" class="sc-visually-hidden">{{ loadingLabel }}</span>
  </button>
</template>

<style scoped>
.scene-native-button {
  min-height: var(--sc-scene-control-height, 36px);
  padding: 0 14px;
  border: 1px solid #b9c5d2;
  border-radius: var(--sc-scene-control-radius, 7px);
  background: white;
  color: #183247;
  font: 600 13px/1 "Segoe UI", sans-serif;
}

.scene-native-button[data-tier='primary'] {
  border-color: #146bd1;
  background: #146bd1;
  color: white;
}

.scene-native-button[data-tier='transparent'] {
  border-color: transparent;
  background: transparent;
  color: #1769c2;
}

.scene-native-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.scene-native-button__spinner {
  display: inline-block;
  inline-size: 0.9em;
  block-size: 0.9em;
  margin-inline-end: 6px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  vertical-align: -0.12em;
  animation: scene-native-button-spin 720ms linear infinite;
}

@keyframes scene-native-button-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .scene-native-button__spinner { animation: none; }
}
</style>
