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

import { eventProbeWriteKind } from './standard_expense_success_scope.mjs';
test('event success permit binds operator, exact request, generated identity and confirm only', () => {
  const scope = { model: 'sc.contract.event', phase: 'create', id: 123, projectId: 464,
    request: { op: 'create', model: 'sc.contract.event', vals: { project_id: 464, name: 'TPL53-EVENT-SAVE-1790807163178', description: 'content' },
      context: { company_id: 8, menu_id: 414, action_id: 713 } } };
  const create = { intent: 'api.data', params: scope.request };
  assert.equal(eventProbeWriteKind('fixture_role_contract_operator', create, scope), 'create');
  assert.equal(eventProbeWriteKind('fixture_role_finance', create, scope), null);
  assert.equal(eventProbeWriteKind('fixture_role_contract_operator', create, { ...scope, phase: 'create_in_flight' }), null);
  assert.equal(eventProbeWriteKind('fixture_role_contract_operator', { ...create, params: { ...scope.request, vals: { ...scope.request.vals, state: 'confirmed' } } }, scope), null);
  const submit = { intent: 'execute_button', params: { model: scope.model, res_id: 123, button: { name: 'action_submit', type: 'object' } }, meta: { menu_id: 414, action_id: 713 } };
  assert.equal(eventProbeWriteKind('fixture_role_contract_operator', submit, { ...scope, phase: 'submit' }), 'submit');
  for (const patch of [{ res_id: 124 }, { button: { name: 'action_done', type: 'object' } }, { model: 'sc.plan' }]) {
    assert.equal(eventProbeWriteKind('fixture_role_contract_operator', { ...submit, params: { ...submit.params, ...patch } }, { ...scope, phase: 'submit' }), null);
  }
  assert.equal(eventProbeWriteKind('fixture_role_contract_operator', { ...submit, meta: { menu_id: 1, action_id: 713 } }, { ...scope, phase: 'submit' }), null);
});


test('report handling permits exact parent/create/submit and rejects scope drift', async () => {
  const { reportProbeWriteKind } = await import('./standard_expense_success_scope.mjs');
  const marker = 'TPL53-REPORT-SAVE-1790807163178';
  const scope = { model: 'sc.plan.report', marker, phase: 'parent', parentId: 24, id: 31,
    parentRequest: { op: 'create', model: 'sc.plan', vals: { name: marker.replace('REPORT-SAVE', 'REPORT-PARENT'), project_id: 10 }, context: { company_id: 8 } },
    request: { op: 'create', model: 'sc.plan.report', vals: { name: marker, plan_id: 24, summary: 'content' }, context: { company_id: 8, menu_id: 508, action_id: 656 } } };
  const parent = { intent: 'api.data', params: scope.parentRequest };
  assert.equal(reportProbeWriteKind('fixture_role_pm', parent, scope), 'parent');
  assert.equal(reportProbeWriteKind('fixture_role_finance', parent, scope), null);
  assert.equal(reportProbeWriteKind('fixture_role_pm', parent, { ...scope, phase: 'parent_in_flight' }), null);
  const create = { intent: 'api.data', params: scope.request };
  assert.equal(reportProbeWriteKind('fixture_role_pm', create, { ...scope, phase: 'create' }), 'create');
  for (const vals of [{ ...scope.request.vals, state: 'accepted' }, { ...scope.request.vals, plan_id: 25 }]) {
    const request = { ...scope.request, vals };
    assert.equal(reportProbeWriteKind('fixture_role_pm', { intent: 'api.data', params: request }, { ...scope, phase: 'create', request }), null);
  }
  const submit = { intent: 'execute_button', params: { model: scope.model, res_id: 31, button: { name: 'action_submit', type: 'object' } }, meta: { menu_id: 508, action_id: 656 } };
  assert.equal(reportProbeWriteKind('fixture_role_pm', submit, { ...scope, phase: 'submit' }), 'submit');
  assert.equal(reportProbeWriteKind('fixture_role_pm', submit, { ...scope, phase: 'submit_in_flight' }), null);
  for (const patch of [{ res_id: 32 }, { model: 'sc.plan' }, { button: { name: 'validate_tier', type: 'object' } }]) {
    assert.equal(reportProbeWriteKind('fixture_role_pm', { ...submit, params: { ...submit.params, ...patch } }, { ...scope, phase: 'submit' }), null);
  }
});

