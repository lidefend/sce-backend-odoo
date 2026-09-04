/**
 * BOQ 导入批次只读预检快照投影 API 封装（G3.2）。
 *
 * 数据契约：contracts/domain/boq.yaml v1（只读域，safe_degradation 语义）。
 * Intent：project.boq.import.preview.fetch（后端 search 语义防枚举：
 * 无权限与不存在同响应 BATCH_NOT_FOUND）。
 *
 * 安全降级约定：
 * - 业务层降级（MISSING_PARAMS / BATCH_NOT_FOUND）以后端结构化
 *   ok=false 返回；parseIntentEnvelope 判 ok=false 抛 ApiError，
 *   由调用方 catch 后以 {ok:false, error} 重建并交给 presentation
 *   Model 投影为错误态，消费方不得白屏。
 * - preview_payload 非对象时后端已降级为空快照，前端渲染空态。
 */
import { intentRequest } from './intents';

export const BOQ_IMPORT_PREVIEW_FETCH_INTENT = 'project.boq.import.preview.fetch';
export const BOQ_IMPORT_PREVIEW_SCHEMA = 'sc.boq.import.preview.v1';

/** sc.boq.import.preview.v1 快照（由导入向导在导入时写入） */
export type BoqImportPreviewPayload = {
  schema?: string;
  row_count?: number;
  item_count?: number;
  summary_count?: number;
  heading_count?: number;
  calculation_detail_count?: number;
  skipped_count?: number;
  warning_count?: number;
  amount?: number | null;
  source_diagnostics?: string[];
  analysis_count?: number;
  norm_line_count?: number;
  resource_line_count?: number;
  summary_component_count?: number;
};

/** project.boq.import.batch 只读序列化（后端 _serialize_batch） */
export type BoqImportPreviewBatch = {
  id: number;
  name: string;
  project_id: number | false;
  version_id: number | false;
  state: string;
  filename: string;
  file_digest: string;
  parser_schema: string;
  row_count: number;
  item_count: number;
  skipped_count: number;
  warning_count: number;
  imported_at: string | false;
  imported_by: number | false;
  preview_payload: BoqImportPreviewPayload;
};

export type BoqImportPreviewError = {
  code: string;
  message: string;
  suggested_action: string;
};

/**
 * intentRequest 解包后直传 presentation 的数据形状（生产链路实际到达形状：
 * 信封 {ok,data,meta} 已被 parseIntentEnvelope 剥掉，handler 的 data 即本形状）。
 */
export type BoqImportPreviewData = {
  batch?: BoqImportPreviewBatch;
  preview_schema?: string;
  safe_degradation?: Record<string, unknown>;
};

/**
 * intent 结构化返回的兼容联合形状：
 * - 直传形状：{ batch, preview_schema }（intentRequest 正常路径）
 * - 信封形状：{ ok: false, error }（调用方 catch 分支/历史单测构造；
 *   业务降级经 parseIntentEnvelope ok=false 转异常后由调用方重建）
 */
export type BoqImportPreviewIntentData = BoqImportPreviewData & {
  ok?: boolean;
  data?: BoqImportPreviewData;
  error?: BoqImportPreviewError;
};

/**
 * 拉取 BOQ 导入批次只读预检快照。
 *
 * 入参与后端 handler 对齐：batch_id（指定批次）或 project_id
 * （取该项目最新批次）。传输层异常（网络/协议）照常抛出；
 * 业务降级以原始结构化数据透传，由 Model 投影。
 */
export async function fetchBoqImportPreview(params: {
  batchId?: number;
  projectId?: number;
}): Promise<BoqImportPreviewIntentData> {
  return intentRequest<BoqImportPreviewIntentData>({
    intent: BOQ_IMPORT_PREVIEW_FETCH_INTENT,
    params: {
      ...(params.batchId && params.batchId > 0 ? { batch_id: params.batchId } : {}),
      ...(params.projectId && params.projectId > 0 ? { project_id: params.projectId } : {}),
    },
  });
}
