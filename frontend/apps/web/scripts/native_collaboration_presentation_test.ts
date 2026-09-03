import assert from 'node:assert/strict';
import { shouldShowNativeCollaborationPanel } from '../src/pages/contractForm/collaborationPresentation';
import { resolveNativeFollowerContract } from '../src/pages/contractForm/collaborationContract';

assert.equal(shouldShowNativeCollaborationPanel({
  hasChatterActions: true,
  hasAttachments: true,
  isIntakeCreateMode: false,
}), true, 'saved records keep collaboration visible');

assert.equal(shouldShowNativeCollaborationPanel({
  hasChatterActions: true,
  hasAttachments: false,
  isIntakeCreateMode: true,
}), true, 'intake create keeps collaboration panel when model declares chatter support');

assert.equal(shouldShowNativeCollaborationPanel({
  hasChatterActions: false,
  hasAttachments: true,
  isIntakeCreateMode: true,
}), true, 'intake create exposes pending attachment upload');

assert.equal(shouldShowNativeCollaborationPanel({
  hasChatterActions: true,
  hasAttachments: true,
  isIntakeCreateMode: true,
}), true, 'attachment capability keeps the panel visible when chatter is also declared');

assert.equal(shouldShowNativeCollaborationPanel({
  hasChatterActions: false,
  hasAttachments: false,
  isIntakeCreateMode: false,
}), true, 'saved records always keep collaboration panel for audit history');

assert.equal(resolveNativeFollowerContract({}), null, 'missing follower authority fails closed');
assert.equal(resolveNativeFollowerContract({
  followers: { enabled: true, list_intent: 'wrong', update_intent: 'chatter.followers.update' },
}), null, 'unexpected follower intent cannot create a frontend capability');
assert.deepEqual(resolveNativeFollowerContract({
  followers: {
    enabled: true,
    label: '业务关注者',
    list_intent: 'chatter.followers.list',
    update_intent: 'chatter.followers.update',
    actions: {
      follow: { enabled: true, label: '关注业务' },
      unfollow: { enabled: false, label: '取消关注' },
    },
  },
}), {
  enabled: true,
  label: '业务关注者',
  listIntent: 'chatter.followers.list',
  updateIntent: 'chatter.followers.update',
  actions: {
    follow: { enabled: true, label: '关注业务' },
    unfollow: { enabled: false, label: '取消关注' },
  },
}, 'exact backend intents and action authority project into the professional component');

console.log('native collaboration presentation tests passed');
