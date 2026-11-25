import assert from 'node:assert/strict';
import { ref } from 'vue';

import { decodeContractCarrierCapabilities } from '../src/app/contracts/v2/carrierCapabilities';
import {
  PageOrchestrationDecodeError,
  decodePageOrchestrationContract,
} from '../src/app/pageOrchestration';
import { useActionViewActionRuntime } from '../src/app/action_runtime/useActionViewActionRuntime';
import {
  decodeActionFeedbackRuntimePatch,
  firstActionFeedback,
} from '../src/app/contract/actionFeedback';

const sourceAuthority = {
  kind: 'page_block_action_producer',
  authorities: [
    'contract_v2_action_rules',
    'action_target_schema',
    'odoo_action_groups',
    'ir_model_access',
    'ir_rule',
  ],
  projectionOnly: true,
  noFrontendDefaults: true,
  carrier: 'page-block-action.v1',
  schemaVersion: '1.0.0',
};

function carrier(options: {
  enabled?: boolean;
  authorized?: boolean;
  businessAvailable?: boolean;
  reasonCode?: string;
  reasonMessage?: string;
} = {}) {
  const enabled = options.enabled ?? true;
  const authorized = options.authorized ?? true;
  const businessAvailable = options.businessAvailable ?? true;
  const allowed = authorized && businessAvailable;
  return {
    actionId: 'action.open_project',
    actionRuleRef: 'action.open_project',
    actionKey: 'open_project',
    label: '打开项目',
    intent: 'ui.contract',
    target: {
      source: 'ContractV2ActionRule.target',
      value: {
        type: 'action',
        action_xmlid: 'smart_construction_core.action_sc_project_list',
      },
    },
    visibility: { visible: true, source: 'action_contract' },
    permission: {
      evaluated: true,
      allowed,
      authorizationAllowed: authorized,
      businessAvailable,
    },
    state: {
      enabled,
      disabled: !enabled,
      reasonCode: options.reasonCode || '',
      reasonMessage: options.reasonMessage || '',
    },
  };
}

function actionRule(action = carrier()) {
  return {
    actionId: action.actionId,
    actionKey: action.actionKey,
    label: action.label,
    intent: action.intent,
    target: action.target.value,
    button: {},
    triggerType: 'click',
    sourceWidgetId: 'block.projects',
    targetIds: [],
    dispatchMode: 'server',
    targetScope: 'page',
    refreshMode: 'partial',
    sourceChannel: 'page_block_action',
    authorizationAllowed: action.permission.authorizationAllowed,
    businessAvailable: action.permission.businessAvailable,
    entitlementEvaluated: true,
    allowed: action.permission.allowed,
    enabled: action.state.enabled,
    disabled: action.state.disabled,
    ...(action.state.reasonCode ? { reasonCode: action.state.reasonCode } : {}),
    ...(action.state.reasonMessage ? { reasonMessage: action.state.reasonMessage } : {}),
  };
}

function contract(action = carrier()) {
  return {
    contract_version: '2.1.0',
    schema_version: '2.1.0',
    scene_key: 'workspace.home',
    page: { key: 'workspace.home', title: '角色首页', page_type: 'dashboard' },
    zones: [],
    data_sources: {},
    action_schema: {
      schemaVersion: '1.0.0',
      carrier: 'page-block-action.v1',
      sourceAuthority,
      actions: { [action.actionId]: action },
    },
    action_contract: {
      actionRuleList: [actionRule(action)],
      dependencyGraph: { 'block.projects': [action.actionId] },
    },
  };
}

const decoded = decodePageOrchestrationContract(contract());
assert.equal(decoded.action_schema?.carrier, 'page-block-action.v1');
assert.equal(decoded.action_contract?.actionRuleList.length, 1);
assert.equal(
  decoded.action_schema?.actions['action.open_project'].state.enabled,
  true,
);

const denied = decodePageOrchestrationContract(contract(carrier({
  enabled: false,
  authorized: false,
  reasonCode: 'ACTION_NOT_AUTHORIZED',
  reasonMessage: '当前角色无权执行该动作',
})));
assert.equal(
  denied.action_schema?.actions['action.open_project'].state.reasonCode,
  'ACTION_NOT_AUTHORIZED',
);

