import { strict as assert } from 'node:assert';
import {
  CHART_DATASET_STATE_DEGRADED_SHAPE,
  CHART_DATASET_STATE_EMPTY,
  CHART_DATASET_STATE_ERROR,
  CHART_DATASET_STATE_READY,
  CHART_DATASET_VIEW_READONLY,
  projectChartDataset,
} from '../src/app/presentation/chartDataset';
import {
  buildChartOption,
  resolveChartPalette,
  type ChartPalette,
} from '../src/components/chart/chartAdapter';
import type { ChartDatasetIntentData } from '../src/api/chartFetch';

// ── ready 投影（直传形状：intentRequest 正常路径） ──────────
const READY_RAW: ChartDatasetIntentData = {
  schema: 'sc.visualization.chart.v1',
  chart_key: 'project.cost.structure',
  chart_type: 'bar',
  title: '成本结构',
  unit: 'CNY',
  readonly: true,
  series: [
    {
      name: '本月成本',
      metric: { key: 'cost_amount', label: '成本金额' },
      dimensions: { key: 'cost_category', label: '成本科目' },
      points: [
        { dimension_value: '人工', value: 1200 },
        { dimension_value: '材料', value: 1500 },
        { dimension_value: '机械', value: 900 },
      ],
    },
    {
      name: '上月成本',
      metric: { key: 'cost_amount', label: '成本金额' },
      dimensions: { key: 'cost_category', label: '成本科目' },
      points: [
        { dimension_value: '人工', value: 1100 },
        { dimension_value: '材料', value: 1600 },
      ],
    },
  ],
  safe_degradation: {},
};

const ready = projectChartDataset(READY_RAW);
assert.equal(ready.viewState, CHART_DATASET_STATE_READY);
assert.equal(ready.readonly, CHART_DATASET_VIEW_READONLY);
assert.equal(ready.schema, 'sc.visualization.chart.v1');
assert.equal(ready.chartKey, 'project.cost.structure');
assert.equal(ready.chartType, 'bar');
assert.equal(ready.title, '成本结构');
assert.equal(ready.unit, 'CNY');
assert.equal(ready.errorCode, null);
assert.equal(ready.stateMessage, '');
assert.equal(ready.series.length, 2);
assert.equal(ready.series[0]?.points.length, 3);
assert.equal(ready.series[0]?.points[1]?.value, 1500);
assert.equal(ready.series[0]?.metricLabel, '成本金额');
assert.equal(ready.series[0]?.dimensionLabel, '成本科目');
// 类目轴：按首次出现顺序并集
assert.deepEqual(ready.categories, ['人工', '材料', '机械']);
assert.equal(ready.errorCode, null);

// ── 信封形状（ok=true + data 包裹） ─────────────────────────
const enveloped = projectChartDataset({ ok: true, data: READY_RAW });
assert.equal(enveloped.viewState, CHART_DATASET_STATE_READY);
assert.equal(enveloped.chartKey, 'project.cost.structure');
assert.deepEqual(enveloped.categories, ['人工', '材料', '机械']);

// ── 错误态：CHART_NOT_REGISTERED（契约核心降级） ────────────
const notRegistered = projectChartDataset({
  ok: false,
  error: {
    code: 'CHART_NOT_REGISTERED',
    message: '图表未登记或不可用：project.cost.structure',
    suggested_action: 'fix_input',
  },
  data: { chart_key: 'project.cost.structure' },
});
assert.equal(notRegistered.viewState, CHART_DATASET_STATE_ERROR);
assert.equal(notRegistered.errorCode, 'CHART_NOT_REGISTERED');
assert.equal(notRegistered.suggestedAction, 'fix_input');
assert.equal(notRegistered.chartKey, 'project.cost.structure');
assert.deepEqual(notRegistered.series, []);
assert.deepEqual(notRegistered.categories, []);

