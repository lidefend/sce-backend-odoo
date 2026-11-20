import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { createRequire } from 'node:module';

const require = createRequire(new URL('../package.json', import.meta.url));
const ts = require('typescript');
const vue = require('vue');

function loadTypeScriptModule(relativePath) {
  const source = fs.readFileSync(new URL(relativePath, import.meta.url), 'utf8');
  const code = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  const exports = {};
  return { code, exports };
}

const contextModule = loadTypeScriptModule('../src/app/contextEpoch.ts');
vm.runInNewContext(contextModule.code, {
  exports: contextModule.exports,
  AbortController,
});
const context = contextModule.exports;

const scopeModule = loadTypeScriptModule('../src/views/businessConfigSurface/useBusinessConfigScopeLifecycle.ts');
const publishModule = loadTypeScriptModule('../src/views/businessConfigSurface/useBusinessConfigPublishLifecycle.ts');
const versionsModule = loadTypeScriptModule('../src/views/businessConfigSurface/useBusinessConfigVersions.ts');
const productExperienceModule = loadTypeScriptModule('../src/views/businessConfigSurface/useBusinessConfigProductExperience.ts');
const approvalModule = loadTypeScriptModule('../src/views/businessConfigSurface/useBusinessConfigApprovalEditor.ts');

class ApiError extends Error {
  constructor(message, status, reasonCode = '') {
    super(message);
    this.status = status;
    this.reasonCode = reasonCode;
  }
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, resolve, reject };
}

async function flushMicrotasks() {
  for (let index = 0; index < 8; index += 1) await Promise.resolve();
}

function loadScopeLifecycle(api) {
  const exports = {};
  vm.runInNewContext(scopeModule.code, {
    exports,
    require: (name) => {
      if (name === 'vue') return vue;
      if (name === 'vue-router') return { onBeforeRouteUpdate() {} };
      if (name === '../../app/contextEpoch') return context;
      if (name === '../../app/businessConfigBoundaries') {
        return { isBusinessConfigRuntimeModel: () => false };
      }
      if (name === '../../app/menu') return { findActionMeta: () => null };
      if (name === '../../api/client') return { ApiError };
      throw new Error(`unexpected scope dependency: ${name}`);
    },
  });
  const scope = vue.effectScope();
  const company = vue.ref(1);
  const actorRole = vue.ref('actor-a');
  const targetRole = vue.ref('target-a');
  const model = vue.ref('res.partner');
  const action = vue.ref(11);
  const view = vue.ref(21);
  const scanLoading = vue.ref(false);
  const error = vue.ref('');
  const coverageScan = vue.ref(null);
  const surface = vue.ref({ model: 'res.partner' });
  const deps = {
    scopeAction: action,
    currentModel: vue.computed(() => model.value),
    scopeView: view,
    message: vue.ref({ text: '', detail: '' }),
    surfaceLoadSeq: vue.ref(0),
    loading: vue.ref(false),
    error,
    surfaceError: vue.ref(''),
    withSurfaceLoadTimeout: (request) => request,
    loadBusinessConfigSurface: async () => ({ model: model.value }),
    SURFACE_LOAD_TIMEOUT_MS: 1000,
    scopeRole: vue.computed(() => targetRole.value),
    session: {
      recordContext: { company_id: company.value },
      roleSurface: { role_code: actorRole.value },
      async logout() {},
    },
    router: { async replace() {} },
    route: { query: { company_id: String(company.value) }, fullPath: '/business-config' },
    surface,
    scanLoading,
    coverageScan,
    scanBusinessConfigCoverage: api.scanBusinessConfigCoverage,
    rootMenuXmlid: vue.ref('smart_construction_core.menu_business_config'),
    selectedPageLabel: vue.ref(''),
    scopeModel: model,
    scopeActionId: action,
    scopeViewId: view,
    selectedRuntimeRoute: vue.ref(null),
    focusSelectedConfigPanelOnMobile: async () => {},
    resetEditorPanels() {},
    runtimeReturnQuery: () => ({}),
    confirmScopeChange: async () => true,
    hasUnsavedEdits: () => false,
    resetScopeDrafts() {},
    scopeRoleKey: targetRole,
    scopeBusy: () => false,
    requestIdentity: () => ({
      companyId: company.value,
      actorRoleCode: actorRole.value,
      targetRoleKey: targetRole.value,
      model: model.value,
      actionId: action.value,
      viewId: view.value,
    }),
  };
  const lifecycle = scope.run(() => exports.useBusinessConfigScopeLifecycle(deps));
  return {
    lifecycle,
    scope,
    company,
    actorRole,
    targetRole,
    model,
    action,
    view,
    scanLoading,
    error,
    coverageScan,
  };
}