const missingPermission = structuredClone(contract());
delete (missingPermission.action_schema.actions['action.open_project'] as Record<string, unknown> & {
  permission: Record<string, unknown>;
}).permission.evaluated;
assert.throws(
  () => decodePageOrchestrationContract(missingPermission),
  PageOrchestrationDecodeError,
);

const unknownCarrierKey = structuredClone(contract());
((unknownCarrierKey.action_schema.actions['action.open_project'] as Record<string, unknown> & {
  permission: Record<string, unknown>;
}).permission).authorizationSubject = { model: 'project.project', recordId: 1 };
assert.throws(
  () => decodePageOrchestrationContract(unknownCarrierKey),
  PageOrchestrationDecodeError,
);

const ruleMismatch = structuredClone(contract());
ruleMismatch.action_contract.actionRuleList[0].actionId = 'action.other';
assert.throws(
  () => decodePageOrchestrationContract(ruleMismatch),
  PageOrchestrationDecodeError,
);

const targetMismatch = structuredClone(contract());
targetMismatch.action_contract.actionRuleList[0].target = {
  type: 'action',
  action_xmlid: 'other.action',
};
assert.throws(
  () => decodePageOrchestrationContract(targetMismatch),
  PageOrchestrationDecodeError,
);

const enabledMismatch = structuredClone(contract());
enabledMismatch.action_contract.actionRuleList[0].enabled = false;
assert.throws(
  () => decodePageOrchestrationContract(enabledMismatch),
  PageOrchestrationDecodeError,
);

const reasonMismatch = structuredClone(contract(carrier({
  enabled: false,
  authorized: false,
  reasonCode: 'ACTION_NOT_AUTHORIZED',
  reasonMessage: '当前角色无权执行该动作',
})));
reasonMismatch.action_contract.actionRuleList[0].reasonMessage = '不同原因';
assert.throws(
  () => decodePageOrchestrationContract(reasonMismatch),
  PageOrchestrationDecodeError,
);

const identityMismatch = structuredClone(contract());
identityMismatch.action_contract.actionRuleList[0].label = '不同标签';
assert.throws(
  () => decodePageOrchestrationContract(identityMismatch),
  PageOrchestrationDecodeError,
);

const missingReason = structuredClone(contract(carrier({
  enabled: false,
  authorized: false,
})));
assert.throws(
  () => decodePageOrchestrationContract(missingReason),
  PageOrchestrationDecodeError,
);

const legacyLeak = {
  contract_version: '2.0.0',
  schema_version: '2.0.0',
  scene_key: 'workspace.home',
  page: { title: 'Home' },
  zones: [],
  action_schema: contract().action_schema,
};
assert.throws(
  () => decodePageOrchestrationContract(legacyLeak),
  PageOrchestrationDecodeError,
);

const actionOnlyCapabilities = decodeContractCarrierCapabilities({
  negotiationVersion: '1.0.0',
  status: 'current',
  clientType: 'web_pc',
  compatibilityMode: 'page_block_action_v1',
  acceptedContractVersions: ['2.7.x'],
  clientContractCapabilities: ['page_block_action.v1'],
  contractVersion: '2.7.0',
  pageOrchestrationVersion: '2.1.0',
  carriers: {
    'page_block_data.v1': { schemaVersion: '1.0.0', enabled: false },
    'attachment_fact.v1': { schemaVersion: '1.0.0', enabled: false },
    'page_block_action.v1': { schemaVersion: '1.0.0', enabled: true },
  },
});
assert.equal(actionOnlyCapabilities.carriers['page_block_action.v1'].enabled, true);

const leakedAction = structuredClone({
  negotiationVersion: '1.0.0',
  status: 'current',
  clientType: 'web_pc',
  compatibilityMode: 'page_block_data_v1',
  acceptedContractVersions: ['2.7.x'],
  clientContractCapabilities: ['page_block_data.v1'],
  contractVersion: '2.7.0',
  pageOrchestrationVersion: '2.1.0',
  carriers: {
    'page_block_data.v1': { schemaVersion: '1.0.0', enabled: true },
    'attachment_fact.v1': { schemaVersion: '1.0.0', enabled: false },
    'page_block_action.v1': { schemaVersion: '1.0.0', enabled: true },
  },
});
assert.throws(
  () => decodeContractCarrierCapabilities(leakedAction),
  /CONTRACT_CARRIER_CAPABILITIES_INVALID/,
);

