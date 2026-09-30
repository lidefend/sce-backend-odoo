/**
 * Executable proof for occurrence-scoped field edit authority (WEB-FIX-01).
 *
 * One field code can be rendered at several positions.  A read-only position
 * must not write the draft because an editable sibling of the same field
 * exists.  The counter-example below is built from a real decoded contract and
 * the real canonical presenter, then driven through the real record-form
 * runtime setters and the real event dispatcher, so an inverted predicate, a
 * dropped occurrence key or a re-introduced "some same-name position is
 * writable" aggregate each change at least one expectation here.
 */
import assert from 'node:assert/strict';
import { computed, ref } from 'vue';
import { createContractV2Store } from '../src/app/contracts/v2/store';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import { presentContractV2Form } from '../src/app/presentation/contractFormPresenter';
import {
  collectCanonicalFieldOccurrences,
  collectLayoutFieldOccurrences,
  createFormOccurrenceDecision,
  resolveNamedFieldWritable,
  type FieldOccurrenceSources,
} from '../src/pages/contractForm/fieldOccurrenceWritability';
import { useRecordFormState } from '../src/pages/contractForm/useRecordFormState';
import { dispatchTemplateFieldChange } from '../src/components/template/fieldChange.dispatcher';
import { toContractFormDriverFieldChange } from '../src/components/template/contractFormDriverField';
import type { LayoutNode } from '../src/pages/contractForm/types';

