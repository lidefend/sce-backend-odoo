<template>
  <article
    class="block block-boq-import-preview"
    data-semantic-component="BlockBoqImportPreview"
    :data-state="phase"
    data-readonly="true"
  >
    <header class="block-header">
      <h4>{{ block.title || '数据快照' }}</h4>
    </header>

    <p v-if="phase === 'loading'" class="block-boq-import-preview__hint" data-loading>
      {{ copy.loading }}
    </p>

    <BoqImportPreviewPanel v-else-if="viewModel" :model="viewModel" />

    <p v-else class="block-boq-import-preview__hint" data-empty>
      {{ copy.empty }}
    </p>
  </article>
</template>

<script setup lang="ts">
/**
 * 只读数据快照块包装（驾驶舱 page orchestration block）。
 *
 * 职责（共享层，无行业语义）：
 * - 只消费块契约声明的 fetch_intent / fetch_params，不从路由补充参数；
 * - 通过块契约声明的专用 fetch intent 拉取快照，
 *   经 presentation Model 投影为四态视图模型；
 * - 渲染复用只读面板组件（无写操作入口）。
 * 行业标题与空态文案由后端块契约（dataset copy 字段）提供，
 * 本组件只保留通用 fallback。
 */
import { computed, onUnmounted, ref, watch } from 'vue';
import { createReadonlyBlockLoader, readonlyBlockData } from '../../../app/readonlyBlockRequest';
import type { PageOrchestrationBlock } from '../../../app/pageOrchestration';
import BoqImportPreviewPanel from '../../boq/BoqImportPreviewPanel.vue';
import {
  fetchBoqImportPreview,
  resolveBoqBlockRequest,
  type BoqImportPreviewIntentData,
} from '../../../api/boqImportPreview';
import {
  projectBoqImportPreview,
  type BoqImportPreviewViewModel,
} from '../../../app/presentation/boqImportPreview';

const GENERIC_LOADING = '正在加载数据...';
const GENERIC_EMPTY = '暂无可展示的数据。';

const props = defineProps<{
  block: PageOrchestrationBlock;
  zoneKey: string;
  dataset: unknown;
}>();

const phase = ref<'loading' | 'idle'>('idle');
const viewModel = ref<BoqImportPreviewViewModel | null>(null);

const blockData = computed(() => readonlyBlockData(props.dataset));
const request = computed(() => resolveBoqBlockRequest(blockData.value));

type BlockCopy = { loading: string; empty: string };

const copy = computed<BlockCopy>(() => {
  const data = blockData.value;
  const loading = typeof data.loading_message === 'string' && data.loading_message.trim()
    ? data.loading_message
    : GENERIC_LOADING;
  const pick = request.value.status !== 'ready' ? 'empty_message_no_context' : 'empty_message';
  const datasetEmpty = typeof data[pick] === 'string' && (data[pick] as string).trim()
    ? (data[pick] as string)
    : '';
  const empty = datasetEmpty || GENERIC_EMPTY;
  return { loading, empty };
});

const loader = createReadonlyBlockLoader<BoqImportPreviewIntentData>({
  reset(loading) { viewModel.value = null; phase.value = loading ? 'loading' : 'idle'; },
  success(raw) { viewModel.value = projectBoqImportPreview(raw); },
  error(error) {
    viewModel.value = projectBoqImportPreview({
      ok: false,
      error: { code: 'BOQ_PREVIEW_FETCH_FAILED',
        message: error instanceof Error ? error.message : String(error), suggested_action: 'retry' },
    });
  },
  settled() { phase.value = 'idle'; },
});

watch(() => JSON.stringify(request.value), () => {
  const resolved = request.value;
  void loader.load(resolved.status === 'ready' ? () => fetchBoqImportPreview(resolved.request) : null);
}, { immediate: true, flush: 'sync' });
onUnmounted(() => loader.dispose());
</script>

<style scoped>
.block-boq-import-preview__hint {
  margin: 0;
  color: var(--sc-semantic-text-secondary);
  font-size: 13px;
}
</style>