test('plan version save permits only one exact child creation on the owned parent', async () => {
  const { reportProbeWriteKind } = await import('./standard_expense_success_scope.mjs');
  const marker = 'TPL53-REPORT-SAVE-1790807163178';
  const vals = { version_ids: [[0, 0, { version_no: marker.replace('REPORT-SAVE', 'VERSION-SAVE'), revision_type: 'adjustment', version_date: '2026-10-01' }]] };
  const request = { op: 'write', model: 'sc.plan', ids: [24], vals, context: { company_id: 8 } };
  const scope = { model: 'sc.plan.report', marker, versionProbe: true, phase: 'version-save', parentId: 24,
    parentRequest: { model: 'sc.plan', vals: { name: marker.replace('REPORT-SAVE', 'REPORT-PARENT'), project_id: 10 }, context: { company_id: 8 } },
    versionDefaults: { version_date: '2026-10-01' }, versionRequest: request };
  const body = { intent: 'api.data', params: request };
  assert.equal(reportProbeWriteKind('fixture_role_pm', body, scope), 'version-save');
  for (const patch of [{ phase: 'version-save_in_flight' }, { versionProbe: false }, { parentId: 25 }, { versionDefaults: { version_date: '2026-10-02' } }]) {
    assert.equal(reportProbeWriteKind('fixture_role_pm', body, { ...scope, ...patch }), null);
  }
  assert.equal(reportProbeWriteKind('fixture_role_finance', body, scope), null);
  for (const changed of [{ ...request, ids: [25] }, { ...request, vals: { ...vals, state: 'confirmed' } },
    { ...request, vals: { version_ids: [[0, 0, { ...vals.version_ids[0][2], state: 'approved' }]] } },
    { ...request, vals: { version_ids: [[1, 99, vals.version_ids[0][2]]] } }]) {
    assert.equal(reportProbeWriteKind('fixture_role_pm', { ...body, params: changed }, { ...scope, versionRequest: changed }), null);
  }
});

test('version submit binds actual child and navigation context without replay', async () => {
  const { reportProbeWriteKind } = await import('./standard_expense_success_scope.mjs');
  const marker = 'TPL53-REPORT-SAVE-1790807163178';
  const scope = { model: 'sc.plan.report', marker, versionProbe: true, versionSubmitProbe: true, phase: 'version-submit', parentId: 24, versionId: 31,
    parentRequest: { model: 'sc.plan', vals: { name: marker.replace('REPORT-SAVE', 'REPORT-PARENT'), project_id: 10 }, context: { company_id: 8 } },
    versionActionContext: { menu_id: 507, action_id: 655 } };
  const body = { intent: 'execute_button', params: { model: 'sc.plan.version', res_id: 31, button: { name: 'action_submit', type: 'object' } }, meta: { menu_id: 507, action_id: 655 } };
  assert.equal(reportProbeWriteKind('fixture_role_pm', body, scope), 'version-submit');
  for (const patch of [{ phase: 'version-submit_in_flight' }, { versionSubmitProbe: false }, { versionId: 32 }, { versionActionContext: { menu_id: 508, action_id: 655 } }]) {
    assert.equal(reportProbeWriteKind('fixture_role_pm', body, { ...scope, ...patch }), null);
  }
  assert.equal(reportProbeWriteKind('fixture_role_finance', body, scope), null);
  assert.equal(reportProbeWriteKind('fixture_role_pm', { ...body, params: { ...body.params, button: { name: 'validate_tier', type: 'object' } } }, scope), null);
});

