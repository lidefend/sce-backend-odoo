import assert from 'node:assert/strict';

import {
  buildContractFormActions,
  resolveNativeContractActionState,
} from '../src/pages/contractForm/contractActionPresentation';
import { collectActionParams, buildFormActionExecutionPlan } from '../src/pages/contractForm/actionExecutionPlan';
import { useFormActionRuntime } from '../src/pages/contractForm/useFormActionRuntime';
import { resolveCanonicalFormActionExecution } from '../src/pages/contractForm/canonicalFormActionExecutor';
import type { ContractV2ButtonStatus } from '../src/app/contracts/v2/types';

const approveIdentity = 'native_button:object:action_approval_decision:/form[1]/header[1]/button[2]:1';
const rejectIdentity = 'native_button:object:action_approval_reject:/form[1]/header[1]/button[3]:1';

const approveRow = {
  actionId: 'action.action_approval_decision',
  actionKey: 'action_approval_decision',
  backendIdentity: approveIdentity,
  sourceWidgetId: 'page.header',
  label: '审批通过',
  level: 'header',
  targetScope: 'page',
  button: { name: 'action_approval_decision', type: 'object' },
  actionSemantics: {
    kind: 'business', purpose: 'approve', executor: 'contract.action',
    origin: 'workflow.contract.service',
  },
  presentation: { tier: 'primary', semantic: 'default' },
  visibleProfiles: ['edit', 'readonly'],
  allowed: true,
  enabled: true,
  disabled: false,
  entitlementEvaluated: true,
};

const rejectRow = {
  actionId: 'action.action_approval_reject',
  actionKey: 'action_approval_reject',
  backendIdentity: rejectIdentity,
  sourceWidgetId: 'page.header',
  label: '驳回',
  level: 'header',
  targetScope: 'page',
  button: { name: 'action_approval_reject', type: 'object' },
  actionSemantics: {
    kind: 'business', purpose: 'reject', executor: 'contract.action',
    origin: 'workflow.contract.service',
  },
  // This is the consumer contract for a decision that requires user input.
  // The required param must survive even without a duplicated presentation flag.
  required_params: ['reason'],
  presentation: {
    tier: 'secondary',
    semantic: 'destructive',
    requires_reason: true,
    reason_input: {
      title: '驳回付款申请',
      label: '拒绝原因',
      help: '请说明拒绝原因，提交后会写入正式审批记录。',
      submit_label: '确认驳回',
      cancel_label: '取消',
    },
  },
  visibleProfiles: ['edit', 'readonly'],
  allowed: true,
  enabled: true,
  disabled: false,
  entitlementEvaluated: true,
};

const statuses: Record<string, ContractV2ButtonStatus> = {
  approve: {
    btnId: 'btn.action_approval_decision',
    backendIdentity: approveIdentity,
    visible: true,
    disabled: false,
  },
  reject: {
    btnId: 'btn.action_approval_reject',
    backendIdentity: rejectIdentity,
    visible: true,
    disabled: false,
  },
};

const actions = buildContractFormActions({
  model: 'payment.request',
  recordId: 41,
  renderProfile: 'readonly',
  sceneReadyActions: [],
  v2ButtonStatus: statuses,
  v2ActionRuleList: [approveRow, rejectRow],
});

assert.deepEqual(
  actions.map((action) => action.key),
  ['action_approval_decision', 'action_approval_reject'],
  'the consumer must present the two delivered decision actions in declared order',
);
const approve = actions.find((action) => action.key === 'action_approval_decision');
const reject = actions.find((action) => action.key === 'action_approval_reject');
assert.equal(approve?.enabled, true);
assert.equal(approve?.actionSemantics?.purpose, 'approve');
assert.equal(reject?.enabled, true);
assert.equal(reject?.actionSemantics?.purpose, 'reject');
assert.equal(reject?.requiresReason, true);
assert.deepEqual(reject?.requiredParams, ['reason']);
assert.deepEqual(reject?.reasonPresentation, {
  title: '驳回付款申请',
  label: '拒绝原因',
  help: '请说明拒绝原因，提交后会写入正式审批记录。',
  submitLabel: '确认驳回',
  cancelLabel: '取消',
});

