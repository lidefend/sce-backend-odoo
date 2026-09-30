import { executeSceneMutation } from '../src/app/sceneMutationRuntime';
import assert from 'node:assert/strict';
import { reactive, ref } from 'vue';
import { resolveCreateDefaults, resolveCreateRouteRelationLabels } from '../src/pages/contractForm/createDefaults.ts';
import { applyIncomingFormFieldValue } from '../src/pages/contractForm/recordHydration.ts';
import { evaluateNativeModifierValue } from '../src/app/modifierEngine.ts';
import { buildSaveRecordPayload, createSingleFlightSave, validateBeforeSaveRecord } from '../src/pages/contractForm/saveRecordHelpers.ts';
import { usePrimaryFormActionRuntime } from '../src/pages/contractForm/usePrimaryFormActionRuntime.ts';
import { submissionRequirementErrors } from '../src/pages/contractForm/submissionRequirements';
import { nativeAttachmentRefreshDecision } from '../src/pages/contractForm/useNativeAttachmentRuntime';
import { sanitizeUiErrorMessage } from '../src/pages/contractForm/fieldUtils.ts';
import { useRecordFormState } from '../src/pages/contractForm/useRecordFormState.ts';
import { useRecordFormProgress } from '../src/pages/contractForm/useRecordFormProgress.ts';

// A relation control can emit an unchanged value during hydration. Saving an
// unrelated field must not clear or rewrite that relation; intentional clears remain writes.
for (const [before, after, expected] of [
  [[], [], {}],
  [[7, 9], [9, 7], {}],
  [[7], [], { links: [[6, 0, []]] }],
  [[], [9], { links: [[6, 0, [9]]] }],
] as const) {
  assert.deepEqual(buildSaveRecordPayload({
    recordId: 501, formFields: { links: { type: 'many2many' } },
    dirtyFieldSet: new Set(['links']), editableMap: { links: [[6, 0, [...after]]] },
    formData: { links: [...after] }, originalValues: { links: [...before] },
    comparableFieldValue: (_name, value) => JSON.stringify([...(value as number[])].sort((a, b) => a - b)),
  }), expected);
}
console.log('[create_record_user_journey] unchanged relation payload: 4 cases PASS');

