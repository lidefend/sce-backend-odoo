<template>
  <div
    v-if="blockComponent"
    class="block-renderer"
    :class="blockClasses"
  >
    <component
      :is="blockComponent"
      :block="block"
      :zone-key="zoneKey"
      :dataset="dataset"
      @action="onAction"
    />
  </div>
  <ScErrorState
    v-else
    class="block-fallback"
    density="compact"
    :heading-level="5"
    title="当前内容暂不可用"
    description="请稍后重试或联系管理员。"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import ScErrorState from '../design-system/ScErrorState.vue';
import { resolveBlockComponent } from '../../app/pageBlockRegistry';
import type { PageBlockActionEvent, PageOrchestrationBlock } from '../../app/pageOrchestration';

const props = defineProps<{
  block: PageOrchestrationBlock;
  zoneKey: string;
  dataset: unknown;
}>();

const emit = defineEmits<{
  (event: 'action', payload: PageBlockActionEvent): void;
}>();

const blockComponent = computed(() => resolveBlockComponent(String(props.block.block_type || '')));
const blockClasses = computed(() => {
  const type = String(props.block.block_type || 'unknown').replace(/[^a-zA-Z0-9_-]/g, '-');
  const key = String(props.block.key || 'unknown').replace(/[^a-zA-Z0-9_-]/g, '-');
  return [`block-type-${type}`, `block-key-${key}`];
});

function onAction(payload: PageBlockActionEvent) {
  emit('action', payload);
}
</script>

<style scoped>
.block-renderer {
  min-width: 0;
  height: 100%;
}
.block-fallback {
  min-height: 0;
}
</style>
