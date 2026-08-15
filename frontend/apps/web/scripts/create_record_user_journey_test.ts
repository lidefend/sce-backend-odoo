import assert from 'node:assert/strict';
import { ref } from 'vue';
import { resolveCreateDefaults, resolveCreateRouteRelationLabels } from '../src/pages/contractForm/createDefaults';
import { applyIncomingFormFieldValue } from '../src/pages/contractForm/recordHydration';
import { buildSaveRecordPayload } from '../src/pages/contractForm/saveRecordHelpers';
import { usePrimaryFormActionRuntime } from '../src/pages/contractForm/usePrimaryFormActionRuntime';

const contract = {
  fields: {
    amount: { type: 'float' },
    owner_id: { type: 'many2one' },
    title: { type: 'char' },
  },
  __unified_page_contract_v2: {
    pageInfo: { contractVersion: '2.2.0', pageId: 'x.document.create', clientType: 'web' },
    layoutContract: { containerTree: [] },
    actionContract: { actionRuleList: [] },
    dataContract: {
      mainData: { amount: 0, owner_id: false, title: '' },
      dataMeta: { sourceContext: { context: {} } },
    },
  },
} as never;
const query = {
  default_owner_id: '17',
  default_owner_id_label: 'Owner A',
  default_title: 'Draft A',
};
const defaults = resolveCreateDefaults({ contract, routeQuery: query, v2ContractStore: null });
const formData: Record<string, unknown> = {};
const relationOptions: Record<string, Array<{ id: number; label: string }>> = {};
const relationKeywords: Record<string, string> = {};
const upsertRelationOption = (name: string, option: { id: number; label: string } | null) => {
  if (!option) return;
  relationOptions[name] = [option];
};
for (const name of Object.keys(contract.fields)) {
  applyIncomingFormFieldValue({
    fieldName: name,
    descriptor: contract.fields[name as keyof typeof contract.fields] as never,
    incoming: name in defaults ? defaults[name] : '',
    target: { formData, relationOptions, relationKeywords, upsertRelationOption, initOne2manyRows: () => undefined },
  });
}
for (const [name, label] of Object.entries(resolveCreateRouteRelationLabels(contract, query, defaults))) {
  const id = Number(formData[name] || 0);
  upsertRelationOption(name, { id, label });
  relationKeywords[name] = label;
}
assert.deepEqual(formData, { amount: 0, owner_id: 17, title: 'Draft A' });
assert.equal(relationKeywords.owner_id, 'Owner A');

formData.amount = 80;
const payload = buildSaveRecordPayload({
  comparableFieldValue: (_name, value) => value,
  contract,
  dirtyFieldSet: new Set(['amount']),
  editableMap: { ...formData },
  formData,
  originalValues: {},
  recordId: null,
});
assert.deepEqual(payload, { amount: 80, owner_id: 17, title: 'Draft A' });

const events: string[] = [];
const stored: Record<string, unknown> = {};
const recordId = ref(0);
const action = {
  key: 'submit', label: 'Submit', kind: 'object', level: 'header', selection: 'single',
  actionId: null, methodName: 'action_submit', targetModel: 'x.document', context: {},
  domainRaw: '', target: '', url: '', enabled: true, hint: '', intent: '', semantic: 'primary_action',
  sourceWidgetId: 'page.root', clientMode: '', visibleProfiles: ['create'], requiredParams: [],
  requiresReason: false, authorizationAllowed: true, requiresSavedRecord: true,
} as never;
const runtime = usePrimaryFormActionRuntime({
  actionId: () => 31,
  applyProjectionRefreshPolicy: async () => { events.push('refresh'); },
  busyKind: ref(null),
  confirmActionSafety: async () => { events.push('confirm'); return true; },
  errorMessage: ref(''),
  executeButtonRequest: async (request) => {
    events.push('submit');
    assert.equal(request.model, 'x.document');
    assert.equal(request.res_id, 501);
    assert.deepEqual(request.button, { name: 'action_submit', type: 'object' });
    stored.state = 'submit';
    return { result: null } as never;
  },
  hasChanges: () => true,
  modelName: () => 'x.document',
  navigateActionResponseResult: async () => false,
  primaryCreateFooterAction: () => action,
  primarySubmitAction: () => null,
  recordId,
  reload: async () => { events.push('reopen'); },
  routeMenuId: () => 41,
  saveRecord: async (_refreshPolicy, options) => {
    events.push('save');
    assert.equal(options?.navigateAfterCreate, false);
    Object.assign(stored, payload, { id: 501, state: 'draft' });
    recordId.value = 501;
    return 501;
  },
  status: ref('idle'),
  submissionFeedback: ref({ kind: 'idle', message: '' }),
  validationErrors: ref([]),
} as never);
await runtime.runPrimaryFormAction();
assert.deepEqual(events, ['save', 'confirm', 'submit', 'refresh', 'reopen']);
assert.deepEqual(stored, { amount: 80, owner_id: 17, title: 'Draft A', id: 501, state: 'submit' });

const reopened: Record<string, unknown> = {};
for (const name of Object.keys(contract.fields)) {
  const incoming = name === 'owner_id' ? [stored.owner_id, 'Owner A'] : stored[name];
  applyIncomingFormFieldValue({
    fieldName: name,
    descriptor: contract.fields[name as keyof typeof contract.fields] as never,
    incoming,
    target: { formData: reopened, relationOptions, relationKeywords, upsertRelationOption, initOne2manyRows: () => undefined },
  });
}
assert.deepEqual(reopened, { amount: 80, owner_id: 17, title: 'Draft A' });
assert.equal(relationKeywords.owner_id, 'Owner A');

console.log('[create-record-user-journey] PASS checkpoints=defaults,edit,save,submit,reopen');