test('plan execution scope binds node writes and individual state actions', async () => {
  const { planExecutionWriteKind } = await import('./standard_expense_success_scope.mjs');
  const marker = 'TPL53-REPORT-SAVE-1790807163178';
  const scope = { model: 'sc.plan.report', marker, planExecutionProbe: true, parentId: 24, nodeId: 31, phase: 'node-save',
    parentRequest: { vals: { name: marker.replace('REPORT-SAVE', 'REPORT-PARENT'), project_id: 10 }, context: { company_id: 8, menu_id: 507, action_id: 655 } } };
  const request = { op: 'write', model: 'sc.plan', ids: [24], vals: { line_ids: [[0, 0, { name: marker.replace('REPORT-SAVE', 'PLAN-NODE'), sequence: 10, node_type: 'task' }]] }, context: { company_id: 8 } };
  scope.planRequest = request;
  const body = { intent: 'api.data', params: request };
  assert.equal(planExecutionWriteKind('fixture_role_pm', body, scope), 'node-save');
  for (const patch of [{ parentId: 25 }, { phase: 'node-save_in_flight' }, { planExecutionProbe: false }, { versionProbe: true }]) {
    assert.equal(planExecutionWriteKind('fixture_role_pm', body, { ...scope, ...patch }), null);
  }
  assert.equal(planExecutionWriteKind('fixture_role_finance', body, scope), null);
  for (const [phase, state, progress] of [['node-progress', 'in_progress', 50], ['node-done', 'done', 100]]) {
    const next = { ...request, vals: { line_ids: [[1, 31, { state, progress_rate: progress }]] } };
    assert.equal(planExecutionWriteKind('fixture_role_pm', { ...body, params: next }, { ...scope, phase, planRequest: next }), phase);
    const extra = { ...next, vals: { ...next.vals, state: 'done' } };
    assert.equal(planExecutionWriteKind('fixture_role_pm', { ...body, params: extra }, { ...scope, phase, planRequest: extra }), null);
  }
  const action = { intent: 'execute_button', params: { model: 'sc.plan', res_id: 24, button: { name: 'action_start', type: 'object' } }, meta: { menu_id: 507, action_id: 655 } };
  assert.equal(planExecutionWriteKind('fixture_role_pm', action, { ...scope, phase: 'plan-start' }), 'plan-start');
  assert.equal(planExecutionWriteKind('fixture_role_pm', action, { ...scope, phase: 'plan-confirm' }), null);
});

import { versionReviewWriteKind } from './standard_expense_success_scope.mjs';
const reviewScope = { model: 'sc.plan.report', marker: 'TPL53-REPORT-SAVE-1790816000000', versionReviewProbe: true,
  versionProbe: true, versionSubmitProbe: true, approvalBaseline: { reviewer_id: 28 }, versionId: 14,
  approvalOrigin: { source: 'tier.review', id: 91 }, phase: 'version-config' };