// ── 错误态：MISSING_PARAMS / PROJECT_NOT_FOUND / CHART_DATASET_ERROR ──
for (const code of ['MISSING_PARAMS', 'PROJECT_NOT_FOUND', 'CHART_DATASET_ERROR']) {
  const failed = projectChartDataset({
    ok: false,
    error: { code, message: `msg:${code}`, suggested_action: 'retry' },
    data: {},
  });
  assert.equal(failed.viewState, CHART_DATASET_STATE_ERROR);
  assert.equal(failed.errorCode, code);
}

// 调用方 catch 重建形状（fetch 异常路径）
const fetchFailed = projectChartDataset({
  ok: false,
  error: { code: 'CHART_FETCH_FAILED', message: '网络异常' },
});
assert.equal(fetchFailed.viewState, CHART_DATASET_STATE_ERROR);
assert.equal(fetchFailed.errorCode, 'CHART_FETCH_FAILED');

// ok=false 且 error 缺失 → 兜底错误码
const noError = projectChartDataset({ ok: false, data: {} });
assert.equal(noError.viewState, CHART_DATASET_STATE_ERROR);
assert.equal(noError.errorCode, 'CHART_UNAVAILABLE');

// ── 空态：series 为空 / 全零点 ─────────────────────────────
const emptySeries = projectChartDataset({
  schema: 'sc.visualization.chart.v1',
  chart_key: 'project.cost.structure',
  chart_type: 'bar',
  title: '成本结构',
  series: [],
});
assert.equal(emptySeries.viewState, CHART_DATASET_STATE_EMPTY);
assert.equal(emptySeries.chartKey, 'project.cost.structure');
assert.ok(emptySeries.stateMessage.length > 0);

const zeroPoints = projectChartDataset({
  ...READY_RAW,
  series: [{ name: '空系列', points: [] }],
});
assert.equal(zeroPoints.viewState, CHART_DATASET_STATE_EMPTY);

// ── 防御性降级：ok=true 但缺 chart_key ──────────────────────
const degraded = projectChartDataset({ schema: 'sc.visualization.chart.v1', series: [] });
assert.equal(degraded.viewState, CHART_DATASET_STATE_DEGRADED_SHAPE);
assert.equal(degraded.errorCode, 'CHART_DEGRADED_SHAPE');

// raw 为 null / 畸形
const nullRaw = projectChartDataset(null);
assert.equal(nullRaw.viewState, CHART_DATASET_STATE_ERROR);
assert.equal(nullRaw.errorCode, 'CHART_UNAVAILABLE');

// chart_type 非法值 → 防御性回落 bar（不抛异常）
const badType = projectChartDataset({ ...READY_RAW, chart_type: 'scatter3d' });
assert.equal(badType.viewState, CHART_DATASET_STATE_READY);
assert.equal(badType.chartType, 'bar');

// 字符串数值容错
const stringy = projectChartDataset({
  ...READY_RAW,
  series: [
    {
      name: '字符串数值',
      points: [
        { dimension_value: 'A', value: '42' },
        { dimension_value: '', value: 1 },
        null,
      ] as never,
    },
  ],
});
assert.equal(stringy.viewState, CHART_DATASET_STATE_READY);
assert.equal(stringy.series[0]?.points.length, 1);
assert.equal(stringy.series[0]?.points[0]?.value, 42);

// ── palette 解析：CSS 变量优先，缺失走 fallback ─────────────
const paletteFromVars = resolveChartPalette((cssVar) => {
  const map: Record<string, string> = {
    '--sc-semantic-chart-up': ' #ff0000 ',
    '--sc-semantic-chart-down': '#00aa00',
    '--sc-semantic-chart-series-1': '#111111',
  };
  return map[cssVar] ?? '';
});
assert.equal(paletteFromVars.up, '#ff0000'); // trim
assert.equal(paletteFromVars.down, '#00aa00');
assert.equal(paletteFromVars.series[0], '#111111');
// 未注入的变量走 light 兜底
assert.equal(paletteFromVars.upStrong, '#b91c1c');
assert.equal(paletteFromVars.neutral, '#2563eb');
assert.equal(paletteFromVars.series[5], '#64748b');

