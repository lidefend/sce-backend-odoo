/**
 * BOQ 行内联编辑（工程量 patch）API 封装（G7.2 前端切片）。
 *
 * 数据契约：contracts/domain/boq-line-patch.yaml v1（写域，safe_degradation 语义）。
 * Intent：project.boq.line.patch（后端 PR #441：expected 基线值并发防护 +
 * claim 幂等前置 + 服务端权威重算 + 审计 before/after）。
 *
 * 调用形态沿用 writeRecordV6 的 request_id / idempotency_key 协议：
 * - 幂等键由调用侧按「行 + 时间 + 随机」生成，原样重试命中 replay 分支；
 * - 业务降级（MISSING_PARAMS / INVALID_QUANTITY / LINE_NOT_FOUND /
 *   VERSION_NOT_MUTABLE / BOQ_FROZEN / BASELINE_MISMATCH / QTY_BELOW_DONE /
 *   PATCH_ERROR / IDEMPOTENCY_CONFLICT）以后端结构化 ok=false 返回，
 *   parseIntentEnvelope 判 ok=false 抛 ApiError（reasonCode /
 *   suggestedAction），由调用方 catch 后交给 presentation Model
 *   投影为编辑态错误，消费方不得白屏。
 */
import { intentRequest } from './intents';

export const BOQ_LINE_PATCH_INTENT = 'project.boq.line.patch';
export const BOQ_LINE_PATCH_SCHEMA = 'sc.boq.line.patch.v1';

/** sc.boq.line.patch.v1 执行成功/重放投影（后端 handler _projection 权威重读） */
export type BoqLinePatchResult = {
  schema?: string;
  field?: string;
  line_id?: number;
  version_id?: number;
  version_state?: string;
  project_id?: number;
  quantity_before?: number;
  quantity_after?: number;
  amount_before?: number;
  amount_after?: number;
  qty_remain?: number;
  version_total_amount?: number;
  success?: boolean;
  reason_code?: string;
  message?: string;
  done_at?: string;
  request_id?: string;
  idempotency_key?: string;
  idempotent_replay?: boolean;
};

/**
 * 生成 patch 幂等键：行内联编辑的每次提交尝试唯一；
 * 网络响应丢失后的原样重试应由调用侧复用同一键（保存于编辑会话内）。
 */
export function buildBoqLinePatchIdempotencyKey(lineId: number): string {
  return `boq-line-patch:${lineId}:${Date.now()}:${Math.random().toString(16).slice(2, 8)}`;
}

/**
 * 提交 BOQ 单行工程量 patch。
 *
 * 入参与后端 handler 对齐：line_id + expected_quantity（客户端视角基线，
 * 并发漂移防护）+ new_quantity + idempotency_key。传输层异常照常抛出；
 * 业务降级经 parseIntentEnvelope 转 ApiError，由调用方投影。
 */
export async function patchBoqLineQuantity(params: {
  lineId: number;
  expectedQuantity: number;
  newQuantity: number;
  idempotencyKey: string;
}): Promise<BoqLinePatchResult> {
  return intentRequest<BoqLinePatchResult>({
    intent: BOQ_LINE_PATCH_INTENT,
    params: {
      line_id: params.lineId,
      expected_quantity: params.expectedQuantity,
      new_quantity: params.newQuantity,
      idempotency_key: params.idempotencyKey,
    },
  });
}
