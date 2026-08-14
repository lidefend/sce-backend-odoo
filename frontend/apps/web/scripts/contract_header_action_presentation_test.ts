import assert from 'node:assert/strict';

import { buildContractFormActions } from '../src/pages/contractForm/contractActionPresentation';
import { decodeContractV2ActionRule } from '../src/app/contracts/v2/schema';
import { resolvePrimaryCreateFooterAction } from '../src/pages/contractForm/actionContract';
import { groupContractHeaderActions } from '../src/pages/contractForm/contractHeaderActionPresentation';
import { presentContractHeaderActions } from '../src/pages/contractForm/headerActionPresentation';
import { usePrimaryFormActionRuntime } from '../src/pages/contractForm/usePrimaryFormActionRuntime';

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

const rule = (key: string, sourceWidgetId: string, targetScope: string, overrides: Record<string, unknown> = {}) => ({
  actionKey: key,
  label: key,
  triggerType: 'click',
  sourceWidgetId,
  targetScope,
  button: { name: `action_${key}`, type: 'object' },
  presentation: { tier: 'primary' },
  ...overrides,
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
    rule('root-body', 'page.root', 'body'),
    rule('root-widget', 'page.root', 'widget'),
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

assert.deepEqual(built.map((item) => item.key), ['normalized-root', 'root-header-url', 'root-page-submit', 'second-primary']);
assert.deepEqual(grouped.direct.map((item) => item.key), ['normalized-root', 'native-header']);
assert.deepEqual(grouped.overflow.map((item) => item.key), ['root-header-url', 'root-page-submit', 'second-primary']);
const presented = presentContractHeaderActions({ direct: grouped.direct, overflow: grouped.overflow, excludedKeys: new Set() });
assert.deepEqual(presented.direct.map((item) => item.key), ['normalized-root']);
assert.equal([...presented.direct, ...presented.overflow]
  .filter((item) => item.presentationTier === 'primary' || item.semantic === 'primary_action').length, 1);

const configurationDoesNotClaimPrimary = groupContractHeaderActions({
  actions: [
    action({ key: 'config-primary', label: '设置', presentationTier: 'primary', semantic: 'primary_action' }),
    action({ key: 'business-primary', presentationTier: 'primary', semantic: 'primary_action' }),
  ],
  intakeMode: false,
  nativeTree: true,
  configurationMode: false,
  isSubmitAction: () => false,
});
assert.equal(configurationDoesNotClaimPrimary.direct[0]?.key, 'business-primary');
assert.equal(configurationDoesNotClaimPrimary.configuration[0]?.presentationTier, 'overflow');

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

const decodedDeniedRule = decodeContractV2ActionRule({
  ...rule('decoded-denied-submit', 'page.root', 'page'),
  actionId: 'action.decoded-denied-submit',
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

console.log('[contract_header_action_presentation_test] PASS real_builder_chain=1 root_header_page_object_url=4 body_widget_row_hidden=3 primary=1 config_primary=0 denied_io=0');
