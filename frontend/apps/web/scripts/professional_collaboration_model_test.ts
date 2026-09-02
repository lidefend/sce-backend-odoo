import assert from 'node:assert/strict';
import { canDeleteCollaborationAttachment, canDeleteCollaborationMessage, canDownloadCollaborationAttachment, canExecuteCollaborationCreateAction, canReplyCollaborationMessage, canUpdateCollaborationActivity, collaborationCapabilityReadiness, formatCollaborationTimelineMeta, parseActivityEntry, visibleCollaborationTimeline } from '../src/pages/contractForm/professionalCollaborationModel';
import { nativeAttachmentUploadEnabled } from '../src/pages/contractForm/collaborationContract';

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
assert.equal(canExecuteCollaborationCreateAction({ enabled: true, mode: 'message' } as never, 'message'), true);
assert.equal(canExecuteCollaborationCreateAction({ enabled: true, mode: 'activity' } as never, 'activity'), true);
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
console.log('[professional_collaboration_model_test] PASS cases=37');
