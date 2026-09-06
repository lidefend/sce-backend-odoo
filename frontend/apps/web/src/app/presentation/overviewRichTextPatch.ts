/**
 * 项目概况受限富文本编辑会话投影 Model（G7.4-B 前端切片）。
 *
 * 数据契约：contracts/domain/overview-rich-text-patch.yaml v1（写域，
 * safe_degradation 语义）。消费 intent：project.overview.rich_text.patch
 * （写，单阶段协议——expected 摘要基线已承担并发防护，无 preview 干跑）。
 *
 * 编辑会话状态机（编辑入口进入 / 保存提交 / 取消退出）：
 *  - editing  ：草稿输入中（draft 为受限 HTML 字符串，逐键更新）
 *  - saving   ：已提交 intent，等待服务端权威净化与落库
 *  - error    ：业务降级（结构化错误码 + 用户文案 + suggestedAction），
 *               保留草稿供修改重试，不白屏
 *  - conflict ：BASELINE_MISMATCH（内容已被并发修改），须重新加载基线
 *
 * 成功终态不在此层持有会话：组件层消费 applyOverviewRichTextResult
 * 的服务端权威投影后结束会话（content/digest 以服务端重读为权威）。
 *
 * 纯函数边界：本 Model 不发起 intent、不触 DOM；净化权威在服务端 nh3
 * （ADR-006 决策 2），前端不预净化、不形成写事实——成功投影字段全部
 * 来自服务端重读。
 */
import type { OverviewRichTextPatchResult } from '../../api/overviewRichTextPatch';

export const OVERVIEW_RICH_TEXT_MAX_LENGTH_FALLBACK = 20000;

export const OVERVIEW_RICH_TEXT_SESSION_EDITING = 'editing';
export const OVERVIEW_RICH_TEXT_SESSION_SAVING = 'saving';
export const OVERVIEW_RICH_TEXT_SESSION_ERROR = 'error';
export const OVERVIEW_RICH_TEXT_SESSION_CONFLICT = 'conflict';

export type OverviewRichTextSessionState =
  | typeof OVERVIEW_RICH_TEXT_SESSION_EDITING
  | typeof OVERVIEW_RICH_TEXT_SESSION_SAVING
  | typeof OVERVIEW_RICH_TEXT_SESSION_ERROR
  | typeof OVERVIEW_RICH_TEXT_SESSION_CONFLICT;

export type OverviewRichTextSession = {
  state: OverviewRichTextSessionState;
  projectId: number;
  /** 客户端视角基线摘要（进入编辑时从块读投影快照，提交时透传服务端比对） */
  expectedDigest: string;
  /** 进入编辑时的基线内容（dirty 判定参照） */
  baselineContent: string;
  draft: string;
  idempotencyKey: string;
  errorCode: string | null;
  errorMessage: string | null;
  suggestedAction: string | null;
};

/** 块读投影规范化视图（dashboard 块 envelope data → 编辑面板入参） */
export type OverviewRichTextBlockView = {
  projectId: number;
  content: string;
  digest: string;
  canEdit: boolean;
  maxLength: number;
};

/** 块数据规范化：后端块投影 → 视图模型，缺字段回退默认。
 * 兼容三种形状：块 envelope（data 字段）/ 运行时块 fetch 包装
 * （block.data 字段，project.dashboard.block.fetch）/ 裸 data 字段。 */
export function projectOverviewRichTextBlockData(input: unknown): OverviewRichTextBlockView {
  const source = (input && typeof input === 'object' ? input : {}) as Record<string, unknown>;
  const nested = (source.block && typeof source.block === 'object' ? source.block : {}) as Record<string, unknown>;
  const data = (nested.data && typeof nested.data === 'object'
    ? nested.data
    : (source.data && typeof source.data === 'object' ? source.data : source)) as Record<string, unknown>;
  const text = (value: unknown): string => (typeof value === 'string' ? value : '');
  const maxLengthRaw = Number(data.max_length);
  return {
    projectId: Math.max(0, Math.trunc(Number(data.project_id) || 0)),
    content: text(data.content),
    digest: text(data.overview_digest),
    canEdit: data.can_edit === true,
    maxLength: Number.isFinite(maxLengthRaw) && maxLengthRaw > 0
      ? Math.trunc(maxLengthRaw)
      : OVERVIEW_RICH_TEXT_MAX_LENGTH_FALLBACK,
  };
}

/** 草稿长度校验：超限 → CONTENT_TOO_LONG（契约 safe_degradation 同码） */
export function validateOverviewRichTextDraft(
  draft: string,
  maxLength: number,
): { ok: true } | { ok: false; code: 'CONTENT_TOO_LONG' } {
  const length = String(draft ?? '').length;
  const limit = Number(maxLength) > 0 ? Number(maxLength) : OVERVIEW_RICH_TEXT_MAX_LENGTH_FALLBACK;
  return length <= limit ? { ok: true } : { ok: false, code: 'CONTENT_TOO_LONG' };
}

/** dirty 判定：草稿与基线内容不一致（含清空场景） */
export function isOverviewRichTextDirty(session: OverviewRichTextSession): boolean {
  return String(session.draft ?? '') !== String(session.baselineContent ?? '');
}

