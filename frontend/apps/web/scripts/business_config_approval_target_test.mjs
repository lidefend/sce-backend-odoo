import assert from 'node:assert/strict';
import { test } from 'node:test';
import fs from 'node:fs';
import vm from 'node:vm';
import { createRequire } from 'node:module';
const require = createRequire(new URL('../package.json', import.meta.url));
const ts = require('typescript'), vue = require('vue');
const source = fs.readFileSync(new URL('../src/views/businessConfigSurface/useBusinessConfigApprovalEditor.ts', import.meta.url), 'utf8');
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;

function setup(overrides = {}) {
  const calls = [], parent = vue.ref('parent'), targets = vue.ref([{ value: 'child', label: '子单据' }]), error = vue.ref('');
  const payload = model => ({ model, amount_condition: { supported: false, field: '', label: '', reason_code: 'amount_field_not_declared', message: '该单据不支持金额条件。' }, policy: { target_model: model, target_model_label: '子单据', approval_required: false, mode: 'none', manager_scope_key: '', steps: [] }, scope_options: [{ value: 'executive', label: '管理层' }], runtime_approval_required: false });
  const api = Object.fromEntries(['loadApprovalPolicyConfig', 'saveApprovalPolicyConfig', 'saveApprovalPolicySteps'].map(name => [name, async params => { calls.push({ name, params }); return payload(params.model); }]));
  Object.assign(api, overrides);
  const exports = {};
  vm.runInNewContext(code, { exports, require: name => name === 'vue' ? vue : api });
  const editor = exports.useBusinessConfigApprovalEditor({
    currentModel: vue.computed(() => parent.value), targetOptions: vue.computed(() => targets.value),
    selectedPageLabel: vue.ref('父业务'), error, setMessage() {}, clearMessage() {},
    async loadSurface() {}, async focusActiveEditorPanel() {}, onOpenPanel() {},
  });
  return { editor, calls, parent, targets, error, payload };
}

test('child target and label come from declared configuration contract', async () => {
  const s = setup(); await s.editor.loadApprovalConfig();
  assert.equal(s.calls[0].params.model, 'child');
  assert.equal(s.editor.approvalTargetModel.value, 'child');
  assert.match(s.editor.approvalPolicyLabel.value, /子单据/);
});
test('undeclared and absent targets do not cause backend reads', async () => {
  const s = setup(); await s.editor.loadApprovalConfig('forged');
  s.targets.value = []; await s.editor.loadApprovalConfig();
  assert.equal(s.calls.length, 0); assert.match(s.error.value, /没有此审批配置对象/);
});
test('dirty target cannot switch and both writes stay on selected child', async () => {
  const s = setup(); await s.editor.loadApprovalConfig();
  s.editor.enableApprovalWithDefaultStep();
  s.targets.value.push({ value: 'other', label: '其他' });
  await s.editor.loadApprovalConfig('other');
  assert.equal(s.calls.length, 1);
  assert.equal(await s.editor.saveApprovalConfig(), true);
  assert.deepEqual(s.calls.map(c => c.params.model), ['child', 'child', 'child']);
});
test('removed contract target blocks save', async () => {
  const s = setup(); await s.editor.loadApprovalConfig(); s.editor.enableApprovalWithDefaultStep();
  s.targets.value = [];
  assert.equal(await s.editor.saveApprovalConfig(), false); assert.equal(s.calls.length, 1);
});
test('late read from a previous parent does not open its editor', async () => {
  let release;
  const s = setup({ loadApprovalPolicyConfig: () => new Promise(resolve => { release = resolve; }) });
  const pending = s.editor.loadApprovalConfig(); s.parent.value = 'other'; release(s.payload('child'));
  await pending;
  assert.equal(s.editor.approvalPanelOpen.value, false); assert.equal(s.editor.approvalTargetModel.value, '');
});
test('parent switch during save prevents a subsequent step write', async () => {
  let release;
  const s = setup({ saveApprovalPolicyConfig: () => new Promise(resolve => { release = resolve; }) });
  await s.editor.loadApprovalConfig(); s.editor.enableApprovalWithDefaultStep();
  const pending = s.editor.saveApprovalConfig(); s.parent.value = 'other'; release(s.payload('child'));
  assert.equal(await pending, false);
  assert.equal(s.calls.filter(c => c.name === 'saveApprovalPolicySteps').length, 0);
  assert.match(s.error.value, /配置页面已变化/);
});

