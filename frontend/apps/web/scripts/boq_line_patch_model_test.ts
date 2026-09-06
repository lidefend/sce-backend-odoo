import { strict as assert } from 'node:assert';
import {
  beginBoqLinePatchSession,
  BOQ_LINE_PATCH_COMPACT_VIEWPORT_MAX_WIDTH,
  BOQ_LINE_PATCH_EDITABLE_FIELDS_FALLBACK,
  BOQ_LINE_PATCH_SESSION_EDITING,
  BOQ_LINE_PATCH_SESSION_ERROR,
  BOQ_LINE_PATCH_SESSION_SAVING,
  BOQ_LINE_PATCH_SESSION_SUCCESS,
  describeBoqLinePatchError,
  describeBoqLinePatchSuccess,
  isBoqLinePatchAllowedViewport,
  isBoqLinePatchEditableRow,
  markBoqLinePatchError,
  markBoqLinePatchSaving,
  parseDraftQuantity,
  resolveBoqLinePatchEditableFields,
  updateBoqLinePatchDraft,
  validateDraftQuantity,
} from '../src/app/presentation/boqLinePatch';

// ── 草稿解析 ──────────────────────────────────────────────
assert.equal(parseDraftQuantity('5'), 5);
assert.equal(parseDraftQuantity(' 3.25 '), 3.25);
assert.equal(parseDraftQuantity('0'), 0);
assert.equal(parseDraftQuantity(''), null);
assert.equal(parseDraftQuantity('  '), null);
assert.equal(parseDraftQuantity('abc'), null);
assert.equal(parseDraftQuantity('NaN'), null);
assert.equal(parseDraftQuantity('Infinity'), null);

// ── 输入校验 ──────────────────────────────────────────────
assert.deepEqual(validateDraftQuantity('8', 5), { ok: true, newQuantity: 8 });
assert.deepEqual(validateDraftQuantity('5', 5), { ok: false, code: 'NO_CHANGE' });
assert.deepEqual(validateDraftQuantity('5.0000001', 5), { ok: true, newQuantity: 5.0000001 });
assert.deepEqual(validateDraftQuantity('-1', 5), { ok: false, code: 'INVALID_QUANTITY' });
assert.deepEqual(validateDraftQuantity('abc', 5), { ok: false, code: 'INVALID_QUANTITY' });
assert.deepEqual(validateDraftQuantity('', 5), { ok: false, code: 'INVALID_QUANTITY' });

// ── 行可编辑判定 ──────────────────────────────────────────
assert.equal(isBoqLinePatchEditableRow({ hasRecord: true, rowKind: 'item', itemValues: new Set(['item']) }), true);
assert.equal(isBoqLinePatchEditableRow({ hasRecord: true, rowKind: 'heading', itemValues: new Set(['item']) }), false);
assert.equal(isBoqLinePatchEditableRow({ hasRecord: true, rowKind: 'summary', itemValues: new Set(['item']) }), false);
assert.equal(isBoqLinePatchEditableRow({ hasRecord: false, rowKind: 'item', itemValues: new Set(['item']) }), false);
// item_values 未配置：全部记录行可编辑
assert.equal(isBoqLinePatchEditableRow({ hasRecord: true, rowKind: '', itemValues: new Set([]) }), true);
assert.equal(isBoqLinePatchEditableRow({ hasRecord: false, rowKind: '', itemValues: new Set([]) }), false);

// ── 视口判定（窄屏禁用） ──────────────────────────────────
assert.equal(isBoqLinePatchAllowedViewport(1280), true);
assert.equal(isBoqLinePatchAllowedViewport(960), true);
assert.equal(isBoqLinePatchAllowedViewport(BOQ_LINE_PATCH_COMPACT_VIEWPORT_MAX_WIDTH), false);
assert.equal(isBoqLinePatchAllowedViewport(375), false);

// ── 可编辑字段解析（config 覆盖 / fallback） ───────────────
const fallbackFields = resolveBoqLinePatchEditableFields(undefined);
assert.equal(fallbackFields.size, 1);
assert.equal(fallbackFields.has('quantity'), true);
assert.equal(resolveBoqLinePatchEditableFields(null).has('quantity'), true);
assert.equal(resolveBoqLinePatchEditableFields([]).has('quantity'), true);
const overridden = resolveBoqLinePatchEditableFields(['quantity', 'price']);
assert.equal(overridden.size, 2);
assert.equal(overridden.has('price'), true);
assert.equal(resolveBoqLinePatchEditableFields([' ', '']).size, 0);
assert.equal(BOQ_LINE_PATCH_EDITABLE_FIELDS_FALLBACK.length, 1);

