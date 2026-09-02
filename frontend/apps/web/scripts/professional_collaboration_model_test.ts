import assert from 'node:assert/strict';
import { canDownloadCollaborationAttachment, canUpdateCollaborationActivity, collaborationCapabilityReadiness, formatCollaborationTimelineMeta, parseActivityEntry, visibleCollaborationTimeline } from '../src/pages/contractForm/professionalCollaborationModel';

assert.deepEqual(collaborationCapabilityReadiness({ hasCommentAction: true, hasAttachmentAuthority: true, hasActivityAction: true }), {
  comment: 'ready', attachment: 'ready', activity: 'ready', follower: 'fail_closed',
});
assert.deepEqual(collaborationCapabilityReadiness({ hasCommentAction: false, hasAttachmentAuthority: false, hasActivityAction: false }), {
  comment: 'fail_closed', attachment: 'fail_closed', activity: 'fail_closed', follower: 'fail_closed',
});
const entries = [{ key: 'm', type: 'message' }, { key: 'a', type: 'audit' }, { key: 't', type: 'activity' }] as never;
assert.deepEqual(visibleCollaborationTimeline(entries).map((entry) => entry.key), ['m', 't']);
assert.equal(formatCollaborationTimelineMeta('plain'), 'plain');
assert.match(formatCollaborationTimelineMeta('at 2026-08-25T08:30:00Z'), /2026/);
assert.equal(canDownloadCollaborationAttachment({ key: 'missing', type: 'attachment', attachment: { id: 1, name: 'a' } } as never), false);
assert.equal(canDownloadCollaborationAttachment({ key: 'denied', type: 'attachment', attachment: { id: 1, name: 'a', can_download: false } } as never), false);
assert.equal(canDownloadCollaborationAttachment({ key: 'allowed', type: 'attachment', attachment: { id: 1, name: 'a', can_download: true } } as never), true);
assert.equal(canUpdateCollaborationActivity({ key: 'missing', type: 'activity', activity: { id: 1 } } as never, 'done'), false);
assert.equal(canUpdateCollaborationActivity({ key: 'denied', type: 'activity', activity: { id: 1, can_cancel: false } } as never, 'cancel'), false);
assert.equal(canUpdateCollaborationActivity({ key: 'complete', type: 'activity', activity: { id: 1, can_complete: true } } as never, 'done'), true);
assert.equal(canUpdateCollaborationActivity({ key: 'cancel', type: 'activity', activity: { id: 1, can_cancel: true } } as never, 'cancel'), true);
assert.deepEqual(parseActivityEntry({ key: 'missing-status', type: 'activity', title: '计划', activity: { id: 1, deadline: '2020-01-01' } } as never).status, 'unknown');
assert.deepEqual(parseActivityEntry({ key: 'overdue', type: 'activity', title: '计划', activity: { id: 1, status: 'overdue', status_label: '已逾期' } } as never).statusLabel, '已逾期');
console.log('[professional_collaboration_model_test] PASS cases=14');