function loadPublishLifecycle(getIdentity, editorIntentOwner = context.createContextRequestOwner(getIdentity)) {
  const exports = {};
  vm.runInNewContext(publishModule.code, {
    exports,
    require: (name) => {
      if (name === 'vue') return vue;
      if (name === '../../app/contextEpoch') return context;
      throw new Error(`unexpected publish dependency: ${name}`);
    },
  });
  const listRequests = [];
  const analysisRequests = [];
  const staged = [];
  const refs = {
    currentModel: vue.ref('res.partner'),
    listSearchBusy: vue.ref(false),
    error: vue.ref(''),
    scopeAction: vue.ref(11),
    scopeView: vue.ref(21),
    scopeRole: vue.ref('target-a'),
    listSearchAudit: vue.ref(null),
    listColumnsText: vue.ref(''),
    searchFiltersText: vue.ref(''),
    searchGroupByText: vue.ref(''),
    listSearchBase: vue.ref({ list: '', filter: '', group: '' }),
    activeListSearchEditor: vue.ref('list'),
    requestedListSearchTab: vue.ref('list'),
    analysisPanelOpen: vue.ref(false),
    approvalPanelOpen: vue.ref(false),
    listSearchPanelOpen: vue.ref(false),
    analysisAudit: vue.ref(null),
    pivotMeasuresText: vue.ref(''),
    pivotDimensionsText: vue.ref(''),
    graphMeasuresText: vue.ref(''),
    graphDimensionsText: vue.ref(''),
    graphType: vue.ref('bar'),
    analysisBase: vue.ref({ pivotMeasures: '', pivotDimensions: '', graphMeasures: '', graphDimensions: '', graphType: 'bar' }),
    activeAnalysisEditor: vue.ref('pivotMeasure'),
    requestedAnalysisTab: vue.ref('pivotMeasure'),
    listSearchSaving: vue.ref(false),
  };
  const messages = [];
  const deps = {
    ...refs,
    clearMessage() {},
    auditBusinessListSearchConfig: (params) => new Promise((resolve, reject) => {
      listRequests.push({ params, resolve, reject });
    }),
    namesToText: (names) => (names || []).join('\n'),
    normalizeNamesText: (value) => String(value || '').split(/\n+/).map((item) => item.trim()).filter(Boolean).join('\n'),
    focusActiveEditorPanel: async () => {},
    setMessage: (text, detail = '') => messages.push({ text, detail }),
    auditBusinessAnalysisConfig: (params) => new Promise((resolve, reject) => {
      analysisRequests.push({ params, resolve, reject });
    }),
    hasListSearchDraftChanges: vue.computed(() => true),
    parseNames: (value) => String(value || '').split(/\n+/).map((item) => item.trim()).filter(Boolean),
    stageUnifiedDraftItem: async (payload) => { staged.push(payload); },
    contractTargetKey: (model, viewType, actionId, viewId) => `${model}:${viewType}:${actionId}:${viewId}`,
    listContractPayload: (names) => ({ columns: names }),
    searchContractPayload: (filters, groups) => ({ filters, groups }),
    hasAnalysisDraftChanges: vue.computed(() => true),
    analysisContractPayload: (viewType, measures, dimensions, graphType) => ({ viewType, measures, dimensions, graphType }),
    previewDraft: async () => ({ preview: { formal_contract_write_count: 0 } }),
    openImpactDialog: async () => true,
    changeSet: vue.ref({ item_count: 1 }),
    publishDraft: async () => ({ item_count: 1 }),
    loadSurface: async () => {},
    rollbackPublished: async () => ({ id: 1 }),
    discardDraft: async () => {},
    requestIdentity: getIdentity,
    editorIntentOwner,
  };
  const scope = vue.effectScope();
  const lifecycle = scope.run(() => exports.useBusinessConfigPublishLifecycle(deps));
  return { lifecycle, scope, refs, listRequests, analysisRequests, staged, messages, editorIntentOwner };
}