// Exercise the real relation draft runtime: query text is not a saved value or
// a deferred create request, even when the contract permits inline creation.
{
const relationDescriptor = { type: 'many2one', relation: 'x.related', relation_entry: {
  can_read: true, can_create: true, inline_create: { enabled: true, create_on_no_match: true },
} };
const relationDraft: Record<string, unknown> = { owner_id: 17 };
const relationKeywords: Record<string, string> = {};
const relationDirty = new Set<string>();
const relationRecordId = ref(501);
const relationOriginal = ref<Record<string, unknown>>({ owner_id: 17 });
const createCalls: string[] = [];
const pendingCreateFields = ref<string[]>([]);
const relationState = useRecordFormState({
  pendingInlineCreateFields: pendingCreateFields,
  formFields: ref({ owner_id: relationDescriptor }), model: ref('x.main'), recordId: relationRecordId,
  formData: relationDraft, originalValues: relationOriginal,
  relationKeywords, invalidatedRelationKeywords: {}, clearedDynamicRelationFields: {},
  relationOptions: ref({ owner_id: [{ id: 17, label: 'Selected' }] }),
  validationFieldErrors: ref({}), validationErrors: ref([]), applyingOnchangePatch: ref(false),
  dirtyFieldSet: relationDirty, changedFieldSet: new Set<string>(),
  contractV2ActionRules: ref([]), canonicalFieldWritable: () => true,
  layoutNodes: ref([{ kind: 'field', name: 'owner_id', descriptor: relationDescriptor, readonly: false }]),
  getOnchangeTimer: () => null, setOnchangeTimer: () => {},
  relationKeyword: (name: string) => relationKeywords[name] || '',
  setRelationKeyword: (name: string, keyword: string) => { relationKeywords[name] = keyword; },
  clearDynamicRelationDependents: () => {},
  queryRelationOptions: async () => [],
  quickCreateRelation: async (_name: string, _descriptor: unknown, label: string) => {
    createCalls.push(label); relationDraft.owner_id = 28;
  },
  relationUiLabel: (_descriptor: unknown, _key: string, fallback: string) => fallback,
} as never);
relationState.queryMany2oneInline('owner_id', relationDescriptor as never, 'Query only');
assert.equal(relationDraft.owner_id, 17);
assert.equal(relationDirty.size, 0);
await relationState.resolvePendingInlineRelationCreates();
assert.deepEqual(createCalls, []);
relationDraft.owner_id = false;
await relationState.resolvePendingInlineRelationCreates();
assert.deepEqual(createCalls, [], 'query on an empty relation must not create during save');
await relationState.commitMany2oneInline('owner_id', relationDescriptor as never, 'Explicit new');
assert.deepEqual(pendingCreateFields.value, ['owner_id'], 'false-to-false creation still has reactive pending state');
relationState.queryMany2oneInline('owner_id', relationDescriptor as never, 'Later query');
await relationState.resolvePendingInlineRelationCreates();
assert.deepEqual(createCalls, ['Explicit new'], 'only the explicit create intent names the new record');
await relationState.resolvePendingInlineRelationCreates();
assert.equal(createCalls.length, 1, 'a completed intent is not replayed');
await relationState.commitMany2oneInline('owner_id', relationDescriptor as never, 'Cancelled');
relationState.setMany2oneField('owner_id', relationDescriptor as never, '');
await relationState.resolvePendingInlineRelationCreates();
assert.equal(createCalls.length, 1, 'explicit clear cancels a staged create');
await relationState.commitMany2oneInline('owner_id', relationDescriptor as never, 'Old record');
relationRecordId.value = 502;
await relationState.resolvePendingInlineRelationCreates();
assert.equal(createCalls.length, 1, 'pending create cannot cross record identity');
await relationState.commitMany2oneInline('owner_id', relationDescriptor as never, 'Old draft');
relationOriginal.value = { ...relationOriginal.value, is_favorite: true };
await relationState.resolvePendingInlineRelationCreates();
assert.deepEqual(createCalls, ['Explicit new', 'Old draft'], 'unrelated favorite persistence must not cancel creation');
await relationState.commitMany2oneInline('owner_id', relationDescriptor as never, 'Discarded draft');
relationState.resetPendingInlineRelationCreates();
relationDirty.clear();
await relationState.resolvePendingInlineRelationCreates();
assert.equal(createCalls.length, 2, 'reload or discard invalidates the pending intent');
assert.deepEqual(pendingCreateFields.value, []);
console.log('[create-record-user-journey] PASS relation-intent-counterexamples=9');
}