// ---------------------------------------------------------------------------
// A real contract that renders the same field `amount` twice: the read-only
// summary occurrence `field.amount` and the editable detail occurrence
// `field.amount.occ.detail`.
// ---------------------------------------------------------------------------
function contractSnapshot(amountReadonly: boolean, amountDetailReadonly: boolean, pageAuth = 'edit') {
  return {
    pageInfo: {
      pageId: 'page.x.document.form', sceneKey: 'x.document.form', pageName: 'Document',
      model: 'x.document', viewType: 'form', layoutType: 'form', renderMode: 'governed',
      contractVersion: '2.2.0', clientType: 'web_pc',
    },
    layoutContract: {
      pageId: 'page.x.document.form', layoutType: 'form', adaptMode: 'pc',
      layoutHints: { mobileColumns: 1 },
      componentRegistry: {
        'sc.input.text': { version: '1.0', adapter: { web_pc: 'ElInput' }, selectedAdapter: 'TDesignInput' },
        'sc.relation.many2one': { version: '1.0', adapter: { web_pc: 'ElSelect' } },
      },
      containerTree: [{
        containerId: 'section.identity', containerType: 'group', type: 'group', title: 'Identity', span: 24,
        children: [
          {
            containerId: 'field.amount', containerType: 'field', type: 'field', name: 'amount', widgetId: 'field.amount', fieldCode: 'amount', title: '', span: 12,
            nativeLocator: '//form/sheet/group/field[@name="amount"]', occurrenceIndex: 1, sourcePosition: 0,
            children: [], widgetList: [{
              widgetId: 'field.amount', widgetType: 'input', fieldCode: 'amount', label: 'Amount', span: 12,
              componentKey: 'sc.input.text', capabilities: [],
              componentConfig: { fieldType: 'char', native_locator: '//form/sheet/group/field[@name="amount"]', occurrence_index: 1, source_position: 0 },
              fieldDescriptor: { name: 'amount', type: 'char' },
              nativeLocator: '//form/sheet/group/field[@name="amount"]', occurrenceIndex: 1, sourcePosition: 0,
              ownerContainerId: 'field.amount',
            }],
          },
          {
            containerId: 'field.amount.occ.detail', containerType: 'field', type: 'field', name: 'amount', widgetId: 'field.amount.occ.detail', fieldCode: 'amount', title: '', span: 12,
            nativeLocator: '//form/sheet/group/field[@name="amount"]', occurrenceIndex: 2, sourcePosition: 1,
            children: [], widgetList: [{
              widgetId: 'field.amount.occ.detail', widgetType: 'input', fieldCode: 'amount', label: 'Amount (detail)', span: 12,
              componentKey: 'sc.input.text', capabilities: [],
              componentConfig: { fieldType: 'char', native_locator: '//form/sheet/group/field[@name="amount"]', occurrence_index: 2, source_position: 1 },
              fieldDescriptor: { name: 'amount', type: 'char' },
              nativeLocator: '//form/sheet/group/field[@name="amount"]', occurrenceIndex: 2, sourcePosition: 1,
              ownerContainerId: 'field.amount.occ.detail',
            }],
          },
          {
            containerId: 'field.owner_id', containerType: 'field', type: 'field', name: 'owner_id', widgetId: 'field.owner_id', fieldCode: 'owner_id', title: '', span: 12,
            children: [], widgetList: [{
              widgetId: 'field.owner_id', widgetType: 'relation', fieldCode: 'owner_id', label: 'Owner', span: 12,
              componentKey: 'sc.relation.many2one', capabilities: [], componentConfig: { fieldType: 'many2one' },
              fieldDescriptor: { name: 'owner_id', type: 'many2one', relation: 'x.related' },
              ownerContainerId: 'field.owner_id',
            }],
          },
        ],
        widgetList: [],
      }],
    },
    actionContract: {
      actionRuleList: [{
        actionId: 'action.amount', actionKey: 'action.amount', backendIdentity: 'onchange:field.amount',
        triggerType: 'change', sourceWidgetId: 'field.amount', targetIds: [], dispatchMode: 'serverDebounced',
        targetScope: 'widget', refreshMode: 'none', allowed: true, enabled: true, disabled: false,
        entitlementEvaluated: true, visibleProfiles: ['edit', 'create'],
      }],
      dependencyGraph: {},
    },
    statusContract: {
      globalStatus: {
        pageVisible: true, pageAuth, reasonCode: '',
        modelRights: { read: true, write: true, create: true, unlink: true, duplicate: true },
        recordRights: { read: true, write: true, create: true, unlink: true, duplicate: true },
        viewCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        entryCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        effectiveRecordCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        effectiveRenderProfile: pageAuth === 'read' ? 'readonly' : 'edit',
      },
      widgetStatus: [
        { widgetId: 'field.amount', visible: true, readonly: amountReadonly, required: false, disabled: false, auth: amountReadonly ? 'read' : 'edit' },
        { widgetId: 'field.amount.occ.detail', visible: true, readonly: amountDetailReadonly, required: false, disabled: false, auth: amountDetailReadonly ? 'read' : 'edit' },
        { widgetId: 'field.owner_id', visible: true, readonly: false, required: false, disabled: false },
      ],
      buttonStatus: [], containerStatus: [], selectorStatus: [],
    },
    dataContract: {
      mainData: { amount: '1', owner_id: [17, 'Existing'] }, tableRows: {}, relationRows: {},
      dictData: {}, pagination: {}, dataSource: {}, dataMeta: {},
    },
    runtimeContract: {
      patchStrategy: 'full', cachePolicy: 'snapshot', optimistic: false, lazyContainer: [],
      virtualization: {}, retryPolicy: {},
    },
    meta: {
      etag: 'e', snapshotId: 's', traceId: 't', requestId: 'r', sourceType: 'ui.contract',
      lifecycle: {
        lifecycleVersion: '1', stage: 'sealed',
        definition: { schemaId: 'v2', schemaVersion: '2', schemaSha256: 'schema', contractVersion: '2', normativeStatus: 'active' },
        generation: { generator: 'test', generatorVersion: '1', sourceType: 'test', sourceSha256: 'source' },
        runtime: { requestId: 'r', traceId: 't', clientType: 'web_pc', traceSource: 'test' },
        integrity: { algorithm: 'sha256', contractSha256: 'contract-sha' }, authority: {},
      },
    },
  };
}