/** 进入编辑：以块读投影为基线快照（幂等键在提交时生成并记录） */
export function beginOverviewRichTextSession(input: {
  projectId: number;
  content: string;
  digest: string;
}): OverviewRichTextSession {
  return {
    state: OVERVIEW_RICH_TEXT_SESSION_EDITING,
    projectId: Math.max(0, Math.trunc(Number(input.projectId) || 0)),
    expectedDigest: String(input.digest ?? ''),
    baselineContent: String(input.content ?? ''),
    draft: String(input.content ?? ''),
    idempotencyKey: '',
    errorCode: null,
    errorMessage: null,
    suggestedAction: null,
  };
}

/** 草稿更新（逐键） */
export function updateOverviewRichTextDraft(
  session: OverviewRichTextSession,
  draft: string,
): OverviewRichTextSession {
  return { ...session, draft: String(draft ?? '') };
}

/** 提交中（记录当次幂等键：原样重试须复用同一键） */
export function markOverviewRichTextSaving(
  session: OverviewRichTextSession,
  idempotencyKey?: string,
): OverviewRichTextSession {
  return {
    ...session,
    state: OVERVIEW_RICH_TEXT_SESSION_SAVING,
    ...(idempotencyKey ? { idempotencyKey } : {}),
    errorCode: null,
    errorMessage: null,
    suggestedAction: null,
  };
}

/** 错误码 → 用户文案与建议动作（与契约 safe_degradation 一一对应） */
const PATCH_ERROR_MESSAGES: Record<string, string> = {
  CAPABILITY_DISABLED: '该编辑能力当前未启用，请联系管理员。',
  MISSING_PARAMS: '编辑参数缺失，请重试。',
  CONTENT_TOO_LONG: '内容超出长度上限，请精简后再保存。',
  PROJECT_NOT_FOUND: '目标记录不存在或不可访问，请刷新后重试。',
  BASELINE_MISMATCH: '内容已被并发修改，请基于最新内容重新编辑。',
  PATCH_ERROR: '内容更新失败，可重试。',
  IDEMPOTENCY_CONFLICT: '重复提交冲突，请稍后重试。',
  IDEMPOTENCY_IN_FLIGHT: '同一提交正在处理中，请稍候。',
  PERMISSION_DENIED: '当前角色无该编辑权限。',
  AUTH_REQUIRED: '登录状态失效，请重新登录后再编辑。',
  NETWORK_ERROR: '网络异常，请检查连接后重试。',
};

const PATCH_SUGGESTED_ACTIONS: Record<string, string> = {
  BASELINE_MISMATCH: 'reload_and_retry',
  PROJECT_NOT_FOUND: 'reload',
  CONTENT_TOO_LONG: 'fix_input',
  MISSING_PARAMS: 'fix_input',
  PATCH_ERROR: 'retry',
  IDEMPOTENCY_CONFLICT: 'retry',
  IDEMPOTENCY_IN_FLIGHT: 'retry',
};

export function describeOverviewRichTextError(reasonCode: string | null | undefined): {
  message: string;
  suggestedAction: string | null;
} {
  const code = String(reasonCode || '').trim();
  return {
    message: PATCH_ERROR_MESSAGES[code] || '内容更新失败，请重试。',
    suggestedAction: PATCH_SUGGESTED_ACTIONS[code] || null,
  };
}

/** 业务降级：保留草稿供修改重试（BASELINE_MISMATCH 单独走 conflict 态） */
export function markOverviewRichTextError(
  session: OverviewRichTextSession,
  reasonCode: string | null | undefined,
): OverviewRichTextSession {
  const code = String(reasonCode || '').trim();
  if (code === 'BASELINE_MISMATCH') {
    const described = describeOverviewRichTextError(code);
    return {
      ...session,
      state: OVERVIEW_RICH_TEXT_SESSION_CONFLICT,
      errorCode: code,
      errorMessage: described.message,
      suggestedAction: described.suggestedAction,
    };
  }
  const described = describeOverviewRichTextError(code);
  return {
    ...session,
    state: OVERVIEW_RICH_TEXT_SESSION_ERROR,
    errorCode: code || null,
    errorMessage: described.message,
    suggestedAction: described.suggestedAction,
  };
}

/** 成功结果投影：内容/摘要/长度全部来自服务端重读（权威） */
export type OverviewRichTextSavedView = {
  content: string;
  digest: string;
  length: number;
  sanitizedInputChanged: boolean;
  replay: boolean;
};

export function applyOverviewRichTextResult(result: OverviewRichTextPatchResult): OverviewRichTextSavedView {
  return {
    content: String(result?.content_after ?? ''),
    digest: String(result?.content_digest_after ?? ''),
    length: Math.max(0, Math.trunc(Number(result?.length_after) || 0)),
    sanitizedInputChanged: result?.sanitized_input_changed === true,
    replay: result?.idempotent_replay === true,
  };
}

/** 成功结果的用户摘要（sanitized_input_changed 提示契约决策语义） */
export function describeOverviewRichTextSuccess(result: OverviewRichTextPatchResult): string {
  if (result?.idempotent_replay === true) {
    return '该提交此前已生效（幂等重放确认）。';
  }
  if (result?.sanitized_input_changed === true) {
    return '内容已保存：部分输入不符合安全策略，已按受限格式调整后落库。';
  }
  return '内容已保存（服务端净化后落库）。';
}
