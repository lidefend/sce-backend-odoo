<template>
  <section
    class="chart-dataset-panel"
    data-chart-dataset
    :data-view-state="model.viewState"
    data-readonly="true"
    :data-chart-key="model.chartKey || undefined"
    :aria-busy="loadingEngine"
  >
    <!-- 错误态：结构化错误透传，不白屏 -->
    <div v-if="model.viewState === 'error'" class="chart-dataset-panel__error" data-chart-error>
      <p class="chart-dataset-panel__error-code" data-error-code>{{ model.errorCode }}</p>
      <p class="chart-dataset-panel__error-message" data-error-message>{{ model.errorMessage }}</p>
      <p v-if="model.suggestedAction" class="chart-dataset-panel__error-hint" data-suggested-action>
        {{ model.suggestedAction }}
      </p>
    </div>

    <!-- 空态 / 防御性降级态 -->
    <div
      v-else-if="model.viewState === 'empty' || model.viewState === 'degraded_shape'"
      class="chart-dataset-panel__empty"
      data-chart-empty
    >
      <p class="chart-dataset-panel__empty-title">{{ model.title || model.chartKey || '图表' }}</p>
      <p class="chart-dataset-panel__empty-message" data-empty-message>{{ model.stateMessage }}</p>
    </div>

    <!-- 就绪态：echarts Canvas 只读渲染 -->
    <template v-else>
      <header class="chart-dataset-panel__header" data-chart-header>
        <h3 class="chart-dataset-panel__title">{{ model.title || model.chartKey }}</h3>
        <p class="chart-dataset-panel__meta" data-chart-meta>
          <span data-chart-schema>{{ model.schema }}</span>
          <span v-if="model.unit" data-chart-unit>单位：{{ model.unit }}</span>
        </p>
      </header>

      <div
        ref="canvasHost"
        class="chart-dataset-panel__canvas"
        data-chart-canvas
        :data-chart-type="model.chartType"
      >
        <p v-if="loadingEngine" class="chart-dataset-panel__hint" data-chart-loading>
          正在加载图表引擎...
        </p>
        <p v-else-if="engineError" class="chart-dataset-panel__hint" data-chart-engine-error>
          {{ engineError }}
        </p>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
/**
 * 可视化图表只读面板（G6.1，ADR-002）。
 *
 * 数据契约：contracts/domain/chart.yaml v1（只读域）。
 * 只读投影组件：不含任何写操作，错误/空态均结构化渲染。
 *
 * 引擎纪律（ADR-002 条件 1/3）：
 * - echarts 仅在就绪态首次渲染时经动态 import 按需加载
 *   （echarts/core + charts/components/renderers 子路径），
 *   不进首屏 bundle；
 * - 只 use BarChart/LineChart/PieChart + Grid/Tooltip/Legend +
 *   CanvasRenderer（tree-shakeable，禁全量引入，守卫
 *   scripts/verify/frontend_chart_engine_guard.py 钉死）；
 * - 颜色唯一来源 @sc/design-tokens CSS 变量
 *   --sc-semantic-chart-*（涨红跌绿，adapter 解析）。
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import type { ChartDatasetViewModel } from '../../app/presentation/chartDataset';
import { buildChartOption, resolveChartPalette } from './chartAdapter';

/** 动态加载后按需 use 的 echarts 模块形状（避免静态引入类型） */
type ChartModule = {
  init: (
    host: HTMLElement,
    options?: Record<string, unknown>,
  ) => {
    setOption: (option: Record<string, unknown>, opts?: Record<string, unknown>) => void;
    resize: () => void;
    dispose: () => void;
  };
  use: (modules: unknown[]) => void;
};

const props = defineProps<{
  model: ChartDatasetViewModel;
}>();

const canvasHost = ref<HTMLElement | null>(null);
const loadingEngine = ref(false);
const engineError = ref('');

let chartInstance: ReturnType<ChartModule['init']> | null = null;
let enginePromise: Promise<ChartModule> | null = null;
let resizeObserver: ResizeObserver | null = null;
let renderToken = 0;