const model = presentContractV2Form(
  createContractV2Store(decodeContractV2Snapshot(contractSnapshot(true, false))),
  'edit',
  { amount: '1', owner_id: 17 },
);
const canonical = collectCanonicalFieldOccurrences(model);
assert.deepEqual(
  canonical.filter((occurrence) => occurrence.name === 'amount').map((occurrence) => [occurrence.key, occurrence.readonly]),
  [['field.amount', true], ['field.amount.occ.detail', false]],
  'the contract must expose both occurrences of `amount` with their own editability',
);

// The page's occurrence sources: the contract occurrences plus the rendered
// native positions, resolved by the exact function the page hands to the runtime.
const layoutNodes = ref<LayoutNode[]>([]);
const sources = computed<FieldOccurrenceSources>(() => ({
  canonical: collectCanonicalFieldOccurrences(model),
  layout: collectLayoutFieldOccurrences(layoutNodes.value),
}));
const decide = createFormOccurrenceDecision(() => sources.value);

assert.equal(decide('amount', 'field.amount'), 'blocked', 'the read-only occurrence of `amount` is blocked');
assert.equal(decide('amount', 'field.amount.occ.detail'), 'writable', 'the editable occurrence of `amount` is writable');
assert.equal(decide('amount', ''), 'unresolved', 'a missing occurrence identity is not resolved by name');
assert.equal(decide('amount', 'field.amount.occ.absent'), 'unresolved', 'an unknown occurrence identity is unresolved');
assert.equal(decide('owner_id', 'field.amount'), 'unresolved', 'a key naming another field is a mismatched identity');

// ---------------------------------------------------------------------------
// The real record-form runtime: the mutation entry every user edit passes.
// ---------------------------------------------------------------------------
const onchangeRules = contractSnapshot(true, false).actionContract.actionRuleList;
function createRuntime(overrides: Record<string, unknown> = {}) {
  const formData: Record<string, unknown> = { amount: '1', owner_id: 17 };
  const dirty = new Set<string>();
  const changed = new Set<string>();
  const timerCalls: number[] = [];
  const inlineCreates: string[] = [];
  const runtime = useRecordFormState({
    pendingInlineCreateFields: ref<string[]>([]),
    formFields: { value: {
      amount: { name: 'amount', type: 'char' },
      owner_id: { name: 'owner_id', type: 'many2one', relation: 'x.related', relation_entry: { can_read: true, can_create: true, inline_create: { enabled: true, create_on_no_match: true } } },
    } },
    model: { value: 'x.document' }, recordId: { value: 501 }, rights: { value: { write: true } },
    formData, originalValues: { value: { amount: '1', owner_id: 17 } },
    submissionFeedback: { value: null }, relationKeywords: {}, invalidatedRelationKeywords: {},
    clearedDynamicRelationFields: {}, relationQueryTimers: {}, relationOptions: { value: {} },
    validationErrors: { value: [] }, validationFieldErrors: { value: {} },
    onchangeModifiersPatch: { value: {} }, onchangeWarnings: { value: [] }, onchangeLinePatches: { value: [] },
    applyingOnchangePatch: { value: false }, changedFieldSet: changed, dirtyFieldSet: dirty,
    getOnchangeTimer: () => null, setOnchangeTimer: (timer: ReturnType<typeof setTimeout> | null) => { if (timer) timerCalls.push(1); },
    contractV2ActionRules: { value: onchangeRules }, layoutNodes, nativeStatusbar: { value: {} }, route: { query: {} },
    isNativeFavoriteField: () => false, clearDynamicRelationDependents: () => {},
    openRelationCreateForm: async () => ({}), openRelationSearchDialog: async () => ({}),
    openRelationRecordForm: async () => ({}), relationOptionsForField: () => [],
    switchFormByRelationOption: async () => ({}), queryRelationOptions: async () => [],
    setRelationKeyword: () => {}, setMany2oneOption: () => {}, relationKeyword: () => '',
    quickCreateRelation: async (_name: string, _descriptor: unknown, label: string) => { inlineCreates.push(label); },
    relationUiLabel: (_descriptor: unknown, _key: string, fallback?: string) => fallback || '',
    relationModel: () => '', relationIds: () => [], upsertRelationOption: () => {},
    buildOne2manyCommandValue: () => [], one2manyFieldRows: () => [], initOne2manyRows: () => {},
    applyOnchangeLinePatches: () => {}, isWritableFieldVisible: () => true,
    canonicalFieldWritable: (name: string) => resolveNamedFieldWritable(sources.value.canonical, name),
    fieldOccurrenceDecision: decide,
    ...overrides,
  });
  return { runtime, formData, dirty, changed, timerCalls, inlineCreates };
}