test('version review config permit binds exact model, role, values and single use phase', () => {
  const body = { intent: 'sc.approval_policy.config.set', params: { model: 'sc.plan.version', approval_required: true, mode: 'single', manager_scope_key: 'executive' } };
  assert.equal(versionReviewWriteKind('fixture_role_config_admin', body, reviewScope), 'version-config');
  for (const patch of [{ model: 'sc.plan' }, { approval_required: false }, { mode: 'linear' }, { manager_scope_key: 'business_admin' }, { company_id: 9 }]) {
    assert.equal(versionReviewWriteKind('fixture_role_config_admin', { ...body, params: { ...body.params, ...patch } }, reviewScope), null);
  }
  assert.equal(versionReviewWriteKind('fixture_role_pm', body, reviewScope), null);
  assert.equal(versionReviewWriteKind('fixture_role_config_admin', body, { ...reviewScope, phase: 'version-config_in_flight' }), null);
  assert.equal(versionReviewWriteKind('fixture_role_config_admin', body, { ...reviewScope, approvalBaseline: null }), null);
});
test('version review step permit excludes extra steps, existing ids and conditions', () => {
  const step = { name: `${reviewScope.marker}-审批`, approval_scope_key: 'executive', active: true, amount_min: false, amount_max: false, condition_note: '', note: '' };
  const body = { intent: 'sc.approval_policy.steps.set', params: { model: 'sc.plan.version', steps: [step] } };
  const scope = { ...reviewScope, phase: 'version-steps' };
  assert.equal(versionReviewWriteKind('fixture_role_config_admin', body, scope), 'version-steps');
  for (const steps of [[step, step], [{ ...step, id: 1 }], [{ ...step, amount_min: 100 }], [{ ...step, approval_scope_key: 'project_manager' }]]) {
    assert.equal(versionReviewWriteKind('fixture_role_config_admin', { ...body, params: { ...body.params, steps } }, scope), null);
  }
});
test('version review action permit binds actual review origin and actor without broad method access', () => {
  const scope = { ...reviewScope, phase: 'version-approve' };
  const body = { intent: 'execute_button', params: { model: 'sc.plan.version', res_id: 14, button: { name: 'validate_tier', type: 'object' } }, meta: { work_item_origin: scope.approvalOrigin } };
  assert.equal(versionReviewWriteKind('fixture_role_executive', body, scope), 'version-approve');
  assert.equal(versionReviewWriteKind('fixture_role_pm', body, scope), null);
  assert.equal(versionReviewWriteKind('fixture_role_executive', body, { ...scope, phase: 'done' }), null);
  assert.equal(versionReviewWriteKind('fixture_role_executive', { ...body, params: { ...body.params, res_id: 15 } }, scope), null);
  assert.equal(versionReviewWriteKind('fixture_role_executive', { ...body, params: { ...body.params, button: { name: 'unlink', type: 'object' } } }, scope), null);
  assert.equal(versionReviewWriteKind('fixture_role_executive', { ...body, meta: { work_item_origin: { source: 'tier.review', id: 92 } } }, scope), null);
});

import { paymentReviewWriteKind } from './standard_expense_success_scope.mjs';
const paymentDefaults = { company_id: 8, default_payment_request_id: 1710, default_project_id: 10,
  default_partner_id: 56, default_planned_amount: 2000, default_document_no: 'FE-A-PR-003',
  default_business_category_id: 16, default_business_category_code: 'finance.payment.execution.partner' };
const paymentScope = { model: 'sc.payment.execution', marker: 'TPL53-PAYMENT-REVIEW-1790816000000',
  source: { id: 1710, company_id: 8 }, baseline: { execution_ids: [186], source: [{ id: 1710, company_id: [8, 'A'],
    project_id: [10, 'Project'], partner_id: [56, 'Partner'], amount: 2000, unpaid_amount: 2000, state: 'approved' }] },
  phase: 'create', paymentDate: '2026-10-01',
  continuation: { id: 803, menu_id: 335, res_model: 'sc.payment.execution', context: paymentDefaults },
  request: { op: 'create', model: 'sc.payment.execution', context: { ...paymentDefaults, action_id: 803, menu_id: 335 },
    vals: { business_category_id: 16, date_payment: '2026-10-01', paid_amount: 1, planned_amount: 2000,
      payment_method: '银行转账', document_no: 'FE-A-PR-003', note: 'TPL53-PAYMENT-REVIEW-1790816000000',
      payment_account_name: 'FE Company A Operating Account', payment_bank_name: 'FE Construction Bank',
      payment_account_no: 'FE-PAYER-0001', attachment_ids: [[6, 0, []]] } } };
