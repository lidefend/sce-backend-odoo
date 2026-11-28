#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ts = require('../../frontend/apps/web/node_modules/typescript');

const ROOT = path.resolve(__dirname, '..', '..');
const SOURCE = path.join(ROOT, 'frontend/apps/web/src/app/navigationContext.ts');

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
  vm.runInNewContext(transpiled, { module, exports: module.exports }, { filename: SOURCE });
  return module.exports;
}

function assertDeepEqual(actual, expected, label) {
  const actualJson = JSON.stringify(actual);
  const expectedJson = JSON.stringify(expected);
  if (actualJson !== expectedJson) {
    throw new Error(`${label}: expected ${expectedJson}, got ${actualJson}`);
  }
}

function main() {
  const runtime = loadRuntime();
  assertDeepEqual(
    runtime.buildBusinessCategoryCreateNavQuery({
      categoryCode: 'project',
      option: {
        label: '项目办理',
        categoryId: 18,
        defaultValues: {
          project_id: 7,
          active: true,
          ignored_object: { id: 1 },
          ignored_array: [1],
          ignored_null: null,
        },
      },
      fallbackLabel: 'fallback',
    }),
    {
      current_business_category_code: 'project',
      default_business_category_code: 'project',
      ctx_source: 'business_category_create_picker',
      default_business_category_id: '18',
      default_project_id: '7',
      default_active: 'true',
    },
    'business category create query',
  );

  assertDeepEqual(
    runtime.buildBusinessCategoryCreateNavQuery({ categoryCode: '  ', fallbackLabel: 'fallback' }),
    undefined,
    'empty category code',
  );

  assertDeepEqual(
    runtime.pickContractNavQuery({
      scene: 'projects.ledger',
      scene_key: 'projects.ledger',
      scene_label: '项目台账',
      menu_id: '12',
      action_id: '34',
      domain_raw: '[]',
      context_raw: '{}',
      return_url: '/s/projects.ledger',
    }),
    {
      menu_id: '12',
      action_id: '34',
      domain_raw: '[]',
      context_raw: '{}',
      return_url: '/s/projects.ledger',
    },
    'scene identity stays in the route path while execution context is carried',
  );

  console.log('[navigation_context_smoke] PASS');
}

main();