assert.deepEqual(
  resolveCanonicalFormActionExecution(approveRow, actions),
  { kind: 'contract-action', action: approve },
  'the renderer must resolve the exact delivered backend identity',
);
assert.deepEqual(
  buildFormActionExecutionPlan({
    action: approve!,
    modelName: 'payment.request',
    recordId: 41,
  }),
  {
    kind: 'record_button',
    model: 'payment.request',
    recordId: 41,
    methodName: 'action_approval_decision',
    buttonType: 'object',
    authorityActionId: 'action.action_approval_decision',
    backendIdentity: approveIdentity,
    sourceWidgetId: 'page.header',
    serverActionId: null,
    serverActionXmlId: '',
    context: {},
    refreshPolicy: undefined,
  },
  'execution must use the delivered rule rather than infer a method from the model',
);
assert.deepEqual(
  buildFormActionExecutionPlan({
    action: reject!,
    modelName: 'payment.request',
    recordId: 41,
  }),
  {
    kind: 'record_button',
    model: 'payment.request',
    recordId: 41,
    methodName: 'action_approval_reject',
    buttonType: 'object',
    authorityActionId: 'action.action_approval_reject',
    backendIdentity: rejectIdentity,
    sourceWidgetId: 'page.header',
    serverActionId: null,
    serverActionXmlId: '',
    context: {},
    refreshPolicy: undefined,
  },
  'a reason-bearing decision must still execute as a declared record button',
);

let missingReason = '';
assert.equal(
  await collectActionParams(reject!, (reason) => { missingReason = reason; }, async () => '   '),
  null,
  'an empty required decision reason must prevent execution',
);
assert.equal(missingReason, 'missing_reason');
assert.deepEqual(
  await collectActionParams(reject!, () => assert.fail('a filled reason must pass'), async () => '  依据不足  '),
  { reason: '依据不足' },
  'the declared reason input must be collected without a model-specific branch',
);

let missingReasonRequests = 0;
const cancelledRejectRuntime = useFormActionRuntime({
  busyKind: { value: null },
  collectActionParams: async () => null,
  confirmActionSafety: async () => true,
  ensureSavedBeforeRecordAction: async () => true,
  executeRecordButton: async () => {
    missingReasonRequests += 1;
    throw new Error('missing reason must not issue a request');
  },
  modelName: () => 'payment.request',
  recordId: () => 41,
} as never);
await cancelledRejectRuntime.runAction(reject!);
assert.equal(missingReasonRequests, 0, 'an empty or cancelled reason must stop before execute_button');

let capturedRejectRequest: Record<string, unknown> | null = null;
let filledReasonRequests = 0;
let filledReasonCollections = 0;
let filledReasonSaveChecks = 0;
const filledRejectRuntime = useFormActionRuntime({
  actionId: () => 0,
  applyProjectionRefreshPolicy: async () => {},
  busyKind: { value: null },
  collectActionParams: async () => {
    filledReasonCollections += 1;
    return { reason: '依据不足' };
  },
  confirmActionSafety: async () => true,
  currentQuery: () => ({}),
  ensureSavedBeforeRecordAction: async () => {
    filledReasonSaveChecks += 1;
    return true;
  },
  errorMessage: { value: '' },
  executeRecordButton: async (request) => {
    filledReasonRequests += 1;
    capturedRejectRequest = request as unknown as Record<string, unknown>;
    return { result: { type: 'noop' } };
  },
  executeSceneMutation: async () => ({}),
  modelName: () => 'payment.request',
  navigateActionResponseResult: async () => false,
  recordId: () => 41,
  reload: async () => {},
  routeMenuId: () => undefined,
  status: { value: null },
  submissionFeedback: { value: null },
} as never);
await filledRejectRuntime.runAction(reject!);
assert.equal(filledReasonSaveChecks, 1, 'a reason-bearing record action must pass the save precondition once');
assert.equal(filledReasonCollections, 1, 'a filled reason must be collected exactly once');
assert.equal(filledReasonRequests, 1, 'a filled reason must issue exactly one execute_button request');
assert.equal(
  (capturedRejectRequest as { action_params?: Record<string, unknown> } | null)?.action_params?.reason,
  '依据不足',
  'the declared reason must be carried by the same execute_button request as its action identity',
);

assert.deepEqual(
  resolveNativeContractActionState(approve, true),
  { disabled: true, title: '' },
  'a busy form must disable the decision control',
);

const staleActions = buildContractFormActions({
  model: 'payment.request',
  recordId: 41,
  renderProfile: 'readonly',
  sceneReadyActions: [],
  v2ButtonStatus: {
    ...statuses,
    approve: { ...statuses.approve, visible: false },
    reject: { ...statuses.reject, visible: false },
  },
  v2ActionRuleList: [approveRow, rejectRow],
});
assert.deepEqual(
  staleActions,
  [],
  'a completed or no-longer-authorized task must remove both decision controls',
);

console.log('[approval_contract_closure_test] PASS cases=12');