test('payment review create binds actor/source/amount/phase and rejects state injection', () => {
  const body = { intent: 'api.data', params: paymentScope.request };
  assert.equal(paymentReviewWriteKind('fixture_role_pfl035_finance_user', body, paymentScope), 'create');
  for (const role of ['fixture_role_finance', 'fixture_role_config_admin'])
    assert.equal(paymentReviewWriteKind(role, body, paymentScope), null);
  for (const patch of [{ payment_request_id: 30 }, { paid_amount: 2 }, { state: 'confirmed' }, { company_id: 1 }, { review_ids: [123] }]) {
    const request = { ...paymentScope.request, vals: { ...paymentScope.request.vals, ...patch } };
    assert.equal(paymentReviewWriteKind('fixture_role_pfl035_finance_user', { ...body, params: request }, { ...paymentScope, request }), null);
  }
  assert.equal(paymentReviewWriteKind('fixture_role_pfl035_finance_user', body, { ...paymentScope, phase: 'create_in_flight' }), null);
});
test('payment approval toggle only disables the existing policy with the config administrator', () => {
  const scope = { ...paymentScope, approvalToggle: true, phase: 'config_disable', configContext: { company_id: 8 }, baseline: {
    ...paymentScope.baseline, policies: [{ id: 18, company_id: [8, 'A'], target_model: paymentScope.model,
      approval_required: true, mode: 'single' }] } };
  const body = { intent: 'sc.approval_policy.config.set', params: { model: scope.model,
    approval_required: false, mode: 'none', manager_scope_key: 'finance_manager', context: { company_id: 8 } } };
  assert.equal(paymentReviewWriteKind('fixture_role_config_admin', body, scope), 'config_disable');
  for (const role of ['fixture_role_finance', 'fixture_role_pfl035_finance_user'])
    assert.equal(paymentReviewWriteKind(role, body, scope), null);
  for (const patch of [{ approvalToggle: false }, { phase: 'config_disable_in_flight' },
    { baseline: { execution_ids: [186], policies: [] } }])
    assert.equal(paymentReviewWriteKind('fixture_role_config_admin', body, { ...scope, ...patch }), null);
  for (const params of [{ ...body.params, model: 'payment.request' }, { ...body.params, approval_required: true },
    { ...body.params, manager_scope_key: 'executive' }, { ...body.params, company_id: 1 }, { ...body.params, context: { company_id: 1 } },
    { ...body.params, context: undefined }])
    assert.equal(paymentReviewWriteKind('fixture_role_config_admin', { ...body, params }, scope), null);
  assert.equal(paymentReviewWriteKind('fixture_role_config_admin', { ...body, intent: 'sc.approval_policy.steps.set' }, scope), null);
});
test('payment review binds existing-record exclusion and blocks payment posting', () => {
  const scope = { ...paymentScope, phase: 'submit', id: 200 };
  const body = { intent: 'execute_button', params: { model: scope.model, res_id: 200, button: { name: 'action_confirm', type: 'object' } }, meta: { action_id: 803, menu_id: 335 } };
  assert.equal(paymentReviewWriteKind('fixture_role_pfl035_finance_user', body, scope), 'submit');
  assert.equal(paymentReviewWriteKind('fixture_role_finance', body, scope), null);
  for (const name of ['action_paid', 'action_cancel', 'unlink'])
    assert.equal(paymentReviewWriteKind('fixture_role_pfl035_finance_user', { ...body, params: { ...body.params, button: { name, type: 'object' } } }, scope), null);
  assert.equal(paymentReviewWriteKind('fixture_role_pfl035_finance_user', { ...body, params: { ...body.params, res_id: 186 } }, { ...scope, id: 186 }), null);
});
test('payment review approval binds actual origin and denies replay', () => {
  const scope = { ...paymentScope, phase: 'approve', id: 200, origin: { source: 'tier.review', id: 123 } };
  const body = { intent: 'execute_button', params: { model: scope.model, res_id: 200, button: { name: 'validate_tier', type: 'object' } }, meta: { work_item_origin: scope.origin } };
  assert.equal(paymentReviewWriteKind('fixture_role_finance', body, scope), 'approve');
  assert.equal(paymentReviewWriteKind('fixture_role_pfl035_finance_user', body, scope), null);
  assert.equal(paymentReviewWriteKind('fixture_role_finance', { ...body, meta: { work_item_origin: { source: 'tier.review', id: 124 } } }, scope), null);
  assert.equal(paymentReviewWriteKind('fixture_role_finance', body, { ...scope, phase: 'done' }), null);
});

