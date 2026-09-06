import { strict as assert } from 'node:assert';
import {
  applyOverviewRichTextResult,
  beginOverviewRichTextSession,
  describeOverviewRichTextError,
  describeOverviewRichTextSuccess,
  isOverviewRichTextDirty,
  markOverviewRichTextError,
  markOverviewRichTextSaving,
  OVERVIEW_RICH_TEXT_MAX_LENGTH_FALLBACK,
  OVERVIEW_RICH_TEXT_SESSION_CONFLICT,
  OVERVIEW_RICH_TEXT_SESSION_EDITING,
  OVERVIEW_RICH_TEXT_SESSION_ERROR,
  OVERVIEW_RICH_TEXT_SESSION_SAVING,
  projectOverviewRichTextBlockData,
  updateOverviewRichTextDraft,
  validateOverviewRichTextDraft,
} from '../src/app/presentation/overviewRichTextPatch';

// ── 块数据规范化（envelope / 裸 data / 缺字段回退） ─────────
const envelope = projectOverviewRichTextBlockData({
  data: {
    project_id: 7,
    content: '<p>hello</p>',
    overview_digest: 'abc123def4567890',
    max_length: 20000,
    can_edit: true,
  },
});
assert.equal(envelope.projectId, 7);
assert.equal(envelope.content, '<p>hello</p>');
assert.equal(envelope.digest, 'abc123def4567890');
assert.equal(envelope.canEdit, true);
assert.equal(envelope.maxLength, 20000);

// 裸 data（刷新路径直接给 data 字段）
const bare = projectOverviewRichTextBlockData({ project_id: 3, content: '', overview_digest: '' });
assert.equal(bare.projectId, 3);
assert.equal(bare.canEdit, false);

// 运行时块 fetch 包装（project.dashboard.block.fetch → {block: {data: …}}）
const runtimeWrapped = projectOverviewRichTextBlockData({
  project_id: 7,
  block_key: 'block.project.overview',
  block: {
    block_key: 'block.project.overview',
    block_type: 'rich_text_overview',
    state: 'ready',
    data: { project_id: 7, content: '<p>wrapped</p>', overview_digest: 'd2', can_edit: false },
  },
  degraded: false,
});
assert.equal(runtimeWrapped.projectId, 7);
assert.equal(runtimeWrapped.content, '<p>wrapped</p>');
assert.equal(runtimeWrapped.digest, 'd2');
assert.equal(runtimeWrapped.canEdit, false);

// 缺字段 / 非法输入回退
const fallback = projectOverviewRichTextBlockData(null);
assert.equal(fallback.projectId, 0);
assert.equal(fallback.content, '');
assert.equal(fallback.maxLength, OVERVIEW_RICH_TEXT_MAX_LENGTH_FALLBACK);
assert.equal(projectOverviewRichTextBlockData('junk').content, '');
assert.equal(projectOverviewRichTextBlockData({ data: { max_length: 'x' } }).maxLength, OVERVIEW_RICH_TEXT_MAX_LENGTH_FALLBACK);
assert.equal(projectOverviewRichTextBlockData({ data: { max_length: 0 } }).maxLength, OVERVIEW_RICH_TEXT_MAX_LENGTH_FALLBACK);

// ── 会话状态机 ──────────────────────────────────────────────
const session = beginOverviewRichTextSession({
  projectId: 7,
  content: '<p>baseline</p>',
  digest: 'digest0000000001',
});
assert.equal(session.state, OVERVIEW_RICH_TEXT_SESSION_EDITING);
assert.equal(session.projectId, 7);
assert.equal(session.expectedDigest, 'digest0000000001');
assert.equal(session.draft, '<p>baseline</p>');
assert.equal(isOverviewRichTextDirty(session), false);

const edited = updateOverviewRichTextDraft(session, '<p>draft</p>');
assert.equal(isOverviewRichTextDirty(edited), true);
assert.equal(isOverviewRichTextDirty(session), false); // 不可变：原会话不受影响

// 清空也是 dirty（合法写场景）
const cleared = updateOverviewRichTextDraft(session, '');
assert.equal(isOverviewRichTextDirty(cleared), true);

