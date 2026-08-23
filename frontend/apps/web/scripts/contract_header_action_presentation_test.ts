import assert from 'node:assert/strict';

import { buildContractFormActions } from '../src/pages/contractForm/contractActionPresentation';
import { decodeContractV2ActionRule, decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import { resolvePrimaryCreateFooterAction } from '../src/pages/contractForm/actionContract';
import { groupContractHeaderActions, resolvePrimaryBusinessActionState } from '../src/pages/contractForm/contractHeaderActionPresentation';
import { presentContractHeaderActions } from '../src/pages/contractForm/headerActionPresentation';
import { usePrimaryFormActionRuntime } from '../src/pages/contractForm/usePrimaryFormActionRuntime';
import { useFormActionRuntime } from '../src/pages/contractForm/useFormActionRuntime';
import {
  evaluateNativeModifierValue,
  resolveNativeModifierFieldValue,
  resolveNativeOccurrenceBehavior,
  resolveNativeRelationActiveActions,
} from '../src/pages/contractForm/nativeLayoutUtils';

const action = (overrides: Record<string, unknown>) => ({
  key: 'action',
  label: 'Action',
  sourceWidgetId: 'page.header',
  level: 'header',
  mutation: true,
  enabled: true,
  presentationTier: 'secondary',
  ...overrides,
}) as never;

const activeRelationVisibility = {
  kind: 'any',
  exprs: [
    { kind: 'field_compare', field: 'type', operator: '!=', value: 'pay' },
    { kind: 'field_compare', field: 'state', operator: '!=', value: 'approved' },
    { kind: 'not', expr: { kind: 'field_truthy', field: 'has_active_relation' } },
  ],
};
const modifierMainData = { has_active_relation: true };
const modifierFormData = { type: 'pay', state: 'approved' };
assert.equal(evaluateNativeModifierValue(
  activeRelationVisibility,
  (field) => resolveNativeModifierFieldValue(modifierFormData, modifierMainData, field),
), false, 'normalized mainData supplies hidden modifier dependencies omitted from form hydration');
assert.equal(evaluateNativeModifierValue(
  activeRelationVisibility,
  (field) => resolveNativeModifierFieldValue({ ...modifierFormData, has_active_relation: false }, modifierMainData, field),
), true, 'hydrated formData remains authoritative when it contains the dependency');

const evaluateDraftModifier = (value: unknown) => evaluateNativeModifierValue(
  value,
  (field) => resolveNativeModifierFieldValue({ state: 'draft' }, {}, field),
);
assert.deepEqual(resolveNativeOccurrenceBehavior({
  type: 'field', name: 'amount', modifiers: {
    invisible: false,
    readonly: { kind: 'field_compare', field: 'state', operator: '=', value: 'draft' },
    required: true,
  },
}, evaluateDraftModifier), {
  invisible: false,
  readonly: true,
  required: true,
}, 'first same-name occurrence evaluates its own dynamic behavior');
assert.deepEqual(resolveNativeOccurrenceBehavior({
  type: 'field', name: 'amount', modifiers: {
    invisible: { kind: 'field_compare', field: 'state', operator: '=', value: 'done' },
    readonly: false,
    required: false,
  },
}, evaluateDraftModifier), {
  invisible: false,
  readonly: false,
  required: false,
}, 'second same-name occurrence remains independent from the first occurrence');
assert.equal(resolveNativeOccurrenceBehavior({
  type: 'field', name: 'amount', modifiers: {
    invisible: { kind: 'field_compare', field: 'state', operator: '=', value: 'done' },
  },
}, (value) => evaluateNativeModifierValue(value, (field) => field === 'state' ? 'done' : undefined)).invisible, true,
'the occurrence responds to record context changes');
assert.deepEqual(resolveNativeRelationActiveActions({
  type: 'field',
  name: 'partner_id',
  relation_active_actions: { create: false, write: true },
}, evaluateDraftModifier), {
  create: false,
  write: true,
}, 'many2one relation actions remain separate from field readonly behavior');
assert.deepEqual(resolveNativeRelationActiveActions({
  type: 'field',
  name: 'reference',
  attributes: { can_create: '0' },
}, evaluateDraftModifier), {
  create: null,
  write: null,
}, 'raw unsupported attributes never become relation action verdicts');

const rule = (key: string, sourceWidgetId: string, targetScope: string, overrides: Record<string, unknown> = {}) => ({
  actionId: `action.${key}`,
  actionKey: key,
  backendIdentity: `button:object:action_${key}`,
  label: key,
  triggerType: 'click',
  sourceWidgetId,
  targetScope,
  button: { name: `action_${key}`, type: 'object' },
  presentation: { tier: 'primary' },
  allowed: true,
  enabled: true,
  disabled: false,
  entitlementEvaluated: true,
  ...overrides,
});

const decodeSnapshotWithActions = (actionRuleList: Array<Record<string, unknown>>) => decodeContractV2Snapshot({
  pageInfo: {
    pageId: 'x.document.form', sceneKey: 'x.document.form', pageName: 'Document', model: 'x.document',
    viewType: 'form', layoutType: 'form', renderMode: 'governed', contractVersion: '2.2.0', clientType: 'web_pc',
  },
  layoutContract: {
    pageId: 'x.document.form', layoutType: 'form', adaptMode: 'pc', containerTree: [], layoutHints: {}, componentRegistry: {},
  },
  statusContract: { globalStatus: { pageVisible: true }, widgetStatus: [], buttonStatus: [], containerStatus: [], selectorStatus: [] },
  actionContract: { actionRuleList, dependencyGraph: {} },
  dataContract: { mainData: {}, tableRows: {}, relationRows: {}, dictData: {}, pagination: {}, dataSource: {}, dataMeta: {} },
  runtimeContract: { patchStrategy: 'incremental', cachePolicy: 'etag', optimistic: false, lazyContainer: [], virtualization: {}, retryPolicy: {} },
  meta: {
    etag: 'upc-v2-sha256-test', snapshotId: 'snapshot.upc.v2.test', traceId: 'trace.test', requestId: 'request.test', sourceType: 'ui.contract',
    lifecycle: {
      lifecycleVersion: '1.0.0', stage: 'runtime_delivery',
      definition: { schemaId: 'smart_core.unified_page_contract_v2', schemaVersion: '2.2.0', schemaSha256: 'test', contractVersion: '2.2.0', normativeStatus: 'stable' },
      generation: { generator: 'test', generatorVersion: '2.2.0', sourceType: 'ui.contract', sourceSha256: 'test' },
      runtime: { requestId: 'request.test', traceId: 'trace.test', clientType: 'web_pc', traceSource: 'request_context' },
      integrity: { algorithm: 'sha256', contractSha256: 'test' }, authority: {},
    },
  },
});

const built = buildContractFormActions({
  contract: null,
  model: 'res.partner',
  recordId: 7,
  renderProfile: 'readonly',
  sceneReadyActions: [],
  v2ButtonStatus: {},
  workflowActionRows: [],
  v2ActionRuleList: [
    rule('normalized-root', 'page.root', 'header'),
    rule('second-primary', 'page.root', 'header'),
    rule('root-header-url', 'page.root', 'header', { button: {}, target: { url: '/integration/status' } }),
    rule('root-page-submit', 'page.root', 'page'),
    rule('root-body', 'page.root', 'body', {
      backendIdentity: 'native_button:object:action_root_body:/form/sheet/button[1]:0',
      nativeIdentity: { canonical_region: 'layout' },
    }),
    rule('root-widget', 'page.root', 'widget', {
      nativeIdentity: { canonical_region: 'stat_buttons' },
    }),
    rule('row-action', 'page.row', 'row'),
  ],
  policyContext: {} as never,
  evaluateNativeActionVisibility: () => true,
  isTierValidationActionHidden: () => false,
});

const grouped = groupContractHeaderActions({
  actions: [action({ key: 'native-header', sourceWidgetId: 'page.header' }), ...built],
  intakeMode: false,
  nativeTree: true,
  configurationMode: false,
  isSubmitAction: () => false,
});

const readonlyPrimary = action({ key: 'readonly-submit', methodName: 'action_submit', presentationTier: 'primary' });
assert.deepEqual(resolvePrimaryBusinessActionState({
  busy: false, canSave: false, configurationMode: false, hasChanges: false, hasRecord: true,
  intakeMode: false, primaryCreateAction: null, primarySubmitAction: readonlyPrimary,
  quickSubmitDisabled: true,
}), { show: true, disabled: false });
assert.deepEqual(resolvePrimaryBusinessActionState({
  busy: false, canSave: false, configurationMode: false, hasChanges: false, hasRecord: true,
  intakeMode: false, primaryCreateAction: null, primarySubmitAction: { ...readonlyPrimary, enabled: false },
  quickSubmitDisabled: true,
}), { show: true, disabled: true });
assert.deepEqual(resolvePrimaryBusinessActionState({
  busy: false, canSave: false, configurationMode: false, hasChanges: false, hasRecord: true,
  intakeMode: false, primaryCreateAction: null, primarySubmitAction: null,
  quickSubmitDisabled: true,
}), { show: false, disabled: true });
assert.deepEqual(resolvePrimaryBusinessActionState({
  busy: false, canSave: true, configurationMode: false, hasChanges: true, hasRecord: true,
  intakeMode: false, primaryCreateAction: null, primarySubmitAction: readonlyPrimary,
  quickSubmitDisabled: false,
}), { show: true, disabled: true });

assert.deepEqual(built.map((item) => item.key), [
  'root-body', 'row-action', 'normalized-root', 'root-header-url',
  'root-page-submit', 'second-primary', 'root-widget',
]);
assert.equal(built.find((item) => item.key === 'root-body')?.level, 'body');
assert.equal(
  built.find((item) => item.key === 'root-body')?.backendIdentity,
  'native_button:object:action_root_body:/form/sheet/button[1]:0',
);
assert.equal(built.find((item) => item.key === 'root-widget')?.level, 'smart');
assert.equal(built.find((item) => item.key === 'row-action')?.level, 'body');
assert.deepEqual(grouped.direct.map((item) => item.key), ['normalized-root', 'native-header']);
assert.deepEqual(grouped.overflow.map((item) => item.key), ['root-header-url', 'root-page-submit', 'second-primary']);
const presented = presentContractHeaderActions({ direct: grouped.direct, overflow: grouped.overflow, excludedKeys: new Set() });
assert.deepEqual(presented.direct.map((item) => item.key), ['normalized-root']);
assert.equal([...presented.direct, ...presented.overflow]
  .filter((item) => item.presentationTier === 'primary' || item.semantic === 'primary_action').length, 1);

const configurationDoesNotClaimPrimary = groupContractHeaderActions({
  actions: [
    action({ key: 'local-mode', label: '字段管理', intent: 'ui.local_mode', enabled: false, presentationTier: 'primary', semantic: 'primary_action' }),
    action({ key: 'business-primary', label: '设置付款条件', intent: 'execute_button', presentationTier: 'primary', semantic: 'primary_action' }),
  ],
  intakeMode: false,
  nativeTree: true,
  configurationMode: false,
  isSubmitAction: () => false,
});
assert.equal(configurationDoesNotClaimPrimary.direct[0]?.key, 'business-primary');
assert.equal(configurationDoesNotClaimPrimary.configuration[0]?.presentationTier, 'overflow');
assert.equal(configurationDoesNotClaimPrimary.configuration[0]?.enabled, false);
let disabledConfigurationIo = 0;
const disabledConfigurationRuntime = useFormActionRuntime({
  confirmActionSafety: async () => { disabledConfigurationIo += 1; return true; },
  applyClientMode: () => { disabledConfigurationIo += 1; },
} as never);
await disabledConfigurationRuntime.runAction(configurationDoesNotClaimPrimary.configuration[0] as never);
assert.equal(disabledConfigurationIo, 0);

const normalizedWinner = buildContractFormActions({
  contract: null,
  model: 'res.partner',
  recordId: 7,
  renderProfile: 'readonly',
  sceneReadyActions: [action({ key: 'same-action', label: 'scene loser', intent: 'execute_button' })],
  v2ButtonStatus: {},
  workflowActionRows: [{
    key: 'same-action', label: 'native loser', kind: 'object', level: 'header',
    payload: { method: 'action_same' }, allowed: false,
  }],
  v2ActionRuleList: [rule('same-action', 'page.root', 'page', {
    label: 'Normalized winner',
    backendIdentity: 'button:object:action_same',
    visibleProfiles: ['readonly'],
    actionSafety: {
      classification: 'danger', requiresConfirm: true,
      confirmMessage: 'Confirm normalized action', reasonCode: 'DANGER_ACTION',
    },
    allowed: true,
    enabled: false,
  })],
  policyContext: {} as never,
  evaluateNativeActionVisibility: () => true,
  isTierValidationActionHidden: () => false,
});
assert.equal(normalizedWinner.length, 1);
assert.equal(normalizedWinner[0]?.label, 'Normalized winner');
assert.equal(normalizedWinner[0]?.backendIdentity, 'button:object:action_same');
assert.equal(normalizedWinner[0]?.enabled, false);
assert.equal(normalizedWinner[0]?.authorizationAllowed, false);
assert.deepEqual(normalizedWinner[0]?.visibleProfiles, ['readonly']);
assert.deepEqual(normalizedWinner[0]?.actionSafety, {
  classification: 'danger', requiresConfirm: true,
  confirmMessage: 'Confirm normalized action', reasonCode: 'DANGER_ACTION',
});

const rejectedLegacyFallback = buildContractFormActions({
  contract: null,
  model: 'res.partner',
  recordId: 7,
  renderProfile: 'edit',
  sceneReadyActions: [],
  v2ButtonStatus: {},
  workflowActionRows: [{ key: 'legacy-only', label: 'Legacy only', kind: 'object', level: 'header' }],
  policyContext: {} as never,
  evaluateNativeActionVisibility: () => true,
  isTierValidationActionHidden: () => false,
});
assert.equal(rejectedLegacyFallback.length, 0, 'V2 form action presentation must reject legacy-only action rows');

const normalizedRecordHandoff = buildContractFormActions({
  contract: null,
  model: 'x.document',
  recordId: 81,
  renderProfile: 'readonly',
  sceneReadyActions: [],
  v2ButtonStatus: {},
  workflowActionRows: [],
  v2ActionRuleList: [rule('open_followup', 'page.header', 'header', {
    label: 'Open follow-up',
    button: {},
    target: { url: '/f/x.followup/new', target: 'self' },
    visibleProfiles: ['readonly'],
    presentation: { tier: 'secondary' },
    allowed: true,
    enabled: true,
  })],
  policyContext: {} as never,
  evaluateNativeActionVisibility: () => true,
  isTierValidationActionHidden: () => false,
});
assert.equal(normalizedRecordHandoff.length, 1);
assert.equal(normalizedRecordHandoff[0]?.label, 'Open follow-up');
assert.equal(normalizedRecordHandoff[0]?.url, '/f/x.followup/new');
assert.equal(normalizedRecordHandoff[0]?.enabled, true);
assert.deepEqual(normalizedRecordHandoff[0]?.visibleProfiles, ['readonly']);

const decodedRuntimeOpenSnapshot = decodeSnapshotWithActions([{
  ...rule('open-runtime-followup', 'page.header', 'page', {
    button: {},
    target: { url: '/f/x.followup/new', target: 'self' },
    presentation: { tier: 'secondary' },
    allowed: true,
    enabled: true,
  }),
  actionId: 'action.open-runtime-followup',
  targetIds: [],
  dispatchMode: 'server',
  refreshMode: 'partial',
}]);
const decodedRuntimeOpenActions = buildContractFormActions({
  contract: null,
  model: 'x.document',
  recordId: 7,
  renderProfile: 'readonly',
  sceneReadyActions: [],
  v2ButtonStatus: {},
  workflowActionRows: [],
  v2ActionRuleList: decodedRuntimeOpenSnapshot.actionContract.actionRuleList as unknown as Array<Record<string, unknown>>,
  policyContext: {} as never,
  evaluateNativeActionVisibility: () => true,
  isTierValidationActionHidden: () => false,
});
assert.equal(decodedRuntimeOpenActions[0]?.kind, 'open');
assert.equal(decodedRuntimeOpenActions[0]?.url, '/f/x.followup/new');
const explicitEmptyNormalizedAuthority = buildContractFormActions({
  contract: null,
  model: 'res.partner',
  recordId: 7,
  renderProfile: 'edit',
  sceneReadyActions: [],
  v2ButtonStatus: {},
  workflowActionRows: [{ key: 'must-not-leak', label: 'Must not leak', kind: 'object', level: 'header' }],
  v2ActionRuleList: [],
  policyContext: {} as never,
  evaluateNativeActionVisibility: () => true,
  isTierValidationActionHidden: () => false,
});
assert.deepEqual(explicitEmptyNormalizedAuthority, []);

const sceneCannotCreateAuthority = buildContractFormActions({
  model: 'res.partner', recordId: 7, renderProfile: 'readonly',
  sceneReadyActions: [{
    key: 'scene-only', actionId: 'action.scene-only', backendIdentity: 'button:object:action_scene_only',
    sourceWidgetId: 'page.header', allowed: true, enabled: true, disabled: false, entitlementEvaluated: true,
    target: { method: 'action_scene_only' },
  }],
  v2ButtonStatus: {}, v2ActionRuleList: [],
  evaluateNativeActionVisibility: () => true, isTierValidationActionHidden: () => false,
});
assert.deepEqual(sceneCannotCreateAuthority, [], 'Scene presentation rows cannot create executable authority');

for (const missingKey of ['actionId', 'backendIdentity', 'sourceWidgetId', 'allowed', 'enabled', 'disabled', 'entitlementEvaluated']) {
  const missing = rule(`missing-${missingKey}`, 'page.header', 'page');
  delete missing[missingKey as keyof typeof missing];
  const rejected = buildContractFormActions({
    model: 'res.partner', recordId: 7, renderProfile: 'readonly', sceneReadyActions: [],
    v2ButtonStatus: {}, v2ActionRuleList: [missing],
    evaluateNativeActionVisibility: () => true, isTierValidationActionHidden: () => false,
  });
  assert.deepEqual(rejected, [], `missing ${missingKey} must fail closed`);
}

const duplicateIdentityRejected = buildContractFormActions({
  model: 'res.partner', recordId: 7, renderProfile: 'readonly', sceneReadyActions: [], v2ButtonStatus: {},
  v2ActionRuleList: [
    rule('duplicate-one', 'page.header', 'page', { backendIdentity: 'button:object:duplicate' }),
    rule('duplicate-two', 'page.header', 'page', { backendIdentity: 'button:object:duplicate' }),
  ],
  evaluateNativeActionVisibility: () => true, isTierValidationActionHidden: () => false,
});
assert.deepEqual(duplicateIdentityRejected, [], 'ambiguous backend identity must fail closed');

const statusIdentityMismatchRejected = buildContractFormActions({
  model: 'res.partner', recordId: 7, renderProfile: 'readonly', sceneReadyActions: [],
  v2ButtonStatus: {
    'btn.status-mismatch': {
      btnId: 'btn.status-mismatch', backendIdentity: 'button:object:another_action', visible: true, disabled: false,
    },
  },
  v2ActionRuleList: [rule('status-mismatch', 'page.header', 'page')],
  evaluateNativeActionVisibility: () => true, isTierValidationActionHidden: () => false,
});
assert.deepEqual(statusIdentityMismatchRejected, [], 'status identity mismatch must fail closed');

const deniedBuilt = buildContractFormActions({
  contract: null,
  model: 'res.partner',
  recordId: 0,
  renderProfile: 'create',
  sceneReadyActions: [],
  v2ButtonStatus: { 'btn.denied-page-submit': { visible: true, disabled: true, reasonCode: 'DENIED' } },
  workflowActionRows: [],
  v2ActionRuleList: [rule('denied-page-submit', 'page.root', 'page')],
  policyContext: {} as never,
  evaluateNativeActionVisibility: () => true,
  isTierValidationActionHidden: () => false,
});
assert.equal(deniedBuilt.length, 1);
assert.equal(deniedBuilt[0]?.enabled, false);
assert.equal(deniedBuilt[0]?.authorizationAllowed, false);
assert.equal(deniedBuilt[0]?.requiresSavedRecord, true);
assert.equal(resolvePrimaryCreateFooterAction({
  actions: deniedBuilt,
}), null);
assert.equal(resolvePrimaryCreateFooterAction({ actions: [] }), null);
const deniedCreatePresentation = groupContractHeaderActions({
  actions: deniedBuilt,
  intakeMode: false,
  nativeTree: true,
  configurationMode: false,
  isSubmitAction: () => true,
});
assert.equal(deniedCreatePresentation.direct[0]?.key, 'denied-page-submit');
assert.equal(deniedCreatePresentation.direct[0]?.enabled, false);

const decodedDeniedRule = decodeContractV2ActionRule({
  ...rule('decoded-denied-submit', 'page.root', 'page'),
  actionId: 'action.decoded-denied-submit',
  backendIdentity: 'button:object:action_decoded_denied_submit',
  targetIds: [],
  dispatchMode: 'server',
  refreshMode: 'partial',
  allowed: false,
  enabled: false,
  disabled: true,
});
assert.equal(decodedDeniedRule.allowed, false);
assert.equal(decodedDeniedRule.enabled, false);
assert.equal(decodedDeniedRule.disabled, true);
assert.equal(decodedDeniedRule.backendIdentity, 'button:object:action_decoded_denied_submit');
const decodedDeniedBuilt = buildContractFormActions({
  contract: null,
  model: 'res.partner',
  recordId: 0,
  renderProfile: 'create',
  sceneReadyActions: [],
  v2ButtonStatus: {},
  workflowActionRows: [],
  v2ActionRuleList: [decodedDeniedRule as unknown as Record<string, unknown>],
  policyContext: {} as never,
  evaluateNativeActionVisibility: () => true,
  isTierValidationActionHidden: () => false,
});
assert.equal(decodedDeniedBuilt[0]?.enabled, false);
const deniedExistingBuilt = buildContractFormActions({
  contract: null,
  model: 'res.partner',
  recordId: 7,
  renderProfile: 'edit',
  sceneReadyActions: [],
  v2ButtonStatus: { 'btn.denied-existing-submit': { visible: true, disabled: true, reasonCode: 'DENIED_EXISTING' } },
  workflowActionRows: [],
  v2ActionRuleList: [rule('denied-existing-submit', 'page.root', 'page')],
  policyContext: {} as never,
  evaluateNativeActionVisibility: () => true,
  isTierValidationActionHidden: () => false,
});
const deniedExistingPresentation = groupContractHeaderActions({
  actions: deniedExistingBuilt,
  intakeMode: false,
  nativeTree: true,
  configurationMode: false,
  isSubmitAction: () => true,
});
assert.equal(deniedExistingPresentation.direct[0]?.key, 'denied-existing-submit');
assert.equal(deniedExistingPresentation.direct[0]?.enabled, false);

const allowedCreateBuilt = buildContractFormActions({
  contract: null,
  model: 'res.partner',
  recordId: 0,
  renderProfile: 'create',
  sceneReadyActions: [],
  v2ButtonStatus: {},
  workflowActionRows: [],
  v2ActionRuleList: [rule('allowed-page-submit', 'page.root', 'page')],
  policyContext: {} as never,
  evaluateNativeActionVisibility: () => true,
  isTierValidationActionHidden: () => false,
});
assert.equal(allowedCreateBuilt[0]?.authorizationAllowed, true);
assert.equal(allowedCreateBuilt[0]?.requiresSavedRecord, true);
assert.equal(allowedCreateBuilt[0]?.enabled, false);
const allowedCreateAction = resolvePrimaryCreateFooterAction({ actions: allowedCreateBuilt });
assert.equal(allowedCreateAction?.enabled, true);
const submitPresentation = groupContractHeaderActions({
  actions: allowedCreateBuilt,
  intakeMode: false,
  nativeTree: true,
  configurationMode: false,
  isSubmitAction: () => true,
});
const submittedPrimaryPresentation = presentContractHeaderActions({
  direct: submitPresentation.direct,
  overflow: submitPresentation.overflow,
  excludedKeys: new Set([allowedCreateAction?.key || '']),
});
assert.deepEqual(submittedPrimaryPresentation, { direct: [], overflow: [] });

let saveCalls = 0;
let confirmCalls = 0;
const deniedRuntime = usePrimaryFormActionRuntime({
  primaryCreateFooterAction: () => action({ key: 'denied-runtime', enabled: false }),
  saveRecord: async () => { saveCalls += 1; return 9; },
  confirmActionSafety: async () => { confirmCalls += 1; return true; },
} as never);
await deniedRuntime.runPrimaryFormAction();
assert.equal(saveCalls, 0);
assert.equal(confirmCalls, 0);

const deniedExistingRuntime = usePrimaryFormActionRuntime({
  primaryCreateFooterAction: () => null,
  primarySubmitAction: () => action({ key: 'denied-existing', enabled: false }),
  hasChanges: () => true,
  saveRecord: async () => { saveCalls += 1; return 9; },
  confirmActionSafety: async () => { confirmCalls += 1; return true; },
} as never);
await deniedExistingRuntime.runPrimaryFormAction();
assert.equal(saveCalls, 0);
assert.equal(confirmCalls, 0);

const allowedCreateRuntime = usePrimaryFormActionRuntime({
  primaryCreateFooterAction: () => allowedCreateAction,
  saveRecord: async () => { saveCalls += 1; return 9; },
  confirmActionSafety: async () => { confirmCalls += 1; return false; },
  recordId: { value: 0 },
} as never);
await allowedCreateRuntime.runPrimaryFormAction();
assert.equal(saveCalls, 1);
assert.equal(confirmCalls, 1);

const intake = groupContractHeaderActions({
  actions: [action({ key: 'normalized-root', sourceWidgetId: 'page.root', level: 'header' })],
  intakeMode: true,
  nativeTree: true,
  configurationMode: false,
  isSubmitAction: () => false,
});
assert.deepEqual(intake, { direct: [], overflow: [], configuration: [] });

console.log('[contract_header_action_presentation_test] PASS real_builder_chain=1 normalized_authority=1 full_snapshot_decode=1 danger_decode=1 submit_true=1 native_fallback=1 root_header_page_object_url=4 body_widget_row_adapters=3 primary=1 config_primary=0 denied_io=0');