function loadApprovalEditor(getIdentity, editorIntentOwner) {
  const exports = {};
  const requests = [];
  const calls = [];
  const payload = (model) => ({
    model,
    amount_condition: {
      supported: true,
      field: 'amount_total',
      label: '金额',
      reason_code: 'amount_field_declared',
      message: '按金额判断',
    },
    policy: {
      target_model: model,
      target_model_label: '子单据',
      approval_required: false,
      mode: 'none',
      manager_scope_key: '',
      steps: [],
    },
    scope_options: [{ value: 'manager', label: '管理层' }],
    runtime_approval_required: false,
  });
  vm.runInNewContext(approvalModule.code, {
    exports,
    require: (name) => {
      if (name === 'vue') return vue;
      if (name === '../../app/contextEpoch') return context;
      if (name === '../../api/businessConfig') {
        return {
          loadApprovalPolicyConfig: (params) => new Promise((resolve, reject) => {
            requests.push({ params, resolve, reject });
          }),
          saveApprovalPolicyConfig: async (params) => {
            calls.push({ name: 'saveApprovalPolicyConfig', params });
            return payload(params.model);
          },
          saveApprovalPolicySteps: async (params) => {
            calls.push({ name: 'saveApprovalPolicySteps', params });
            return payload(params.model);
          },
        };
      }
      throw new Error(`unexpected approval dependency: ${name}`);
    },
  });
  const parent = vue.ref('parent.model');
  const error = vue.ref('');
  const scope = vue.effectScope();
  const editor = scope.run(() => exports.useBusinessConfigApprovalEditor({
    currentModel: vue.computed(() => parent.value),
    targetOptions: vue.computed(() => [{ value: 'child.model', label: '子单据' }]),
    selectedPageLabel: vue.ref('父业务'),
    error,
    setMessage() {},
    clearMessage() {},
    loadSurface: async () => {},
    focusActiveEditorPanel: async () => {},
    onOpenPanel() {},
    requestIdentity: getIdentity,
    editorIntentOwner,
  }));
  return { editor, scope, requests, calls, error, payload };
}

function listPayload(columns) {
  return {
    has_business_list_config: true,
    has_business_search_config: true,
    business_config_list_columns: columns,
    business_config_search_filters: [],
    business_config_search_group_by: [],
    suggested_list_columns: [],
    suggested_search_filters: [],
    suggested_search_group_by: [],
  };
}

function analysisPayload() {
  return {
    has_business_analysis_config: true,
    has_business_pivot_config: true,
    has_business_graph_config: true,
    pivot_measures: ['amount_total'],
    pivot_dimensions: ['company_id'],
    graph_measures: ['amount_total'],
    graph_dimensions: ['state'],
    graph_type: 'bar',
    suggested_pivot_measures: [],
    suggested_pivot_dimensions: [],
    suggested_graph_measures: [],
    suggested_graph_dimensions: [],
    suggested_graph_type: 'bar',
  };
}

let cases = 0;

// Shared loading flags keep the newest activity owner until its own completion.
{
  const busy = vue.ref(false);
  const releaseFirst = context.beginBooleanActivity(busy);
  const releaseSecond = context.beginBooleanActivity(busy);
  releaseFirst();
  assert.equal(busy.value, true);
  releaseSecond();
  assert.equal(busy.value, false);
  cases += 1;
}

// C1: A slowly completes after B; B remains authoritative.
{
  const requests = [];
  const harness = loadScopeLifecycle({
    scanBusinessConfigCoverage: (params) => new Promise((resolve, reject) => {
      requests.push({ params, resolve, reject });
    }),
  });
  context.beginContextTransition();
  const a = harness.lifecycle.scanCoverage();
  harness.company.value = 2;
  harness.actorRole.value = 'actor-b';
  harness.targetRole.value = 'target-b';
  context.beginContextTransition();
  const b = harness.lifecycle.scanCoverage();
  requests[1].resolve({ items: [{ model: 'b.model', action_id: 22, view_id: 0, name: 'B' }], include_all_root_menu_actions: false });
  await b;
  requests[0].resolve({ items: [{ model: 'a.model', action_id: 11, view_id: 0, name: 'A' }], include_all_root_menu_actions: false });
  await a;
  assert.equal(harness.coverageScan.value.items[0].model, 'b.model');
  assert.equal(harness.scanLoading.value, false);
  harness.scope.stop();
  cases += 1;
}