// A staged create intent is its own state: it must not clear the relation value
// (which would look like a removed association to onchange and to the draft),
// and it must be invalidated by an explicit relation write instead.
{
const relationDescriptor = { type: 'many2one', relation: 'x.related', relation_entry: {
  can_read: true, can_create: true, inline_create: { enabled: true, create_on_no_match: true },
} };
const stagedDraft: Record<string, unknown> = { owner_id: 17 };
const stagedKeywords: Record<string, string> = {};
const stagedDirty = new Set<string>();
const stagedPending = ref<string[]>([]);
const stagedCreateCalls: string[] = [];
const stagedState = useRecordFormState({
  pendingInlineCreateFields: stagedPending,
  formFields: ref({ owner_id: relationDescriptor }), model: ref('x.main'), recordId: ref(501),
  formData: stagedDraft, originalValues: ref<Record<string, unknown>>({ owner_id: 17 }),
  relationKeywords: stagedKeywords, invalidatedRelationKeywords: {}, clearedDynamicRelationFields: {},
  relationOptions: ref({ owner_id: [{ id: 17, label: 'Selected' }] }),
  validationFieldErrors: ref({}), validationErrors: ref([]), applyingOnchangePatch: ref(false),
  dirtyFieldSet: stagedDirty, changedFieldSet: new Set<string>(),
  contractV2ActionRules: ref([]), canonicalFieldWritable: () => true,
  layoutNodes: ref([{ kind: 'field', name: 'owner_id', descriptor: relationDescriptor, readonly: false }]),
  getOnchangeTimer: () => null, setOnchangeTimer: () => {},
  relationKeyword: (name: string) => stagedKeywords[name] || '',
  setRelationKeyword: (name: string, keyword: string) => { stagedKeywords[name] = keyword; },
  clearDynamicRelationDependents: () => {},
  relationOptionsForField: () => [{ id: 17, label: 'Selected' }, { id: 31, label: 'Replacement' }],
  switchFormByRelationOption: async () => undefined,
  queryRelationOptions: async () => [],
  quickCreateRelation: async (_name: string, _descriptor: unknown, label: string) => {
    stagedCreateCalls.push(label); stagedDraft.owner_id = 28;
  },
  relationUiLabel: (_descriptor: unknown, _key: string, fallback: string) => fallback,
} as never);
await stagedState.commitMany2oneInline('owner_id', relationDescriptor as never, 'Brand new');
assert.equal(stagedDraft.owner_id, 17, 'staging a create intent never clears the relation value');
assert.deepEqual(stagedPending.value, ['owner_id']);
await stagedState.resolvePendingInlineRelationCreates();
assert.deepEqual(stagedCreateCalls, ['Brand new'], 'a staged intent creates the requested record');
assert.equal(stagedDraft.owner_id, 28, 'a successful create binds the new record id to the relation');
await stagedState.resolvePendingInlineRelationCreates();
assert.equal(stagedCreateCalls.length, 1, 'a completed intent is never replayed');
await stagedState.commitMany2oneInline('owner_id', relationDescriptor as never, 'Staged then replaced');
stagedState.setMany2oneField('owner_id', relationDescriptor as never, '31');
await stagedState.resolvePendingInlineRelationCreates();
assert.equal(stagedCreateCalls.length, 1, 'an explicit relation write cancels the staged create');
assert.deepEqual(stagedPending.value, []);
console.log('[create-record-user-journey] PASS relation-create-intent-counterexamples=8');
}

{
  const draft = reactive<Record<string, unknown>>({ owner_id: false });
  const keywords = reactive({ owner_id: '' });
  const pending = ref<string[]>([]);
  const progress = useRecordFormProgress({
    formData: draft, originalValues: ref({ owner_id: false }), relationKeywords: keywords,
    pendingInlineCreateFields: pending, canonicalFormFields: ref({ owner_id: { type: 'many2one' } }),
    layoutNodes: () => [], relationInlineCreate: () => ({ enabled: true, createOnNoMatch: true }),
    relationModel: () => 'x.related', isFieldWritable: () => true,
    fieldType: () => 'many2one', nativeStatusbar: () => ({}),
    comparableFieldValue: (_name: string, value: unknown) => value,
  } as never);
  assert.equal(progress.hasChanges.value, false);
  keywords.owner_id = 'Query only';
  assert.equal(progress.hasChanges.value, false, 'search text is not an unsaved relation change');
  pending.value = ['owner_id'];
  assert.equal(progress.hasChanges.value, true, 'an explicit pending creation participates in leave protection');
  pending.value = [];
  assert.equal(progress.hasChanges.value, false);
  draft.owner_id = 20;
  assert.equal(progress.hasChanges.value, true);
  console.log('[create-record-user-journey] PASS relation-dirty-state=5');
}

const fieldDescriptors = {
  amount: { name: 'amount', type: 'float' },
  owner_id: { name: 'owner_id', type: 'many2one' },
  title: { name: 'title', type: 'char' },
};