// Counter-example: A is read-only, B is writable.
{
  const { runtime, formData, dirty, changed, timerCalls } = createRuntime();
  runtime.setTextField('amount', '10', 'field.amount');
  assert.equal(formData.amount, '1', 'a read-only occurrence must not write the draft');
  assert.deepEqual([...dirty], [], 'a read-only occurrence must not mark the field dirty');
  assert.deepEqual([...changed], [], 'a read-only occurrence must not queue an onchange');
  assert.deepEqual(timerCalls, [], 'a read-only occurrence must not schedule an onchange roundtrip');

  runtime.setTextField('amount', '10', 'field.amount.occ.detail');
  assert.equal(formData.amount, '10', 'the editable occurrence writes the draft');
  assert.deepEqual([...dirty], ['amount'], 'the editable occurrence marks the field dirty');
  assert.deepEqual([...changed], ['amount'], 'the editable occurrence queues exactly one onchange');
  assert.deepEqual(timerCalls, [1], 'the editable occurrence schedules exactly one roundtrip');

  // The editable write is a draft write, not a per-occurrence write: the single
  // draft is what every occurrence, including the read-only one, displays.
  assert.equal(formData.amount, '10', 'the read-only occurrence is not blocked from displaying the new value');
}

// Every keyed setter takes the same decision.
{
  const { runtime, formData, dirty } = createRuntime();
  runtime.setBooleanField('amount', true, 'field.amount');
  runtime.setSelectionField('amount', 'x', 'field.amount');
  runtime.setMany2oneField('amount', undefined, '7', 'field.amount');
  runtime.queryMany2oneInline('amount', undefined, 'q', 'field.amount');
  assert.equal(formData.amount, '1', 'no keyed setter may write through a read-only occurrence');
  assert.deepEqual([...dirty], [], 'no keyed setter may mark the field dirty through a read-only occurrence');
}

// A page that is not editable blocks even the otherwise writable occurrence.
{
  const readonlyModel = presentContractV2Form(
    createContractV2Store(decodeContractV2Snapshot(contractSnapshot(false, false, 'read'))),
    'readonly',
    { amount: '1' },
  );
  const readonlyDecide = createFormOccurrenceDecision(() => ({
    canonical: collectCanonicalFieldOccurrences(readonlyModel),
    layout: collectLayoutFieldOccurrences([]),
  }));
  assert.equal(readonlyDecide('amount', 'field.amount.occ.detail'), 'blocked', 'a read-only page blocks the writable occurrence');
  const { runtime, formData, dirty } = createRuntime({
    canonicalFieldWritable: undefined,
    fieldOccurrenceDecision: readonlyDecide,
  });
  runtime.setTextField('amount', '10', 'field.amount.occ.detail');
  assert.equal(formData.amount, '1', 'a read-only page must not accept a keyed edit');
  assert.deepEqual([...dirty], [], 'a read-only page must not mark the field dirty');
}

// An absent identity is the documented compatibility boundary: native
// companions of a rendered control (a date range's hidden end field, a
// favourite toggle) and relation sub-table controls address a field that has no
// occurrence identity of its own, so the field-whole rule still applies to
// them. It is a different input from a keyed event, which never consults it.
{
  const { runtime, formData, dirty } = createRuntime();
  runtime.setTextField('amount', '10');
  assert.equal(formData.amount, '10', 'identity-less callers keep the field-whole rule');
  assert.deepEqual([...dirty], ['amount'], 'identity-less callers keep the field-whole rule');
}

