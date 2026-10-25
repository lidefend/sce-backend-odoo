import assert from 'node:assert/strict';
import { permitsContractWrite as permit, isExactSignedReadback } from './daily_demo_contract_ui_policy.mjs';
const scope = { enabled: true, key: 'DEMO-DELIVERY-SYNTHETIC', recordId: 0 };
const create = { intent: 'api.data', params: { op: 'create', model: 'sc.general.contract', vals: { contract_name: scope.key } } };
assert.equal(permit(create, scope), true);
assert.equal(permit(create, { ...scope, enabled: false }), false);
assert.equal(permit(create, { ...scope, key: 'other' }), false);
assert.equal(permit(create, { ...scope, recordId: 8 }), false);
assert.equal(permit({ ...create, params: { ...create.params, model: 'res.users' } }, scope), false);
assert.equal(permit({ ...create, params: { ...create.params, vals: { ...create.params.vals, state: 'signed' } } }, scope), false);
const write = { intent: 'api.data', params: { model: 'sc.general.contract', op: 'write', ids: [8], vals: { amount_total: 12500 } } };
assert.equal(permit(write, { ...scope, recordId: 8 }), true);
assert.equal(permit(write, { ...scope, recordId: 9 }), false);
assert.equal(permit({ ...write, params: { ...write.params, ids: [8, 9] } }, { ...scope, recordId: 8 }), false);
assert.equal(permit({ ...write, params: { ...write.params, vals: { state: 'signed' } } }, { ...scope, recordId: 8 }), false);
assert.equal(permit({ intent: 'execute_button', params: { model: 'sc.general.contract', res_id: 8, button: { name: 'action_confirm', type: 'object' } } }, { ...scope, recordId: 8 }), true);
assert.equal(permit({ intent: 'execute_button', params: { model: 'sc.general.contract', res_id: 8, button: 'unlink' } }, { ...scope, recordId: 8 }), false);
assert.equal(permit({ intent: 'execute_button', params: { model: 'sc.general.contract', res_id: 8, button: { name: 'action_confirm', type: 'server' } } }, { ...scope, recordId: 8 }), false);
assert.equal(permit({ intent: 'api.onchange', params: { model: 'sc.general.contract', res_id: 8 } }, { ...scope, recordId: 8 }), true);
assert.equal(permit({ intent: 'api.onchange', params: { model: 'sc.general.contract', res_id: 9 } }, { ...scope, recordId: 8 }), false);
assert.equal(permit({ intent: 'chatter.timeline', params: { model: 'sc.general.contract', res_id: 8 } }, { ...scope, recordId: 8 }), true);
assert.equal(permit({ intent: 'chatter.post', params: { model: 'sc.general.contract', res_id: 8 } }, { ...scope, recordId: 8 }), false);
assert.equal(permit({ intent: 'chatter.followers.list', params: { model: 'sc.general.contract', res_id: 8 } }, { ...scope, recordId: 8 }), true);
assert.equal(permit({ intent: 'chatter.followers.list', params: { model: 'sc.general.contract', res_id: 9 } }, { ...scope, recordId: 8 }), false);
console.log('19 contract UI request-containment assertions passed');

const readOnly = { ...scope, enabled: false, readOnly: true, recordId: 8 };
assert.equal(permit(create, readOnly), false);
assert.equal(permit(write, readOnly), false);
assert.equal(permit({ intent: 'execute_button', params: { model: 'sc.general.contract', res_id: 8, button: { name: 'action_confirm', type: 'object' } } }, readOnly), false);
assert.equal(permit({ intent: 'api.onchange', params: { model: 'sc.general.contract', res_id: 8 } }, readOnly), false);
assert.equal(permit({ intent: 'chatter.timeline', params: { model: 'sc.general.contract', res_id: 8 } }, readOnly), true);
assert.equal(permit({ intent: 'chatter.followers.list', params: { model: 'sc.general.contract', res_id: 8 } }, readOnly), true);
assert.equal(permit({ intent: 'chatter.followers.list', params: { model: 'sc.general.contract', res_id: 9 } }, readOnly), false);
console.log('7 final-readback containment assertions passed');

const signed = { pathname: '/t/demo/f/sc.general.contract/6', basePath: '/t/demo', recordId: 6,
  key: 'DEMO-DELIVERY-20261025-UI01', name: 'DEMO-DELIVERY-20261025-UI01', amount: '¥12,600.00', state: 'signed' };
assert.equal(isExactSignedReadback(signed), true);
for (const change of [{ pathname: '/t/demo/f/sc.general.contract/60' }, { recordId: 60 },
  { amount: '126000' }, { amount: '12600 trailing' }, { name: signed.name + '-extra' },
  { state: 'confirmed' }, { pathname: '/other/f/sc.general.contract/6' }]) {
  assert.equal(isExactSignedReadback({ ...signed, ...change }), false);
}
console.log('8 exact signed-readback assertions passed');
