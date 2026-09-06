/**
 * 项目概况受限富文本编辑（rich text patch）API 封装（G7.4-B 前端切片）。
 *
 * 数据契约：contracts/domain/overview-rich-text-patch.yaml v1（写域，
 * safe_degradation 语义）。
 * Intent：project.overview.rich_text.patch（后端 PR #444：nh3 服务端净化 +
 * kill switch 门控 + claim 幂等前置 + expected 摘要基线并发防护）。
 *
 * 调用形态沿用 boqLinePatch 的 idempotency_key 协议：
 * - 幂等键由调用侧按「记录 + 时间 + 随机」生成，原样重试命中 replay 分支；
 * - 业务降级（CAPABILITY_DISABLED / MISSING_PARAMS / CONTENT_TOO_LONG /
 *   PROJECT_NOT_FOUND / BASELINE_MISMATCH / PATCH_ERROR / 幂等冲突）以后端
 *   结构化 ok=false 返回，parseIntentEnvelope 判 ok=false 抛 ApiError
 *   （reasonCode / suggestedAction），由调用方 catch 后交给 presentation
 *   Model 投影为编辑态错误，消费方不得白屏。
 */
import { intentRequest } from './intents';

export const OVERVIEW_RICH_TEXT_PATCH_INTENT = 'project.overview.rich_text.patch';
export const OVERVIEW_RICH_TEXT_PATCH_SCHEMA = 'project.overview.rich_text.patch/v1';

/** 块刷新 intent（短名 block_key，运行时块读投影权威） */
export const DASHBOARD_BLOCK_FETCH_INTENT = 'project.dashboard.block.fetch';
export const OVERVIEW_RICH_TEXT_BLOCK_KEY = 'block.project.overview';

/** project.overview.rich_text.patch/v1 执行成功/重放投影（后端 handler 权威重读） */
export type OverviewRichTextPatchResult = {
  schema?: string;
  field?: string;
  project_id?: number;
  content_digest_before?: string;
  content_digest_after?: string;
  length_before?: number;
  length_after?: number;
  content_modified?: boolean;
  sanitized_input_changed?: boolean;
  content_after?: string;
  max_length?: number;
  success?: boolean;
  reason_code?: string;
  message?: string;
  done_at?: string;
  request_id?: string;
  idempotency_key?: string;
  idempotent_replay?: boolean;
};

/**
 * 生成 patch 幂等键：编辑会话的每次提交尝试唯一；
 * 网络响应丢失后的原样重试应由调用侧复用同一键（保存于编辑会话内）。
 */
export function buildOverviewRichTextPatchIdempotencyKey(projectId: number): string {
  return `overview-rich-text-patch:${projectId}:${Date.now()}:${Math.random().toString(16).slice(2, 8)}`;
}

/**
 * 提交项目概况受限富文本 patch。
 *
 * 入参与后端 handler 对齐：project_id + expected_overview_digest（客户端
 * 视角基线摘要，并发漂移防护，来自块读投影）+ new_overview_html（原始草稿，
 * 服务端 nh3 净化是唯一写权威）+ idempotency_key。
 */
export async function patchOverviewRichText(params: {
  projectId: number;
  expectedOverviewDigest: string;
  newOverviewHtml: string;
  idempotencyKey: string;
}): Promise<OverviewRichTextPatchResult> {
  return intentRequest<OverviewRichTextPatchResult>({
    intent: OVERVIEW_RICH_TEXT_PATCH_INTENT,
    params: {
      project_id: params.projectId,
      expected_overview_digest: params.expectedOverviewDigest,
      new_overview_html: params.newOverviewHtml,
      idempotency_key: params.idempotencyKey,
    },
  });
}

/**
 * 冲突后刷新概况块读投影（BASELINE_MISMATCH → 重新加载最新内容与摘要基线）。
 * 运行时块走 project.dashboard.block.fetch（短名 block_key）。
 */
export async function fetchOverviewRichTextBlock(projectId: number): Promise<unknown> {
  return intentRequest<unknown>({
    intent: DASHBOARD_BLOCK_FETCH_INTENT,
    params: {
      project_id: projectId,
      block_key: OVERVIEW_RICH_TEXT_BLOCK_KEY,
    },
  });
}