const successFeedback = decodeActionFeedbackRuntimePatch({
  actionFeedback: [{
    schemaVersion: '1.0.0',
    actionId: 'action.open_project',
    status: 'success',
    reasonCode: '',
    message: '',
    traceId: 'trace-p0c-success',
  }],
});
assert.equal(successFeedback.length, 1);
assert.equal(successFeedback[0].actionId, 'action.open_project');
assert.equal(successFeedback[0].traceId, 'trace-p0c-success');
assert.equal(firstActionFeedback({
  actionFeedback: [{
    schemaVersion: '1.0.0',
    actionId: 'action.open_project',
    status: 'denied',
    reasonCode: 'ACTION_NOT_AUTHORIZED',
    message: '当前角色无权执行该动作',
    traceId: 'trace-p0c-denied',
  }],
})?.status, 'denied');

assert.throws(
  () => decodeActionFeedbackRuntimePatch({
    actionFeedback: [{
      schemaVersion: '1.0.0',
      actionId: 'action.open_project',
      status: 'failed',
      reasonCode: '',
      message: '',
      traceId: 'trace-p0c-failed',
    }],
  }),
  /denied\/failed/,
);
assert.throws(
  () => decodeActionFeedbackRuntimePatch({
    actionFeedback: [{
      schemaVersion: '1.0.0',
      actionId: 'action.open_project',
      status: 'success',
      reasonCode: '',
      message: '',
      traceId: 'trace-p0c-extra',
      authorizationSubject: { model: 'project.project', recordId: 1 },
    }],
  }),
  /未声明属性/,
);

const batchMessage = ref('');
const runtime = useActionViewActionRuntime({
  selectedIds: ref([1]),
  batchBusy: ref(false),
  batchMessage,
  pageText: (_key: string, fallback: string) => fallback,
  load: async () => undefined,
  sessionLoadAppInit: async () => undefined,
  recordIntentTrace: () => undefined,
  resolveActionContextRecordId: () => 1,
  resolveOpenNavigation: () => ({ kind: 'none', url: '' }),
  buildRouteTarget: (value: unknown) => value,
  routerPush: async (value: unknown) => value,
  resolveNavigationUrl: (value: string) => value,
  openWindow: () => undefined,
  resolveMissingOpenTargetMessage: () => '',
  resolveExecIds: () => [1],
  resolveRunIds: (ids: number[]) => ids,
  resolveCounters: ({ successCount, failureCount, ok }) => ({
    successCount: successCount + (ok ? 1 : 0),
    failureCount: failureCount + (ok ? 0 : 1),
  }),
  resolveDoneMessage: () => 'generic completion',
  resolveRequiresRecordContextMessage: () => '',
  resolveSelectionBlockMessage: () => '',
  resolveMissingModelMessage: () => '',
  executeProjectionRefresh: async () => undefined,
  executeSceneMutation: async () => undefined,
  executeButton: async () => {
    throw Object.assign(new Error('denied'), {
      details: {
        runtimePatch: {
          actionFeedback: [{
            schemaVersion: '1.0.0',
            actionId: 'action.submit',
            status: 'denied',
            reasonCode: 'ACTION_NOT_AUTHORIZED',
            message: '当前角色无权执行该动作',
            traceId: 'trace-p0c-runtime',
          }],
        },
      },
    });
  },
  buildButtonRequest: () => ({
    model: 'x.model',
    res_id: 1,
    button: { name: 'submit', type: 'object' },
  }),
  resolveResponseNavigation: () => ({ nextActionId: null, entryTarget: null }),
  shouldNavigate: () => false,
});
await runtime.runContractAction({
  key: 'action.submit',
  model: 'x.model',
  methodName: 'submit',
  selection: 'single',
});
assert.equal(batchMessage.value, '当前角色无权执行该动作');

console.log('P0_C_PAGE_BLOCK_ACTION_CARRIER=PASS');