// saving：记录幂等键；不带键时保留原值
const saving = markOverviewRichTextSaving(edited, 'key-1');
assert.equal(saving.state, OVERVIEW_RICH_TEXT_SESSION_SAVING);
assert.equal(saving.idempotencyKey, 'key-1');
assert.equal(saving.errorCode, null);
const savingNoKey = markOverviewRichTextSaving(edited);
assert.equal(savingNoKey.idempotencyKey, '');

// ── 长度校验 ────────────────────────────────────────────────
assert.deepEqual(validateOverviewRichTextDraft('<p>ok</p>', 20000), { ok: true });
assert.deepEqual(validateOverviewRichTextDraft('', 20000), { ok: true });
assert.deepEqual(validateOverviewRichTextDraft('x'.repeat(20001), 20000), { ok: false, code: 'CONTENT_TOO_LONG' });
assert.deepEqual(validateOverviewRichTextDraft('x'.repeat(20000), 20000), { ok: true });
// 非法上限回退默认值
assert.deepEqual(validateOverviewRichTextDraft('x'.repeat(20001), 0), { ok: false, code: 'CONTENT_TOO_LONG' });

// ── 错误投影：BASELINE_MISMATCH 走 conflict 态 ───────────────
const conflict = markOverviewRichTextError(saving, 'BASELINE_MISMATCH');
assert.equal(conflict.state, OVERVIEW_RICH_TEXT_SESSION_CONFLICT);
assert.equal(conflict.errorCode, 'BASELINE_MISMATCH');
assert.ok(conflict.errorMessage.includes('并发修改'));
assert.equal(conflict.suggestedAction, 'reload_and_retry');
// 草稿保留供重载后比对
assert.equal(conflict.draft, '<p>draft</p>');

const errored = markOverviewRichTextError(saving, 'CAPABILITY_DISABLED');
assert.equal(errored.state, OVERVIEW_RICH_TEXT_SESSION_ERROR);
assert.equal(errored.errorCode, 'CAPABILITY_DISABLED');
assert.ok(errored.errorMessage.includes('未启用'));

const unknown = markOverviewRichTextError(saving, 'SOMETHING_ELSE');
assert.equal(unknown.state, OVERVIEW_RICH_TEXT_SESSION_ERROR);
assert.ok(unknown.errorMessage.length > 0);

// ── 成功结果投影（服务端权威重读） ──────────────────────────
const saved = applyOverviewRichTextResult({
  content_after: '<p>after</p>',
  content_digest_after: 'digest0000000002',
  length_after: 12,
  sanitized_input_changed: true,
  idempotent_replay: false,
});
assert.equal(saved.content, '<p>after</p>');
assert.equal(saved.digest, 'digest0000000002');
assert.equal(saved.length, 12);
assert.equal(saved.sanitizedInputChanged, true);
assert.equal(saved.replay, false);

// 缺字段回退
const savedEmpty = applyOverviewRichTextResult({});
assert.equal(savedEmpty.content, '');
assert.equal(savedEmpty.digest, '');
assert.equal(savedEmpty.length, 0);
assert.equal(savedEmpty.sanitizedInputChanged, false);
assert.equal(savedEmpty.replay, false);

// ── 文案投影 ────────────────────────────────────────────────
assert.ok(describeOverviewRichTextSuccess({ sanitized_input_changed: true }).includes('安全策略'));
assert.ok(describeOverviewRichTextSuccess({ sanitized_input_changed: false }).includes('保存'));
assert.ok(describeOverviewRichTextSuccess({ idempotent_replay: true }).includes('幂等'));
assert.equal(describeOverviewRichTextError('BASELINE_MISMATCH').suggestedAction, 'reload_and_retry');
assert.equal(describeOverviewRichTextError('UNKNOWN_CODE').suggestedAction, null);
assert.ok(describeOverviewRichTextError('').message.length > 0);

// 未使用常量守卫（确保状态字面量被覆盖）
assert.ok([OVERVIEW_RICH_TEXT_SESSION_EDITING, OVERVIEW_RICH_TEXT_SESSION_SAVING,
  OVERVIEW_RICH_TEXT_SESSION_ERROR, OVERVIEW_RICH_TEXT_SESSION_CONFLICT]
  .every((value) => typeof value === 'string'));

console.log('overview_rich_text_model_test: all assertions passed');
