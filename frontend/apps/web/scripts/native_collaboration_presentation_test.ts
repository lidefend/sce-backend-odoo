import assert from 'node:assert/strict';
import { shouldShowNativeCollaborationPanel } from '../src/pages/contractForm/collaborationPresentation';

assert.equal(shouldShowNativeCollaborationPanel({
  hasChatterActions: true,
  hasAttachments: true,
  isIntakeCreateMode: false,
}), true, 'saved records keep collaboration visible');

assert.equal(shouldShowNativeCollaborationPanel({
  hasChatterActions: true,
  hasAttachments: false,
  isIntakeCreateMode: true,
}), false, 'intake create does not expose record-bound chatter');

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
}), false, 'empty collaboration contracts do not create a panel');

console.log('native collaboration presentation tests passed');
