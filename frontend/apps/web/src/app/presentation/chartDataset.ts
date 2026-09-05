/**
 * 可视化图表只读数据投影 Model（G6.1，ADR-002）。
 *
 * 数据契约：contracts/domain/chart.yaml v1（只读域，safe_degradation 语义）。
 * 消费 intent：project.dashboard.chart.fetch（只读，MACHINE_ACCESS=read）。
 *
 * 视图状态机（复用 G3.2 四态纪律）：
 *  - ready           ：series 非空且形状合法，投影可直接渲染的系列与类目轴
 *  - empty           ：ok=true 但 series 为空 / 全空点（后端降级语义），
 *                      渲染空态，不白屏
 *  - error           ：ok=false（MISSING_PARAMS / CHART_NOT_REGISTERED /
 *                      PROJECT_NOT_FOUND / CHART_DATASET_ERROR），
 *                      透传结构化错误与 suggested_action
 *  - degraded_shape  ：ok=true 但投影形状异常，防御性降级
 *
 * 只读投影边界：本 Model 不产生任何写 intent；颜色与涨红跌绿语义不在
 * 本层表达——由 chart adapter 经 @sc/design-tokens CSS 变量决定
 * （ADR-002 条件 5/6）。
 */
import type {
  ChartDatasetData,
  ChartDatasetIntentData,
  ChartSeries,
  ChartSeriesPoint,
} from '../../api/chartFetch';

/** 契约 schema 版本（与 api/chartFetch.ts 保持一致；本地声明保持纯函数无运行时依赖） */
const CHART_SCHEMA_VERSION = 'sc.visualization.chart.v1';

export const CHART_DATASET_VIEW_READONLY = true;
export const CHART_DATASET_STATE_READY = 'ready';
export const CHART_DATASET_STATE_EMPTY = 'empty';
export const CHART_DATASET_STATE_ERROR = 'error';
export const CHART_DATASET_STATE_DEGRADED_SHAPE = 'degraded_shape';

export const CHART_DATASET_EMPTY_MESSAGE =
  '该图表暂无可展示的数据（数据缺失或构建为空），可稍后重试。';
export const CHART_DATASET_DEGRADED_SHAPE_MESSAGE =
  '图表数据形状异常，已降级为只读摘要展示。';

export type ChartDatasetViewState =
  | typeof CHART_DATASET_STATE_READY
  | typeof CHART_DATASET_STATE_EMPTY
  | typeof CHART_DATASET_STATE_ERROR
  | typeof CHART_DATASET_STATE_DEGRADED_SHAPE;

export type ChartType = 'bar' | 'line' | 'pie';

/** 归一化数据点：dimension_value 文本 + 有限数值 */
export type ChartPointView = {
  dimensionValue: string;
  value: number;
};

/** 归一化系列：契约字段的只读视图投影 */
export type ChartSeriesView = {
  name: string;
  metricKey: string;
  metricLabel: string;
  dimensionKey: string;
  dimensionLabel: string;
  points: ChartPointView[];
};

export type ChartDatasetViewModel = {
  viewState: ChartDatasetViewState;
  readonly: typeof CHART_DATASET_VIEW_READONLY;
  schema: string;
  chartKey: string;
  chartType: ChartType;
  title: string;
  unit: string;
  series: ChartSeriesView[];
  /** 类目轴：全部系列 dimension_value 的按序并集（bar/line 用） */
  categories: string[];
  errorCode: string | null;
  errorMessage: string | null;
  suggestedAction: string | null;
  stateMessage: string;
};

function toText(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function toNumber(value: unknown): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return 0;
}

function normalizeChartType(value: unknown): ChartType {
  const text = toText(value);
  if (text === 'bar' || text === 'line' || text === 'pie') return text;
  return 'bar';
}

function normalizePoints(raw: unknown): ChartPointView[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((point) => {
      if (!point || typeof point !== 'object') return null;
      const record = point as ChartSeriesPoint;
      const dimensionValue = toText(record.dimension_value).trim();
      if (!dimensionValue) return null;
      return { dimensionValue, value: toNumber(record.value) };
    })
    .filter((point): point is ChartPointView => point !== null);
}

function normalizeSeries(raw: unknown): ChartSeriesView[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((entry) => {
    if (!entry || typeof entry !== 'object') {
      return {
        name: '',
        metricKey: '',
        metricLabel: '',
        dimensionKey: '',
        dimensionLabel: '',
        points: [],
      };
    }
    const record = entry as ChartSeries;
    return {
      name: toText(record.name),
      metricKey: toText(record.metric?.key),
      metricLabel: toText(record.metric?.label),
      dimensionKey: toText(record.dimensions?.key),
      dimensionLabel: toText(record.dimensions?.label),
      points: normalizePoints(record.points),
    };
  });
}

