import assert from 'node:assert/strict';
import test from 'node:test';
import { recoverChangeSet, listLabels } from './standard_list_lowcode_loop.mjs';

test('uncertain publish is read back and rolled back without republishing', async () => {
  const calls = [];
  const result = await recoverChangeSet(async (op) => {
    calls.push(op);
    return op === 'get' ? { state: 'published' } : { state: 'published', publish_result: { published_content_verified: true } };
  }, 'owned-token', 'stable-recovery-id');
  assert.equal(result, 'rolled_back');
  assert.deepEqual(calls, ['get', 'rollback']);
});
test('rollback conflict remains a failure and does not fall back to discard', async () => {
  const calls = [];
  await assert.rejects(recoverChangeSet(async (op) => {
    calls.push(op);
    if (op === 'get') return { state: 'published' };
    throw new Error('CHANGE_SET_ROLLBACK_CONFLICT');
  }, 'owned-token', 'stable-recovery-id'), /ROLLBACK_CONFLICT/);
  assert.deepEqual(calls, ['get', 'rollback']);
});
test('failed validation discards only its own unpublished draft', async () => {
  const calls = [];
  assert.equal(await recoverChangeSet(async (op, params) => {
    calls.push([op, params.change_set_token]);
    return { state: op === 'get' ? 'failed' : 'discarded' };
  }, 'owned-token', 'stable-recovery-id'), 'discarded');
  assert.deepEqual(calls, [['get', 'owned-token'], ['discard', 'owned-token']]);
});
test('unreadable state performs no speculative mutation', async () => {
  const calls = [];
  await assert.rejects(recoverChangeSet(async (op) => { calls.push(op); throw new Error('offline'); }, 'token', 'id'), /offline/);
  assert.deepEqual(calls, ['get']);
});
test('lost publish response and stale ready read do not discard an in-flight transaction', async () => {
  const calls = [];
  await assert.rejects(recoverChangeSet(async (op) => {
    calls.push(op);
    return { state: 'ready' };
  }, 'owned-token', 'stable-recovery-id', true), /publish outcome unresolved/);
  assert.deepEqual(calls, ['get']);
});
test('unknown state and unverified restoration cannot pass', async () => {
  await assert.rejects(recoverChangeSet(async () => ({ state: 'unknown' }), 'token', 'id'), /unknown recovery/);
  await assert.rejects(recoverChangeSet(async () => ({ state: 'published' }), 'token', 'id'), /content must be verified/);
});
test('restored semantic labels detect differences and reject the wrong model', () => {
  const contract = { pageInfo: { model: 'payment.request' }, layoutContract: { columns: [{ fieldCode: 'name', label: '编号' }] } };
  assert.deepEqual(listLabels(contract), [['name', '编号']]);
  const changed = structuredClone(contract);
  changed.layoutContract.columns[0].label = 'changed';
  assert.notDeepEqual(listLabels(changed), listLabels(contract));
  assert.throws(() => listLabels({ ...contract, pageInfo: { model: 'other' } }), /wrong contract/);
  assert.throws(() => listLabels({ ...contract, layoutContract: {} }), /empty label/);
});
