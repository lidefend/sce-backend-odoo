<template>
  <article
    class="block block-chart-dataset"
    data-semantic-component="BlockChartDataset"
    :data-state="phase"
    data-readonly="true"
  >
    <header class="block-header">
      <h4>{{ block.title || '成本结构图表' }}</h4>
    </header>

    <p v-if="phase === 'loading'" class="block-chart-dataset__hint" data-loading>
      {{ copy.loading }}
    </p>

    <ChartDatasetPanel v-else-if="viewModel" :model="viewModel" />

    <p v-else class="block-chart-dataset__hint" data-empty>
      {{ copy.empty }}
    </p>
  </article>
</template>

<script setup lang="ts">
/**
 * 驾驶舱成本结构图表块包装（G6.1 Task #100，BlockBoqImportPreview 同款纪律）。
 *
 * 职责（共享层，无行业语义）：
 * - 从块契约 dataset（后端块投影）或路由 query 解析项目上下文 id
 *   与 chart_key（后端登记的三段键，本块不自行造键）；
 * - 通过块契约声明的 fetch intent（project.dashboard.chart.fetch）拉取
 *   只读数据投影，经 presentation Model 投影为四态视图模型；
 * - 渲染复用只读图表面板（echarts 懒加载，涨红跌绿经 token）。
 * 行业标题与空态文案由后端块契约（dataset copy 字段）提供，
 * 本组件只保留通用 fallback；任何降级（未登记/无数据/构建失败）
 * 均渲染结构化空/错态，不白屏。
 */
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import type { PageOrchestrationBlock } from '../../../app/pageOrchestration';
import ChartDatasetPanel from '../../chart/ChartDatasetPanel.vue';
import {
  fetchChartDataset,
  type ChartDatasetIntentData,
} from '../../../api/chartFetch';
import {
  projectChartDataset,
  type ChartDatasetViewModel,
} from '../../../app/presentation/chartDataset';

const GENERIC_LOADING = '正在加载数据...';
const GENERIC_EMPTY = '暂无可展示的数据。';
const DEFAULT_CHART_KEY = 'project.cost.structure';

const props = defineProps<{
  block: PageOrchestrationBlock;
  zoneKey: string;
  dataset: unknown;
}>();

const route = useRoute();
const phase = ref<'loading' | 'idle'>('idle');
const viewModel = ref<ChartDatasetViewModel | null>(null);

type BlockData = {
  project_id?: number;
  chart_key?: string;
  fetch_intent?: string;
  fetch_params?: { chart_key?: string; project_id?: number };
  loading_message?: string;
  empty_message?: string;
  empty_message_no_context?: string;
};

const blockData = computed<BlockData>(() => {
  const source = (props.dataset && typeof props.dataset === 'object' ? props.dataset : {}) as Record<string, unknown>;
  const data = (source.data && typeof source.data === 'object' ? source.data : {}) as Record<string, unknown>;
  return data as BlockData;
});

function toPositiveInt(value: unknown): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : 0;
}

const projectId = computed<number>(() => {
  const fromData = toPositiveInt(blockData.value.project_id)
    || toPositiveInt(blockData.value.fetch_params?.project_id);
  if (fromData > 0) return fromData;
  const fromQuery = toPositiveInt(route.query.project_id ?? route.query.projectId);
  return fromQuery;
});

/** chart_key 唯一来源：后端块契约（登记键），路由 query 仅兜底 */
const chartKey = computed<string>(() => {
  const fromData = String(blockData.value.chart_key
    || blockData.value.fetch_params?.chart_key || '').trim();
  if (fromData) return fromData;
  const fromQuery = String(route.query.chart_key || '').trim();
  return fromQuery || DEFAULT_CHART_KEY;
});

type BlockCopy = { loading: string; empty: string };

const copy = computed<BlockCopy>(() => {
  const loading = typeof blockData.value.loading_message === 'string' && blockData.value.loading_message.trim()
    ? blockData.value.loading_message
    : GENERIC_LOADING;
  const pick = projectId.value <= 0 ? 'empty_message_no_context' : 'empty_message';
  const datasetEmpty = typeof blockData.value[pick] === 'string' && (blockData.value[pick] as string).trim()
    ? (blockData.value[pick] as string)
    : '';
  return { loading, empty: datasetEmpty || GENERIC_EMPTY };
});

async function loadChart() {
  const resolvedProject = projectId.value;
  const resolvedChartKey = chartKey.value;
  viewModel.value = null;
  if (resolvedProject <= 0 || !resolvedChartKey) {
    phase.value = 'idle';
    return;
  }
  phase.value = 'loading';
  try {
    const raw: ChartDatasetIntentData = await fetchChartDataset({
      chartKey: resolvedChartKey,
      projectId: resolvedProject,
    });
    viewModel.value = projectChartDataset(raw);
  } catch (err) {
    // 传输层异常：以结构化错误重建（面板渲染错误态，不白屏）。
    viewModel.value = projectChartDataset({
      ok: false,
      error: {
        code: 'CHART_FETCH_FAILED',
        message: err instanceof Error ? err.message : String(err),
      },
    } as ChartDatasetIntentData);
  } finally {
    phase.value = 'idle';
  }
}

onMounted(() => {
  void loadChart();
});

watch([projectId, chartKey], () => {
  void loadChart();
});
</script>

<style scoped>
.block-chart-dataset__hint {
  margin: 0;
  color: var(--sc-text-secondary, #666);
  font-size: 13px;
}
</style>