/** 类目轴：按首次出现顺序合并全部系列的 dimension_value */
function buildCategories(series: ChartSeriesView[]): string[] {
  const seen = new Set<string>();
  const ordered: string[] = [];
  for (const entry of series) {
    for (const point of entry.points) {
      if (!seen.has(point.dimensionValue)) {
        seen.add(point.dimensionValue);
        ordered.push(point.dimensionValue);
      }
    }
  }
  return ordered;
}

function errorViewModel(
  raw: ChartDatasetIntentData | null | undefined,
  fallbackMessage: string,
): ChartDatasetViewModel {
  const error = raw?.error;
  return {
    viewState: CHART_DATASET_STATE_ERROR,
    readonly: CHART_DATASET_VIEW_READONLY,
    schema: CHART_SCHEMA_VERSION,
    chartKey: toText(raw?.data?.chart_key),
    chartType: 'bar',
    title: '',
    unit: '',
    series: [],
    categories: [],
    errorCode: toText(error?.code) || 'CHART_UNAVAILABLE',
    errorMessage: toText(error?.message) || fallbackMessage,
    suggestedAction: toText(error?.suggested_action) || null,
    stateMessage: toText(error?.message) || fallbackMessage,
  };
}


function emptyState(
  source: ChartDatasetData,
  stateMessage: string,
): ChartDatasetViewModel {
  return {
    viewState: CHART_DATASET_STATE_EMPTY,
    readonly: CHART_DATASET_VIEW_READONLY,
    schema: toText(source.schema) || CHART_SCHEMA_VERSION,
    chartKey: toText(source.chart_key),
    chartType: normalizeChartType(source.chart_type),
    title: toText(source.title),
    unit: toText(source.unit),
    series: [],
    categories: [],
    errorCode: null,
    errorMessage: null,
    suggestedAction: null,
    stateMessage,
  };
}

/**
 * 将 intent 结构化返回投影为只读视图模型。
 * 纯函数：无网络/会话/DOM 依赖，可被 esbuild 单测直接覆盖。
 *
 * 输入形状兼容（信封解包错位防御，与 boqImportPreview 同款）：
 * - 直传形状 { schema, chart_key, series, ... }：intentRequest 正常路径；
 * - 信封形状 { ok, data: {...}, error }：调用方 catch 分支重建。
 */
export function projectChartDataset(
  raw: ChartDatasetIntentData | null | undefined,
): ChartDatasetViewModel {
  if (!raw || typeof raw !== 'object' || raw.ok === false) {
    return errorViewModel(raw, '未能获取图表数据。');
  }

  const record = raw as ChartDatasetIntentData;
  const hasDirectPayload =
    record.chart_key !== undefined || record.series !== undefined;
  const source: ChartDatasetData = hasDirectPayload
    ? record
    : record.data && typeof record.data === 'object'
      ? record.data
      : {};

  const chartKey = toText(source.chart_key);
  const series = normalizeSeries(source.series);

  if (!chartKey || series.length === 0) {
    // 形状异常：ok=true 但缺 chart_key 或 series 非法 → 防御性降级，不白屏。
    if (!chartKey) {
      return {
        viewState: CHART_DATASET_STATE_DEGRADED_SHAPE,
        readonly: CHART_DATASET_VIEW_READONLY,
        schema: toText(source.schema) || CHART_SCHEMA_VERSION,
        chartKey: '',
        chartType: normalizeChartType(source.chart_type),
        title: toText(source.title),
        unit: toText(source.unit),
        series: [],
        categories: [],
        errorCode: 'CHART_DEGRADED_SHAPE',
        errorMessage: CHART_DATASET_DEGRADED_SHAPE_MESSAGE,
        suggestedAction: 'retry',
        stateMessage: CHART_DATASET_DEGRADED_SHAPE_MESSAGE,
      };
    }
    // chart_key 合法但 series 空 → 契约空态语义。
    return emptyState(source, CHART_DATASET_EMPTY_MESSAGE);
  }

  const totalPoints = series.reduce((sum, entry) => sum + entry.points.length, 0);
  if (totalPoints === 0) {
    // 全系列零点：同样按空态渲染（后端降级为空 series）。
    return emptyState(source, CHART_DATASET_EMPTY_MESSAGE);
  }

  return {
    viewState: CHART_DATASET_STATE_READY,
    readonly: CHART_DATASET_VIEW_READONLY,
    schema: toText(source.schema) || CHART_SCHEMA_VERSION,
    chartKey,
    chartType: normalizeChartType(source.chart_type),
    title: toText(source.title),
    unit: toText(source.unit),
    series,
    categories: buildCategories(series),
    errorCode: null,
    errorMessage: null,
    suggestedAction: null,
    stateMessage: '',
  };
}
