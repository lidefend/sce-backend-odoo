import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { ref } from 'vue';

import { normalizeV2ActionRows } from '../src/app/action_runtime/useActionViewActionPresentationRuntime';
import { useActionViewContractActionButtonRuntime } from '../src/app/action_runtime/useActionViewContractActionButtonRuntime';
import { useActionViewActionRuntime } from '../src/app/action_runtime/useActionViewActionRuntime';
import { buildContractActionButtonRequest } from '../src/app/runtime/actionViewContractActionRuntime';
import type { ContractV2NormalizedStore } from '../src/app/contracts/v2/types';

const fixturePath = path.resolve(
  process.cwd(),
  'addons/smart_construction_core/tests/fixtures/p0_c_fix01_action_button.json',
);
const requestFixture = JSON.parse(fs.readFileSync(fixturePath, 'utf8')) as {
  name: string;
  type: string;
  action_id: string;
  backend_identity: string;
  source_widget_id: string;
};

const rule = {
  actionId: requestFixture.action_id,
  actionKey: 'toggle_active',
  label: '启用/停用',
  intent: 'execute_button',
  backendIdentity: requestFixture.backend_identity,
  sourceWidgetId: requestFixture.source_widget_id,
  button: {
    name: requestFixture.name,
    type: requestFixture.type,
  },
  triggerType: 'click',
  targetIds: [],
  dispatchMode: 'server',
  targetScope: 'page',
  refreshMode: 'partial',
  allowed: true,
  enabled: true,
  disabled: false,
  entitlementEvaluated: true,
  authorizationAllowed: true,
  businessAvailable: true,
};
const store = {
  snapshot: {
    actionContract: {
      actionRuleList: [rule],
      surfacePolicies: {},
    },
    runtimeContract: {},
  },
  widgetsByFieldCode: new Map(),
} as unknown as ContractV2NormalizedStore;

const rows = normalizeV2ActionRows(store);
assert.equal(rows.length, 1);
const selectedIds = ref([7]);
const buttonRuntime = useActionViewContractActionButtonRuntime({
  selectedIds,
  resolvedModelRef: ref('res.partner'),
  modelRef: ref('res.partner'),
  pageText: (_key: string, fallback: string) => fallback,
  isActionViewNumericToken: (value: unknown) => /^\d+$/.test(String(value || '')),
  hasActionViewNoiseMarker: () => false,
  normalizeSceneActionProtocol: () => null,
  parseContractContextRaw: (value: unknown) => (
    value && typeof value === 'object' && !Array.isArray(value)
      ? value as Record<string, unknown>
      : {}
  ),
  normalizeActionKind: (value: unknown) => String(value || ''),
  toPositiveInt: (value: unknown) => {
    const parsed = Number(value || 0);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
  },
  detectObjectMethodFromActionKey: (_key: string, methodName: string) => methodName,
});
const action = buttonRuntime.toContractActionButton(rows[0], new Set());
assert.ok(action);
assert.equal(action.contractActionId, requestFixture.action_id);
assert.equal(action.backendIdentity, requestFixture.backend_identity);
assert.equal(action.sourceWidgetId, requestFixture.source_widget_id);

const built = buildContractActionButtonRequest({
  model: action.model,
  recordId: 7,
  methodName: action.methodName,
  actionKey: action.key,
  contractActionId: action.contractActionId,
  backendIdentity: action.backendIdentity,
  sourceWidgetId: action.sourceWidgetId,
  kind: action.kind,
});
assert.deepEqual(built.button, requestFixture);

let captured: unknown = null;
const batchMessage = ref('');
const runtime = useActionViewActionRuntime({
  selectedIds,
  batchBusy: ref(false),
  batchMessage,
  pageText: (_key: string, fallback: string) => fallback,
  load: async () => undefined,
  sessionLoadAppInit: async () => undefined,
  recordIntentTrace: () => undefined,
  resolveActionContextRecordId: () => 7,
  resolveOpenNavigation: () => ({ kind: 'none', url: '' }),
  buildRouteTarget: (value: unknown) => value,
  routerPush: async (value: unknown) => value,
  resolveNavigationUrl: (value: string) => value,
  openWindow: () => undefined,
  resolveMissingOpenTargetMessage: () => '',
  resolveExecIds: () => [7],
  resolveRunIds: (ids: number[]) => ids,
  resolveCounters: ({ successCount, failureCount, ok }) => ({
    successCount: successCount + (ok ? 1 : 0),
    failureCount: failureCount + (ok ? 0 : 1),
  }),
  resolveDoneMessage: () => 'done',
  resolveRequiresRecordContextMessage: () => '',
  resolveSelectionBlockMessage: () => '',
  resolveMissingModelMessage: () => '',
  executeProjectionRefresh: async () => undefined,
  executeSceneMutation: async () => undefined,
  executeButton: async (payload) => {
    captured = payload;
    return {
      result: { type: 'refresh', success: true, reason_code: 'OK' },
      runtimePatch: {
        actionFeedback: [{
          schemaVersion: '1.0.0',
          actionId: requestFixture.action_id,
          status: 'success',
          reasonCode: 'OK',
          message: '',
          traceId: 'trace-p0c-fix01',
        }],
      },
    };
  },
  buildButtonRequest: buildContractActionButtonRequest,
  resolveResponseNavigation: () => ({ nextActionId: null, entryTarget: null }),
  shouldNavigate: () => false,
});
await runtime.runContractAction(action);
assert.deepEqual((captured as { button: unknown }).button, requestFixture);

let missingActionExecuted = false;
const missingRuntime = useActionViewActionRuntime({
  selectedIds,
  batchBusy: ref(false),
  batchMessage: ref(''),
  pageText: (_key: string, fallback: string) => fallback,
  load: async () => undefined,
  sessionLoadAppInit: async () => undefined,
  recordIntentTrace: () => undefined,
  resolveActionContextRecordId: () => 7,
  resolveOpenNavigation: () => ({ kind: 'none', url: '' }),
  buildRouteTarget: (value: unknown) => value,
  routerPush: async (value: unknown) => value,
  resolveNavigationUrl: (value: string) => value,
  openWindow: () => undefined,
  resolveMissingOpenTargetMessage: () => '',
  resolveExecIds: () => [7],
  resolveRunIds: (ids: number[]) => ids,
  resolveCounters: ({ successCount, failureCount, ok }) => ({
    successCount: successCount + (ok ? 1 : 0),
    failureCount: failureCount + (ok ? 0 : 1),
  }),
  resolveDoneMessage: () => 'missing identity',
  resolveRequiresRecordContextMessage: () => '',
  resolveSelectionBlockMessage: () => '',
  resolveMissingModelMessage: () => '',
  executeProjectionRefresh: async () => undefined,
  executeSceneMutation: async () => undefined,
  executeButton: async () => {
    missingActionExecuted = true;
    return {};
  },
  buildButtonRequest: buildContractActionButtonRequest,
  resolveResponseNavigation: () => ({ nextActionId: null, entryTarget: null }),
  shouldNavigate: () => false,
});
await missingRuntime.runContractAction({ ...action, contractActionId: '' });
assert.equal(missingActionExecuted, false, 'missing canonical actionId must stop before execute_button');

console.log('P0_C_FIX01_ACTION_ID_CHAIN=PASS');
