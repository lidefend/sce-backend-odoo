#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ts = require('../../frontend/apps/web/node_modules/typescript');

const ROOT = path.resolve(__dirname, '..', '..');
const SOURCE = path.join(
  ROOT,
  'frontend/apps/web/src/app/runtime/actionViewContractActionRuntime.ts',
);

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
      if (name.endsWith('routeQuery')) {
        return { buildEntryTargetRouteTarget: () => ({ name: 'action', query: {} }) };
      }
      if (name.endsWith('navigationContext')) {
        return {
          contractActionCarryQuery: () => ({}),
          entryTargetMenuId: () => 0,
          entryTargetModel: () => '',
        };
      }
      if (name.endsWith('contractGap')) {
        return {
          contractGapError: (defect, message) => Object.assign(new Error(message), {
            name: 'ContractGapError',
            defect,
          }),
        };
      }
      throw new Error(`unexpected require: ${name}`);
    },
  };
  vm.runInNewContext(transpiled, sandbox, { filename: SOURCE });
  return module.exports;
}

async function main() {
  const runtime = loadRuntime();
  const batchRequest = runtime.buildContractActionButtonRequest({
    model: 'x.model', recordId: [3, 4], methodName: 'action_confirm',
    actionKey: 'confirm', contractActionId: 'action.confirm',
    backendIdentity: 'button:object:action_confirm', sourceWidgetId: 'page.row',
    executionScope: 'recordset', kind: 'object',
  });
  if (JSON.stringify(batchRequest.res_id) !== '[3,4]' || batchRequest.button.execution_scope !== 'recordset') {
    throw new Error('native collection action must retain the complete selected set in one intent request');
  }

  if (runtime.stableActionContractId('  Project/Done ', 'fallback') !== 'Project.Done') {
    throw new Error('stableActionContractId must normalize spaces and slashes');
  }
  if (runtime.stableActionContractId('123', 'fallback') !== 'id.123') {
    throw new Error('stableActionContractId must prefix non-alpha ids');
  }

  const visible = runtime.applyActionViewV2ButtonStatus(
    { key: 'Project/Done', enabled: true, hint: '' },
    { 'btn.Project.Done': { visible: true, disabled: true, reasonCode: 'policy_blocked' } },
  );
  if (!visible || visible.enabled !== false || visible.hint !== 'policy_blocked') {
    throw new Error('applyActionViewV2ButtonStatus must apply disabled status by stable button id');
  }

  const hidden = runtime.applyActionViewV2ButtonStatus(
    { key: 'archive', enabled: true, hint: '' },
    { archive: { visible: false, disabled: false } },
  );
  if (hidden !== null) {
    throw new Error('applyActionViewV2ButtonStatus must remove invisible buttons');
  }

  const untouched = runtime.applyActionViewV2ButtonStatus(
    { key: 'open', enabled: true, hint: 'keep' },
    {},
  );
  if (!untouched || untouched.enabled !== true || untouched.hint !== 'keep') {
    throw new Error('applyActionViewV2ButtonStatus must preserve buttons without status');
  }

  const hookPath = path.join(ROOT, 'frontend/apps/web/src/app/action_runtime/useActionViewActionRuntime.ts');
  const hookModule = { exports: {} };
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(hookPath, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText, {
    module: hookModule, exports: hookModule.exports,
    require: (name) => {
      if (name.endsWith('actionFeedback')) return { firstActionFeedback: () => undefined };
      if (name.endsWith('contractGap')) return { contractGapError: (_facts, message) => new Error(message) };
      throw new Error(`unexpected hook dependency ${name}`);
    },
  }, { filename: hookPath });
  const requests = [];
  let navigations = 0;
  const hook = hookModule.exports.useActionViewActionRuntime({
    selectedIds: { value: [3, 4, 5] }, batchBusy: { value: false }, batchMessage: { value: '' },
    pageText: (_key, fallback) => fallback,
    resolveSelectionBlockMessage: () => '', resolveActionContextRecordId: () => null,
    resolveExecIds: ({ selectedIds }) => selectedIds,
    buildButtonRequest: runtime.buildContractActionButtonRequest,
    executeButton: async (request) => { requests.push(request); return {}; },
    resolveResponseNavigation: () => ({ nextActionId: 7 }), shouldNavigate: () => true,
    buildRouteTarget: (value) => value, routerPush: async () => { navigations += 1; },
  });
  const collectionAction = { key: 'confirm', model: 'x.model', methodName: 'action_confirm',
    kind: 'object', selection: 'multi', executionScope: 'recordset', contractActionId: 'action.confirm',
    backendIdentity: 'button:object:action_confirm', sourceWidgetId: 'page.row' };
  await hook.runContractAction(collectionAction);
  if (requests.length !== 1 || JSON.stringify(requests[0].res_id) !== '[3,4,5]' || navigations !== 1) {
    throw new Error('collection navigation must follow one request containing every selected record');
  }
  let missingScopeRejected = false;
  try { await hook.runContractAction({ ...collectionAction, executionScope: undefined }); }
  catch { missingScopeRejected = true; }
  if (!missingScopeRejected || requests.length !== 1) {
    throw new Error('undeclared multi selection must fail before sending any request');
  }
  console.log('[action_view_contract_action_runtime_smoke] PASS');
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
