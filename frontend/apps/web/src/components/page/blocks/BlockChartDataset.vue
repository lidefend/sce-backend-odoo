<template>
  <article
    class="block block-chart-dataset"
    data-semantic-component="BlockChartDataset"
    :data-state="phase"
    data-readonly="true"
  >
    <ScCard class="block-card" :bordered="false" :title="block.title || '数据图表'">

      <p v-if="phase === 'loading'" class="block-chart-dataset__hint" data-loading>
        {{ copy.loading }}
      </p>

      <ChartDatasetPanel v-else-if="viewModel" :model="viewModel" />

      <p v-else class="block-chart-dataset__hint" data-empty>
        {{ copy.empty }}
      </p>
    </ScCard>
  </article>
</template>

<script setup lang="ts">
import ScCard from '../../design-system/ScCard.vue';
/**
 * 驾驶舱只读图表块包装（page orchestration block，G6.1 Task 100，
 * 与数据快照块包装同款纪律）。
 *
 * 职责（共享层，无行业语义）：
 * - 只消费块契约声明的 fetch_intent / fetch_params，不从路由补充参数；
 * - 通过块契约声明的 fetch intent 拉取只读数据投影，
 *   经 presentation Model 投影为四态视图模型；
 * - 渲染复用只读图表面板（echarts 懒加载，涨红跌绿经 token）。
 * 行业标题与空态文案由后端块契约（dataset copy 字段）提供，
 * 本组件只保留通用 fallback；任何降级（未登记/无数据/构建失败）
 * 均渲染结构化空/错态，不白屏。
 */
import { computed, onUnmounted, ref, watch } from 'vue';
import { createReadonlyBlockLoader, readonlyBlockData } from '../../../app/readonlyBlockRequest';
import type { PageOrchestrationBlock } from '../../../app/pageOrchestration';
import ChartDatasetPanel from '../../chart/ChartDatasetPanel.vue';
import {
  fetchChartDataset,
  resolveChartBlockRequest,
  type ChartDatasetIntentData,
} from '../../../api/chartFetch';
import {
  projectChartDataset,
  type ChartDatasetViewModel,
} from '../../../app/presentation/chartDataset';

const GENERIC_LOADING = '正在加载数据...';
const GENERIC_EMPTY = '暂无可展示的数据。';

const props = defineProps<{
  block: PageOrchestrationBlock;
  zoneKey: string;
  dataset: unknown;
}>();

const phase = ref<'loading' | 'idle'>('idle');
const viewModel = ref<ChartDatasetViewModel | null>(null);

const blockData = computed(() => readonlyBlockData(props.dataset));
const request = computed(() => resolveChartBlockRequest(blockData.value));

type BlockCopy = { loading: string; empty: string };

const copy = computed<BlockCopy>(() => {
  const loading = typeof blockData.value.loading_message === 'string' && blockData.value.loading_message.trim()
    ? blockData.value.loading_message
    : GENERIC_LOADING;
  const pick = request.value.status !== 'ready' ? 'empty_message_no_context' : 'empty_message';
  const datasetEmpty = typeof blockData.value[pick] === 'string' && (blockData.value[pick] as string).trim()
    ? (blockData.value[pick] as string)
    : '';
  return { loading, empty: datasetEmpty || GENERIC_EMPTY };
});

const loader = createReadonlyBlockLoader<ChartDatasetIntentData>({
  reset(loading) { viewModel.value = null; phase.value = loading ? 'loading' : 'idle'; },
  success(raw) { viewModel.value = projectChartDataset(raw); },
  error(error) {
    viewModel.value = projectChartDataset({
      ok: false,
      error: { code: 'CHART_FETCH_FAILED',
        message: error instanceof Error ? error.message : String(error), suggested_action: 'retry' },
    });
  },
  settled() { phase.value = 'idle'; },
});

watch(() => JSON.stringify(request.value), () => {
  const resolved = request.value;
  void loader.load(resolved.status === 'ready' ? () => fetchChartDataset(resolved.request) : null);
}, { immediate: true, flush: 'sync' });
onUnmounted(() => loader.dispose());
</script>

<style scoped>
.block { min-width: 0; }
.block-card { min-width: 0; height: 100%; }
.block-chart-dataset__hint {
  margin: 0;
  color: var(--sc-semantic-text-secondary);
  font-size: 13px;
}
</style>
