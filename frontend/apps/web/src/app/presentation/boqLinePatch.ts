/**
 * BOQ 行内联编辑（工程量 patch）编辑会话投影 Model（G7.2 前端切片）。
 *
 * 数据契约：contracts/domain/boq-line-patch.yaml v1（写域，safe_degradation 语义）。
 * 消费 intent：project.boq.line.patch（写，单阶段协议——expected 基线已承担
 * 并发防护，无需 preview 干跑）。
 *
 * 编辑会话状态机（双击进入 / Enter 或失焦提交 / Esc 取消）：
 *  - editing  ：草稿输入中（draft 为字符串，逐键更新）
 *  - saving   ：已提交 intent，等待服务端权威投影
 *  - error    ：业务降级（结构化错误码 + 用户文案 + suggestedAction），
 *               保留草稿与基线供修改重试，不白屏
 *  - success  ：服务端投影已确认（组件层随后整表权威 reload，本层只投影结果）
 *
 * 纯函数边界：本 Model 不发起 intent、不触 DOM；组件层负责 viewport 监听
 * 与 reload。金额不在此层形成事实——成功投影字段全部来自服务端重读。
 */
import type { BoqLinePatchResult } from '../../api/boqLinePatch';

export const BOQ_LINE_PATCH_EDITABLE_FIELDS_FALLBACK = ['quantity'] as const;
/** 窄屏/触屏视口阈值（与 HierarchicalWorksheet 既有断点一致） */
export const BOQ_LINE_PATCH_COMPACT_VIEWPORT_MAX_WIDTH = 959;

export const BOQ_LINE_PATCH_SESSION_EDITING = 'editing';
export const BOQ_LINE_PATCH_SESSION_SAVING = 'saving';
export const BOQ_LINE_PATCH_SESSION_ERROR = 'error';
export const BOQ_LINE_PATCH_SESSION_SUCCESS = 'success';

export type BoqLinePatchSessionState =
  | typeof BOQ_LINE_PATCH_SESSION_EDITING
  | typeof BOQ_LINE_PATCH_SESSION_SAVING
  | typeof BOQ_LINE_PATCH_SESSION_ERROR
  | typeof BOQ_LINE_PATCH_SESSION_SUCCESS;

export type BoqLinePatchSession = {
  state: BoqLinePatchSessionState;
  lineId: number;
  /** 客户端视角基线（进入编辑时从行数据快照，提交时透传服务端比对） */
  expectedQuantity: number;
  draft: string;
  idempotencyKey: string;
  errorCode: string | null;
  errorMessage: string | null;
  suggestedAction: string | null;
};

/** 输入校验结果：INVALID_QUANTITY（负数/非法）或 NO_CHANGE（免提交） */
export type BoqLinePatchValidation =
  | { ok: true; newQuantity: number }
  | { ok: false; code: 'INVALID_QUANTITY' | 'NO_CHANGE' };

/** 错误码 → 用户文案与建议动作（与契约 safe_degradation 一一对应） */
const PATCH_ERROR_MESSAGES: Record<string, string> = {
  MISSING_PARAMS: '编辑参数缺失，请重试。',
  INVALID_QUANTITY: '工程量须为非负数字。',
  LINE_NOT_FOUND: '目标行不存在或不可访问，请刷新后重试。',
  VERSION_NOT_MUTABLE: '当前版本状态不可编辑（仅草稿/已校验版本可修改工程量）。',
  BOQ_FROZEN: '数据已进入冻结节点，不可修改工程量。',
  BASELINE_MISMATCH: '该行已被并发修改，请基于最新工程量重新提交。',
  QTY_BELOW_DONE: '新工程量不能低于累计完成量。',
  PATCH_ERROR: '工程量更新失败，可重试。',
  IDEMPOTENCY_CONFLICT: '重复提交冲突，请稍后重试。',
  IDEMPOTENCY_IN_FLIGHT: '同一提交正在处理中，请稍候。',
  PERMISSION_DENIED: '当前角色无工程量编辑权限。',
  AUTH_REQUIRED: '登录状态失效，请重新登录后再编辑。',
  NETWORK_ERROR: '网络异常，请检查连接后重试。',
};

const PATCH_SUGGESTED_ACTIONS: Record<string, string> = {
  BASELINE_MISMATCH: 'reload_and_retry',
  VERSION_NOT_MUTABLE: 'create_new_version',
  LINE_NOT_FOUND: 'check_params',
  QTY_BELOW_DONE: 'fix_input',
  INVALID_QUANTITY: 'fix_input',
  MISSING_PARAMS: 'fix_input',
  PATCH_ERROR: 'retry',
  IDEMPOTENCY_CONFLICT: 'retry',
  IDEMPOTENCY_IN_FLIGHT: 'retry',
};

