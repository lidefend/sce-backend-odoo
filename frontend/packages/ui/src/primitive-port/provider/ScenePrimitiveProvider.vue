<template>
  <slot v-if="validation.ok" />
  <div
    v-else
    class="sc-primitive-contract-error"
    role="alert"
    data-scene-primitive-contract-error
  >
    <strong>Scene Primitive 契约错误</strong>
    <span>{{ validation.error.message }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, provide } from 'vue';
import type {
  SceneCompositionContext,
  SceneDensity,
  ScenePrimitiveAdapter,
} from '../types';
import { validatePrimitiveAdapterRuntimeShape } from '../validation';
import { scenePrimitiveContextKey } from './context';

const props = withDefaults(defineProps<{
  primitives: ScenePrimitiveAdapter;
  density?: SceneDensity;
}>(), {
  density: 'compact',
});

const validation = computed(() => validatePrimitiveAdapterRuntimeShape(props.primitives));

const context: SceneCompositionContext = {
  get primitives() {
    return props.primitives;
  },
  get density() {
    return props.density;
  },
};

provide(scenePrimitiveContextKey, context);
</script>

<style scoped>
.sc-primitive-contract-error {
  display: grid;
  gap: 4px;
  padding: 12px;
  border: 1px solid var(--sc-status-error-border, currentColor);
  border-radius: 6px;
  color: var(--sc-status-error-text, currentColor);
  background: var(--sc-status-error-bg, transparent);
}
</style>
