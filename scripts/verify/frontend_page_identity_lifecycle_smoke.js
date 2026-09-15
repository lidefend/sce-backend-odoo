#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ts = require('../../frontend/apps/web/node_modules/typescript');

const ROOT = path.resolve(__dirname, '..', '..');
const APP_DIR = path.join(ROOT, 'frontend/apps/web/src/app');
const cache = new Map();

function loadTs(moduleName, importerDir = APP_DIR) {
  const unresolved = path.resolve(importerDir, moduleName);
  const sourcePath = unresolved.endsWith('.ts') ? unresolved : `${unresolved}.ts`;
  if (cache.has(sourcePath)) return cache.get(sourcePath).exports;
  const source = fs.readFileSync(sourcePath, 'utf8');
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const module = { exports: {} };
  cache.set(sourcePath, module);
  const localRequire = (request) => {
    // The form adapter re-exports the route adapter, whose browser bootstrap is
    // outside this pure identity test. Fail if the tested path invokes it.
    if (request === './pageIdentityRoute') {
      return { resolveRoutePageIdentity: () => { throw new Error('unexpected route resolution'); } };
    }
    if (request.startsWith('.')) return loadTs(request, path.dirname(sourcePath));
    if (!request.startsWith('@')) return require(request);
    throw new Error(`unsupported lifecycle smoke import: ${request}`);
  };
  vm.runInNewContext(`(function(require,module,exports){${output}\n})`, {}, { filename: sourcePath })(localRequire, module, module.exports);
  return module.exports;
}

function equal(actual, expected, label) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(`${label}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
  }
}

function main() {
  const { buildContractFormPageIdentity } = loadTs('pageIdentityAdapters');
  const { resolveProductPageIdentity } = loadTs('pageIdentity');
  const sourceRecord = { id: 17, name: 'DOC-017', display_name: 'Document / Project / DOC-017' };
  const draft = { amount: 20, display_name: sourceRecord.display_name };
  const input = {
    action: { name: 'Document' }, contract: {}, formData: draft, recordData: sourceRecord,
    isCreate: false, isEdit: false, recordMissing: false, renderError: false, status: 'ok',
  };
  const identity = (overrides = {}) => resolveProductPageIdentity(buildContractFormPageIdentity({ ...input, ...overrides }));
  equal(identity().title, 'DOC-017', 'body-omitted identity uses authorized contract data');
  equal(identity().documentTitle.startsWith('DOC-017 - '), true, 'document title shares contract identity');
  equal(identity().breadcrumbs.slice(-1)[0].label, 'DOC-017', 'breadcrumb shares contract identity');
  equal(identity({ isEdit: true }).title, 'DOC-017', 'edit keeps body-omitted contract identity');
  equal(identity({ formData: { ...draft, name: 'DRAFT-017' } }).title, 'DRAFT-017', 'current draft identity outranks source snapshot');
  equal(identity({ formData: { ...draft, name: '' } }).title, sourceRecord.display_name, 'explicitly cleared draft identity is not restored');
  equal(identity({ recordData: { display_name: sourceRecord.display_name } }).title, sourceRecord.display_name, 'missing authorized identity retains display fallback');
  equal(identity({ recordData: { code: 'CODE-017' }, contract: { views: { form: { profile: { title_field: 'code' } } } } }).title, 'CODE-017', 'declared non-name identity remains authoritative');
  equal(identity({ isCreate: true }).title, '新建Document', 'create ignores prior record identity');
  equal(identity({ recordMissing: true }).title, '记录不存在', 'missing record suppresses snapshot identity');
  equal(draft, { amount: 20, display_name: sourceRecord.display_name }, 'identity does not add fields to writable draft');
  equal(sourceRecord.name, 'DOC-017', 'identity does not mutate authorized source');
  const { createPageIdentityCoordinator } = loadTs('pageIdentityCoordinator');
  const coordinator = createPageIdentityCoordinator();

  equal(coordinator.begin('/a/1', { kind: 'list', actionName: '付款申请' }).title, '付款申请', 'list route begins identity');
  equal(coordinator.begin('/r/payment.request/1', { kind: 'detail', actionName: '付款申请', state: 'loading' }).title, '付款申请 · 加载中', 'direct detail refresh loading identity');
  equal(coordinator.publish('/r/payment.request/1', { kind: 'detail', actionName: '付款申请', recordDisplayName: 'FE-A-PR-001' }).title, 'FE-A-PR-001', 'async detail publication');
  equal(coordinator.publish('/r/payment.request/1', { kind: 'edit', actionName: '付款申请', recordDisplayName: 'FE-A-PR-001' }).title, 'FE-A-PR-001', 'detail to edit keeps stable record identity');
  equal(coordinator.begin('/r/payment.request/2', { kind: 'detail', actionName: '付款申请', state: 'loading' }).title, '付款申请 · 加载中', 'fast record switch begins clean identity');
  equal(coordinator.publish('/r/payment.request/1', { kind: 'detail', recordDisplayName: 'STALE-PR-001' }), null, 'stale record publication rejected');
  equal(coordinator.publish('/r/payment.request/2', { kind: 'detail', recordDisplayName: 'FE-A-PR-002' }).title, 'FE-A-PR-002', 'active record publication accepted');
  equal(coordinator.begin('/company-b/a/1', { kind: 'list', actionName: '付款申请' }).title, '付款申请', 'company switch begins route identity');
  equal(coordinator.publish('/r/payment.request/2', { kind: 'detail', recordDisplayName: 'FE-A-PR-002' }), null, 'company switch rejects old record publication');
  equal(coordinator.begin('/project-member', { fallbackTitle: '角色首页' }).title, '角色首页', 'role switch replaces finance identity');
  equal(coordinator.clear().title, '工作台', 'logout clears business identity');
  equal(coordinator.currentKey(), '', 'logout clears active route key');

  console.log('[frontend_page_identity_lifecycle_smoke] PASS assertions=24');
}

main();
