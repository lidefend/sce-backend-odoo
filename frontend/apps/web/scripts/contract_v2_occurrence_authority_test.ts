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
import { computed, ref } from 'vue';
import { createContractV2Store } from '../src/app/contracts/v2/store';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import { useRecordFormLayout } from '../src/pages/contractForm/useRecordFormLayout';

const VISIBLE_BUTTON_IDENTITY = 'native_button:object:action_sc_submit:/form[1]/sheet[1]/div[1]/div[2]/div[1]/div[2]/button[5]:1';
const HIDDEN_BUTTON_IDENTITY = 'native_button:object:action_sc_start:/form[1]/sheet[1]/div[1]/div[2]/div[1]/div[2]/button[4]:1';

function buttonNode(name: string, backendIdentity: string, occurrenceIndex: number) {
  const locator = `/form[1]/sheet[1]/div[1]/div[2]/div[1]/div[2]/button[${occurrenceIndex}]`;
  return {
    containerId: name, containerType: 'button', type: 'button', name, string: name, title: name,
    nativeLocator: locator, occurrenceIndex, sourcePosition: occurrenceIndex,
    attributes: { name, type: 'object' },
    action: { name, actionId: `action.${name}`, backendIdentity, kind: 'object', level: 'body', intent: 'execute' },
    children: [], widgetList: [],
  };
}

function fieldNode(name: string, widgetId: string, occurrenceIndex: number) {
  const locator = `/form[1]/sheet[1]/div[1]/div[2]/div[1]/div[2]/field[${occurrenceIndex}]`;
  return {
    containerId: widgetId, containerType: 'field', type: 'field', name, widgetId,
    fieldCode: name, label: name,
    title: name, nativeLocator: locator, occurrenceIndex, sourcePosition: occurrenceIndex,
    fieldInfo: { name, type: 'selection', readonly: true, required: true, modifiers: { readonly: true } },
    children: [],
    widgetList: [{
      widgetId, widgetType: 'select', fieldCode: name, label: name, span: 12,
      componentKey: 'sc.select.remote', capabilities: [],
      componentConfig: {
        fieldType: 'selection', native_locator: locator, occurrence_index: occurrenceIndex,
        source_position: occurrenceIndex, readonly: true, required: true,
      },
      fieldDescriptor: { name, type: 'selection' },
      nativeLocator: locator, occurrenceIndex, sourcePosition: occurrenceIndex,
      ownerContainerId: widgetId,
    }],
  };
}

const snapshot = {
  pageInfo: {
    pageId: 'page.project.project.form', sceneKey: 'project.project.form', pageName: 'Project',
    model: 'project.project', viewType: 'form', layoutType: 'form', renderMode: 'governed',
    contractVersion: '2.2.0', clientType: 'web_pc',
  },
  layoutContract: {
    pageId: 'page.project.project.form', layoutType: 'form', adaptMode: 'pc',
    layoutHints: { mobileColumns: 1 },
    componentRegistry: {},
    // The real project stage row: one declared flex container holding the
    // declared stage fields and the declared stage actions, in declared order.
    containerTree: [{
      containerId: 'container.native.0', containerType: 'container', type: 'container',
      title: '', styleToken: 'd-flex flex-wrap gap-2', children: [
        buttonNode('action_sc_submit', VISIBLE_BUTTON_IDENTITY, 5),
        buttonNode('action_sc_start', HIDDEN_BUTTON_IDENTITY, 4),
        fieldNode('sc_approval_state', 'field.sc_approval_state.occ.1', 1),
        fieldNode('validation_status', 'field.validation_status.occ.1', 2),
        {
          containerId: 'container.hidden.1', containerType: 'container', type: 'container',
          title: '', nativeLocator: '/form[1]/sheet[1]/div[1]/div[2]/div[1]/div[3]', occurrenceIndex: 1,
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
      nativeIdentity: {
        authoritative: true, name: 'action_sc_submit', type: 'object',
        native_locator: '/form[1]/sheet[1]/div[1]/div[2]/div[1]/div[2]/button[5]', occurrence_index: 5,
      },
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
const layout = useRecordFormLayout({
  v2ContractStore: storeRef,
  contractVisibleFields: computed(() => [] as string[]),
  onchangeModifiersPatch: ref<Record<string, Record<string, unknown>>>({}),
  formData: { lifecycle_state: 'draft', sc_approval_state: 'draft', validation_status: 'no' },
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

console.log('[contract_v2_occurrence_authority_test] PASS declared authority consumption cases=14');
