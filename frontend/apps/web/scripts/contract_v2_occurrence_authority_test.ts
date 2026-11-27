/**
 * Executable proof that a declared node's authoritative verdict is consumed.
 *
 * The contract publishes one verdict per declared node: fields on
 * `statusContract.widgetStatus` (keyed by widgetId), declared action buttons on
 * `statusContract.buttonStatus` (keyed by the occurrence-bound backendIdentity)
 * and structural containers on `statusContract.containerStatus` (keyed by
 * containerId).  The renderer must consume that verdict for the node it
 * describes.
 *
 * The defect this locks: `runtimeOccurrenceState` looked the node up by
 * widgetId only.  A declared action button carries no widgetId, so it fell
 * through to the fail-closed branch and the contract-visible "提交立项" action
 * disappeared from the product surface while the contract said visible=true.
 * The counter-example below drives the real store and the real record-form
 * layout, so a re-introduced widgetId-only lookup, a dropped backendIdentity
 * index or a button verdict read as field authority each change an expectation.
 */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { isContractGapError } from '../src/app/contract/contractGap';
import { computed, reactive, ref } from 'vue';
import { createContractV2Store } from '../src/app/contracts/v2/store';
import { decodeContractV2ActionRule, decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import {
  resolveRecordFormFieldWidgetSemantics,
  resolveRecordFormFieldWidget,
  useRecordFormFieldSchemas,
} from '../src/pages/contractForm/useRecordFormFieldSchemas';
import { useRecordFormLayout } from '../src/pages/contractForm/useRecordFormLayout';

const VISIBLE_BUTTON_IDENTITY = 'native_button:object:action_sc_submit:/form[1]/sheet[1]/div[1]/div[2]/div[1]/div[2]/button[5]:1';
const HIDDEN_BUTTON_IDENTITY = 'native_button:object:action_sc_start:/form[1]/sheet[1]/div[1]/div[2]/div[1]/div[2]/button[4]:1';

function nativeOccurrence(
  name: string,
  kind: 'field' | 'container' | 'button' | 'widget',
  locator: string,
  occurrenceIndex: number,
  extra: Record<string, unknown> = {},
) {
  const occurrenceKey = createHash('sha256')
    .update(`${kind}:${name}:${locator}:${occurrenceIndex}`)
    .digest('hex')
    .slice(0, 24);
  return {
    schemaVersion: '1.0.0' as const,
    model: 'project.project',
    viewType: 'form',
    viewId: 91,
    viewXmlId: 'project.view_project_form',
    viewContentHash: 'a'.repeat(64),
    viewStructureKey: `struct.v1.${'b'.repeat(24)}`,
    crossEnvironmentStable: true,
    kind,
    name,
    nativeLocator: locator,
    occurrenceIndex,
    sourcePosition: occurrenceIndex,
    occurrenceKey: `occ.v1.${occurrenceKey}`,
    authoritative: true,
    sourceAuthority: {
      kind: 'ir.ui.view' as const,
      projectionOnly: true as const,
      noBusinessFactAuthority: true as const,
    },
    ...extra,
  };
}

function buttonNode(name: string, backendIdentity: string, occurrenceIndex: number) {
  const locator = `/form[1]/sheet[1]/div[1]/div[2]/div[1]/div[2]/button[${occurrenceIndex}]`;
  return {
    containerId: name, containerType: 'button', type: 'button', name, string: name, title: name,
    span: 12, nativeLocator: locator, occurrenceIndex, sourcePosition: occurrenceIndex,
    nativeIdentity: nativeOccurrence(name, 'container', locator, occurrenceIndex, { type: 'object' }),
    attributes: { name, type: 'object' },
    action: { name, actionId: `action.${name}`, backendIdentity, kind: 'object', level: 'body', intent: 'execute' },
    children: [], widgetList: [],
  };
}

function fieldNode(name: string, widgetId: string, occurrenceIndex: number) {
  const locator = `/form[1]/sheet[1]/div[1]/div[2]/div[1]/div[2]/field[${occurrenceIndex}]`;
  const identity = nativeOccurrence(name, 'field', locator, occurrenceIndex);
  return {
    containerId: widgetId, containerType: 'field', type: 'field', name, widgetId,
    span: 12, fieldCode: name, label: name,
    title: name, nativeLocator: locator, occurrenceIndex, sourcePosition: occurrenceIndex,
    nativeIdentity: identity,
    fieldInfo: { name, type: 'selection', readonly: true, required: true, modifiers: { readonly: true } },
    children: [],
    widgetList: [{
      widgetId, widgetType: 'select', fieldCode: name, label: name, span: 12,
      semanticType: 'choice', capabilities: [],
      componentConfig: {
        fieldType: 'selection', native_locator: locator, occurrence_index: occurrenceIndex,
        source_position: occurrenceIndex, readonly: true, required: true,
      },
      fieldDescriptor: {
        schemaVersion: '1.0.0',
        fieldCode: name,
        label: name,
        fieldType: 'selection',
        widgetType: 'select',
        semanticType: 'choice',
        required: true,
        readonly: true,
        selection: [['draft', 'Draft'], ['done', 'Done']],
      },
      nativeLocator: locator, occurrenceIndex, sourcePosition: occurrenceIndex,
      nativeIdentity: identity,
      ownerContainerId: widgetId,
    }],
  };
}

const snapshot = {
  pageInfo: {
    pageId: 'page.project.project.form', sceneKey: 'project.project.form', pageName: 'Project',
    model: 'project.project', viewType: 'form', layoutType: 'form', renderMode: 'governed',
    contractVersion: '2.7.0', clientType: 'web_pc',
  },
  layoutContract: {
    pageId: 'page.project.project.form', layoutType: 'form', adaptMode: 'pc',
    layoutHints: { mobileColumns: 1 },
    // The real project stage row: one declared flex container holding the
    // declared stage fields and the declared stage actions, in declared order.
    containerTree: [{
      containerId: 'container.native.0', containerType: 'container', type: 'container',
      title: '', span: 24, columns: 2, styleToken: 'd-flex flex-wrap gap-2', children: [
        buttonNode('action_sc_submit', VISIBLE_BUTTON_IDENTITY, 5),
        buttonNode('action_sc_start', HIDDEN_BUTTON_IDENTITY, 4),
        fieldNode('sc_approval_state', 'field.sc_approval_state.occ.1', 1),
        fieldNode('validation_status', 'field.validation_status.occ.1', 2),
        {
          containerId: 'container.hidden.1', containerType: 'container', type: 'container',
          title: '', span: 24, nativeLocator: '/form[1]/sheet[1]/div[1]/div[2]/div[1]/div[3]', occurrenceIndex: 1,
          nativeIdentity: nativeOccurrence(
            'container.hidden.1',
            'container',
            '/form[1]/sheet[1]/div[1]/div[2]/div[1]/div[3]',
            1,
          ),
          children: [], widgetList: [],
        },
      ],
      widgetList: [],
    }],
  },
  actionContract: {
    actionRuleList: [{
      actionId: 'action.action_sc_submit', actionKey: 'action_sc_submit', backendIdentity: VISIBLE_BUTTON_IDENTITY,
      triggerType: 'click', sourceWidgetId: 'action_sc_submit', targetIds: [], dispatchMode: 'server',
      targetScope: 'page', refreshMode: 'partial', allowed: true, enabled: true, disabled: false,
      entitlementEvaluated: true, visibleProfiles: ['edit', 'create', 'readonly'],
    }],
    dependencyGraph: {},
  },
  statusContract: {
    globalStatus: {
      pageVisible: true, pageAuth: 'edit', reasonCode: '',
      modelRights: { read: true, write: true, create: true, unlink: true, duplicate: true },
      recordRights: { read: true, write: true, create: true, unlink: true, duplicate: true },
      viewCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
      entryCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
      effectiveRecordCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
      effectiveRenderProfile: 'edit',
    },
    widgetStatus: [
      { widgetId: 'field.sc_approval_state.occ.1', visible: true, readonly: true, required: true, disabled: false, auth: 'read' },
      { widgetId: 'field.validation_status.occ.1', visible: false, readonly: true, required: false, disabled: false, auth: 'none', reasonCode: 'NATIVE_MODIFIER_INVISIBLE' },
    ],
    buttonStatus: [
      { btnId: 'btn.action_sc_submit', backendIdentity: VISIBLE_BUTTON_IDENTITY, visible: true, disabled: false },
      { btnId: 'btn.action_sc_start', backendIdentity: HIDDEN_BUTTON_IDENTITY, visible: false, disabled: false, reasonCode: 'ACTION_NOT_VISIBLE_IN_STATE' },
      { btnId: 'btn.form.save', backendIdentity: '', visible: true, disabled: false },
    ],
    containerStatus: [
      { containerId: 'container.hidden.1', visible: false, disabled: false, reasonCode: 'NATIVE_MODIFIER_INVISIBLE' },
    ],
    selectorStatus: [],
  },
  dataContract: {
    mainData: { lifecycle_state: 'draft', sc_approval_state: 'draft', validation_status: 'no' },
    tableRows: {}, relationRows: {}, dictData: {}, pagination: {}, dataSource: {}, dataMeta: {},
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

const strictSnapshot = structuredClone(snapshot);
strictSnapshot.pageInfo.contractVersion = '2.7.0';
const strictField = fieldNode('validation_status', 'field.validation_status.occ.strict', 1);
const strictViewIdentity = {
  schemaVersion: '1.0.0',
  model: 'project.project',
  viewType: 'form',
  viewId: 91,
  viewXmlId: 'project.view_project_form',
  viewContentHash: 'a'.repeat(64),
  viewStructureKey: 'struct.v1.' + 'b'.repeat(24),
  crossEnvironmentStable: true,
  occurrenceKey: 'occ.v1.' + 'c'.repeat(24),
  authoritative: true,
  sourceAuthority: {
    kind: 'ir.ui.view',
    projectionOnly: true,
    noBusinessFactAuthority: true,
  },
};
strictField.nativeIdentity = {
  ...strictViewIdentity,
  kind: 'field',
  name: 'validation_status',
  nativeLocator: strictField.nativeLocator,
  occurrenceIndex: strictField.occurrenceIndex,
  sourcePosition: strictField.sourcePosition,
};
strictField.widgetList[0].nativeIdentity = {
  ...strictViewIdentity,
  kind: 'field',
  name: 'select',
  nativeLocator: strictField.widgetList[0].nativeLocator,
  occurrenceIndex: strictField.widgetList[0].occurrenceIndex,
  sourcePosition: strictField.widgetList[0].sourcePosition,
};
strictField.widgetList[0].fieldDescriptor = {
  schemaVersion: '1.0.0',
  fieldCode: 'validation_status',
  label: 'validation_status',
  fieldType: 'selection',
  widgetType: 'select',
  semanticType: 'choice',
  required: true,
  readonly: true,
  selection: [['draft', 'Draft']],
} as never;
strictSnapshot.layoutContract.containerTree = [strictField];
strictSnapshot.statusContract.widgetStatus = [{
  widgetId: 'field.validation_status.occ.strict',
  visible: true,
  readonly: true,
  required: true,
  disabled: false,
  auth: 'read',
}];
strictSnapshot.statusContract.buttonStatus = [];
strictSnapshot.statusContract.containerStatus = [];
strictSnapshot.actionContract.actionRuleList = [];
const strictDecoded = decodeContractV2Snapshot(strictSnapshot);
for (const retiredOrUnknownVersion of ['1.0.0', '2.0.0', '2.5.0', '2.6.9', '2.8.0']) {
  const unsupported = structuredClone(strictSnapshot);
  unsupported.pageInfo.contractVersion = retiredOrUnknownVersion;
  assert.throws(() => decodeContractV2Snapshot(unsupported), /must be a negotiated 2.7 version/,
    `unsupported version ${retiredOrUnknownVersion} must not enter compatibility consumption`);
}
assert.equal(
  strictDecoded.layoutContract.containerTree[0].widgetList[0].fieldDescriptor?.fieldCode,
  'validation_status',
  'strict 2.7 form occurrences must validate canonical fieldCode/fieldType descriptors',
);
assert.equal(
  resolveRecordFormFieldWidget({
    fieldType: 'selection',
    widgetType: 'select',
    widget: 'checkbox',
  } as never),
  'select',
  'record-form schema widget identity comes from canonical widgetType, not a layout or component fallback',
);
assert.equal(
  resolveRecordFormFieldWidget({
    fieldType: 'char',
    widget: 'text',
  } as never),
  'text',
  'a normalized form descriptor may expose its canonical widget alias when widgetType is absent',
);
assert.deepEqual(
  resolveRecordFormFieldWidgetSemantics({
    fieldType: 'float',
    widgetType: 'float_time',
    widgetOptions: { readonly_empty_text: '未登记', kind: 'duration' },
  } as never),
  { readonly_empty_text: '未登记', kind: 'duration' },
  'record-form widget semantics come from the canonical descriptor widgetOptions',
);

const missingNativeIdentity = structuredClone(strictSnapshot);
delete missingNativeIdentity.layoutContract.containerTree[0].nativeIdentity;
delete missingNativeIdentity.layoutContract.containerTree[0].widgetList[0].nativeIdentity;
assert.throws(
  () => decodeContractV2Snapshot(missingNativeIdentity),
  /native layout occurrence requires nativeIdentity/,
  '2.7 must retain strict native occurrence authority',
);

const malformedActionIdentity = structuredClone(strictSnapshot);
malformedActionIdentity.actionContract.actionRuleList = [{
  actionId: 'action.open_form',
  triggerType: 'click',
  sourceWidgetId: 'page.row',
  targetIds: [],
  dispatchMode: 'server',
  targetScope: 'page',
  refreshMode: 'partial',
  nativeIdentity: { kind: 'button' },
}];
assert.throws(
  () => decodeContractV2Snapshot(malformedActionIdentity),
  /nativeIdentity/,
  '2.7 action identities must use the strict occurrence carrier',
);


const retiredActionIdentity = {
  ...malformedActionIdentity.actionContract.actionRuleList[0],
  nativeIdentity: { authoritative: true, name: 'open_form', native_locator: '/tree/button[1]' },
};
assert.throws(() => decodeContractV2ActionRule(retiredActionIdentity), /nativeIdentity/,
  'standalone action consumption must reject the retired identity carrier');
const aliasedRoot = structuredClone(strictSnapshot) as Record<string, unknown>;
aliasedRoot.page_info = aliasedRoot.pageInfo;
delete aliasedRoot.pageInfo;
assert.throws(() => decodeContractV2Snapshot(aliasedRoot), /pageInfo/,
  'retired root aliases cannot substitute current declarations');


// A structural group's fetch-time predicate must follow the same live draft
// used by the controls. Neither static hiding nor authority may be released.
for (const [id, reason, disabled, staticHidden, dependency] of [
  ['dynamic', 'NATIVE_MODIFIER_INVISIBLE', false, false, 'category'],
  ['authority', 'POLICY_HIDDEN', false, false, 'category'],
  ['disabled', 'NATIVE_MODIFIER_INVISIBLE', true, false, 'category'],
  ['static', 'NATIVE_MODIFIER_INVISIBLE', false, true, 'category'],
  ['unresolved', 'NATIVE_MODIFIER_UNRESOLVED', true, false, 'category'],
] as const) {
  snapshot.layoutContract.containerTree[0].children.push({
    containerId: id, containerType: 'group', type: 'group', title: id,
    nativeLocator: '/form[1]/sheet[1]/group[' + id + ']', occurrenceIndex: 1,
    nativeIdentity: nativeOccurrence(id, 'container', '/form[1]/sheet[1]/group[' + id + ']', 1),
    visible: !staticHidden, span: 24, columns: 2,
    children: id === 'dynamic' ? [fieldNode('group_content', 'field.group_content.occ.1', 1)] : [], widgetList: [],
    modifiers: {invisible: {kind: 'field_compare', field: dependency, operator: '!=', value: 'fund'}},
  } as never);
  snapshot.statusContract.containerStatus.push({
    containerId: id, visible: false, disabled, reasonCode: reason,
  });
}
snapshot.statusContract.widgetStatus.push({
  widgetId: 'field.group_content.occ.1', visible: true, readonly: true, required: false, disabled: false, auth: 'read',
});
const draft = reactive<Record<string, unknown>>({
  lifecycle_state: 'draft', sc_approval_state: 'draft', validation_status: 'no', category: 'salary',
});

const store = createContractV2Store(decodeContractV2Snapshot(snapshot));

assert.equal(
  store.buttonStatusByBackendIdentity.get(VISIBLE_BUTTON_IDENTITY)?.visible, true,
  'the store must index a declared button verdict by its occurrence-bound backendIdentity',
);
assert.equal(
  store.buttonStatusByBackendIdentity.get(HIDDEN_BUTTON_IDENTITY)?.visible, false,
  'the hidden declared button must keep its own verdict',
);
assert.equal(
  store.buttonStatusByBackendIdentity.size, 2,
  'a button verdict without a backendIdentity is not bound to any occurrence and must not be indexed',
);
assert.equal(
  store.buttonStatusById.get('btn.action_sc_submit')?.visible, true,
  'the existing btnId index must keep working',
);

// The store starts empty and is published once the record form is mounted, as
// the real page does: the layout must consume the contract that arrives.
const storeRef = ref<typeof store | null>(null);
let liveModifierValues: (() => Record<string, unknown>) | undefined;
const layout = useRecordFormLayout({
  v2ContractStore: storeRef,
  contractVisibleFields: computed(() => [] as string[]),
  onchangeModifiersPatch: ref<Record<string, Record<string, unknown>>>({}),
  formData: draft,
  modifierValues: () => liveModifierValues ? liveModifierValues() : draft,
  isQuickIntakeMode: computed(() => false),
  contractFieldLabel: (name: string) => name,
  fieldSemanticMeta: () => ({}),
  showHud: computed(() => false),
  advancedExpanded: ref(false),
  coreFieldNames: computed(() => [] as string[]),
  advancedFieldNames: computed(() => [] as string[]),
  renderProfile: computed(() => 'edit'),
  recordId: computed(() => 581),
  isContractFieldOrderEditable: computed(() => false),
  fieldOrderDraft: ref<string[]>([]),
  fieldOrderPreviewActive: ref(false),
  changedFieldGroupDraft: () => ({}),
  fieldMoveTargetDraft: {},
  fieldGroupBase: ref<Record<string, string>>({}),
  fieldGroupDraft: {},
  effectiveGroupVisible: () => true,
  lowCodeFormLayoutBase: ref([]),
  nativeLayoutVisibilityRevision: ref(0),
  nativeFormDesignFieldKeys: ref<string[]>([]),
  nativeFormDesignFieldLabels: ref<Record<string, string>>({}),
  formLayoutColumnsDraft: ref(1 as const),
  fieldVisibilityDraft: {},
  contractActionFromNativeRow: () => null,
  policyContext: computed(() => ({})),
  rights: computed(() => ({ create: true, write: true })),
  markFieldChanged: () => {},
  layoutNodes: () => [],
});

storeRef.value = store;
const normalized = layout.runtimeNativeFormLayoutNodes();
assert(normalized.length > 0, 'the published contract must reach the native layout tree');
const collect = (nodes: Array<Record<string, unknown>>, out: Array<Record<string, unknown>> = []) => {
  for (const node of nodes) {
    out.push(node);
    collect((node.children || []) as Array<Record<string, unknown>>, out);
  }
  return out;
};
const rows = collect(normalized as unknown as Array<Record<string, unknown>>);
const nodeByContainerId = (containerId: string) => {
  const found = rows.filter((row) => String(row.containerId || '') === containerId);
  assert.equal(found.length, 1, `the normalized declared tree must carry exactly one node ${containerId}`);
  return found[0];
};

const submit = layout.runtimeOccurrenceState(nodeByContainerId('action_sc_submit') as never);
assert.equal(submit.invisible, false, 'a contract-visible declared action must render');
assert.equal(submit.readonly, false, 'a button verdict is not field-level edit authority');
assert.equal(submit.required, false, 'a button verdict is not field-level required authority');
assert.equal(submit.disabled, false, 'the contract says the declared action is enabled');

const start = layout.runtimeOccurrenceState(nodeByContainerId('action_sc_start') as never);
assert.equal(start.invisible, true, 'a contract-invisible declared action must not render');

const approval = layout.runtimeOccurrenceState(nodeByContainerId('field.sc_approval_state.occ.1') as never);
assert.equal(approval.invisible, false, 'the contract-visible field must render');
assert.equal(approval.readonly, true, 'the field widget auth=read must stay readonly');
assert.equal(approval.required, true, 'the field widget required flag must survive');

const validation = layout.runtimeOccurrenceState(nodeByContainerId('field.validation_status.occ.1') as never);
assert.equal(validation.invisible, true, 'a native-modifier-invisible field must not render');

assert.equal(
  layout.runtimeOccurrenceState(nodeByContainerId('container.hidden.1') as never).invisible, true,
  'a container verdict without a widgetId must still be consumed by containerId',
);

const unknown = layout.runtimeOccurrenceState({
  type: 'button', name: 'no_such_declared_action',
  nativeLocator: '/form[1]/sheet[1]/div[1]/div[2]/div[1]/div[2]/button[99]', occurrenceIndex: 99,
} as never);
assert.equal(unknown.invisible, true, 'a node the contract never decided must fail closed');
assert.equal(unknown.reasonCode, 'V2_OCCURRENCE_STATUS_MISSING', 'and it must say why');

const plainField = layout.runtimeOccurrenceState({ type: 'field', name: 'partner_id' } as never);
assert.equal(plainField.invisible, false, 'a non-occurrence node keeps the field-name runtime state path');


const dynamic = nodeByContainerId('dynamic') as never;
assert.equal(layout.isNativeLayoutNodeVisible(dynamic), false);
draft.category = 'fund';
assert.equal(layout.runtimeOccurrenceState(dynamic).invisible, false);
assert.equal(layout.isNativeLayoutNodeVisible(dynamic), true);
assert(layout.baseNativeFormLayoutNodes.value.some(node =>
  JSON.stringify(node).includes('"containerId":"dynamic"')), 'live group reaches the rendered tree');
for (const id of ['authority', 'disabled', 'static', 'unresolved']) {
  assert.equal(layout.isNativeLayoutNodeVisible(nodeByContainerId(id) as never), false, id);
}
draft.category = 'salary';
assert.equal(layout.isNativeLayoutNodeVisible(dynamic), false, 'switching back hides the group');
assert(!JSON.stringify(layout.baseNativeFormLayoutNodes.value).includes('"containerId":"dynamic"'));
console.log('[contract_v2_occurrence_authority_test] PASS declared authority and reactive container cases');

// Missing dependencies are a visible contract defect under the strict engine,
// not an ordinary hidden group. Keep this negative case isolated from valid trees.
const missingDependencySnapshot = structuredClone(snapshot);
const missingNode = missingDependencySnapshot.layoutContract.containerTree[0].children.find((node) => node.containerId === 'dynamic')!;
missingNode.modifiers = { invisible: { kind: 'field_compare', field: 'absent_category', operator: '!=', value: 'fund' } };
storeRef.value = createContractV2Store(decodeContractV2Snapshot(missingDependencySnapshot));
const missingTarget = collect(layout.runtimeNativeFormLayoutNodes() as unknown as Array<Record<string, unknown>>)
  .find((node) => node.containerId === 'dynamic')!;
assert.throws(() => layout.isNativeLayoutNodeVisible(missingTarget as never), { name: 'ContractGapError' });
storeRef.value = store;

// Exercise the actual mounted layout hook, including its container dependency
// check, with a declared context and hostile same-name draft/model fields.
const contextual = structuredClone(snapshot);
const contextualNode = contextual.layoutContract.containerTree[0].children.find((node) => node.containerId === 'dynamic')!;
contextualNode.modifiers = { invisible: { kind: 'not', expr: {
  kind: 'value_truthy', semantics: 'python', value_expr: { kind: 'context_get', key: 'show_group', default: true },
} } };
contextual.dataContract.mainData['$native.context'] = { show_group: false };
draft['$native.context'] = { show_group: false };
for (const [context, expectedVisible] of [[{}, true], [{ show_group: true }, true], [{ show_group: false }, false]] as const) {
  contextual.dataContract.dataMeta.sourceContext = { context };
  storeRef.value = createContractV2Store(decodeContractV2Snapshot(contextual));
  const target = collect(layout.runtimeNativeFormLayoutNodes() as unknown as Array<Record<string, unknown>>)
    .find((node) => node.containerId === 'dynamic')!;
  assert.equal(layout.runtimeOccurrenceState(target as never).invisible, !expectedVisible);
  assert.equal(layout.isNativeLayoutNodeVisible(target as never), expectedVisible);
}
delete contextual.dataContract.dataMeta.sourceContext;
storeRef.value = createContractV2Store(decodeContractV2Snapshot(contextual));
assert.throws(() => layout.evaluateNativeModifierValue(contextualNode.modifiers.invisible), { name: 'ContractGapError' });
console.log('[contract_v2_occurrence_authority_test] PASS native context binding count=4');

// Restore a valid contract before the reactive scheduler flushes the fixture.
storeRef.value = store;
delete draft['$native.context'];

const { useOne2manyRuntime } = await import('../src/pages/contractForm/useOne2manyRuntime');
const collectionStore = structuredClone(snapshot);
collectionStore.dataContract.dataMeta.nativeModifierFieldTypes = { line_ids: 'one2many' };
storeRef.value = createContractV2Store(decodeContractV2Snapshot(collectionStore));
const collectionRows = useOne2manyRuntime({ model: () => 'x.document', recordId: () => 7,
  originalValues: () => ({ line_ids: [42] }), parentValues: () => ({}), onchangeLinePatches: () => [],
  resolveColumns: () => [{ name: 'name', label: 'Name', ttype: 'char' }], resolvePrimaryColumn: () => 'name',
  resolveRelationOptions: () => [], markFieldChanged: () => {},
});
liveModifierValues = () => collectionRows.projectModifierValues({ line_ids: [[0, 0, { name: 'New' }]], '$native.fieldTypes': { line_ids: 'one2many' } });
collectionRows.initRows('line_ids', [42]);
assert.equal(layout.evaluateNativeModifierValue({ kind: 'field_truthy', field: 'line_ids' }), true);
collectionRows.removeRow('line_ids', 'o2m_id_42');
assert.equal(layout.evaluateNativeModifierValue({ kind: 'field_truthy', field: 'line_ids' }), false);
collectionRows.restoreRow('line_ids', 'o2m_id_42');
assert.equal(layout.evaluateNativeModifierValue({ kind: 'field_truthy', field: 'line_ids' }), true);
liveModifierValues = undefined;
storeRef.value = store;
console.log('native layout live collection projection: passed');

// Required validation follows occurrence editability, not a flattened model flag.
const requiredNode = (name: string, readonly = false) => ({
  type: 'field', name, span: 12, readonly,
  fieldInfo: { name, type: 'char', required: true, readonly: false },
});
const requiredTree = ref<Array<Record<string, unknown>>>([
  requiredNode('shared', true),
  { type: 'group', hidden: true, children: [requiredNode('shared')] },
  { ...requiredNode('lines', true), children: [requiredNode('child_only')] },
]);
let occurrenceReadonly = false;
const requiredSchemas = useRecordFormFieldSchemas({
  v2ContractStore: ref(null), nativeFormLayoutNodes: requiredTree,
  isNativeFieldVisible: () => true,
  isNativeLayoutNodeVisible: (node: { hidden?: boolean }) => !node.hidden,
  runtimeOccurrenceState: () => ({ readonly: occurrenceReadonly, required: false }),
  recordId: computed(() => 0), rights: computed(() => ({ create: true, write: true })),
  contractFieldLabel: (name: string) => name,
  isContractFieldOrderEditable: computed(() => false),
  effectiveFieldSize: () => 'normal', rememberFormConfigFieldLabel: () => {},
} as never);
assert.deepEqual(requiredSchemas.nativeRequiredEditableFieldNames(), [],
  'readonly occurrence plus hidden editable duplicate must not demand an editor rule; child fields stay child-owned');
requiredTree.value[1].hidden = false;
assert.deepEqual(requiredSchemas.nativeRequiredEditableFieldNames(), ['shared'],
  'a visible editable duplicate requires validation even though another occurrence is readonly');
occurrenceReadonly = true;
assert.deepEqual(requiredSchemas.nativeRequiredEditableFieldNames(), [],
  'live readonly state uses the same occurrence projection as rendering');
occurrenceReadonly = false;
requiredTree.value.push(requiredNode('shared'));
assert.deepEqual(requiredSchemas.nativeRequiredEditableFieldNames(), ['shared'], 'duplicate business fields are deduplicated');
requiredTree.value = [{ ...requiredNode('missing'), nativeLocator: '/form/field[1]', occurrenceIndex: 1, widgetId: 'missing.widget' }];
assert.throws(() => requiredSchemas.nativeRequiredEditableFieldNames(),
  (error: unknown) => isContractGapError(error) && error.defect.missing.includes('fieldDescriptor'),
  'visible occurrence without its strict descriptor cannot become a legal empty validation scope');
requiredTree.value = [{ type: 'field', name: 'unknown', span: 12 }];
assert.throws(() => requiredSchemas.nativeRequiredEditableFieldNames(),
  (error: unknown) => isContractGapError(error), 'missing field metadata fails closed');
requiredTree.value = [];
assert.equal(requiredSchemas.nativeRequiredEditableFieldNames(), null, 'no native tree explicitly selects legacy validation authority');
console.log('[native-required-coverage] PASS cases=7');

// Selected action form identity survives decoding/normalization; malformed IDs fail closed.
const { resolveContractV2SourceContext } = await import('../src/app/contracts/v2/store');
const selectedForm = structuredClone(snapshot);
selectedForm.dataContract.dataMeta.sourceContext = { formViewId: 731 };
assert.equal(resolveContractV2SourceContext(createContractV2Store(decodeContractV2Snapshot(selectedForm))).formViewId, 731);
for (const formViewId of [0, -1, 1.5, '731', null, Number.MAX_SAFE_INTEGER + 1]) {
  selectedForm.dataContract.dataMeta.sourceContext = { formViewId } as never;
  assert.throws(() => decodeContractV2Snapshot(selectedForm));
}
console.log('[contract_v2_occurrence_authority_test] PASS selected form identity count=7');

const domainFixture = (await import('./fixtures/native_relation_domain.json')).default;
const domainSnapshot = structuredClone(snapshot);
function attachDomain(nodes: Array<Record<string, unknown>>): boolean {
  for (const node of nodes) {
    const widgets = node.widgetList as Array<Record<string, unknown>> | undefined;
    if (widgets?.length) {
      Object.assign(widgets[0].fieldDescriptor as object, {
        ...domainFixture.finalWireDescriptor,
        fieldCode: (widgets[0].fieldDescriptor as Record<string, unknown>).fieldCode,
      });
      return true;
    }
    if (Array.isArray(node.children) && attachDomain(node.children)) return true;
  }
  return false;
}
assert(attachDomain(domainSnapshot.layoutContract.containerTree as unknown as Array<Record<string, unknown>>));
const { resolveContractV2FormFieldMap } = await import('../src/app/contracts/v2/store');
const domainFields = resolveContractV2FormFieldMap(createContractV2Store(decodeContractV2Snapshot(domainSnapshot)));
assert(Object.values(domainFields).some(field => JSON.stringify((field as Record<string, unknown>).domain_expression) === JSON.stringify(domainFixture.finalWireDescriptor.domainExpression)));
console.log('[contract_v2_occurrence_authority_test] compiled domain normalized store PASS');

const { dynamicRelationDomainFromDescriptor } = await import('../src/pages/contractForm/relationDescriptor');
const projectedDomain = Object.values(domainFields).find(field => (field as Record<string, unknown>).domain_expression);
assert(projectedDomain);
for (const recordId of [false, 4] as const) {
  assert.deepEqual(dynamicRelationDomainFromDescriptor({
    descriptor: projectedDomain as never,
    resolveDependencyValue: field => field === 'id' ? recordId : undefined,
    normalizeDependencyValue: (_field, value) => value,
    currentFieldValue: () => undefined,
  }), [['id', 'not child_of', recordId]]);
}
console.log('[contract_v2_occurrence_authority_test] backend final wire through domain consumer PASS cases=2');