test('payment review continuation only opens the authorized source without granting arbitrary actions', () => {
  const scope = { ...paymentScope, phase: 'open' };
  const body = { intent: 'execute_button', params: { model: 'payment.request', res_id: 1710,
    button: { type: 'object', name: 'action_create_payment_execution' } }, meta: { action_id: 775, menu_id: 545 } };
  assert.equal(paymentReviewWriteKind('fixture_role_pfl035_finance_user', body, scope), 'open');
  assert.equal(paymentReviewWriteKind('fixture_role_finance', body, scope), null);
  assert.equal(paymentReviewWriteKind('fixture_role_pfl035_finance_user', { ...body, params: { ...body.params, res_id: 30 } }, scope), null);
  assert.equal(paymentReviewWriteKind('fixture_role_pfl035_finance_user', { ...body, meta: { action_id: 803, menu_id: 335 } }, scope), null);
  assert.equal(paymentReviewWriteKind('fixture_role_pfl035_finance_user', body, { ...scope, phase: 'open_in_flight' }), null);
});

test('payment create binds native defaults and baseline even when captured request is replaced', () => {
  for (const patch of [{ default_payment_request_id: 30 }, { default_state: 'confirmed' }, { default_project_id: 99 },
    { default_company_id: 1 }, { default_business_category_id: 17 }]) {
    const request = { ...paymentScope.request, context: { ...paymentScope.request.context, ...patch } };
    assert.equal(paymentReviewWriteKind('fixture_role_pfl035_finance_user', { intent: 'api.data', params: request }, { ...paymentScope, request }), null);
  }
  for (const patch of [{ attachment_ids: [[6, 0, [1]]] }, { planned_amount: 1 }, { date_payment: '2020-01-01' },
    { document_no: 'other' }, { payment_account_no: 'other' }]) {
    const request = { ...paymentScope.request, vals: { ...paymentScope.request.vals, ...patch } };
    assert.equal(paymentReviewWriteKind('fixture_role_pfl035_finance_user', { intent: 'api.data', params: request }, { ...paymentScope, request }), null);
  }
  for (const patch of [{ continuation: null }, { baseline: { execution_ids: [186], source: [] } }])
    assert.equal(paymentReviewWriteKind('fixture_role_pfl035_finance_user', { intent: 'api.data', params: paymentScope.request }, { ...paymentScope, ...patch }), null);
});

test('payment workflow configuration binds the original step, order and restoration', () => {
  const scope = { ...paymentScope, approvalFlow: true, phase: 'flow_steps', configContext: { company_id: 8 },
    baseline: { ...paymentScope.baseline, policies: [{ id: 18, company_id: [8, 'A'], target_model: paymentScope.model }],
      steps: [{ id: 2187, policy_id: [18, 'Policy'], active: true, name: '财务经理审批', approval_scope_key: 'finance_manager' }] } };
  const steps = [{ id: 2187, name: `${scope.marker}-财务复核`, approval_scope_key: 'finance_manager', active: true,
    amount_min: false, amount_max: false, condition_note: '', note: '' },
    { name: `${scope.marker}-管理层终审`, approval_scope_key: 'executive', active: true,
      amount_min: false, amount_max: false, condition_note: '', note: '' }];
  const body = { intent: 'sc.approval_policy.steps.set', params: { model: scope.model, steps, context: scope.configContext } };
  assert.equal(paymentReviewWriteKind('fixture_role_config_admin', body, scope), 'flow_steps');
  for (const changed of [steps.toReversed(), [steps[0]], [steps[0], { ...steps[1], approval_scope_key: 'finance_manager' }]])
    assert.equal(paymentReviewWriteKind('fixture_role_config_admin', { ...body, params: { ...body.params, steps: changed } }, scope), null);
  assert.equal(paymentReviewWriteKind('fixture_role_finance', body, scope), null);
  assert.equal(paymentReviewWriteKind('fixture_role_config_admin', body, { ...scope, phase: 'flow_steps_in_flight' }), null);
  const original = [{ ...steps[0], name: '财务经理审批' }];
  assert.equal(paymentReviewWriteKind('fixture_role_config_admin', { ...body, params: { ...body.params, steps: original } },
    { ...scope, phase: 'restore_steps' }), 'restore_steps');
});

