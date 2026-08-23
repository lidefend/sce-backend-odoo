import assert from 'node:assert/strict';
import { ref } from 'vue';
import { resolveCreateDefaults, resolveCreateRouteRelationLabels } from '../src/pages/contractForm/createDefaults';
import { applyIncomingFormFieldValue } from '../src/pages/contractForm/recordHydration';
import { buildSaveRecordPayload } from '../src/pages/contractForm/saveRecordHelpers';
import { usePrimaryFormActionRuntime } from '../src/pages/contractForm/usePrimaryFormActionRuntime';

const fieldDescriptors = {
  amount: { name: 'amount', type: 'float' },
  owner_id: { name: 'owner_id', type: 'many2one' },
  title: { name: 'title', type: 'char' },
};
const v2ContractStore = {
  snapshot: {
    pageInfo: { contractVersion: '2.2.0', pageId: 'x.document.create', clientType: 'web' },
    layoutContract: { containerTree: [] },
    actionContract: { actionRuleList: [] },
    dataContract: {
      mainData: { amount: 0, owner_id: false, title: '' },
      dataMeta: { sourceContext: { context: {} } },
    },
  },
  widgetsByFieldCodeAll: new Map(Object.entries(fieldDescriptors).map(([name, descriptor]) => [name, [{
    widgetId: `field.${name}`,
    widgetType: descriptor.type,
    fieldCode: name,
    label: name,
    span: 6,
    componentKey: 'sc.input.text',
    capabilities: [],
    componentConfig: {},
    fieldDescriptor: descriptor,
  }]])),
} as never;
const query = {
  default_owner_id: '17',
  default_owner_id_label: 'Owner A',
  default_title: 'Draft A',
};
const defaults = resolveCreateDefaults({ routeQuery: query, v2ContractStore });
const formData: Record<string, unknown> = {};
const relationOptions: Record<string, Array<{ id: number; label: string }>> = {};
const relationKeywords: Record<string, string> = {};
const upsertRelationOption = (name: string, option: { id: number; label: string } | null) => {
  if (!option) return;
  relationOptions[name] = [option];
};
for (const name of Object.keys(fieldDescriptors)) {
  applyIncomingFormFieldValue({
    fieldName: name,
    descriptor: fieldDescriptors[name as keyof typeof fieldDescriptors] as never,
    incoming: name in defaults ? defaults[name] : '',
    target: { formData, relationOptions, relationKeywords, upsertRelationOption, initOne2manyRows: () => undefined },
  });
}
for (const [name, label] of Object.entries(resolveCreateRouteRelationLabels(v2ContractStore, query, defaults))) {
  const id = Number(formData[name] || 0);
  upsertRelationOption(name, { id, label });
  relationKeywords[name] = label;
}
assert.deepEqual(formData, { amount: 0, owner_id: 17, title: 'Draft A' });
assert.equal(relationKeywords.owner_id, 'Owner A');

formData.amount = 80;
const payload = buildSaveRecordPayload({
  comparableFieldValue: (_name, value) => value,
  formFields: fieldDescriptors as never,
  dirtyFieldSet: new Set(['amount']),
  editableMap: { ...formData },
  formData,
  originalValues: {},
  recordId: null,
});
assert.deepEqual(payload, { amount: 80, owner_id: 17, title: 'Draft A' });

const events: string[] = [];
const stored: Record<string, unknown> = { ...payload, id: 501, state: 'draft' };
events.push('save-draft');
const recordId = ref(501);
const action = {
  key: 'submit', label: 'Submit', kind: 'object', level: 'header', selection: 'single',
  authorityActionId: 'action.submit', backendIdentity: 'button:object:action_submit',
  actionId: null, methodName: 'action_submit', targetModel: 'x.document', context: {},
  domainRaw: '', target: '', url: '', enabled: true, hint: '', intent: '', semantic: 'primary_action',
  sourceWidgetId: 'page.root', clientMode: '', visibleProfiles: ['edit'], requiredParams: [],
  requiresReason: false, authorizationAllowed: true, requiresSavedRecord: false,
} as never;

const reopened: Record<string, unknown> = {};
for (const name of Object.keys(fieldDescriptors)) {
  const incoming = name === 'owner_id' ? [stored.owner_id, 'Owner A'] : stored[name];
  applyIncomingFormFieldValue({
    fieldName: name,
    descriptor: fieldDescriptors[name as keyof typeof fieldDescriptors] as never,
    incoming,
    target: { formData: reopened, relationOptions, relationKeywords, upsertRelationOption, initOne2manyRows: () => undefined },
  });
}
events.push('reopen-draft');
assert.deepEqual(reopened, { amount: 80, owner_id: 17, title: 'Draft A' });
assert.equal(relationKeywords.owner_id, 'Owner A');

reopened.title = 'Draft A revised';
const editPayload = buildSaveRecordPayload({
  comparableFieldValue: (_name, value) => value,
  formFields: fieldDescriptors as never,
  dirtyFieldSet: new Set(['title']),
  editableMap: { ...reopened },
  formData: reopened,
  originalValues: { amount: 80, owner_id: 17, title: 'Draft A' },
  recordId: 501,
});
assert.deepEqual(editPayload, { title: 'Draft A revised' });

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
    assert.deepEqual(request.button, {
      name: 'action_submit',
      type: 'object',
      action_id: 'action.submit',
      backend_identity: 'button:object:action_submit',
      source_widget_id: 'page.root',
      server_action_id: undefined,
      xml_id: undefined,
    });
    stored.state = 'submit';
    return { result: null } as never;
  },
  hasChanges: () => true,
  modelName: () => 'x.document',
  navigateActionResponseResult: async () => false,
  primaryCreateFooterAction: () => null,
  primarySubmitAction: () => action,
  recordId,
  reload: async () => { events.push('reopen'); },
  routeMenuId: () => 41,
  saveRecord: async (_refreshPolicy, options) => {
    events.push('save-edit');
    assert.equal(options, undefined);
    Object.assign(stored, editPayload);
    return true;
  },
  status: ref('idle'),
  submissionFeedback: ref({ kind: 'idle', message: '' }),
  validationErrors: ref([]),
} as never);
await runtime.runPrimaryFormAction();
assert.deepEqual(events, ['save-draft', 'reopen-draft', 'save-edit', 'confirm', 'submit', 'refresh', 'reopen']);
assert.deepEqual(stored, { amount: 80, owner_id: 17, title: 'Draft A revised', id: 501, state: 'submit' });

console.log('[create-record-user-journey] PASS checkpoints=defaults,save,reopen,edit,submit,refresh');
