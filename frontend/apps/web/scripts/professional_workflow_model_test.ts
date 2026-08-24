import assert from 'node:assert/strict';
import {
  resolveWorkflowActionBarAuthority,
  resolveWorkflowStatusAuthority,
  workflowDisabledReason,
} from '../src/pages/contractForm/professionalWorkflowModel';

const action = (key: string, enabled = true, reasonCode = '') => ({
  key, enabled, reasonCode, visible: true, tier: key === 'save' ? 'primary' : 'overflow',
} as never);
const authority = resolveWorkflowActionBarAuthority([action('save'), action('approve', false, 'WAITING')], [action('cancel')], 'save');
assert.equal(authority.actionCount, 3);
assert.equal(authority.disabledCount, 1);
assert.equal(authority.primaryKey, 'save');
assert.equal(workflowDisabledReason(action('approve', false, 'WAITING')), 'WAITING');
assert.equal(workflowDisabledReason(action('approve', false)), '当前操作不可用');
assert.equal(workflowDisabledReason(action('approve', true)), '');

for (const readonly of [true, false]) {
  const status = resolveWorkflowStatusAuthority({
    visible: true, field: 'state', current: 'draft', states: [{ value: 'draft', label: 'Draft' }], reachedValues: [], readonly,
  });
  assert.equal(status.stateCount, 1);
  assert.equal(status.readonly, readonly);
}
assert.deepEqual(resolveWorkflowStatusAuthority({ visible: false, field: '', current: '', states: [], reachedValues: [], readonly: true }), {
  visible: false, current: '', stateCount: 0, readonly: true,
});
assert.throws(() => resolveWorkflowStatusAuthority({ visible: true, field: 'state', current: '', states: [], reachedValues: [], readonly: true }), /STATUS_INCOMPLETE/);
console.log('[professional_workflow_model_test] PASS cases=10');