// C2: A -> B -> A must not revive the first A response.
{
  const requests = [];
  const harness = loadScopeLifecycle({
    scanBusinessConfigCoverage: (params) => new Promise((resolve) => requests.push({ params, resolve })),
  });
  context.beginContextTransition();
  const firstA = harness.lifecycle.scanCoverage();
  harness.company.value = 2;
  harness.actorRole.value = 'actor-b';
  harness.targetRole.value = 'target-b';
  context.beginContextTransition();
  const b = harness.lifecycle.scanCoverage();
  harness.company.value = 1;
  harness.actorRole.value = 'actor-a';
  harness.targetRole.value = 'target-a';
  context.beginContextTransition();
  const secondA = harness.lifecycle.scanCoverage();
  requests[2].resolve({ items: [{ model: 'a2.model', action_id: 11, view_id: 0, name: 'A2' }], include_all_root_menu_actions: false });
  await secondA;
  requests[1].resolve({ items: [{ model: 'b.model', action_id: 22, view_id: 0, name: 'B' }], include_all_root_menu_actions: false });
  await b;
  requests[0].resolve({ items: [{ model: 'a1.model', action_id: 11, view_id: 0, name: 'A1' }], include_all_root_menu_actions: false });
  await firstA;
  assert.equal(harness.coverageScan.value.items[0].model, 'a2.model');
  harness.scope.stop();
  cases += 1;
}

// C5: old failure cannot replace the newer success or loading state.
{
  const requests = [];
  const harness = loadScopeLifecycle({
    scanBusinessConfigCoverage: (params) => new Promise((resolve, reject) => requests.push({ params, resolve, reject })),
  });
  context.beginContextTransition();
  const old = harness.lifecycle.scanCoverage();
  harness.action.value = 12;
  context.beginContextTransition();
  const current = harness.lifecycle.scanCoverage();
  requests[1].resolve({ items: [{ model: 'res.partner', action_id: 12, view_id: 21, name: 'Current' }], include_all_root_menu_actions: false });
  await current;
  requests[0].reject(new Error('old failure'));
  await old;
  assert.equal(harness.error.value, '');
  assert.equal(harness.coverageScan.value.items[0].action_id, 12);
  assert.equal(harness.scanLoading.value, false);
  harness.scope.stop();
  cases += 1;
}

// C3/C4/C6: editor reads bind action/view and only accept the newest request.
{
  let action = 11;
  let view = 21;
  let epochCompany = 1;
  const harness = loadPublishLifecycle(() => ({
    companyId: epochCompany,
    actorRoleCode: 'actor-a',
    targetRoleKey: 'target-a',
    model: harness.refs.currentModel.value,
    actionId: action,
    viewId: view,
    viewType: 'tree+search',
  }));
  context.beginContextTransition();
  const stale = harness.lifecycle.loadListSearchConfig();
  action = 12;
  view = 22;
  context.beginContextTransition();
  const current = harness.lifecycle.loadListSearchConfig();
  harness.listRequests[1].resolve(listPayload(['date']));
  await current;
  harness.listRequests[0].resolve(listPayload(['name', 'owner']));
  await stale;
  assert.equal(harness.refs.listColumnsText.value, 'date');
  assert.equal(harness.refs.listSearchPanelOpen.value, true);

  const first = harness.lifecycle.loadListSearchConfig();
  const second = harness.lifecycle.loadListSearchConfig();
  harness.listRequests[3].resolve(listPayload(['amount_total']));
  await second;
  harness.listRequests[2].resolve(listPayload(['name']));
  await first;
  assert.equal(harness.refs.listColumnsText.value, 'amount_total');

  const lateReopen = harness.lifecycle.loadListSearchConfig();
  action = 13;
  context.beginContextTransition();
  harness.refs.listSearchPanelOpen.value = false;
  harness.listRequests[4].resolve(listPayload(['state']));
  await lateReopen;
  assert.equal(harness.refs.listSearchPanelOpen.value, false);
  harness.scope.stop();
  cases += 1;
}

