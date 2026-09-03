<template>
  <article
    class="block block-boq-import-preview"
    data-semantic-component="BlockBoqImportPreview"
    :data-state="phase"
    data-readonly="true"
  >
    <header class="block-header">
      <h4>{{ block.title || '清单导入预览' }}</h4>
    </header>

    <p v-if="phase === 'loading'" class="block-boq-import-preview__hint" data-loading>
      正在加载清单导入预检快照...
    </p>

    <BoqImportPreviewPanel v-else-if="viewModel" :model="viewModel" />

    <p v-else class="block-boq-import-preview__hint" data-empty>
      {{ emptyMessage }}
    </p>
  </article>
</template>

<script setup lang="ts">
/**
 * BOQ 导入预检快照块（G3.3 组件挂接）。
 *
 * 驾驶舱 page orchestration block 的薄包装：
 * - 从块契约 dataset（ProjectBoqPreviewBuilder 投影）或路由
 *   query（route_context.query_key = project_id）解析项目上下文；
 * - 通过专用 intent（project.boq.import.preview.fetch）拉取快照，
 *   经 presentation Model 投影为四态视图模型；
 * - 渲染复用 BoqImportPreviewPanel（只读，无写操作入口）。
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

const props = defineProps<{
  block: PageOrchestrationBlock;
  zoneKey: string;
  dataset: unknown;
}>();

const route = useRoute();
const phase = ref<'loading' | 'idle'>('idle');
const viewModel = ref<BoqImportPreviewViewModel | null>(null);

const projectId = computed(() => resolveBoqBlockProjectId(props.dataset, route.query));

const emptyMessage = computed(() => {
  if (projectId.value <= 0) {
    return '当前未指定项目上下文，无法展示清单导入预检快照。';
  }
  return '该项目还没有清单导入批次记录。';
});

async function loadPreview() {
  const resolvedProjectId = projectId.value;
  viewModel.value = null;
  if (resolvedProjectId <= 0) {
    phase.value = 'idle';
    return;
  }
  phase.value = 'loading';
  try {
    const raw: BoqImportPreviewIntentData = await fetchBoqImportPreview({
      projectId: resolvedProjectId,
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