test('payment workflow second review is bound to the executive and real work-item origin', () => {
  const origin = { source: 'tier.review', id: 123 };
  const scope = { ...paymentScope, approvalFlow: true, phase: 'approve', id: 200, origin, reviewStage: 2 };
  const body = { intent: 'execute_button', params: { model: scope.model, res_id: 200, button: { type: 'object', name: 'validate_tier' } },
    meta: { work_item_origin: origin } };
  assert.equal(paymentReviewWriteKind('fixture_role_executive', body, scope), 'approve');
  assert.equal(paymentReviewWriteKind('fixture_role_finance', body, scope), null);
  assert.equal(paymentReviewWriteKind('fixture_role_executive', body, { ...scope, reviewStage: 1 }), null);
});

import { documentFlowWriteKind } from './standard_expense_success_scope.mjs';
const documentScope = { model: 'sc.project.document', marker: 'TPL53-DOCUMENT-FLOW-1790807163178',
  projectId: 10, docTypeId: 21, menuId: 412, actionId: 700, responsibleId: 29, phase: 'create', id: 123,
  request: { op: 'create', model: 'sc.project.document',
    vals: { name: 'TPL53-DOCUMENT-FLOW-1790807163178', project_id: 10, doc_type_id: 21, document_kind: 'site', responsible_id: 29 },
    context: { company_id: 8, allowed_company_ids: [8], lang: 'zh_CN', menu_id: 412, action_id: 700 } } };
test('document create binds exact PM values and dynamically selected project/classification', () => {
  const body = { intent: 'api.data', params: documentScope.request };
  assert.equal(documentFlowWriteKind('fixture_role_pm', body, documentScope), 'create');
  const scope = structuredClone(documentScope);
  scope.projectId = scope.request.vals.project_id = 27;
  scope.docTypeId = scope.request.vals.doc_type_id = 36;
  assert.equal(documentFlowWriteKind('fixture_role_pm', { intent: 'api.data', params: scope.request }, scope), 'create');
  for (const role of ['fixture_role_config_admin', 'fixture_role_finance', 'fixture_role_executive']) {
    assert.equal(documentFlowWriteKind(role, body, documentScope), null);
  }
  for (const patch of [{ phase: 'create_in_flight' }, { marker: 'other' }, { projectId: 11 }, { docTypeId: 22 }, { menuId: 413 }, { actionId: 701 }]) {
    assert.equal(documentFlowWriteKind('fixture_role_pm', body, { ...documentScope, ...patch }), null);
  }
});
test('document captured request cannot authorize extra business fields, identity drift or context bypass', () => {
  for (const vals of [{ state: 'approved' }, { responsible_id: 1 }, { company_id: 9 }, { document_kind: 'archive' },
    { attachment_ids: [[6, 0, [1]]] }, { contract_id: 12 }, { name: 'arbitrary' }]) {
    const scope = structuredClone(documentScope);
    Object.assign(scope.request.vals, vals);
    assert.equal(documentFlowWriteKind('fixture_role_pm', { intent: 'api.data', params: scope.request }, scope), null);
  }
  for (const context of [{ company_id: 9 }, { menu_id: 1 }, { action_id: 1 }, { default_state: 'approved' }, { skip_validation_check: true }, { sudo: true }]) {
    const scope = structuredClone(documentScope);
    Object.assign(scope.request.context, context);
    assert.equal(documentFlowWriteKind('fixture_role_pm', { intent: 'api.data', params: scope.request }, scope), null);
  }
});
for (const [phase, name] of [['submit', 'action_submit'], ['archive', 'action_archive']]) {
  test(`document ${phase} permits only one bound record, PM entry and exact action`, () => {
    const scope = { ...documentScope, phase };
    const body = { intent: 'execute_button', params: { model: scope.model, res_id: scope.id, button: { name, type: 'object' } },
      meta: { menu_id: 412, action_id: 700 } };
    assert.equal(documentFlowWriteKind('fixture_role_pm', body, scope), phase);
    assert.equal(documentFlowWriteKind('fixture_role_config_admin', body, scope), null);
    assert.equal(documentFlowWriteKind('fixture_role_pm', body, { ...scope, phase: `${phase}_in_flight` }), null);
    for (const patch of [{ res_id: 124 }, { model: 'sc.plan' }, { args: [[124]] }, { kwargs: { context: { sudo: true } } },
      { button: { name: 'action_approve', type: 'object' } }]) {
      assert.equal(documentFlowWriteKind('fixture_role_pm', { ...body, params: { ...body.params, ...patch } }, scope), null);
    }
    assert.equal(documentFlowWriteKind('fixture_role_pm', { ...body, meta: { menu_id: 413, action_id: 700 } }, scope), null);
    assert.equal(documentFlowWriteKind('fixture_role_pm', { ...body, meta: {} }, scope), null);
  });
}
test('document review requires actual tier work item and bound executive record; done cannot replay', () => {
  const scope = { ...documentScope, phase: 'approve', approvalOrigin: { source: 'tier.review', id: 456 } };
  const body = { intent: 'execute_button', params: { model: scope.model, res_id: scope.id, button: { name: 'validate_tier', type: 'object' } },
    meta: { work_item_origin: scope.approvalOrigin } };
  assert.equal(documentFlowWriteKind('fixture_role_executive', body, scope), 'approve');
  assert.equal(documentFlowWriteKind('fixture_role_pm', body, scope), null);
  assert.equal(documentFlowWriteKind('fixture_role_executive', { ...body, meta: { work_item_origin: { source: 'tier.review', id: 457 } } }, scope), null);
  assert.equal(documentFlowWriteKind('fixture_role_executive', body, { ...scope, phase: 'done' }), null);
  assert.equal(documentFlowWriteKind('fixture_role_pm', { ...body, params: { ...body.params, button: { type: 'object' } }, meta: { menu_id: 412, action_id: 700 } }, { ...scope, phase: 'done' }), null);
});

