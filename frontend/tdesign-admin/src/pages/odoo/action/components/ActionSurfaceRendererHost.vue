<template>
  <component
    :is="renderer"
    v-if="renderer"
    :mode="mode"
    :rows="rows"
    :fields="fields"
    :config="config"
    :aggregates="aggregates"
    :grouped-rows="groupedRows"
    @open="(row: Dict) => emit('open', row)"
    @activity-action="(payload: Dict) => emit('activity-action', payload)"
    @timeline-change="(payload: Dict) => emit('timeline-change', payload)"
  />
  <t-alert
    v-if="registration?.status === 'fallback'"
    class="renderer-diagnostic"
    theme="warning"
    :message="`当前视图按可读运行时展示（${registration.reasonCode}），未宣称 Odoo 完整语义。`"
  />
  <t-alert
    v-else
    theme="warning"
    title="当前视图暂不可用"
    :message="registration?.reasonCode || 'ACTION_SURFACE_RENDERER_NOT_REGISTERED'"
  />
</template>
<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue';

import type { ActionSurfaceViewMode } from '../runtime/actionSurfaceRegistry';
import { actionSurfaceRegistration } from '../runtime/actionSurfaceRegistry';

type Dict = Record<string, any>;

const props = defineProps<{
  mode: ActionSurfaceViewMode;
  rows: Dict[];
  fields: Array<{ code: string; label: string; type: string }>;
  config?: Dict;
  aggregates?: Dict;
  groupedRows?: Array<Dict>;
}>();
const emit = defineEmits<{
  open: [row: Dict];
  'activity-action': [payload: Dict];
  'timeline-change': [payload: Dict];
}>();
const AdvancedViewRuntime = defineAsyncComponent(() => import('./AdvancedViewRuntime.vue'));
const registration = computed(() => actionSurfaceRegistration(props.mode, props.config || {}));
const renderer = computed(() => {
  const key = registration.value?.activeRendererKey;
  return ['core.pivot', 'core.graph', 'core.calendar', 'core.gantt', 'core.activity'].includes(String(key)) ||
    ['pivot', 'graph', 'calendar', 'gantt', 'activity'].includes(props.mode)
    ? AdvancedViewRuntime
    : null;
});
</script>