// An identity that is present but cannot be resolved is refused, never
// normalised into a different position of the same field.
{
  const { runtime, formData, dirty } = createRuntime();
  runtime.setTextField('amount', '10', 'field.amount.occ.absent');
  runtime.setTextField('amount', '10', 'native_field_amount_0');
  runtime.setSelectionField('amount', 'x', 'field.amount.occ.absent');
  runtime.setBooleanField('amount', true, 'field.amount.occ.absent');
  runtime.setMany2oneField('amount', undefined, '7', 'field.amount.occ.absent');
  runtime.setTextField('owner_id', '10', 'field.amount');
  runtime.queryMany2oneInline('owner_id', undefined, 'q', 'field.amount');
  assert.equal(formData.amount, '1', 'an unresolvable identity must not write the draft');
  assert.equal(formData.owner_id, 17, 'a mismatched identity must not write another field');
  assert.deepEqual([...dirty], [], 'an unresolvable identity must not mark any field dirty');
}

// A native position the contract does not name is still decided per position.
{
  const layout = ref<LayoutNode[]>([
    { key: 'native_field_note_0', kind: 'field', name: 'note', label: 'Note', readonly: true, required: false },
    { key: 'native_field_note_4', kind: 'field', name: 'note', label: 'Note', readonly: false, required: false },
  ]);
  const layoutDecide = createFormOccurrenceDecision(() => ({
    canonical: [],
    layout: collectLayoutFieldOccurrences(layout.value),
  }));
  assert.equal(layoutDecide('note', 'native_field_note_0'), 'blocked', 'a read-only rendered position is blocked');
  assert.equal(layoutDecide('note', 'native_field_note_4'), 'writable', 'an editable rendered position is writable');
}

// The value cannot leak from the "some position is writable" aggregate: the
// aggregate stays, but it is only reachable without an occurrence identity.
{
  const occurrences = collectCanonicalFieldOccurrences(model).filter((item) => item.name === 'amount');
  assert.equal(resolveNamedFieldWritable(occurrences, 'amount'), true, 'the name aggregate is unchanged for identity-less callers');
  assert.equal(decide('amount', 'field.amount'), 'blocked', 'the keyed decision never consults the aggregate');
}

// ---------------------------------------------------------------------------
// A position that becomes read-only, or a record that changes, invalidates a
// deferred relation result instead of applying it to the new draft.
// ---------------------------------------------------------------------------
{
  const { runtime, inlineCreates } = createRuntime();
  await runtime.commitMany2oneInline('owner_id', {
    type: 'many2one', relation: 'x.related',
    relation_entry: { can_read: true, can_create: true, inline_create: { enabled: true, create_on_no_match: true } },
  } as never, 'Staged on writable position', 'field.owner_id');
  await runtime.resolvePendingInlineRelationCreates();
  assert.deepEqual(inlineCreates, ['Staged on writable position'], 'a writable occurrence may apply its create result');

  const flip = createRuntime();
  await flip.runtime.commitMany2oneInline('owner_id', {
    type: 'many2one', relation: 'x.related',
    relation_entry: { can_read: true, can_create: true, inline_create: { enabled: true, create_on_no_match: true } },
  } as never, 'Staged then readonly', 'field.owner_id.occ.gone');
  await flip.runtime.resolvePendingInlineRelationCreates();
  assert.deepEqual(flip.inlineCreates, [], 'a position whose identity no longer resolves must not apply its result');
}

