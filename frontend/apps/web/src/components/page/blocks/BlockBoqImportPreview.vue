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
 * - 从块契约 dataset（后端块投影）或路由 query 解析数据上下文 id；
 * - 通过块契约声明的专用 fetch intent 拉取快照，
 *   经 presentation Model 投影为四态视图模型；
 * - 渲染复用只读面板组件（无写操作入口）。
 * 行业标题与空态文案由后端块契约（dataset copy 字段）提供，
 * 本组件只保留通用 fallback。
 */
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import type { PageOrchestrationBlock } from '../../../app/pageOrchestration';
import BoqImportPreviewPanel from '../../boq/BoqImportPreviewPanel.vue';
import {
  fetchBoqImportPreview,
  type BoqImportPreviewIntentData,
} from '../../../api/boqImportPreview';
import {
  projectBoqImportPreview,
  resolveBoqBlockProjectId,
  type BoqImportPreviewViewModel,
} from '../../../app/presentation/boqImportPreview';

const GENERIC_LOADING = '正在加载数据...';
const GENERIC_EMPTY = '暂无可展示的数据。';

const props = defineProps<{
  block: PageOrchestrationBlock;
  zoneKey: string;
  dataset: unknown;
}>();

const route = useRoute();
const phase = ref<'loading' | 'idle'>('idle');
const viewModel = ref<BoqImportPreviewViewModel | null>(null);

const projectId = computed(() => resolveBoqBlockProjectId(props.dataset, route.query));

type BlockCopy = { loading: string; empty: string };

const copy = computed<BlockCopy>(() => {
  const source = (props.dataset && typeof props.dataset === 'object' ? props.dataset : {}) as Record<string, unknown>;
  const data = (source.data && typeof source.data === 'object' ? source.data : {}) as Record<string, unknown>;
  const loading = typeof data.loading_message === 'string' && data.loading_message.trim()
    ? data.loading_message
    : GENERIC_LOADING;
  const pick = projectId.value <= 0 ? 'empty_message_no_context' : 'empty_message';
  const datasetEmpty = typeof data[pick] === 'string' && (data[pick] as string).trim()
    ? (data[pick] as string)
    : '';
  const empty = datasetEmpty || GENERIC_EMPTY;
  return { loading, empty };
});

async function loadPreview() {
  const resolvedId = projectId.value;
  viewModel.value = null;
  if (resolvedId <= 0) {
    phase.value = 'idle';
    return;
  }
  phase.value = 'loading';
  try {
    const raw: BoqImportPreviewIntentData = await fetchBoqImportPreview({
      projectId: resolvedId,
    });
    viewModel.value = projectBoqImportPreview(raw);
  } catch (err) {
    viewModel.value = projectBoqImportPreview({
      ok: false,
      error: {
        code: 'BOQ_PREVIEW_FETCH_FAILED',
        message: err instanceof Error ? err.message : String(err),
      },
    } as BoqImportPreviewIntentData);
  } finally {
    phase.value = 'idle';
  }
}

onMounted(() => {
  void loadPreview();
});

watch(projectId, () => {
  void loadPreview();
});
</script>

<style scoped>
.block-boq-import-preview__hint {
  margin: 0;
  color: var(--sc-text-secondary, #666);
  font-size: 13px;
}
</style>
