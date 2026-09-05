/**
 * 可视化图表渲染 adapter（G6.1，ADR-002 条件 5/6）。
 *
 * 职责边界：
 * - 颜色唯一来源是 @sc/design-tokens 输出的 CSS 变量
 *   --sc-semantic-chart-*（涨=红、跌=绿；6 个系列色序）；
 * - 本模块不 import echarts（option 是纯数据，供 echarts/core 消费），
 *   不依赖 DOM——palette 通过注入的读取函数解析，可被 esbuild 单测
 *   直接覆盖；
 * - 数值与类目完全来自 presentation Model（后端权威投影），
 *   adapter 不聚合、不补点、不改写。
 *
 * 涨红跌绿语义（ADR-002 条件 5）：
 * - bar：单系列逐柱环比（value[i] vs value[i-1]），首柱/持平用 neutral，
 *   涨用 up（红）、跌用 down（绿）；
 * - line / pie：按系列色序 series_1~6 分配（趋势语义由数据本身表达，
 *   不额外断言涨跌）。
 */
import type { ChartDatasetViewModel, ChartSeriesView } from '../../app/presentation/chartDataset';

export type ChartPalette = {
  up: string;
  upStrong: string;
  down: string;
  downStrong: string;
  neutral: string;
  warning: string;
  /** 系列色序（series_1 ~ series_6） */
  series: string[];
};

/** token 名 → CSS 变量名（@sc/design-tokens dist/web/tokens.*.css） */
const CHART_PALETTE_VARS = {
  up: '--sc-semantic-chart-up',
  upStrong: '--sc-semantic-chart-up-strong',
  down: '--sc-semantic-chart-down',
  downStrong: '--sc-semantic-chart-down-strong',
  neutral: '--sc-semantic-chart-neutral',
  warning: '--sc-semantic-chart-warning',
  series: [
    '--sc-semantic-chart-series-1',
    '--sc-semantic-chart-series-2',
    '--sc-semantic-chart-series-3',
    '--sc-semantic-chart-series-4',
    '--sc-semantic-chart-series-5',
    '--sc-semantic-chart-series-6',
  ],
} as const;

/**
 * CSS 变量缺失时的兜底（与 semantic.light.json 输出一致）。
 * 仅在 token CSS 未加载的异常场景生效，等价于样式层
 * `var(--sc-semantic-chart-up, #ef4444)` 的 fallback 语义；
 * 正常路径颜色始终来自 @sc/design-tokens 注入。
 */
const FALLBACK_PALETTE: ChartPalette = {
  up: '#ef4444',
  upStrong: '#b91c1c',
  down: '#22c55e',
  downStrong: '#047857',
  neutral: '#2563eb',
  warning: '#f59e0b',
  series: ['#2563eb', '#14b8a6', '#4338ca', '#00b6fe', '#3285e6', '#64748b'],
};

/**
 * 解析图表调色板。
 *
 * @param read CSS 变量读取函数（组件传 computed style 的
 *        getPropertyValue；单测注入伪实现）。
 */
export function resolveChartPalette(read: (cssVar: string) => string): ChartPalette {
  const pick = (cssVar: string, fallback: string): string => {
    const value = (read(cssVar) || '').trim();
    return value || fallback;
  };
  return {
    up: pick(CHART_PALETTE_VARS.up, FALLBACK_PALETTE.up),
    upStrong: pick(CHART_PALETTE_VARS.upStrong, FALLBACK_PALETTE.upStrong),
    down: pick(CHART_PALETTE_VARS.down, FALLBACK_PALETTE.down),
    downStrong: pick(CHART_PALETTE_VARS.downStrong, FALLBACK_PALETTE.downStrong),
    neutral: pick(CHART_PALETTE_VARS.neutral, FALLBACK_PALETTE.neutral),
    warning: pick(CHART_PALETTE_VARS.warning, FALLBACK_PALETTE.warning),
    series: CHART_PALETTE_VARS.series.map((cssVar, index) =>
      pick(cssVar, FALLBACK_PALETTE.series[index]),
    ),
  };
}

/** 逐柱环比的涨红跌绿着色函数（echarts itemStyle.color 回调签名） */
function barTrendColor(palette: ChartPalette): (params: {
  dataIndex: number;
  value?: number | string | null;
}) => string {
  // 闭包持有上一柱数值，逐柱推进（echarts 按序调用）。
  let previous: number | null = null;
  return (params) => {
    const current = typeof params.value === 'number' && Number.isFinite(params.value)
      ? params.value
      : Number(params.value);
    if (!Number.isFinite(current)) return palette.neutral;
    const base = previous;
    previous = current;
    if (base === null) return palette.neutral;
    if (current > base) return palette.up;
    if (current < base) return palette.down;
    return palette.neutral;
  };
}

/** 系列数值按类目轴对齐（缺失类目补 null，不改写、不插值） */
function alignPointsToCategories(
  series: ChartSeriesView,
  categories: string[],
): Array<number | null> {
  const byDimension = new Map(series.points.map((point) => [point.dimensionValue, point.value]));
  return categories.map((category) => {
    const value = byDimension.get(category);
    return value === undefined ? null : value;
  });
}

/**
 * 构建 echarts option（纯数据，无 echarts 依赖、无 DOM 依赖）。
 *
 * 输入是 presentation Model 的 ready 态；其他状态由组件渲染空/错态，
 * 不进入本函数。option 里的任何数值都来自后端投影。
 */
export function buildChartOption(
  model: ChartDatasetViewModel,
  palette: ChartPalette,
): Record<string, unknown> {
  const base: Record<string, unknown> = {
    animation: false,
    tooltip: {
      trigger: model.chartType === 'pie' ? 'item' : 'axis',
    },
  };

  if (model.chartType === 'pie') {
    // 饼图取首个系列（多系列饼图无行业语义，防御性只取第一份）。
    const first = model.series[0];
    return {
      ...base,
      series: [
        {
          type: 'pie',
          radius: ['38%', '66%'],
          center: ['50%', '50%'],
          data: first.points.map((point) => ({
            name: point.dimensionValue,
            value: point.value,
          })),
          color: palette.series,
          label: { show: true, formatter: '{b}: {d}%' },
        },
      ],
    };
  }

  const seriesList = model.series.map((entry, index) => {
    const data = alignPointsToCategories(entry, model.categories);
    if (model.chartType === 'bar' && model.series.length === 1) {
      // 单系列柱状图：逐柱涨红跌绿（ADR-002 条件 5 核心场景）。
      return {
        name: entry.name || entry.metricLabel || model.title,
        type: 'bar',
        data,
        itemStyle: { color: barTrendColor(palette) },
      };
    }
    return {
      name: entry.name || entry.metricLabel || `系列${index + 1}`,
      type: model.chartType,
      data,
      color: palette.series[index % palette.series.length],
      symbolSize: 6,
    };
  });

  return {
    ...base,
    grid: { left: 8, right: 16, top: 32, bottom: 8, containLabel: true },
    legend:
      model.series.length > 1
        ? { top: 0, left: 'center', textStyle: { fontSize: 12 } }
        : undefined,
    xAxis: {
      type: 'category',
      data: model.categories,
      axisLabel: { fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      name: model.unit || undefined,
      axisLabel: { fontSize: 12 },
    },
    series: seriesList,
  };
}