// ---------------------------------------------------------------------------
// The event entry keeps the identity: the producer stamps it and the dispatcher
// forwards it unchanged.
// ---------------------------------------------------------------------------
{
  const change = toContractFormDriverFieldChange(
    { key: 'field.amount.occ.detail', name: 'amount', label: 'Amount', type: 'char', required: false, readonly: false, invalid: false, inputValue: '1', selectionOptions: [] } as never,
    '10',
  );
  assert.equal(change.occurrenceKey, 'field.amount.occ.detail', 'the control must stamp its own occurrence identity');

  const seen: Array<[string, string, string]> = [];
  dispatchTemplateFieldChange(change, {
    onBoolean: (name, _value, key) => { seen.push(['boolean', name, key]); },
    onSelection: (name, _value, key) => { seen.push(['selection', name, key]); },
    onMany2one: (name, _descriptor, _value, key) => { seen.push(['many2one', name, key]); },
    onText: (name, _value, key) => { seen.push(['text', name, key]); },
  });
  assert.deepEqual(seen, [['text', 'amount', 'field.amount.occ.detail']], 'the dispatcher must forward the occurrence identity');

  const { runtime, formData, dirty } = createRuntime();
  dispatchTemplateFieldChange(change, {
    onBoolean: (name, value, key) => runtime.setBooleanField(name, value, key),
    onSelection: (name, value, key) => runtime.setSelectionField(name, value, key),
    onMany2one: (name, descriptor, value, key) => runtime.setMany2oneField(name, descriptor as never, value, key),
    onText: (name, value, key) => runtime.setTextField(name, value, key),
  });
  assert.equal(formData.amount, '10', 'the real entry chain applies a writable occurrence edit exactly once');
  assert.deepEqual([...dirty], ['amount'], 'the real entry chain marks the field dirty once');

  const readonlyChange = toContractFormDriverFieldChange(
    { key: 'field.amount', name: 'amount', label: 'Amount', type: 'char', required: false, readonly: true, invalid: false, inputValue: '1', selectionOptions: [] } as never,
    '10',
  );
  const readonlyRuntime = createRuntime();
  dispatchTemplateFieldChange(readonlyChange, {
    onBoolean: (name, value, key) => readonlyRuntime.runtime.setBooleanField(name, value, key),
    onSelection: (name, value, key) => readonlyRuntime.runtime.setSelectionField(name, value, key),
    onMany2one: (name, descriptor, value, key) => readonlyRuntime.runtime.setMany2oneField(name, descriptor as never, value, key),
    onText: (name, value, key) => readonlyRuntime.runtime.setTextField(name, value, key),
  });
  assert.equal(readonlyRuntime.formData.amount, '1', 'the real entry chain rejects a read-only occurrence edit');
  assert.deepEqual([...readonlyRuntime.dirty], [], 'the real entry chain leaves the draft untouched for a read-only occurrence');
}

// Opening an existing record is navigation, not a draft mutation. The existing
// relationship navigation handler owns canRead/canOpen; write-only operations
// must still fail at this occurrence boundary.
{
  const opened: string[] = [];
  const edits: string[] = [];
  const { runtime, formData, dirty, changed, timerCalls } = createRuntime({
    canonicalFieldWritable: () => false,
    fieldOccurrenceDecision: () => 'blocked',
    openRelationRecordForm: async (name: string) => { opened.push(name); },
    openRelationCreateForm: async () => { edits.push('create'); },
    openRelationSearchDialog: async () => { edits.push('search'); },
  });
  runtime.setMany2oneField('owner_id', undefined, '__open_record__', 'field.owner.readonly');
  assert.deepEqual(opened, ['owner_id'], 'readonly relation opening delegates to the authorized navigation handler');
  for (const value of ['31', '', '__create__', '__search_more__']) {
    runtime.setMany2oneField('owner_id', undefined, value, 'field.owner.readonly');
  }
  assert.deepEqual(edits, [], 'readonly navigation cannot grant create or selection rights');
  assert.equal(formData.owner_id, 17, 'readonly navigation never changes the relationship');
  assert.equal(dirty.size, 0);
  assert.equal(changed.size, 0);
  assert.equal(timerCalls.length, 0, 'navigation does not trigger onchange');
}
console.log('[readonly-relation-navigation] PASS cases=5');

console.log('[contract-field-occurrence-identity] PASS counterexample=read-only-position-cannot-write-via-writable-sibling');