// Editing a required field must obey the same contract as creation, including
// submitted fields hidden by a presentation preference. Untouched legacy gaps
// must not turn an unrelated partial update into a full-record repair.
async function validateEdit(values: Record<string, unknown>, visible = true) {
  return validateBeforeSaveRecord({
    model: 'x.document',
    recordId: 501,
    collectSceneValidationPrecheckErrors: () => [],
    collectWritableValues: () => values,
    formData: { title: 'Existing title', owner_id: false, ...values },
    isWritableFieldVisible: () => visible,
    layoutNodes: [
      { kind: 'field', name: 'title', label: '标题', readonly: false, descriptor: { type: 'char', required: true } },
      { kind: 'field', name: 'owner_id', label: '负责人', readonly: false, descriptor: { type: 'many2one', required: true } },
      { kind: 'field', name: 'active', label: '启用', readonly: false, descriptor: { type: 'boolean', required: true } },
    ] as never,
    layoutFieldLabels: () => ({ title: '标题', owner_id: '负责人' }),
    normalizeFieldValue: (_name, value) => value,
    one2manyFieldErrors: {}, one2manyIssues: [],
    resolvePendingInlineRelationCreates: async () => [],
    resolvePendingMany2manyTagCreates: async () => [],
  });
}
for (const empty of ['', '  ', false, null, undefined]) {
  const rejected = await validateEdit({ title: empty });
  assert.equal(rejected.ok, false, 'clearing a required field in edit mode must fail');
  // The error states its business ownership, not only a message: the field it
  // belongs to, the record or draft it belongs to, and the rule identity.
  assert.equal(rejected.fieldErrors?.title?.message, '标题不能为空');
  assert.equal(rejected.fieldErrors?.title?.target.fieldCode, 'title');
  assert.equal(rejected.fieldErrors?.title?.target.recordId, 501);
  assert.equal(rejected.fieldErrors?.title?.code, 'REQUIRED_VALUE_MISSING');
}
assert.equal((await validateEdit({ title: '' }, false)).ok, false, 'hidden submitted required values still obey the contract');
assert.equal((await validateEdit({ title: 'Updated title' })).ok, true, 'untouched missing owner must not block a partial update');
assert.equal((await validateEdit({ owner_id: false })).ok, false, 'clearing a required relation must fail');
assert.equal((await validateEdit({ active: false })).ok, true, 'a required boolean may be false');
assert.equal((await validateEdit({ active: null })).ok, false, 'an absent required boolean still fails');
console.log('[edit-required-validation] PASS cases=10');
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
assert.equal(sanitizeUiErrorMessage('Failed to fetch', '保存失败'), '网络异常，请检查连接后重试。');

const temporalFormData: Record<string, unknown> = {};
for (const [name, type, incoming] of [
  ['confirmed_on', 'date', false],
  ['confirmed_at', 'datetime', false],
  ['scheduled_at', 'datetime', '2026-09-15 09:30:00'],
] as const) {
  applyIncomingFormFieldValue({
    fieldName: name,
    descriptor: { name, type } as never,
    incoming,
    target: {
      formData: temporalFormData,
      relationOptions: {},
      relationKeywords: {},
      upsertRelationOption: () => undefined,
      initOne2manyRows: () => undefined,
    },
  });
}
assert.deepEqual(temporalFormData, {
  confirmed_on: '',
  confirmed_at: '',
  scheduled_at: '2026-09-15T09:30',
}, 'empty Odoo temporal values stay falsey while real values remain input-compatible');
assert.equal(
  evaluateNativeModifierValue(
    { kind: 'field_truthy', field: 'confirmed_at' },
    (field) => temporalFormData[field],
  ),
  false,
  'an empty confirmation datetime must not make dependent inputs readonly',
);

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

let releaseSave: ((value: number) => void) | null = null;
let createCalls = 0;
const singleFlightSave = createSingleFlightSave(async () => {
  createCalls += 1;
  return new Promise<number>((resolve) => { releaseSave = resolve; });
});
const firstSave = singleFlightSave();
const duplicateSave = singleFlightSave();
assert.equal(firstSave, duplicateSave, 'duplicate save clicks must share one in-flight write');
assert.equal(createCalls, 1);
releaseSave?.(501);
assert.equal(await duplicateSave, 501);

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

