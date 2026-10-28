import assert from 'node:assert/strict';
import { canDeleteCollaborationAttachment, canDeleteCollaborationMessage, canDownloadCollaborationAttachment, canExecuteCollaborationCreateAction, canReplyCollaborationMessage, canUpdateCollaborationActivity, collaborationCapabilityReadiness, formatCollaborationTimelineMeta, isCollaborationAuthorityAbsence, parseActivityEntry, parseMessageEntry, visibleCollaborationTimeline } from '../src/pages/contractForm/professionalCollaborationModel';
import { nativeAttachmentUploadEnabled, nativeChatterActionsFromContract } from '../src/pages/contractForm/collaborationContract';

assert.deepEqual(collaborationCapabilityReadiness({ hasCommentAction: true, hasAttachmentAuthority: true, hasActivityAction: true, hasFollowerAuthority: true }), {
  comment: 'ready', attachment: 'ready', activity: 'ready', follower: 'ready',
});
assert.deepEqual(collaborationCapabilityReadiness({ hasCommentAction: false, hasAttachmentAuthority: false, hasActivityAction: false, hasFollowerAuthority: false }), {
  comment: 'fail_closed', attachment: 'fail_closed', activity: 'fail_closed', follower: 'fail_closed',
});
const entries = [{ key: 'm', type: 'message' }, { key: 'a', type: 'audit' }, { key: 't', type: 'activity' }] as never;
assert.deepEqual(visibleCollaborationTimeline(entries).map((entry) => entry.key), ['m', 't']);
assert.equal(formatCollaborationTimelineMeta('plain'), 'plain');
assert.match(formatCollaborationTimelineMeta('at 2026-08-25T08:30:00Z'), /2026/);
assert.equal(canDownloadCollaborationAttachment({ key: 'missing', type: 'attachment', attachment: { id: 1, name: 'a' } } as never), false);
assert.equal(canDownloadCollaborationAttachment({ key: 'denied', type: 'attachment', attachment: { id: 1, name: 'a', can_download: false } } as never), false);
assert.equal(canDownloadCollaborationAttachment({ key: 'missing-intent', type: 'attachment', attachment: { id: 1, name: 'a', can_download: true } } as never), false);
assert.equal(canDownloadCollaborationAttachment({ key: 'wrong-intent', type: 'attachment', attachment: { id: 1, name: 'a', can_download: true, download_intent: 'file.preview' } } as never), false);
assert.equal(canDownloadCollaborationAttachment({ key: 'allowed', type: 'attachment', attachment: { id: 1, name: 'a', can_download: true, download_intent: 'file.download' } } as never), true);
assert.equal(canDeleteCollaborationAttachment({ key: 'missing-delete', type: 'attachment', attachment: { id: 1, can_delete: true } } as never), false);
assert.equal(canDeleteCollaborationAttachment({ key: 'wrong-intent', type: 'attachment', attachment: { id: 1, can_delete: true, delete_intent: 'file.delete' } } as never), false);
assert.equal(canDeleteCollaborationAttachment({ key: 'delete', type: 'attachment', attachment: { id: 1, can_delete: true, delete_intent: 'chatter.attachment.delete' } } as never), true);
assert.equal(canUpdateCollaborationActivity({ key: 'missing', type: 'activity', activity: { id: 1 } } as never, 'done'), false);
assert.equal(canUpdateCollaborationActivity({ key: 'wrong-intent', type: 'activity', activity: { id: 1, can_complete: true, update_intent: 'mail.activity.update' } } as never, 'done'), false);
assert.equal(canUpdateCollaborationActivity({ key: 'missing-id', type: 'activity', activity: { can_complete: true, update_intent: 'chatter.activity.update' } } as never, 'done'), false);
assert.equal(canUpdateCollaborationActivity({ key: 'denied', type: 'activity', activity: { id: 1, can_cancel: false, update_intent: 'chatter.activity.update' } } as never, 'cancel'), false);
assert.equal(canUpdateCollaborationActivity({ key: 'complete', type: 'activity', activity: { id: 1, can_complete: true, update_intent: 'chatter.activity.update' } } as never, 'done'), true);
assert.equal(canUpdateCollaborationActivity({ key: 'cancel', type: 'activity', activity: { id: 1, can_cancel: true, update_intent: 'chatter.activity.update' } } as never, 'cancel'), true);
assert.equal(canExecuteCollaborationCreateAction(null, 'message'), false);
assert.equal(canExecuteCollaborationCreateAction({ enabled: false, mode: 'message' } as never, 'message'), false);
assert.equal(canExecuteCollaborationCreateAction({ enabled: true, mode: 'note' } as never, 'message'), false);
assert.equal(canExecuteCollaborationCreateAction({ enabled: true, mode: 'message', payload: {} } as never, 'message'), false);
assert.equal(canExecuteCollaborationCreateAction({ enabled: true, mode: 'message', payload: { execute_intent: 'mail.message.create' } } as never, 'message'), false);
assert.equal(canExecuteCollaborationCreateAction({ enabled: true, mode: 'message', payload: { execute_intent: 'chatter.post' } } as never, 'message'), true);
assert.equal(canExecuteCollaborationCreateAction({ enabled: true, mode: 'note', payload: { execute_intent: 'chatter.post' } } as never, 'note'), true);
assert.equal(canExecuteCollaborationCreateAction({ enabled: true, mode: 'activity', payload: { execute_intent: 'chatter.post' } } as never, 'activity'), false);
assert.equal(canExecuteCollaborationCreateAction({ enabled: true, mode: 'activity', payload: { execute_intent: 'chatter.activity.schedule' } } as never, 'activity'), true);
assert.equal(nativeChatterActionsFromContract({ enabled: true, actions: [{ key: 'message', intent: 'message', payload: { mode: 'message' } }] }, { model: 'x.model', recordId: 1 })[0]?.enabled, false);
assert.equal(nativeChatterActionsFromContract({ enabled: true, actions: [{ key: 'message', intent: 'message', payload: { mode: 'message', execute_intent: 'chatter.post' } }] }, { model: 'x.model', recordId: 1 })[0]?.enabled, true);
assert.equal(nativeChatterActionsFromContract({ enabled: true, actions: [{ key: 'activity', intent: 'activity', payload: { mode: 'activity', execute_intent: 'chatter.post' } }] }, { model: 'x.model', recordId: 1 })[0]?.enabled, false);
assert.equal(nativeChatterActionsFromContract({ enabled: true, actions: [{ key: 'activity', intent: 'activity', payload: { mode: 'activity', execute_intent: 'chatter.activity.schedule' } }] }, { model: 'x.model', recordId: 1 })[0]?.enabled, true);
assert.equal(nativeAttachmentUploadEnabled({ enabled: true }), false);
assert.equal(nativeAttachmentUploadEnabled({ enabled: true, upload: { enabled: false } }), false);
assert.equal(nativeAttachmentUploadEnabled({ enabled: true, upload: { enabled: true } }), false);
assert.equal(nativeAttachmentUploadEnabled({ enabled: true, upload: { enabled: true, intent: 'ir.attachment.create' } }), false);
assert.equal(nativeAttachmentUploadEnabled({ enabled: true, upload: { enabled: true, intent: 'file.upload' } }), true);
assert.equal(canReplyCollaborationMessage({ key: 'missing-reply', type: 'message', message: { id: 1 } } as never), false);
assert.equal(canReplyCollaborationMessage({ key: 'missing-intent', type: 'message', message: { id: 1, can_reply: true } } as never), false);
assert.equal(canReplyCollaborationMessage({ key: 'wrong-intent', type: 'message', message: { id: 1, can_reply: true, reply_intent: 'mail.message.reply' } } as never), false);
assert.equal(canReplyCollaborationMessage({ key: 'missing-id', type: 'message', message: { can_reply: true, reply_intent: 'chatter.post' } } as never), false);
assert.equal(canReplyCollaborationMessage({ key: 'reply', type: 'message', message: { id: 1, can_reply: true, reply_intent: 'chatter.post' } } as never), true);
assert.equal(canDeleteCollaborationMessage({ key: 'missing-delete', type: 'message', message: { id: 1, can_delete: true } } as never), false);
assert.equal(canDeleteCollaborationMessage({ key: 'wrong-delete', type: 'message', message: { id: 1, can_delete: true, delete_intent: 'mail.message.unlink' } } as never), false);
assert.equal(canDeleteCollaborationMessage({ key: 'delete', type: 'message', message: { id: 1, can_delete: true, delete_intent: 'chatter.message.delete' } } as never), true);
assert.deepEqual(parseActivityEntry({ key: 'missing-status', type: 'activity', title: '计划', activity: { id: 1, deadline: '2020-01-01' } } as never).status, 'unknown');
assert.deepEqual(parseActivityEntry({ key: 'overdue', type: 'activity', title: '计划', activity: { id: 1, status: 'overdue', status_label: '已逾期' } } as never).statusLabel, '已逾期');
// The timeline authority gates a rebuildable projection by the current business
// scope, so a readable record outside that scope answers NOT_FOUND. That is a
// declared neutral state, not a record-level failure; a system/network failure
// must still surface as an error.
assert.equal(isCollaborationAuthorityAbsence({ status: 404, reasonCode: 'NOT_FOUND' }), true, 'in-scope-miss on a rebuildable projection is an authority absence');
assert.equal(isCollaborationAuthorityAbsence({ status: 403 }), true, 'an authority permission boundary is an authority absence');
assert.equal(isCollaborationAuthorityAbsence({ reasonCode: 'PERMISSION_DENIED' }), true, 'a permission reason code is an authority absence without a numeric status');
assert.equal(isCollaborationAuthorityAbsence({ status: 500, reasonCode: 'SYSTEM_ERROR' }), false, 'a system failure must stay a visible error');
assert.equal(isCollaborationAuthorityAbsence({ status: 0, reasonCode: 'NETWORK_ERROR' }), false, 'a network failure must stay a visible error');
assert.equal(isCollaborationAuthorityAbsence(new Error('boom')), false, 'an untyped error must stay a visible error');
assert.equal(isCollaborationAuthorityAbsence(null), false, 'a missing cause is not an authority absence');
// FEPC-09 observed author/body pairs; remaining envelope fields are synthetic.
const observedMessages = [
  ['OdooBot', ''],
  ['项目审批岗', '项目立项已通过，尚未启动。'],
  ['项目审批岗', '项目初始化已完成：已建立项目管理对象；任务根节点已就绪；成本/资金/风险承载采用按业务事件驱动补充。'],
  ['项目审批岗', '项目 创建'],
];
const punctuationBodies = ['进度: 已完成', '说明：保留前缀', '阶段·正文', '甲 · 乙: 丙：丁', '  开头：内容\n下一行  ', '<b>说明：</b>原文'];
const messageCases = [
  ...observedMessages.map(([author, body]) => ({ author, body })),
  ...punctuationBodies.map((body) => ({ author: '服务端作者', body })),
];
let messageAssertions = 0;
for (const [index, sample] of messageCases.entries()) {
  const entry = { key: `message-${index}`, type: 'message', typeLabel: '备注', title: '标题不能替代正文',
    meta: '元信息不能替代作者', body: sample.body, at: '2026-10-28T03:40:21',
    message: { id: index + 1, author_name: sample.author, can_reply: true, reply_intent: 'chatter.post' } };
  const before = JSON.stringify(entry);
  const parsed = parseMessageEntry(entry);
  assert.equal(parsed.author, sample.author); messageAssertions++;
  assert.equal(parsed.body, sample.body); messageAssertions++;
  assert.equal(parsed.at, entry.at); messageAssertions++;
  assert.equal(parsed.atLabel, formatCollaborationTimelineMeta(entry.at)); messageAssertions++;
  assert.equal(parsed.icon, 'chat'); messageAssertions++;
  assert.equal(canReplyCollaborationMessage(entry), true); messageAssertions++;
  assert.equal(JSON.stringify(entry), before); messageAssertions++;
}
for (const message of [undefined, {}, { author_name: '' }]) {
  const parsed = parseMessageEntry({ key: 'missing-author', type: 'message', typeLabel: '备注', title: '标题',
    meta: '元信息作者', body: '正文作者猜测：不得截断', message });
  assert.equal(parsed.author, ''); messageAssertions++;
  assert.equal(parsed.body, '正文作者猜测：不得截断'); messageAssertions++;
  assert.equal(parsed.atLabel, undefined); messageAssertions++;
}
console.log(`[professional_collaboration_model_test] PASS existing_cases=52 message_assertions=${messageAssertions}`);
