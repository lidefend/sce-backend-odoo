import assert from 'node:assert/strict';
import { collaborationCapabilityReadiness, formatCollaborationTimelineMeta, visibleCollaborationTimeline } from '../src/pages/contractForm/professionalCollaborationModel';

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
console.log('[professional_collaboration_model_test] PASS cases=5');
