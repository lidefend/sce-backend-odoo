import assert from 'node:assert/strict';
import test from 'node:test';
import { permitsProjectNameWrite } from './standard_project_save_scope.mjs';

const permit = { name: 'Exact temporary name' };
const request = { intent: 'api.data', params: { op: 'write', model: 'project.project', ids: [10], vals: { name: permit.name } } };
test('permits only the exact project name write', () => {
  assert.equal(permitsProjectNameWrite('fixture_role_pm', request, permit), true);
});
test('rejects absent permit and other role', () => {
  assert.equal(permitsProjectNameWrite('fixture_role_pm', request, null), false);
  assert.equal(permitsProjectNameWrite('fixture_role_finance', request, permit), false);
});
for (const [key, value] of [['ids', [11]], ['ids', [10, 11]], ['model', 'payment.request'],
  ['op', 'unlink'], ['vals', { name: 'Different' }], ['vals', { name: permit.name, sc_approval_state: 'approved' }]]) {
  test(`rejects changed ${key}: ${JSON.stringify(value)}`, () => {
    assert.equal(permitsProjectNameWrite('fixture_role_pm', { ...request, params: { ...request.params, [key]: value } }, permit), false);
  });
}

import { expenseProbeWriteKind, permitsExpensePolicyWrite } from './standard_expense_success_scope.mjs';
const expenseScope = { phase: 'create', id: 120, request: { op: 'create', model: 'sc.expense.claim',
  vals: { summary: 'TPL53-EXPENSE-SUCCESS-1790802321792' }, context: { company_id: 8, menu_id: '564', action_id: '758' } }, filename: 'probe.txt', data: 'ZmlsZQ==' };
test('expense writes bind exact create request and reject changed values/role/replay', () => {
  const body = { intent: 'api.data', params: expenseScope.request };
  assert.equal(expenseProbeWriteKind('fixture_role_finance', body, expenseScope), 'create');
  assert.equal(expenseProbeWriteKind('fixture_role_pm', body, expenseScope), null);
  assert.equal(expenseProbeWriteKind('fixture_role_finance', body, { ...expenseScope, phase: 'create_in_flight' }), null);
  assert.equal(expenseProbeWriteKind('fixture_role_finance', { ...body, params: { ...body.params, vals: { state: 'approved' } } }, expenseScope), null);
});
test('expense upload binds phase, record and exact file', () => {
  const scope = { ...expenseScope, phase: 'upload' };
  const body = { intent: 'file.upload', params: { model: 'sc.expense.claim', res_id: scope.id, name: scope.filename, data: scope.data, mimetype: 'text/plain' } };
  assert.equal(expenseProbeWriteKind('fixture_role_finance', body, scope), 'upload');
  for (const patch of [{ res_id: 121 }, { data: 'different' }, { model: 'payment.request' }]) {
    assert.equal(expenseProbeWriteKind('fixture_role_finance', { ...body, params: { ...body.params, ...patch } }, scope), null);
  }
});
test('expense submit binds identity, entry and exact action', () => {
  const scope = { ...expenseScope, phase: 'submit' };
  const body = { intent: 'execute_button', params: { model: 'sc.expense.claim', res_id: 120, button: { name: 'action_submit', type: 'object' } }, meta: { menu_id: 564, action_id: 758 } };
  assert.equal(expenseProbeWriteKind('fixture_role_finance', body, scope), 'submit');
  assert.equal(expenseProbeWriteKind('fixture_role_finance', { ...body, meta: { menu_id: 545, action_id: 775 } }, scope), null);
  assert.equal(expenseProbeWriteKind('fixture_role_finance', { ...body, params: { ...body.params, button: { name: 'action_done', type: 'object' } } }, scope), null);
});

test('expense policy permit binds administrator, exact record, field and allowed value', () => {
  const permit = { id: 18, value: 'recommended' };
  const body = { intent: 'api.data', params: { op: 'write', model: 'sc.business.category', ids: [18], vals: { attachment_policy: 'recommended' } } };
  assert.equal(permitsExpensePolicyWrite('fixture_role_config_admin', body, permit), true);
  assert.equal(permitsExpensePolicyWrite('fixture_role_finance', body, permit), false);
  assert.equal(permitsExpensePolicyWrite('fixture_role_config_admin', body, null), false);
  for (const patch of [{ ids: [19] }, { ids: [18, 19] }, { op: 'create' }, { model: 'sc.expense.claim' },
    { vals: { attachment_policy: 'none' } }, { vals: { attachment_policy: 'recommended', active: false } }]) {
    assert.equal(permitsExpensePolicyWrite('fixture_role_config_admin', { ...body, params: { ...body.params, ...patch } }, permit), false);
  }
});

test('expense partial upload permits only current exact file and rejects confirmed replay', () => {
  const files = [{ name: 'first.txt', data: 'Zmlyc3Q=' }, { name: 'second.txt', data: 'c2Vjb25k' }];
  const scope = { ...expenseScope, phase: 'upload', files, uploadIndex: 1 };
  const body = { intent: 'file.upload', params: { model: 'sc.expense.claim', res_id: scope.id,
    name: files[1].name, data: files[1].data, mimetype: 'text/plain' } };
  assert.equal(expenseProbeWriteKind('fixture_role_finance', body, scope), 'upload');
  for (const patch of [files[0], { data: 'different' }, { name: 'other.txt' }, { res_id: 121 }]) {
    assert.equal(expenseProbeWriteKind('fixture_role_finance', { ...body, params: { ...body.params, ...patch } }, scope), null);
  }
  assert.equal(expenseProbeWriteKind('fixture_role_finance', body, { ...scope, uploadIndex: 2 }), null);
  assert.equal(expenseProbeWriteKind('fixture_role_finance', body, { ...scope, phase: 'upload_in_flight' }), null);
});

import { diaryProbeWriteKind } from './standard_expense_success_scope.mjs';
test('diary success permit binds PM, exact request, generated identity and confirm only', () => {
  const scope = { model: 'sc.construction.diary', phase: 'create', id: 123,
    request: { op: 'create', model: 'sc.construction.diary', vals: { project_id: 10, title: 'TPL53-DIARY-SAVE-1790807163178', description: 'content' },
      context: { company_id: 8, menu_id: 414, action_id: 713 } } };
  const create = { intent: 'api.data', params: scope.request };
  assert.equal(diaryProbeWriteKind('fixture_role_pm', create, scope), 'create');
  assert.equal(diaryProbeWriteKind('fixture_role_finance', create, scope), null);
  assert.equal(diaryProbeWriteKind('fixture_role_pm', create, { ...scope, phase: 'create_in_flight' }), null);
  assert.equal(diaryProbeWriteKind('fixture_role_pm', { ...create, params: { ...scope.request, vals: { ...scope.request.vals, state: 'confirmed' } } }, scope), null);
  const submit = { intent: 'execute_button', params: { model: scope.model, res_id: 123, button: { name: 'action_confirm', type: 'object' } }, meta: { menu_id: 414, action_id: 713 } };
  assert.equal(diaryProbeWriteKind('fixture_role_pm', submit, { ...scope, phase: 'submit' }), 'submit');
  for (const patch of [{ res_id: 124 }, { button: { name: 'action_done', type: 'object' } }, { model: 'sc.plan' }]) {
    assert.equal(diaryProbeWriteKind('fixture_role_pm', { ...submit, params: { ...submit.params, ...patch } }, { ...scope, phase: 'submit' }), null);
  }
  assert.equal(diaryProbeWriteKind('fixture_role_pm', { ...submit, meta: { menu_id: 1, action_id: 713 } }, { ...scope, phase: 'submit' }), null);
});