console.log('[create-record-user-journey] PASS checkpoints=defaults,single-flight-save,reopen,edit,submit,refresh');

// Actual shared executor: transport success must not mask a blocked business result.
let mutationChecks = 0;
const mutationInput = { mutation: { intent: 'test.transition', params: { id: '$record_id' } }, actionKey: 'transition', recordId: 51 };
for (const [data, expectedError] of [
  [{ result: 'blocked', message: '任务正在审批中，请在任务详情查看审批进度，通过后再启动。' }, '任务正在审批中'],
  [{ result: 'blocked' }, '当前操作未完成'],
  [{ result: 'success', id: 51 }, ''],
  [{ record_id: 51 }, ''],
] as const) {
  const request = async (payload: { intent: string; params: Record<string, unknown> }) => {
    assert.deepEqual(payload, { intent: 'test.transition', params: { id: 51 } });
    return { traceId: 'test-trace', data: { ...data } };
  };
  if (expectedError) {
    await assert.rejects(executeSceneMutation(mutationInput, request), new RegExp(expectedError));
  } else {
    assert.deepEqual(await executeSceneMutation(mutationInput, request), { intent: 'test.transition', traceId: 'test-trace', data });
  }
  mutationChecks += 1;
}
console.log(`[scene-mutation-outcome] PASS cases=${mutationChecks}`);

const requirementAction = { actionSemantics: { kind: 'business', purpose: 'submit', executor: 'contract.action' } } as never;
const submissionRule = { kind: 'relation_required', field: 'documents', requiredWhen: { field: 'policy', equals: 'required' },
  pendingSource: 'native_attachment', reasonCode: 'DOCUMENT_REQUIRED', message: '请先选择凭证' };
const requirementWorkflow = { submissionRequirements: [submissionRule] };
assert.deepEqual(submissionRequirementErrors(requirementAction, requirementWorkflow, { policy: 'required', documents: [] }, 0), ['请先选择凭证']);
assert.deepEqual(submissionRequirementErrors(requirementAction, requirementWorkflow, { policy: 'required', documents: [] }, 1), []);
assert.deepEqual(submissionRequirementErrors(requirementAction, requirementWorkflow, { policy: 'required' }, 0), ['请先选择凭证']);
assert.deepEqual(submissionRequirementErrors(requirementAction, requirementWorkflow, { policy: 'required' }, 1), []);
assert.deepEqual(submissionRequirementErrors(requirementAction, requirementWorkflow, { policy: 'required', documents: [12] }, 0), []);
assert.deepEqual(submissionRequirementErrors(requirementAction, requirementWorkflow, { policy: 'recommended', documents: [] }, 0), []);
assert.deepEqual(submissionRequirementErrors({ actionSemantics: { kind: 'system', purpose: 'save' } } as never, requirementWorkflow, {}, 0), []);
assert.deepEqual(submissionRequirementErrors(requirementAction, {}, {}, 0), []);
assert.equal(submissionRequirementErrors(requirementAction, requirementWorkflow, { documents: [] }, 0).length, 1);
assert.equal(submissionRequirementErrors(requirementAction, { submissionRequirements: 'invalid' }, {}, 0).length, 1);
assert.equal(submissionRequirementErrors(requirementAction, { submissionRequirements: [{ ...submissionRule, kind: 'unsupported' }] }, {}, 0).length, 1);
assert.deepEqual(submissionRequirementErrors(requirementAction, { submissionRequirements: [{ ...submissionRule, pendingSource: undefined }] }, { policy: 'required', documents: [] }, 3), ['请先选择凭证']);
for (const create of [true, false]) {
  let writes = 0;
  const guarded = usePrimaryFormActionRuntime({
    primaryCreateFooterAction: () => create ? { ...requirementAction, enabled: true } : null,
    primarySubmitAction: () => ({ ...requirementAction, enabled: true }),
    validateSubmissionRequirements: () => false,
    saveRecord: async () => { writes += 1; return 22; },
    executeButtonRequest: async () => { writes += 1; return {}; },
  } as never);
  await guarded.runPrimaryFormAction();
  assert.equal(writes, 0);
}
console.log('[create-record-user-journey] submission prerequisites PASS count=14');

