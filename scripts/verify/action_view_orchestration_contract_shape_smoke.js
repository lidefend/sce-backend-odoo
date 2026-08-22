#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ts = require('../../frontend/apps/web/node_modules/typescript');

const ROOT = path.resolve(__dirname, '..', '..');
const SOURCE = path.join(
  ROOT,
  'frontend/apps/web/src/app/action_runtime/useActionViewContractShapeRuntime.ts',
);

function uniqueFields(fields) {
  const seen = new Set();
  const out = [];
  (fields || []).forEach((field) => {
    const name = String(field || '').trim();
    if (name && !seen.has(name)) {
      seen.add(name);
      out.push(name);
    }
  });
  return out;
}

function loadRuntime() {
  const source = fs.readFileSync(SOURCE, 'utf8');
  const transpiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    },
  }).outputText;
  const module = { exports: {} };
  const sandbox = {
    module,
    exports: module.exports,
    require: (name) => {
      if (name === 'vue') return { computed: (fn) => ({ value: fn() }) };
      if (name.endsWith('actionViewRequestRuntime')) return { uniqueFields };
      if (name.endsWith('contracts/v2/store')) {
        return {
          collectContractV2FieldStatusByCode: () => ({}),
          resolveContractV2FieldDescriptorMap: (store) => Object.fromEntries(
            [...(store?.widgetsByFieldCode?.values?.() || [])].map((row) => [row.fieldCode, row]),
          ),
          resolveContractV2FieldWidgets: (store) => [...(store?.widgetsByFieldCode?.values?.() || [])],
          resolveContractV2ListProfile: (store) => store?.snapshot?.layoutContract?.listProfile || {},
          resolveContractV2PrimaryDataSource: (store) => store?.primaryDataSource || {},
          resolveContractV2SearchContract: (store) => store?.snapshot?.searchContract || {},
          resolveContractV2SurfacePolicies: (store) => store?.snapshot?.actionContract?.surfacePolicies || {},
        };
      }
      throw new Error(`unexpected require: ${name}`);
    },
  };
  vm.runInNewContext(transpiled, sandbox, { filename: SOURCE });
  return module.exports;
}

function assertDeepEqual(actual, expected, label) {
  const actualJson = JSON.stringify(actual);
  const expectedJson = JSON.stringify(expected);
  if (actualJson !== expectedJson) {
    throw new Error(`${label}: expected ${expectedJson}, got ${actualJson}`);
  }
}

function canonicalStore({ viewType = 'list', model = 'project.project', widgets = [], listProfile = {}, searchContract = {} } = {}) {
  return {
    snapshot: {
      pageInfo: { viewType, model },
      layoutContract: { listProfile },
      actionContract: { surfacePolicies: {} },
      searchContract,
    },
    widgetsByFieldCode: new Map(widgets.map((row) => [row.fieldCode, row])),
    primaryDataSource: null,
  };
}

function main() {
  const runtime = loadRuntime();
  const kanbanStore = canonicalStore({ viewType: 'kanban', widgets: [
    { fieldCode: 'name', label: '名称' },
    { fieldCode: 'email', label: '邮箱' },
    { fieldCode: 'phone', label: '电话' },
  ] });
  const kanban = runtime.extractKanbanFieldsFromContract(kanbanStore);
  assertDeepEqual(kanban, ['name', 'email', 'phone'], 'kanban nested fields and slots');

  const calendar = runtime.extractAdvancedViewFieldsFromContract(canonicalStore({ widgets: [
    { fieldCode: 'planned_start' }, { fieldCode: 'planned_stop' }, { fieldCode: 'user_id' }, { fieldCode: 'state' },
  ] }), 'calendar');
  assertDeepEqual(
    calendar,
    ['planned_start', 'planned_stop', 'user_id', 'state'],
    'calendar advanced fields',
  );

  const dashboard = runtime.extractAdvancedViewFieldsFromContract(canonicalStore({ widgets: [
    { fieldCode: 'project_id' }, { fieldCode: 'amount_total' }, { fieldCode: 'date_order' },
  ] }), 'dashboard');
  assertDeepEqual(
    dashboard,
    ['project_id', 'amount_total', 'date_order'],
    'dashboard advanced fields',
  );

  const shapeRuntime = runtime.useActionViewContractShapeRuntime({
    pageText: (_key, fallback) => fallback,
    actionContract: { value: canonicalStore({ widgets: [
      { fieldCode: 'amount_total', label: '合同额' }, { fieldCode: 'company_id', label: '公司' },
    ] }) },
    advancedFields: { value: ['company_id', 'amount_total'] },
    activeGroupByField: { value: '' },
  });
  const meta = shapeRuntime.advancedRowMeta({
    id: 1,
    display_name: 'row',
    company_id: '示例建设公司',
    amount_total: 1200,
  });
  if (meta !== '公司: 示例建设公司 · 合同额: 1200') {
    throw new Error(`advanced display row labels: expected compiled labels, got ${meta}`);
  }

  const projectShapeRuntime = runtime.useActionViewContractShapeRuntime({
    pageText: (_key, fallback) => fallback,
    actionContract: { value: canonicalStore({ viewType: 'kanban', widgets: [
      { fieldCode: 'partner_id', label: 'CODEX_PARTNER_CARD' },
      { fieldCode: 'name', label: 'CODEX_NAME_CARD' },
    ] }) },
    advancedFields: { value: [] },
    activeGroupByField: { value: '' },
  });
  if (projectShapeRuntime.contractColumnLabels.value.name !== 'CODEX_NAME_CARD') {
    throw new Error('project fallback labels must not overwrite orchestrated kanban labels');
  }
  const viewLabels = runtime.extractViewFieldLabelsFromContract(canonicalStore({ widgets: [
    { fieldCode: 'partner_id', label: 'CODEX_PARTNER_CARD' },
  ] }), 'kanban');
  if (viewLabels.partner_id !== 'CODEX_PARTNER_CARD') {
    throw new Error('view-specific labels must prefer the current view block');
  }

  const projectListProfile = projectShapeRuntime.extractListProfile(canonicalStore({
    listProfile: {
      columns: ['name', 'user_id', 'manager_id'],
      hidden_columns: ['manager_id'],
      cross_device_critical_columns: ['name', 'user_id'],
      column_labels: {
        name: '项目名称',
        user_id: '项目负责人',
        manager_id: '项目经理',
      },
    },
  }));
  assertDeepEqual(
    projectListProfile.cross_device_critical_columns,
    ['name', 'user_id'],
    'cross-device critical columns survive contract shape extraction',
  );
  assertDeepEqual(
    projectListProfile.hidden_columns,
    ['manager_id'],
    'optional hidden columns remain available without becoming default-visible',
  );

  console.log('[action_view_orchestration_contract_shape_smoke] PASS');
}

main();