// C7: content from an invalidated read cannot be staged for the new object.
{
  let company = 1;
  const harness = loadPublishLifecycle(() => ({
    companyId: company,
    actorRoleCode: 'actor-a',
    targetRoleKey: 'target-a',
    model: harness.refs.currentModel.value,
    actionId: harness.refs.scopeAction.value,
    viewId: harness.refs.scopeView.value,
    viewType: 'tree+search',
  }));
  context.beginContextTransition();
  const loaded = harness.lifecycle.loadListSearchConfig();
  harness.listRequests[0].resolve(listPayload(['name', 'owner']));
  await loaded;
  harness.refs.listColumnsText.value = 'name\nowner\ndate';
  company = 2;
  context.beginContextTransition();
  assert.equal(await harness.lifecycle.saveListSearchConfig(), false);
  assert.equal(harness.staged.length, 0);
  assert.match(harness.refs.error.value, /尚未完成有效读取/);
  harness.scope.stop();
  cases += 1;
}

// Editor reads share one current-intent sequence without blocking coverage or versions.
{
  const harness = loadPublishLifecycle(() => ({
    companyId: 1,
    actorRoleCode: 'actor-a',
    targetRoleKey: 'target-a',
    model: harness.refs.currentModel.value,
    actionId: harness.refs.scopeAction.value,
    viewId: harness.refs.scopeView.value,
  }));
  context.beginContextTransition();
  const listRead = harness.lifecycle.loadListSearchConfig();
  const analysisRead = harness.lifecycle.loadAnalysisConfig();
  harness.analysisRequests[0].resolve(analysisPayload());
  await analysisRead;
  harness.listRequests[0].resolve(listPayload(['name']));
  await listRead;
  assert.equal(harness.refs.analysisPanelOpen.value, true);
  assert.equal(harness.refs.listSearchPanelOpen.value, false);
  assert.equal(harness.refs.pivotMeasuresText.value, 'amount_total');
  assert.equal(harness.refs.listColumnsText.value, '');
  assert.equal(harness.refs.listSearchBusy.value, false);
  harness.scope.stop();
  cases += 1;
}

// The last opened editor owns the panel even when list/analysis and approval overlap.
{
  const identity = () => ({
    companyId: 1,
    actorRoleCode: 'actor-a',
    targetRoleKey: 'target-a',
    model: 'parent.model',
    actionId: 11,
    viewId: 21,
  });
  const editorIntentOwner = context.createContextRequestOwner(identity);
  const publish = loadPublishLifecycle(identity, editorIntentOwner);
  const approval = loadApprovalEditor(identity, editorIntentOwner);
  context.beginContextTransition();
  const slowList = publish.lifecycle.loadListSearchConfig();
  const approvalRead = approval.editor.loadApprovalConfig();
  approval.requests[0].resolve(approval.payload('child.model'));
  await approvalRead;
  approval.editor.enableApprovalWithDefaultStep();
  assert.equal(approval.editor.approvalPanelOpen.value, true);
  assert.equal(approval.editor.hasApprovalDraftChanges.value, true);
  publish.listRequests[0].resolve(listPayload(['name']));
  await slowList;
  assert.equal(approval.editor.approvalPanelOpen.value, true);
  assert.equal(publish.refs.listSearchPanelOpen.value, false);
  assert.equal(approval.editor.hasApprovalDraftChanges.value, true);
  publish.scope.stop();
  approval.scope.stop();
  editorIntentOwner.dispose();
  cases += 1;
}
{
  const identity = () => ({
    companyId: 1,
    actorRoleCode: 'actor-a',
    targetRoleKey: 'target-a',
    model: 'parent.model',
    actionId: 11,
    viewId: 21,
  });
  const editorIntentOwner = context.createContextRequestOwner(identity);
  const publish = loadPublishLifecycle(identity, editorIntentOwner);
  const approval = loadApprovalEditor(identity, editorIntentOwner);
  context.beginContextTransition();
  const slowApproval = approval.editor.loadApprovalConfig();
  const currentList = publish.lifecycle.loadListSearchConfig();
  publish.listRequests[0].resolve(listPayload(['name']));
  await currentList;
  publish.refs.listColumnsText.value = 'name\nowner';
  assert.equal(publish.refs.listSearchPanelOpen.value, true);
  approval.requests[0].resolve(approval.payload('child.model'));
  await slowApproval;
  assert.equal(publish.refs.listSearchPanelOpen.value, true);
  assert.equal(approval.editor.approvalPanelOpen.value, false);
  assert.notEqual(publish.refs.listColumnsText.value, publish.refs.listSearchBase.value.list);
  publish.scope.stop();
  approval.scope.stop();
  editorIntentOwner.dispose();
  cases += 1;
}