const createdSubmitEvents: string[] = [];
const createdSubmitRuntime = usePrimaryFormActionRuntime({
  primaryCreateFooterAction: () => ({ ...requirementAction, enabled: true, context: {}, methodName: 'action_submit' }),
  saveRecord: async () => { createdSubmitEvents.push('create'); return 902; },
  confirmActionSafety: async () => true,
  busyKind: ref(null), modelName: () => 'x.document', routeMenuId: () => 31, actionId: () => 21,
  executeButtonRequest: async (request: { res_id: number }) => {
    assert.equal(request.res_id, 902); createdSubmitEvents.push('submit'); return { result: { type: 'refresh', res_id: 902 } };
  },
  navigateActionResponseResult: async () => false,
  navigateCreatedRecord: async (id: number) => { assert.equal(id, 902); createdSubmitEvents.push('open-created'); },
  applyProjectionRefreshPolicy: async () => { createdSubmitEvents.push('refresh-new'); },
  reload: async () => { createdSubmitEvents.push('reload-new'); },
  recordId: ref(0), submissionFeedback: ref(null), validationErrors: ref([]), status: ref('ok'), errorMessage: ref(''),
} as never);
await createdSubmitRuntime.runPrimaryFormAction();
assert.deepEqual(createdSubmitEvents, ['create', 'submit', 'open-created']);
console.log('[create-record-user-journey] created submit navigates generated identity PASS count=1');

const failedSubmitEvents: string[] = [];
const failedCreatedSubmitRuntime = usePrimaryFormActionRuntime({
  primaryCreateFooterAction: () => ({ ...requirementAction, enabled: true, context: {}, methodName: 'action_submit' }),
  saveRecord: async () => { failedSubmitEvents.push('create'); return 903; },
  confirmActionSafety: async () => true,
  busyKind: ref(null), modelName: () => 'x.document', routeMenuId: () => 31, actionId: () => 21,
  executeButtonRequest: async () => { failedSubmitEvents.push('submit-failed'); throw new Error('Temporary refusal'); },
  navigateCreatedRecord: async (id: number, _policy: unknown, recovery: string) => { failedSubmitEvents.push(`recover:${id}:${recovery}`); },
  reload: async () => { failedSubmitEvents.push('reload-new'); },
  recordId: ref(0), submissionFeedback: ref(null), validationErrors: ref([]), status: ref('ok'), errorMessage: ref(''),
} as never);
await failedCreatedSubmitRuntime.runPrimaryFormAction();
assert.deepEqual(failedSubmitEvents, ['create', 'submit-failed', 'recover:903:submit']);
console.log('[create-record-user-journey] failed created submit preserves generated identity PASS count=1');

assert.equal(nativeAttachmentRefreshDecision('x.document', 903, 'x.document', 903, false), 'refresh');
assert.equal(nativeAttachmentRefreshDecision('x.document', 903, 'x.document', 903, true), 'deferred');
assert.equal(nativeAttachmentRefreshDecision('x.document', 903, 'x.document', 904, false), 'different_record');
assert.equal(nativeAttachmentRefreshDecision('x.document', 903, 'y.document', 903, false), 'different_record');
assert.equal(nativeAttachmentRefreshDecision('x.document', 903, 'x.document', 0, false), 'different_record');
assert.equal(nativeAttachmentRefreshDecision('x.document', 0, 'x.document', 0, false), 'different_record');
console.log('[create-record-user-journey] attachment refresh ownership and dirty preservation PASS count=6');
