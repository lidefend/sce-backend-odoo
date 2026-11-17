import assert from 'node:assert/strict';
import {
  resolveWorkflowActionBarAuthority,
  resolveWorkflowStatusAuthority,
  workflowDisabledReason,
} from '../src/pages/contractForm/professionalWorkflowModel';
import { resolveActionInteractionState } from '../src/pages/contractForm/actionInteractionState';
import {
  INITIAL_FORM_RUNTIME_STATE,
  reduceFormRuntimeState,
} from '../src/pages/contractForm/runtimeStateReducer';

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

assert.equal(workflowDisabledReason({ ...action('approve', false, 'BLOCKED') as object, enabled: false, reasonMessage: '先补齐依据' } as never), '先补齐依据');

const canonicalAction = (key: string, enabled = true, loading = false) => ({
  key,
  label: key,
  icon: '',
  tier: 'secondary',
  visible: true,
  enabled,
  loading,
  reasonCode: '',
  visibleProfiles: ['edit'],
  safety: {},
  actionRef: {
    actionId: key === 'save' ? 'form.save' : `${key}.action`,
    actionKey: key,
    backendIdentity: `object:${key}`,
  },
} as never);

assert.deepEqual(resolveActionInteractionState(canonicalAction('approve'), 'object:approve'), {
  loading: true,
  disabled: true,
});
assert.deepEqual(resolveActionInteractionState(canonicalAction('save'), 'form.save'), {
  loading: true,
  disabled: true,
});
assert.deepEqual(resolveActionInteractionState(canonicalAction('publish'), 'object:archive'), {
  loading: false,
  disabled: false,
});
assert.deepEqual(resolveActionInteractionState(canonicalAction('archive', true, true), ''), {
  loading: true,
  disabled: true,
});

const started = reduceFormRuntimeState(INITIAL_FORM_RUNTIME_STATE, {
  kind: 'begin',
  transaction: 'runAction',
  busyKind: 'action',
  actionIdentity: 'object:archive',
});
const replaced = reduceFormRuntimeState(started, {
  kind: 'begin',
  transaction: 'runAction',
  busyKind: 'action',
  actionIdentity: 'object:publish',
});
const staleEnd = reduceFormRuntimeState(replaced, {
  kind: 'end',
  transaction: 'runAction',
  actionIdentity: 'object:archive',
});
assert.equal(staleEnd.busyKind, 'action');
assert.equal(staleEnd.busyActionIdentity, 'object:publish');
const ended = reduceFormRuntimeState(staleEnd, {
  kind: 'end',
  transaction: 'runAction',
  actionIdentity: 'object:publish',
});
assert.equal(ended.busyKind, null);
assert.equal(ended.busyActionIdentity, '');
console.log('[professional_workflow_model_test] PASS cases=19');