test('unsupported and missing amount capabilities hide inputs without deleting stored values', async () => {
  const s = setup();
  assert.equal(s.editor.approvalAmountSupported.value, false);
  await s.editor.loadApprovalConfig();
  assert.equal(s.editor.approvalAmountSupported.value, false);
  assert.equal(s.editor.approvalAmountMessage.value, '该单据不支持金额条件。');
  s.editor.enableApprovalWithDefaultStep();
  s.editor.approvalSteps.value[0].amount_min = '100';
  assert.equal(await s.editor.saveApprovalConfig(), false);
  assert.equal(s.editor.approvalSteps.value[0].amount_min, '100');
  assert.match(s.editor.approvalValidationMessage.value, /已有金额条件保留/);
  const missing = setup({ loadApprovalPolicyConfig: async ({ model }) => ({ ...s.payload(model), amount_condition: undefined }) });
  await missing.editor.loadApprovalConfig(); missing.editor.enableApprovalWithDefaultStep();
  assert.equal(missing.editor.approvalAmountSupported.value, false);
  assert.equal(missing.editor.canSaveApprovalDraft.value, false);
  assert.equal(await missing.editor.saveApprovalConfig(), false);
});
test('supported amount retains numeric payload and validates nonfinite, negative and inverted bounds', async () => {
  const s = setup();
  await s.editor.loadApprovalConfig();
  s.editor.approvalAudit.value.amount_condition = { supported: true, field: 'amount', label: '金额', reason_code: 'amount_field_declared', message: '按金额判断' };
  assert.equal(s.editor.approvalAmountSupported.value, true);
  s.editor.enableApprovalWithDefaultStep();
  const step = s.editor.approvalSteps.value[0];
  for (const [min, max] of [['NaN', ''], ['-1', ''], ['', 'Infinity'], ['200', '100']]) {
    step.amount_min = min; step.amount_max = max;
    assert.equal(s.editor.canSaveApprovalDraft.value, false);
    assert.match(s.editor.approvalValidationMessage.value, /金额条件/);
  }
  step.amount_min = '100'; step.amount_max = '200';
  assert.equal(await s.editor.saveApprovalConfig(), true);
  const saved = s.calls.find(row => row.name === 'saveApprovalPolicySteps');
  assert.equal(saved.params.steps[0].amount_min, '100');
  assert.equal(saved.params.steps[0].amount_max, '200');
});
test('switch and failed read cannot reuse prior supported amount authority', async () => {
  let release, count = 0;
  const s = setup({ loadApprovalPolicyConfig: ({ model }) => ++count === 1
    ? Promise.resolve({ ...s.payload(model), amount_condition: { supported: true, field: 'amount', label: '金额', reason_code: 'amount_field_declared', message: '按金额判断' } })
    : new Promise((resolve, reject) => { release = reject; }) });
  await s.editor.loadApprovalConfig();
  assert.equal(s.editor.approvalAmountSupported.value, true);
  s.targets.value.push({ value: 'other', label: '其他' });
  const pending = s.editor.loadApprovalConfig('other');
  assert.equal(s.editor.approvalAmountSupported.value, false);
  assert.equal(s.editor.approvalEditorReady.value, false);
  assert.equal(s.editor.canSaveApprovalDraft.value, false);
  release(new Error('读取失败')); await pending;
  assert.equal(s.editor.approvalAmountSupported.value, false);
  assert.equal(s.editor.approvalAudit.value, null);
  assert.equal(s.editor.approvalEditorReady.value, false);
  assert.equal(s.editor.hasApprovalDraftChanges.value, false);
  const retry = s.editor.loadApprovalConfig('other');
  assert.equal(count, 3);
  release(new Error('仍未读取')); await retry;
});
test('mismatched response and parent changes do not lend amount capability', async () => {
  const s = setup(); await s.editor.loadApprovalConfig();
  s.editor.approvalAudit.value.amount_condition.supported = true;
  assert.equal(s.editor.approvalAmountSupported.value, true);
  s.parent.value = 'other';
  assert.equal(s.editor.approvalAmountSupported.value, false);
  const mismatch = setup({ loadApprovalPolicyConfig: async () => s.payload('wrong') });
  await mismatch.editor.loadApprovalConfig();
  assert.equal(mismatch.editor.approvalAmountSupported.value, false);
  assert.match(mismatch.error.value, /对象不匹配/);
});
