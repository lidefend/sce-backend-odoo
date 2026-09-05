/**
 * 可视化图表只读数据投影 API 封装（G6.1，ADR-002 条件 4「契约先行」）。
 *
 * 数据契约：contracts/domain/chart.yaml v1（只读域，safe_degradation 语义）。
 * Intent：project.dashboard.chart.fetch（后端 search 语义防枚举：
 * 项目不可访问与不存在同响应 PROJECT_NOT_FOUND）。
 *
 * 事实源边界：series 完全由后端 dataset_builder 物化（name + metric +
 * dimensions + points），前端不得聚合、不得补点、不得改写数值，
 * 更不得向渲染层传任意 option。
 *
 * 安全降级约定（与 boqImportPreview 同款）：
 * - 业务层降级（MISSING_PARAMS / CHART_NOT_REGISTERED /
 *   PROJECT_NOT_FOUND / CHART_DATASET_ERROR）以后端结构化 ok=false 返回；
 *   parseIntentEnvelope 判 ok=false 抛 ApiError，由调用方 catch 后以
 *   {ok:false, error} 重建并交给 presentation Model 投影为错误态，
 *   消费方不得白屏。
 */
import { intentRequest } from './intents';

export const CHART_FETCH_INTENT = 'project.dashboard.chart.fetch';
export const CHART_SCHEMA_VERSION = 'sc.visualization.chart.v1';

/** 契约允许的图表类型（chart.yaml v1 enum） */
export type ChartType = 'bar' | 'line' | 'pie';

/** 后端物化的数据点（dimension_value + value，不得补点/改写） */
export type ChartSeriesPoint = {
  dimension_value?: string;
  value?: number | string | null;
};

/** 后端物化的系列投影（chart.yaml fields.series 逐字段） */
export type ChartSeries = {
  name?: string;
  metric?: { key?: string; label?: string };
  dimensions?: { key?: string; label?: string };
  points?: ChartSeriesPoint[];
};

export type ChartDatasetError = {
  code: string;
  message: string;
  suggested_action?: string;
};

/** handler data 形状（sc.visualization.chart.v1 投影） */
export type ChartDatasetData = {
  schema?: string;
  chart_key?: string;
  chart_type?: string;
  title?: string;
  unit?: string;
  readonly?: boolean;
  series?: ChartSeries[];
  safe_degradation?: Record<string, unknown>;
};

/**
 * intent 结构化返回的兼容联合形状：
 * - 直传形状：{ schema, chart_key, ... }（intentRequest 正常路径，
 *   信封 {ok,data,meta} 已被 parseIntentEnvelope 剥掉）；
 * - 信封形状：{ ok: false, error }（调用方 catch 分支重建）。
 */
export type ChartDatasetIntentData = ChartDatasetData & {
  ok?: boolean;
  data?: ChartDatasetData;
  error?: ChartDatasetError;
};

/**
 * 拉取登记图表（visualization.chart capability）的只读数据投影。
 *
 * 入参与后端 handler 对齐：chart_key（三段键）与 project_id 必填。
 * 传输层异常（网络/协议）照常抛出；业务降级以原始结构化数据透传，
 * 由 presentation Model 投影。
 */
export async function fetchChartDataset(params: {
  chartKey: string;
  projectId: number;
}): Promise<ChartDatasetIntentData> {
  return intentRequest<ChartDatasetIntentData>({
    intent: CHART_FETCH_INTENT,
    params: {
      chart_key: params.chartKey,
      project_id: params.projectId,
    },
  });
}
