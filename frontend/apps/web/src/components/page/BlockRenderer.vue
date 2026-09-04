<template>
  <div
    v-if="blockComponent"
    class="block-renderer"
    :class="blockClasses"
    :data-block-key="resolvedBlockKey"
    :data-block-type="resolvedBlockType"
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

/**
 * 语义定位属性（G3.3-B 双角色五视口验收 DOM 契约）：
 * - data-block-key 优先运行时 block_key（后端 block.project.* 全名），
 *   回落契约 stub key；
 * - data-block-type 与注册表 block_type 一致。
 * 验收 harness 以 [data-block-key]/[data-block-type] 等待块挂载完成。
 */
const resolvedBlockKey = computed(() => {
  const block = props.block as PageOrchestrationBlock & { block_key?: unknown };
  const runtimeKey = typeof block.block_key === 'string' ? block.block_key.trim() : '';
  const stubKey = typeof props.block.key === 'string' ? props.block.key.trim() : '';
  return runtimeKey || stubKey;
});
const resolvedBlockType = computed(() => String(props.block.block_type || '').trim());

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
