<template>
  <div v-if="parsed.kind" class="suggested-action-bar" role="group" aria-label="建议操作">
    <span v-if="reasonCode" class="suggested-action-bar__reason">原因码：{{ reasonCode }}</span>
    <t-button v-if="canExecute" size="small" variant="outline" @click="run">
      <template #icon><t-icon name="play-circle" /></template>
      {{ suggestedActionLabel(parsed) }}
    </t-button>
    <t-button v-if="traceId" size="small" variant="text" @click="copy('trace', traceId)">复制 Trace ID</t-button>
    <t-button v-if="reasonCode" size="small" variant="text" @click="copy('reason', reasonCode)">复制原因码</t-button>
  </div>
</template>
<script setup lang="ts">
import { MessagePlugin } from 'tdesign-vue-next';
import { computed } from 'vue';

import {
  canExecuteSuggestedAction,
  executeSuggestedAction,
  parseSuggestedAction,
  suggestedActionLabel,
} from '@/runtime/suggestedAction';

const props = defineProps<{
  action?: unknown;
  traceId?: string;
  reasonCode?: string;
  message?: string;
  onRetry?: () => void;
}>();
const parsed = computed(() => parseSuggestedAction(props.action));
const canExecute = computed(() => canExecuteSuggestedAction(parsed.value));

async function run() {
  const ok = await executeSuggestedAction(parsed.value, {
    onRetry: props.onRetry,
    traceId: props.traceId,
    reasonCode: props.reasonCode,
    message: props.message,
  });
  if (!ok) MessagePlugin.warning('当前建议操作无法执行');
}

async function copy(kind: 'trace' | 'reason', value: string) {
  try {
    await navigator.clipboard.writeText(value);
    MessagePlugin.success(kind === 'trace' ? 'Trace ID 已复制' : '原因码已复制');
  } catch {
    MessagePlugin.warning('复制失败，请手动记录页面信息');
  }
}
</script>
<style scoped>
.suggested-action-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 12px;
  margin-top: 10px;
  border: 1px solid var(--td-warning-color-3);
  border-radius: 6px;
  background: var(--td-warning-color-1);
}
.suggested-action-bar__reason {
  color: var(--td-text-color-secondary);
  font-size: 12px;
}
</style>
