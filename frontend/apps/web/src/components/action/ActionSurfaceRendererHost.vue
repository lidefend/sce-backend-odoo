<template>
  <div
    class="action-surface-renderer-host"
    :data-surface-semantic="descriptor.semantic"
    :data-requested-renderer="descriptor.requestedRendererKey"
    :data-active-renderer="descriptor.activeRendererKey"
    :data-renderer-status="descriptor.status"
  >
    <p
      v-if="descriptor.status === 'fallback'"
      class="action-surface-renderer-host__fallback"
      role="status"
    >该视图暂以列表形式展示</p>
    <component
      :is="rendererComponent"
      v-if="rendererComponent"
      :config="descriptor.config"
      :preference-scope="preferenceScope"
      :reason-code="descriptor.reasonCode"
      @open-record="emit('open-record', $event)"
      @open-action="emit('open-action', $event)"
      @driver-change="emit('driver-change', $event)"
    />
    <slot v-else name="standard" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ActionSurfaceRendererDescriptor } from '../../app/renderers/actionSurfaceRendererRegistry';
import { ACTION_SURFACE_RENDERER_COMPONENTS } from './actionSurfaceRendererComponents';

type Dict = Record<string, unknown>;
const props = withDefaults(defineProps<{ descriptor: ActionSurfaceRendererDescriptor; preferenceScope?: string }>(), {
  preferenceScope: 'default',
});
const emit = defineEmits<{
  'open-record': [row: Dict];
  'open-action': [action: Dict];
  'driver-change': [kit: string];
}>();
const rendererComponent = computed(() => (
  props.descriptor.outlet === 'component'
    ? ACTION_SURFACE_RENDERER_COMPONENTS[props.descriptor.activeRendererKey]
    : undefined
));
</script>

<style scoped>
.action-surface-renderer-host { min-width: 0; }
.action-surface-renderer-host__fallback {
  margin: 0 0 var(--sc-space-sm);
  padding: var(--sc-space-xs) var(--sc-space-sm);
  border-radius: var(--sc-product-radius-control);
  background: var(--sc-app-info-bg);
  color: var(--sc-app-info-text);
  font-size: var(--sc-product-text-sm);
}
</style>