const paletteAllMissing = resolveChartPalette(() => '');
assert.equal(paletteAllMissing.up, '#ef4444');
assert.equal(paletteAllMissing.down, '#22c55e');

// ── option 构建：单系列 bar 涨红跌绿着色 ────────────────────
const singleSeriesReady = projectChartDataset({
  ...READY_RAW,
  series: [READY_RAW.series![0]!],
});
const palette: ChartPalette = {
  up: 'UP', upStrong: 'UPS', down: 'DOWN', downStrong: 'DOWNS',
  neutral: 'NEUTRAL', warning: 'WARN',
  series: ['S1', 'S2', 'S3', 'S4', 'S5', 'S6'],
};
const barOption = buildChartOption(singleSeriesReady, palette) as {
  series: Array<{ type: string; data: Array<number | null>; itemStyle?: { color: unknown } }>;
  xAxis: { data: string[] };
  yAxis: { name?: string };
};
assert.equal(barOption.series.length, 1);
assert.equal(barOption.series[0]?.type, 'bar');
assert.deepEqual(barOption.series[0]?.data, [1200, 1500, 900]);
assert.deepEqual(barOption.xAxis.data, ['人工', '材料', '机械']);
assert.equal(barOption.yAxis.name, 'CNY');
const colorFn = barOption.series[0]?.itemStyle?.color as (
  params: { dataIndex: number; value?: number | null },
) => string;
assert.equal(typeof colorFn, 'function');
// 首柱 neutral；涨→up（红）；跌→down（绿）
assert.equal(colorFn({ dataIndex: 0, value: 1200 }), 'NEUTRAL');
assert.equal(colorFn({ dataIndex: 1, value: 1500 }), 'UP');
assert.equal(colorFn({ dataIndex: 2, value: 900 }), 'DOWN');

// ── option 构建：多系列 bar 用系列色序 + 类目对齐补 null ────
const multiBarOption = buildChartOption(ready, palette) as {
  series: Array<{ type: string; data: Array<number | null>; color?: string; itemStyle?: unknown }>;
  legend?: unknown;
};
assert.equal(multiBarOption.series.length, 2);
assert.equal(multiBarOption.series[0]?.itemStyle, undefined);
assert.equal(multiBarOption.series[0]?.color, 'S1');
assert.equal(multiBarOption.series[1]?.color, 'S2');
assert.ok(multiBarOption.legend);
// 第二系列缺「机械」类目 → 补 null（不补点、不改写）
assert.deepEqual(multiBarOption.series[1]?.data, [1100, 1600, null]);

// ── option 构建：line / pie ─────────────────────────────────
const lineReady = projectChartDataset({ ...READY_RAW, chart_type: 'line' });
const lineOption = buildChartOption(lineReady, palette) as {
  series: Array<{ type: string }>;
};
assert.equal(lineOption.series[0]?.type, 'line');

const pieReady = projectChartDataset({ ...READY_RAW, chart_type: 'pie' });
const pieOption = buildChartOption(pieReady, palette) as {
  series: Array<{
    type: string;
    data: Array<{ name: string; value: number }>;
    color: string[];
  }>;
  tooltip: { trigger: string };
  xAxis?: unknown;
};
assert.equal(pieOption.series[0]?.type, 'pie');
assert.deepEqual(pieOption.series[0]?.data, [
  { name: '人工', value: 1200 },
  { name: '材料', value: 1500 },
  { name: '机械', value: 900 },
]);
assert.deepEqual(pieOption.series[0]?.color, ['S1', 'S2', 'S3', 'S4', 'S5', 'S6']);
assert.equal(pieOption.tooltip.trigger, 'item');
assert.equal(pieOption.xAxis, undefined);

console.info('[chart-dataset-model-test] all assertions passed');