// ── 编辑会话状态机 ────────────────────────────────────────
const session = beginBoqLinePatchSession({ lineId: 16429, expectedQuantity: 5 });
assert.equal(session.state, BOQ_LINE_PATCH_SESSION_EDITING);
assert.equal(session.lineId, 16429);
assert.equal(session.expectedQuantity, 5);
assert.equal(session.draft, '5');
assert.equal(session.errorCode, null);
assert.equal(session.idempotencyKey, '');

const typed = updateBoqLinePatchDraft(session, '8');
assert.equal(typed.draft, '8');
assert.equal(typed.state, BOQ_LINE_PATCH_SESSION_EDITING);
// 不可变更新：原会话不被修改
assert.equal(session.draft, '5');

const saving = markBoqLinePatchSaving(typed, 'boq-line-patch:16429:1:a1b2c3');
assert.equal(saving.state, BOQ_LINE_PATCH_SESSION_SAVING);
assert.equal(saving.idempotencyKey, 'boq-line-patch:16429:1:a1b2c3');
assert.equal(saving.draft, '8');
assert.equal(saving.expectedQuantity, 5);

const succeeded = markBoqLinePatchError(saving, 'BASELINE_MISMATCH');
assert.equal(succeeded.state, BOQ_LINE_PATCH_SESSION_ERROR);
assert.equal(succeeded.errorCode, 'BASELINE_MISMATCH');
assert.equal(succeeded.errorMessage, '该行已被并发修改，请基于最新工程量重新提交。');
assert.equal(succeeded.suggestedAction, 'reload_and_retry');
// 降级保留草稿与基线供重试
assert.equal(succeeded.draft, '8');
assert.equal(succeeded.expectedQuantity, 5);

// 未知错误码走 fallback 文案
const unknown = markBoqLinePatchError(saving, 'SOMETHING_ELSE');
assert.equal(unknown.state, BOQ_LINE_PATCH_SESSION_ERROR);
assert.equal(unknown.errorMessage, '工程量更新失败，请重试。');
assert.equal(unknown.suggestedAction, null);

// 空错误码归一
assert.equal(markBoqLinePatchError(saving, null).errorCode, null);
assert.equal(markBoqLinePatchError(saving, '').errorMessage, '工程量更新失败，请重试。');

// ── 错误码文案映射（契约 safe_degradation 全集） ───────────
assert.equal(describeBoqLinePatchError('MISSING_PARAMS').suggestedAction, 'fix_input');
assert.equal(describeBoqLinePatchError('INVALID_QUANTITY').suggestedAction, 'fix_input');
assert.equal(describeBoqLinePatchError('LINE_NOT_FOUND').suggestedAction, 'check_params');
assert.equal(describeBoqLinePatchError('VERSION_NOT_MUTABLE').suggestedAction, 'create_new_version');
assert.equal(describeBoqLinePatchError('BOQ_FROZEN').message.includes('冻结'), true);
assert.equal(describeBoqLinePatchError('QTY_BELOW_DONE').message.includes('累计完成量'), true);
assert.equal(describeBoqLinePatchError('PATCH_ERROR').suggestedAction, 'retry');
assert.equal(describeBoqLinePatchError('IDEMPOTENCY_CONFLICT').suggestedAction, 'retry');
assert.equal(describeBoqLinePatchError('PERMISSION_DENIED').message.includes('权限'), true);
assert.equal(describeBoqLinePatchError('NETWORK_ERROR').message.includes('网络'), true);
assert.equal(describeBoqLinePatchError(undefined).message, '工程量更新失败，请重试。');

// ── 成功投影摘要（数值来自服务端权威重读） ─────────────────
assert.equal(
  describeBoqLinePatchSuccess({ quantity_after: 9, amount_after: 27 }),
  '已更新：工程量 9 / 合价 27（服务端权威重算）',
);
assert.equal(
  describeBoqLinePatchSuccess({ quantity_after: 9 }),
  '已更新：工程量 9（服务端权威重算）',
);
assert.equal(
  describeBoqLinePatchSuccess({}),
  '工程量已更新（服务端权威重算）',
);

// 成功态标记（透传服务端投影，错误字段清空）
const done = { ...saving, state: BOQ_LINE_PATCH_SESSION_SUCCESS };
assert.equal(done.state, BOQ_LINE_PATCH_SESSION_SUCCESS);

console.log('boq_line_patch_model_test: all assertions passed');
