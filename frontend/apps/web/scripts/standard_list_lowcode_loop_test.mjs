import assert from 'node:assert/strict';
import test from 'node:test';
import { recoverChangeSet, listLabels, recordIds, completeLabelColumns, labelOnlyProjection } from './standard_list_lowcode_loop.mjs';

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
test('record identity survives presentation changes but rejects invalid and duplicate records', () => {
  assert.deepEqual(recordIds([{ id: 9, label: 'before' }, { id: 3 }]), recordIds([{ id: 9, label: 'after' }, { id: 3 }]));
  assert.notDeepEqual(recordIds([{ id: 3 }, { id: 9 }]), [9, 3]);
  assert.throws(() => recordIds([]), /nonempty/);
  assert.throws(() => recordIds([{ id: 0 }]), /positive/);
  assert.throws(() => recordIds([{ id: 9 }, { id: 9 }]), /duplicate/);
});

function fullContract(label = '编号') {
  return { pageInfo: { model: 'payment.request' },
    layoutContract: {
      listProfile: { columns: ['name', 'optional'], fact_columns: ['name', 'optional'], hidden_columns: ['optional'], column_labels: { name: label }, preference_policy: { allow_visibility: false } },
      containerTree: [{ widgetList: [
        { fieldCode: 'name', widgetType: 'table', label, fieldDescriptor: { name: 'name', string: label }, componentConfig: { sort_field: 'id' } },
        { fieldCode: 'optional', widgetType: 'table', label: '可选', componentConfig: { optional: 'hide' } },
      ] }],
    }, actionContract: { delete: false }, dataContract: { domain: [['company_id', '=', 8]] },
    meta: { traceId: 'one', lifecycle: { generation: { sourceSha256: 'one' }, definition: { schemaVersion: '2' } } },
  };
}
test('label candidate enumerates hidden columns without rewriting visibility or mappings', () => {
  const before = fullContract();
  const snapshot = structuredClone(before);
  assert.deepEqual(completeLabelColumns(before, '新标签'), [
    { name: 'name', sequence: 10, label: '新标签' }, { name: 'optional', sequence: 20 },
  ]);
  assert.deepEqual(before, snapshot);
});
test('ambiguous or incomplete column authority fails before staging', () => {
  for (const mutate of [
    (c) => c.layoutContract.listProfile.columns.pop(),
    (c) => c.layoutContract.listProfile.columns.push('name'),
    (c) => c.layoutContract.containerTree[0].widgetList.reverse(),
    (c) => c.layoutContract.listProfile.hidden_columns.push('unknown'),
  ]) {
    const c = fullContract(); mutate(c);
    assert.throws(() => completeLabelColumns(c, 'changed'));
  }
});
test('projection permits only target label and request hashes', () => {
  const before = fullContract(); const next = fullContract('新标签');
  next.meta.traceId = 'two'; next.meta.lifecycle.generation.sourceSha256 = 'two';
  assert.deepEqual(labelOnlyProjection(before, '编号'), labelOnlyProjection(next, '新标签'));
});
test('capability comparison rejects hidden/order/mapping/action/auth and unknown drift', () => {
  const before = labelOnlyProjection(fullContract(), '编号');
  for (const mutate of [
    (c) => c.layoutContract.listProfile.hidden_columns.pop(),
    (c) => c.layoutContract.listProfile.preference_policy.allow_visibility = true,
    (c) => c.layoutContract.containerTree[0].widgetList[0].componentConfig.sort_field = 'name',
    (c) => c.actionContract.delete = true,
    (c) => c.dataContract.domain = [],
    (c) => c.layoutContract.new_unknown_capability = true,
    (c) => c.meta.lifecycle.definition.schemaVersion = '3',
  ]) {
    const c = fullContract('新标签'); mutate(c);
    assert.notDeepEqual(labelOnlyProjection(c, '新标签'), before);
  }
});

test('nested relation with the same name and label is outside label allowance', () => {
  const before = fullContract(); const next = fullContract('新标签');
  before.layoutContract.relation = { name: 'name', label: '编号' };
  next.layoutContract.relation = { name: 'name', label: '新标签' };
  assert.notDeepEqual(labelOnlyProjection(before, '编号'), labelOnlyProjection(next, '新标签'));
});