export function describeBoqLinePatchError(reasonCode: string | null | undefined): {
  message: string;
  suggestedAction: string | null;
} {
  const code = String(reasonCode || '').trim();
  return {
    message: PATCH_ERROR_MESSAGES[code] || '工程量更新失败，请重试。',
    suggestedAction: PATCH_SUGGESTED_ACTIONS[code] || null,
  };
}

/**
 * 草稿字符串 → 工程量数值；空串/非数字/NaN/Infinity 归一为 null。
 */
export function parseDraftQuantity(raw: string): number | null {
  const text = String(raw ?? '').trim();
  if (!text) return null;
  const value = Number(text);
  return Number.isFinite(value) ? value : null;
}

/**
 * 校验新工程量：负数 → INVALID_QUANTITY；与基线一致 → NO_CHANGE（免提交）。
 */
export function validateDraftQuantity(draft: string, expectedQuantity: number): BoqLinePatchValidation {
  const value = parseDraftQuantity(draft);
  if (value === null || value < 0) return { ok: false, code: 'INVALID_QUANTITY' };
  if (Math.abs(value - expectedQuantity) < 1e-9) return { ok: false, code: 'NO_CHANGE' };
  return { ok: true, newQuantity: value };
}

/**
 * 行可编辑判定：仅叶子记录行（有 record 且 rowKind 命中 item_values；
 * item_values 为空视为全部记录行）可编辑，分组/标题/汇总行只读。
 */
export function isBoqLinePatchEditableRow(input: {
  hasRecord: boolean;
  rowKind: string;
  itemValues: ReadonlySet<string>;
}): boolean {
  if (!input.hasRecord) return false;
  if (!input.itemValues.size) return true;
  return input.itemValues.has(input.rowKind);
}

/** 窄屏（<960px）禁用编辑：触控精度与横向滚动稳定性优先 */
export function isBoqLinePatchAllowedViewport(viewportWidth: number): boolean {
  return Number(viewportWidth) > BOQ_LINE_PATCH_COMPACT_VIEWPORT_MAX_WIDTH;
}

/**
 * 可编辑字段集合：后端 worksheet config 可注入 editable_fields 覆盖，
 * 未注入时回退 ['quantity']（G7.2 首版写入面，契约 decision_semantics）。
 */
export function resolveBoqLinePatchEditableFields(
  configEditableFields: string[] | null | undefined,
): Set<string> {
  if (Array.isArray(configEditableFields) && configEditableFields.length) {
    return new Set(configEditableFields.filter((field) => typeof field === 'string' && field.trim()));
  }
  return new Set<string>(BOQ_LINE_PATCH_EDITABLE_FIELDS_FALLBACK);
}

/** 进入编辑：以行当前工程量为基线快照（幂等键在提交时生成并记录） */
export function beginBoqLinePatchSession(input: {
  lineId: number;
  expectedQuantity: number;
}): BoqLinePatchSession {
  return {
    state: BOQ_LINE_PATCH_SESSION_EDITING,
    lineId: input.lineId,
    expectedQuantity: input.expectedQuantity,
    draft: String(input.expectedQuantity ?? ''),
    idempotencyKey: '',
    errorCode: null,
    errorMessage: null,
    suggestedAction: null,
  };
}

/** 草稿更新（逐键） */
export function updateBoqLinePatchDraft(session: BoqLinePatchSession, draft: string): BoqLinePatchSession {
  return { ...session, draft: String(draft ?? '') };
}

/** 提交中（记录当次幂等键：原样重试须复用同一键） */
export function markBoqLinePatchSaving(
  session: BoqLinePatchSession,
  idempotencyKey?: string,
): BoqLinePatchSession {
  return { ...session, state: BOQ_LINE_PATCH_SESSION_SAVING, ...(idempotencyKey ? { idempotencyKey } : {}) };
}

/** 业务降级：保留草稿与基线供修改重试 */
export function markBoqLinePatchError(
  session: BoqLinePatchSession,
  reasonCode: string | null | undefined,
): BoqLinePatchSession {
  const described = describeBoqLinePatchError(reasonCode);
  return {
    ...session,
    state: BOQ_LINE_PATCH_SESSION_ERROR,
    errorCode: String(reasonCode || '').trim() || null,
    errorMessage: described.message,
    suggestedAction: described.suggestedAction,
  };
}

/** 成功结果的用户摘要（数值全部来自服务端重读投影） */
export function describeBoqLinePatchSuccess(result: BoqLinePatchResult): string {
  const after = Number(result?.quantity_after ?? NaN);
  const amount = Number(result?.amount_after ?? NaN);
  const parts: string[] = [];
  if (Number.isFinite(after)) parts.push(`工程量 ${after}`);
  if (Number.isFinite(amount)) parts.push(`合价 ${amount}`);
  return parts.length ? `已更新：${parts.join(' / ')}（服务端权威重算）` : '工程量已更新（服务端权威重算）';
}
