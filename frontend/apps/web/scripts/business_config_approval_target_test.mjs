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
  const payload = model => ({ policy: { target_model: model, target_model_label: '子单据', approval_required: false, mode: 'none', manager_scope_key: '', steps: [] }, scope_options: [{ value: 'executive', label: '管理层' }], runtime_approval_required: false });
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
