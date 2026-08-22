<script setup lang="ts">
import { computed } from 'vue';
import { useSceneUiKit } from '../../kits/context';

defineOptions({ inheritAttrs: false });

const props = withDefaults(
  defineProps<{
    tier?: 'primary' | 'secondary' | 'transparent';
    disabled?: boolean;
  }>(),
  { tier: 'secondary', disabled: false },
);

const emit = defineEmits<{ activate: [] }>();
const { runtime } = useSceneUiKit();
const componentModel = computed(() => runtime.value?.componentModel || 'native');
const driverButton = computed(() => runtime.value?.components.button);

function ui5Design(): 'Emphasized' | 'Default' | 'Transparent' {
  if (props.tier === 'primary') return 'Emphasized';
  if (props.tier === 'transparent') return 'Transparent';
  return 'Default';
}

function tdesignTheme(): 'primary' | 'default' {
  return props.tier === 'primary' ? 'primary' : 'default';
}
</script>

<template>
  <ui5-button v-if="componentModel === 'web-components'" v-bind="$attrs" :design="ui5Design()" :disabled="disabled" @click="emit('activate')">
    <slot />
  </ui5-button>
  <component
    :is="driverButton"
    v-else-if="componentModel === 'vue' && driverButton"
    v-bind="$attrs"
    :theme="tdesignTheme()"
    :variant="tier === 'transparent' ? 'text' : 'base'"
    :disabled="disabled"
    data-scene-driver-control="button"
    @click="emit('activate')"
  >
    <slot />
  </component>
  <button
    v-else
    v-bind="$attrs"
    type="button"
    class="scene-native-button"
    :data-tier="tier"
    :disabled="disabled"
    @click="emit('activate')"
  >
    <slot />
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
</style>