// C8: switching configuration objects during confirmation sends no rollback.
{
  const exports = {};
  vm.runInNewContext(versionsModule.code, {
    exports,
    require: (name) => {
      if (name === 'vue') return vue;
      if (name === '../../app/contextEpoch') return context;
      if (name === '../../api/businessConfig') {
        return {
          loadBusinessConfigContractVersions: async () => ({ contracts: [] }),
          rollbackBusinessConfigContract: async () => {
            rollbackCalls += 1;
            return { rolled_back_to_version: 1 };
          },
        };
      }
      if (name === './formatters') {
        return { countDiff: () => ({ added: [], removed: [] }), formatDiffNames: () => '', viewTypeLabel: (value) => value };
      }
      throw new Error(`unexpected versions dependency: ${name}`);
    },
  });
  let rollbackCalls = 0;
  let action = 11;
  const confirm = deferred();
  const scope = vue.effectScope();
  const lifecycle = scope.run(() => exports.useBusinessConfigVersions({
    currentModel: vue.computed(() => 'res.partner'),
    scopeAction: vue.computed(() => action),
    scopeView: vue.computed(() => 21),
    scopeRole: vue.computed(() => 'target-a'),
    selectedPageLabel: vue.ref('业务'),
    surface: vue.ref({ model: 'res.partner' }),
    advancedPanelOpen: vue.ref(false),
    listSearchSaving: vue.ref(false),
    coverageScan: vue.ref(null),
    error: vue.ref(''),
    setMessage() {},
    clearMessage() {},
    loadSurface: async () => {},
    rescanCoverageAfterBootstrap: async () => {},
    rollbackConfirm: { open: () => confirm.promise },
    requestIdentity: () => ({ companyId: 1, actorRoleCode: 'actor-a', targetRoleKey: 'target-a', model: 'res.partner', actionId: action, viewId: 21, viewType: 'form' }),
  }));
  const pending = lifecycle.rollbackContractFromWorkbench({
    name: 'view.res_partner.form',
    model: 'res.partner',
    view_type: 'form',
    action_id: 11,
    view_id: 21,
    version_no: 3,
    versions: [{}, {}],
  });
  action = 12;
  context.beginContextTransition();
  confirm.resolve(true);
  await pending;
  assert.equal(rollbackCalls, 0);
  scope.stop();
  cases += 1;
}