test('document permit rejects outer and nested context overrides at every write phase', () => {
  for (const phase of ['create', 'submit', 'archive', 'approve']) {
    const scope = { ...documentScope, phase, approvalOrigin: { source: 'tier.review', id: 456 } };
    const role = phase === 'approve' ? 'fixture_role_executive' : 'fixture_role_pm';
    const body = phase === 'create' ? { intent: 'api.data', params: structuredClone(scope.request) }
      : { intent: 'execute_button', params: { model: scope.model, res_id: scope.id,
        button: { name: { submit: 'action_submit', archive: 'action_archive', approve: 'validate_tier' }[phase], type: 'object' } },
        meta: { menu_id: 412, action_id: 700, work_item_origin: scope.approvalOrigin } };
    assert.equal(documentFlowWriteKind(role, { ...body, context: { company_id: 8, allowed_company_ids: [8] } }, scope), phase);
    for (const context of [{ default_state: 'approved' }, { skip_validation_check: true }, { company_id: 9 },
      { allowed_company_ids: [8, 9] }, { lang: 'en_US' }, { project_id: 11 }, { operation_strategy: 'sudo' }]) {
      assert.equal(documentFlowWriteKind(role, { ...body, context }, scope), null);
      const altered = structuredClone(body);
      altered.params.context = { ...altered.params.context, ...context };
      const captured = phase === 'create' ? { ...scope, request: altered.params } : scope;
      assert.equal(documentFlowWriteKind(role, altered, captured), null);
    }
  }
});

test('document create rejects alternate nested parameter carriers and action button contexts', () => {
  for (const key of ['data', 'params', 'args', 'payload', 'context_raw']) {
    const scope = structuredClone(documentScope);
    scope.request[key] = { context: { skip_validation_check: true } };
    assert.equal(documentFlowWriteKind('fixture_role_pm', { intent: 'api.data', params: scope.request }, scope), null);
  }
  const scope = { ...documentScope, phase: 'archive' };
  const body = { intent: 'execute_button', params: { model: scope.model, res_id: scope.id,
    button: { name: 'action_archive', type: 'object', context: { company_id: 9 } } }, meta: { menu_id: 412, action_id: 700 } };
  assert.equal(documentFlowWriteKind('fixture_role_pm', body, scope), null);
});