/** 动态按需加载 echarts（子路径 import，tree-shakeable + 懒加载） */
function loadEngine(): Promise<ChartModule> {
  if (!enginePromise) {
    loadingEngine.value = true;
    enginePromise = Promise.all([
      import('echarts/core'),
      import('echarts/charts'),
      import('echarts/components'),
      import('echarts/renderers'),
    ])
      .then(([core, charts, components, renderers]) => {
        core.use([
          charts.BarChart,
          charts.LineChart,
          charts.PieChart,
          components.GridComponent,
          components.TooltipComponent,
          components.LegendComponent,
          renderers.CanvasRenderer,
        ]);
        loadingEngine.value = false;
        return core as ChartModule;
      })
      .catch((err: unknown) => {
        loadingEngine.value = false;
        enginePromise = null;
        throw err;
      });
  }
  return enginePromise;
}

/** 从组件根解析 token 调色板（颜色唯一来源：@sc/design-tokens） */
function readCssVar(cssVar: string): string {
  const host = canvasHost.value;
  if (!host || typeof window === 'undefined') return '';
  return window.getComputedStyle(host).getPropertyValue(cssVar);
}

async function renderChart(): Promise<void> {
  const token = ++renderToken;
  engineError.value = '';
  const host = canvasHost.value;
  if (!host || props.model.viewState !== 'ready') return;

  try {
    const engine = await loadEngine();
    if (token !== renderToken || canvasHost.value !== host) return;
    if (!chartInstance) {
      chartInstance = engine.init(host, { renderer: 'canvas' });
    }
    chartInstance.setOption(
      buildChartOption(props.model, resolveChartPalette(readCssVar)),
      // 只读投影：数据全量替换，不与旧 option 合并。
      { replaceMerge: ['series', 'xAxis', 'yAxis'] },
    );
  } catch (err: unknown) {
    if (token !== renderToken) return;
    // 引擎加载/渲染失败：结构化提示，不白屏（契约 consumer_contract）。
    engineError.value =
      err instanceof Error ? `图表渲染失败：${err.message}` : '图表渲染失败，请稍后重试。';
  }
}

function teardownChart(): void {
  renderToken += 1;
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
}

onMounted(() => {
  void renderChart();
});

watch(
  () => props.model,
  () => {
    if (props.model.viewState === 'ready') {
      void renderChart();
    } else {
      teardownChart();
    }
  },
);

onBeforeUnmount(teardownChart);

// 容器尺寸变化时同步 resize（驾驶舱栅格拖拽/折叠场景）。
if (typeof ResizeObserver !== 'undefined') {
  // 在 setup 顶层注册（挂载后生效），观察 canvas 宿主。
  const observer = new ResizeObserver(() => {
    chartInstance?.resize();
  });
  resizeObserver = observer;
  watch(canvasHost, (host) => {
    observer.disconnect();
    if (host) observer.observe(host);
  });
}
</script>

<style scoped>
.chart-dataset-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--sc-border-color, #d9d9d9);
  border-radius: 8px;
  font-size: 14px;
}

.chart-dataset-panel__header {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.chart-dataset-panel__title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.chart-dataset-panel__meta {
  margin: 0;
  display: flex;
  gap: 12px;
  color: var(--sc-text-secondary, #666);
  font-size: 12px;
}

.chart-dataset-panel__canvas {
  position: relative;
  width: 100%;
  height: 260px;
  min-height: 200px;
}

.chart-dataset-panel__hint {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  color: var(--sc-text-secondary, #666);
  font-size: 13px;
}

.chart-dataset-panel__error,
.chart-dataset-panel__empty {
  padding: 12px;
  border-radius: 6px;
}

.chart-dataset-panel__error {
  background: var(--sc-surface-danger-muted, #fff1f0);
}

.chart-dataset-panel__error-code {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--sc-danger, #cf1322);
}

.chart-dataset-panel__error-message,
.chart-dataset-panel__empty-message {
  margin: 4px 0 0;
}

.chart-dataset-panel__error-hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--sc-text-secondary, #666);
}

.chart-dataset-panel__empty {
  background: var(--sc-surface-muted, #f5f5f5);
}

.chart-dataset-panel__empty-title {
  margin: 0;
  font-weight: 600;
}
</style>