// FE-05: effective-version reads and context cleanup stay bound to the active company.
{
  const requests = [];
  const exports = {};
  vm.runInNewContext(productExperienceModule.code, {
    exports,
    require: (name) => {
      if (name === 'vue') {
        return Object.assign({}, vue, { onMounted: () => {}, onBeforeUnmount: () => {} });
      }
      if (name === 'vue-router') return { onBeforeRouteLeave() {} };
      if (name === '../../api/intents') {
        return {
          intentRequest: (params) => new Promise((resolve, reject) => {
            requests.push({ params, resolve, reject });
          }),
        };
      }
      if (name === '../../app/contextEpoch') return context;
      if (name === './effectiveConfiguration') {
        return {
          effectiveConfigurationLabel: (contract) => contract.label,
          configurationTargetRoleLabel: (value) => value || '',
        };
      }
      if (name === './formatters') return { normalizeNamesText: (value) => String(value || '') };
      throw new Error(`unexpected product experience dependency: ${name}`);
    },
  });
  const session = vue.reactive({
    recordContext: { company_id: 1, company_name: '公司 A' },
    roleSurface: { role_code: 'actor-a', role_label: '角色 A' },
  });
  const model = vue.ref('res.partner');
  const action = vue.ref(11);
  const view = vue.ref(21);
  const targetRole = vue.ref('target-a');
  const selectedViewType = vue.ref('form');
  const listSearchBusy = vue.ref(false);
  const listSearchSaving = vue.ref(false);
  const approvalLoading = vue.ref(false);
  const versionsLoading = vue.ref(false);
  let surfaceLoads = 0;
  const scope = vue.effectScope();
  const experience = scope.run(() => exports.useBusinessConfigProductExperience({
    session,
    currentModel: vue.computed(() => model.value),
    scopeAction: vue.computed(() => action.value),
    scopeView: vue.computed(() => view.value),
    scopeRole: vue.computed(() => targetRole.value),
    selectedViewType: vue.computed(() => selectedViewType.value),
    surface: vue.ref({ model: 'res.partner' }),
    versionContracts: vue.ref([]),
    listSearchAudit: vue.ref(null),
    analysisAudit: vue.ref(null),
    snapshotSummary: vue.computed(() => null),
    hasListSearchDraftChanges: vue.computed(() => false),
    hasAnalysisDraftChanges: vue.computed(() => false),
    hasApprovalDraftChanges: vue.computed(() => false),
    hasUnifiedDraft: vue.computed(() => false),
    activeChangeSetToken: vue.computed(() => ''),
    listColumnsText: vue.ref(''),
    searchFiltersText: vue.ref(''),
    searchGroupByText: vue.ref(''),
    listSearchBase: vue.ref({ list: '', filter: '', group: '' }),
    listSearchPanelOpen: vue.ref(true),
    analysisPanelOpen: vue.ref(true),
    approvalPanelOpen: vue.ref(true),
    versionsPanelOpen: vue.ref(true),
    listSearchBusy,
    listSearchSaving,
    approvalLoading,
    versionsLoading,
    resetListSearchDraft() {},
    resetAnalysisDraft() {},
    resetApprovalDraft() {},
    resetUnifiedDraftScope() {},
    loadSurface: async () => { surfaceLoads += 1; },
    scanSystemRootCoverage: async () => {},
    setMessage() {},
    openImpactDialog: async () => true,
    requestIdentity: () => ({
      companyId: session.recordContext.company_id,
      actorRoleCode: session.roleSurface.role_code,
      targetRoleKey: targetRole.value,
      model: model.value,
      actionId: action.value,
      viewId: view.value,
    }),
  }));
  context.beginContextTransition();
  await flushMicrotasks();
  assert.equal(requests.length, 1);
  listSearchBusy.value = true;
  listSearchSaving.value = true;
  approvalLoading.value = true;
  versionsLoading.value = true;
  session.recordContext.company_id = 2;
  context.beginContextTransition();
  await flushMicrotasks();
  assert.equal(requests.length, 2);
  requests[1].resolve({ label: '公司 B 当前配置' });
  await flushMicrotasks();
  assert.equal(experience.currentEffectiveVersionLabel.value, '公司 B 当前配置');
  requests[0].resolve({ label: '公司 A 旧配置' });
  await flushMicrotasks();
  assert.equal(experience.currentEffectiveVersionLabel.value, '公司 B 当前配置');
  assert.equal(listSearchBusy.value, false);
  assert.equal(listSearchSaving.value, false);
  assert.equal(approvalLoading.value, false);
  assert.equal(versionsLoading.value, false);
  assert.ok(surfaceLoads >= 1);
  scope.stop();
  cases += 1;
}

// C10: a stable current read can still stage ordinary edits.
{
  const harness = loadPublishLifecycle(() => ({
    companyId: 1,
    actorRoleCode: 'actor-a',
    targetRoleKey: 'target-a',
    model: harness.refs.currentModel.value,
    actionId: harness.refs.scopeAction.value,
    viewId: harness.refs.scopeView.value,
    viewType: 'tree+search',
  }));
  context.beginContextTransition();
  const loaded = harness.lifecycle.loadListSearchConfig();
  harness.listRequests[0].resolve(listPayload(['name']));
  await loaded;
  harness.refs.listColumnsText.value = 'name\ndate';
  assert.equal(await harness.lifecycle.saveListSearchConfig(), true);
  assert.equal(harness.staged.length, 1);
  assert.deepEqual(harness.staged[0].draft_payload.columns, ['name', 'date']);
  harness.scope.stop();
  cases += 1;
}

console.log(`[business_config_context_race] PASS cases=${cases}`);
