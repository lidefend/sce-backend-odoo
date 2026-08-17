import assert from 'node:assert/strict';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import { createContractV2Store } from '../src/app/contracts/v2/store';
import type { ContractV2Snapshot } from '../src/app/contracts/v2/types';
import { presentContractV2Form } from '../src/app/presentation/contractFormPresenter';
import { composeCanonicalFormFloorplan } from '../src/app/presentation/canonicalFormFloorplan';
import {
  canonicalFieldToFormSection,
  canonicalNodeHasContent,
  canonicalSectionFields,
  visibleCanonicalChildren,
} from '../src/pages/contractForm/canonicalFormRenderer';
import { resolveCanonicalFormActionExecution, validateCanonicalFormActionExecutors } from '../src/pages/contractForm/canonicalFormActionExecutor';
import type { ContractAction } from '../src/pages/contractForm/types';

function snapshot(): ContractV2Snapshot {
  return {
    pageInfo: {
      pageId: 'page.x.document.form', sceneKey: 'x.document.form', pageName: 'Document',
      model: 'x.document', viewType: 'form', layoutType: 'form', renderMode: 'governed',
      contractVersion: '2.0.0', clientType: 'web_pc',
    },
    layoutContract: {
      pageId: 'page.x.document.form', layoutType: 'form', adaptMode: 'pc',
      layoutHints: { mobileColumns: 1 }, componentRegistry: {},
      containerTree: [{
        containerId: 'section.identity', containerType: 'group', type: 'group', title: 'Identity', span: 24,
        children: [{
          containerId: 'field.name', containerType: 'field', type: 'field', name: 'name', title: '', span: 12,
          children: [], widgetList: [{
            widgetId: 'field.name', widgetType: 'char', fieldCode: 'name', label: 'Name', span: 12,
            componentKey: 'sc.input.text', capabilities: [], componentConfig: {}, fieldType: 'char',
          }],
        }, {
          containerId: 'field.state', containerType: 'field', type: 'field', name: 'state', title: '', span: 12,
          children: [], widgetList: [{
            widgetId: 'field.state', widgetType: 'selection', fieldCode: 'state', label: 'State', span: 12,
            componentKey: 'sc.display.status', capabilities: [], componentConfig: {}, fieldType: 'selection',
          }],
        }],
        // Aggregated widgets must not duplicate descendant fields.
        widgetList: [{
          widgetId: 'field.name', widgetType: 'char', fieldCode: 'name', label: 'Name', span: 12,
          componentKey: 'sc.input.text', capabilities: [], componentConfig: {}, fieldType: 'char',
        }],
      }, {
        containerId: 'native.notebook', containerType: 'notebook', type: 'notebook', title: 'Related', span: 24,
        sourceAuthority: { projection_only: true, no_business_fact_authority: true },
        children: [{
          containerId: 'field.line_ids', containerType: 'field', type: 'field', name: 'line_ids', title: '', span: 24,
          children: [], widgetList: [{
            widgetId: 'field.line_ids', widgetType: 'one2many', fieldCode: 'line_ids', label: 'Lines', span: 24,
            componentKey: 'sc.relation.table', capabilities: [], componentConfig: {}, fieldType: 'one2many',
          }],
        }], widgetList: [],
      }, {
        containerId: 'native.attachment', containerType: 'attachment', type: 'attachment', title: 'Attachments', span: 24,
        sourceAuthority: { projection_only: true, no_business_fact_authority: true }, children: [], widgetList: [],
      }, {
        containerId: 'native.chatter', containerType: 'chatter', type: 'chatter', title: 'Activity', span: 24,
        sourceAuthority: { projection_only: true, no_business_fact_authority: true }, children: [], widgetList: [],
      }],
    },
    actionContract: {
      actionRuleList: [{
        actionId: 'action.submit', backendIdentity: 'button:object:action_submit', triggerType: 'click',
        sourceWidgetId: 'page.root', targetIds: [], dispatchMode: 'serverBlocking', targetScope: 'page',
        refreshMode: 'full', actionKey: 'action_submit', label: 'Submit', allowed: true, enabled: true,
        disabled: false, visibleProfiles: ['edit', 'readonly'], presentation: { tier: 'primary' },
        actionSafety: { level: 'danger', requiresConfirmation: true },
      }], dependencyGraph: { 'action.submit': ['field.name'] },
    },
    statusContract: {
      globalStatus: { pageVisible: true, pageAuth: 'edit', reasonCode: '' },
      widgetStatus: [
        { widgetId: 'field.name', visible: true, readonly: false, required: true, disabled: false },
        { widgetId: 'field.state', visible: false, readonly: true, required: false, disabled: true, reasonCode: 'STATE_CONTEXT_ONLY' },
        { widgetId: 'field.line_ids', visible: true, readonly: true, required: false, disabled: false },
      ],
      buttonStatus: [{ btnId: 'action.submit', visible: true, disabled: false }],
      containerStatus: [], selectorStatus: [],
    },
    dataContract: {
      mainData: { name: 'D-001', state: 'draft', line_ids: [7] }, tableRows: {}, relationRows: {},
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

function collectFields(nodes: ReturnType<typeof presentContractV2Form>['zones']['primary']) {
  return nodes.flatMap((node): typeof node.fields => [...node.fields, ...collectFields(node.children)]);
}

const source = snapshot();
const before = JSON.stringify(source);
const store = createContractV2Store(decodeContractV2Snapshot(source));
const model = presentContractV2Form(store, 'edit');
assert.equal(JSON.stringify(source), before, 'presenter must not mutate normalized input');
assert.equal(model.identity.sourceContractSha256, 'contract-sha');
assert.deepEqual(model.zones.subordinate.map((node) => node.kind), ['notebook', 'attachment', 'chatter']);
const fields = collectFields([...model.zones.primary, ...model.zones.subordinate]);
assert.deepEqual(fields.map((field) => field.fieldCode), ['name', 'state', 'line_ids']);
assert.equal(fields.find((field) => field.fieldCode === 'name')?.required, true);
assert.equal(fields.find((field) => field.fieldCode === 'state')?.visible, false);
assert.equal(model.actionBar[0]?.actionRef, store.snapshot.actionContract.actionRuleList[0]);
assert.deepEqual(model.actionBar[0]?.actionRef, source.actionContract.actionRuleList[0]);
assert.equal(model.actionBar[0]?.enabled, true);
assert.equal(presentContractV2Form(store, 'create').actionBar[0]?.visible, false);
assert.deepEqual(presentContractV2Form(store, 'edit'), model, 'presenter must be deterministic');

const editFloorplan = composeCanonicalFormFloorplan(model);
assert.deepEqual(editFloorplan.taskNodes.map((node) => node.nodeId), ['section.identity']);
assert.deepEqual(editFloorplan.contextNodes, []);
assert.deepEqual(
  editFloorplan.subordinateNodes.map((node) => node.nodeId),
  model.zones.subordinate.map((node) => node.nodeId),
  'floorplan composition must preserve subordinate node identity and order',
);
const readonlyFloorplan = composeCanonicalFormFloorplan(presentContractV2Form(store, 'readonly'));
assert.deepEqual(
  readonlyFloorplan.taskNodes.map((node) => node.nodeId),
  ['section.identity'],
  'readonly pages must keep the canonical primary content in the main canvas',
);
assert.deepEqual(readonlyFloorplan.contextNodes, []);

const contextRailSnapshot = snapshot();
contextRailSnapshot.layoutContract.containerTree.splice(1, 0, {
  containerId: 'section.context', containerType: 'group', type: 'group', title: 'Context', span: 24,
  children: [{
    containerId: 'field.reference', containerType: 'field', type: 'field', name: 'reference', title: '', span: 24,
    children: [], widgetList: [{
      widgetId: 'field.reference', widgetType: 'char', fieldCode: 'reference', label: 'Reference', span: 24,
      componentKey: 'sc.display.text', capabilities: [], componentConfig: {}, fieldType: 'char',
    }],
  }], widgetList: [],
});
contextRailSnapshot.statusContract.widgetStatus.push({
  widgetId: 'field.reference', visible: true, readonly: true, required: false, disabled: false,
});
contextRailSnapshot.dataContract.mainData.reference = 'REF-001';
const contextRailModel = presentContractV2Form(createContractV2Store(contextRailSnapshot), 'edit');
const contextRailFloorplan = composeCanonicalFormFloorplan(contextRailModel);
assert.deepEqual(contextRailFloorplan.taskNodes.map((node) => node.nodeId), ['section.identity']);
assert.deepEqual(contextRailFloorplan.contextNodes.map((node) => node.nodeId), ['section.context']);
assert.deepEqual(
  collectFields([...contextRailFloorplan.taskNodes, ...contextRailFloorplan.contextNodes]).map((field) => field.widgetId),
  collectFields(contextRailModel.zones.primary).map((field) => field.widgetId),
  'floorplan lanes must preserve the exact canonical field identity set and order within each lane',
);

const runtimeValueModel = presentContractV2Form(store, 'edit', { name: 'D-002' });
assert.equal(
  collectFields(runtimeValueModel.zones.primary).find((field) => field.fieldCode === 'name')?.value,
  'D-002',
  'runtime edits must update the ephemeral render model without changing normalized authority',
);

const relationSnapshot = snapshot();
relationSnapshot.layoutContract.containerTree[0].children.push({
  containerId: 'field.project_id', containerType: 'field', type: 'field', name: 'project_id', title: '', span: 12,
  children: [], widgetList: [{
    widgetId: 'field.project_id', widgetType: 'many2one', fieldCode: 'project_id', label: 'Project', span: 12,
    componentKey: 'sc.relation.many2one', capabilities: [],
    componentConfig: { relation: 'project.project' }, fieldType: 'many2one',
  }],
});
relationSnapshot.statusContract.widgetStatus.push({
  widgetId: 'field.project_id', visible: true, readonly: true, required: false, disabled: false,
});
relationSnapshot.dataContract.mainData.project_id = [852, 'Road Project'];
const relationModel = presentContractV2Form(createContractV2Store(relationSnapshot), 'readonly', { project_id: 852 });
const relationField = collectFields(relationModel.zones.primary).find((field) => field.fieldCode === 'project_id')!;
assert.deepEqual(
  relationField.value,
  { id: 852, displayName: 'Road Project', model: 'project.project' },
  'runtime scalar relation ids must retain the normalized business display identity',
);
const renderedRelation = canonicalFieldToFormSection(relationField);
assert.deepEqual(
  { value: renderedRelation.value, inputValue: renderedRelation.inputValue, text: renderedRelation.many2oneTextValue },
  { value: 'Road Project', inputValue: 852, text: 'Road Project' },
  'all drivers must receive the same relation display name instead of a naked database id',
);

const emptySnapshot = snapshot();
emptySnapshot.dataContract.mainData.name = false;
const emptyName = collectFields(presentContractV2Form(createContractV2Store(emptySnapshot), 'readonly').zones.primary)
  .find((field) => field.fieldCode === 'name');
assert.equal(emptyName?.value, null, 'non-boolean Odoo false values must normalize to one empty display fact');

const duplicateTitleSnapshot = snapshot();
duplicateTitleSnapshot.layoutContract.containerTree[1].title = 'Related';
duplicateTitleSnapshot.layoutContract.containerTree[1].children[0].title = 'Related';
const duplicateTitleModel = presentContractV2Form(createContractV2Store(duplicateTitleSnapshot), 'readonly');
assert.equal(
  duplicateTitleModel.zones.subordinate[0].children[0].title,
  '',
  'a nested subordinate node must not repeat the same visual title as its parent',
);

const readonlyModel = presentContractV2Form(store, 'readonly');
assert.equal(
  collectFields(readonlyModel.zones.primary).find((field) => field.fieldCode === 'name')?.readonly,
  true,
  'readonly route mode must remain authoritative even when the widget status is editable',
);

const rowActionSnapshot = snapshot();
rowActionSnapshot.actionContract.actionRuleList.push({
  ...rowActionSnapshot.actionContract.actionRuleList[0],
  actionId: 'action.open_form', backendIdentity: 'button:object:open_form', actionKey: 'open_form',
  sourceWidgetId: 'page.row', targetScope: 'runtime', presentation: { tier: 'secondary' },
});
rowActionSnapshot.statusContract.buttonStatus.push({ btnId: 'action.open_form', visible: true, disabled: false });
assert.deepEqual(
  presentContractV2Form(createContractV2Store(rowActionSnapshot), 'readonly').actionBar.map((action) => action.key),
  ['action_submit'],
  'row/runtime actions must remain normalized evidence and must not become form action-bar controls',
);

const readOnlyPrincipal = snapshot();
readOnlyPrincipal.statusContract.globalStatus.pageAuth = 'read';
const readOnlyPrincipalModel = presentContractV2Form(createContractV2Store(readOnlyPrincipal), 'edit');
assert.equal(
  collectFields(readOnlyPrincipalModel.zones.primary).find((field) => field.fieldCode === 'name')?.readonly,
  true,
  'page read authority must not become editable through the requested route mode',
);

const unresolvedWidgetStatus = snapshot();
unresolvedWidgetStatus.statusContract.widgetStatus = unresolvedWidgetStatus.statusContract.widgetStatus
  .filter((status) => status.widgetId !== 'field.name');
const unresolvedField = collectFields(
  presentContractV2Form(createContractV2Store(unresolvedWidgetStatus), 'edit').zones.primary,
).find((field) => field.fieldCode === 'name');
assert.deepEqual(
  { visible: unresolvedField?.visible, readonly: unresolvedField?.readonly, disabled: unresolvedField?.disabled, reasonCode: unresolvedField?.reasonCode },
  { visible: false, readonly: true, disabled: true, reasonCode: 'WIDGET_STATUS_UNRESOLVED' },
  'a field without normalized status authority must fail closed',
);

const hiddenContainer = snapshot();
hiddenContainer.statusContract.containerStatus = [{ containerId: 'section.identity', visible: false, disabled: false }];
const hiddenContainerFields = collectFields(presentContractV2Form(createContractV2Store(hiddenContainer), 'edit').zones.primary);
assert.equal(
  hiddenContainerFields.find((field) => field.fieldCode === 'name')?.visible,
  false,
  'container visibility must constrain descendant fields',
);

const disabledContainer = snapshot();
disabledContainer.statusContract.containerStatus = [{ containerId: 'section.identity', visible: true, disabled: true }];
const disabledContainerField = collectFields(
  presentContractV2Form(createContractV2Store(disabledContainer), 'edit').zones.primary,
).find((field) => field.fieldCode === 'name');
assert.deepEqual(
  { readonly: disabledContainerField?.readonly, disabled: disabledContainerField?.disabled },
  { readonly: true, disabled: true },
  'container disabled state must constrain descendant fields',
);

const productionNativeChildren = snapshot() as ContractV2Snapshot & { layoutContract: { containerTree: Array<Record<string, unknown>> } };
delete productionNativeChildren.layoutContract.containerTree[0].span;
const nativeChild = productionNativeChildren.layoutContract.containerTree[0].children[0] as Record<string, unknown>;
nativeChild.widgetId = 'field.name';
delete nativeChild.containerId;
delete nativeChild.containerType;
delete nativeChild.title;
delete nativeChild.span;
const normalizedNativeChild = decodeContractV2Snapshot(productionNativeChildren).layoutContract.containerTree[0].children[0];
assert.equal(decodeContractV2Snapshot(productionNativeChildren).layoutContract.containerTree[0].span, 24);
assert.equal(normalizedNativeChild.containerId, 'field.name');
assert.equal(normalizedNativeChild.containerType, 'field');
assert.equal(normalizedNativeChild.title, 'name');
assert.equal(normalizedNativeChild.span, 24);

const aggregatedNativeChildren = snapshot();
aggregatedNativeChildren.layoutContract.containerTree[0].children[0].widgetList = [];
const aggregatedFields = collectFields(presentContractV2Form(createContractV2Store(aggregatedNativeChildren), 'edit').zones.primary);
assert.deepEqual(aggregatedFields.map((field) => field.fieldCode), ['name', 'state']);

const duplicateAcrossRoots = snapshot();
duplicateAcrossRoots.layoutContract.containerTree.splice(1, 0, {
  containerId: 'legacy.identity.mirror', containerType: 'group', type: 'group', title: 'Legacy mirror', span: 24,
  children: [], widgetList: [{
    widgetId: 'field.name', widgetType: 'char', fieldCode: 'name', label: 'Name', span: 12,
    componentKey: 'sc.input.text', capabilities: [], componentConfig: {}, fieldType: 'char',
  }],
});
const deDuplicatedFields = collectFields(
  presentContractV2Form(createContractV2Store(duplicateAcrossRoots), 'edit').zones.primary,
);
assert.deepEqual(
  deDuplicatedFields.map((field) => field.widgetId),
  ['field.name', 'field.state'],
  'one canonical widget identity must render once even when legacy and product roots both carry it',
);

const renderedName = canonicalFieldToFormSection(deDuplicatedFields[0]);
assert.deepEqual(
  { key: renderedName.key, name: renderedName.name, value: renderedName.value, readonly: renderedName.readonly },
  { key: 'field.name', name: 'name', value: 'D-001', readonly: false },
  'renderer mapping must preserve canonical widget identity and state without native layout input',
);
assert.equal(canonicalNodeHasContent(model.zones.subordinate.find((node) => node.kind === 'chatter')!), true);
assert.deepEqual(
  canonicalSectionFields(model.zones.primary[0]).map((field) => field.fieldCode),
  ['name'],
  'a section mechanically owns the fields carried by its direct field nodes',
);
assert.equal(
  visibleCanonicalChildren(model.zones.primary[0]).some((node) => node.kind === 'field'),
  false,
  'leaf field nodes must not become duplicate visual sections',
);

const invalidNativeChild = snapshot() as ContractV2Snapshot & { layoutContract: { containerTree: Array<Record<string, unknown>> } };
invalidNativeChild.layoutContract.containerTree[0].children = [{ children: [], widgetList: [] }];
assert.throws(() => decodeContractV2Snapshot(invalidNativeChild), /requires a stable native identity/);

const invalidExplicitSpan = snapshot();
invalidExplicitSpan.layoutContract.containerTree[0].span = 0;
assert.throws(() => decodeContractV2Snapshot(invalidExplicitSpan), /span must be an integer between 1 and 24/);

const missingIdentity = snapshot();
delete missingIdentity.actionContract.actionRuleList[0].backendIdentity;
assert.throws(() => presentContractV2Form(createContractV2Store(missingIdentity), 'edit'), /ACTION_REFERENCE_MISSING/);

const disabledSecondaryPrimary = snapshot();
disabledSecondaryPrimary.actionContract.actionRuleList.push({
  ...disabledSecondaryPrimary.actionContract.actionRuleList[0],
  actionId: 'action.blocked', backendIdentity: 'button:object:action_blocked', actionKey: 'action_blocked',
  enabled: true, disabled: false,
});
disabledSecondaryPrimary.statusContract.buttonStatus.push({
  btnId: 'btn.action_blocked', visible: true, disabled: true, reasonCode: 'ACTION_NOT_AVAILABLE_IN_STATE',
});
const disabledSecondaryPrimaryModel = presentContractV2Form(
  createContractV2Store(disabledSecondaryPrimary),
  'edit',
);
assert.equal(
  disabledSecondaryPrimaryModel.actionBar.filter((action) => action.visible && action.enabled && action.tier === 'primary').length,
  1,
  'a visible disabled primary must not compete with the one effective primary action',
);
assert.deepEqual(
  disabledSecondaryPrimaryModel.actionBar.find((action) => action.key === 'action_blocked'),
  {
    key: 'action_blocked', label: 'Submit', tier: 'primary', visible: true, enabled: false,
    reasonCode: 'ACTION_NOT_AVAILABLE_IN_STATE', visibleProfiles: ['edit', 'readonly'],
    safety: { level: 'danger', requiresConfirmation: true },
    actionRef: disabledSecondaryPrimary.actionContract.actionRuleList[1],
  },
  'disabled action evidence must remain visible and fail closed',
);
assert.deepEqual(
  composeCanonicalFormFloorplan(disabledSecondaryPrimaryModel).blockedActions.map((action) => action.key),
  ['action_blocked'],
  'a blocked canonical primary must remain explicit floorplan evidence',
);

const duplicatePrimary = snapshot();
duplicatePrimary.actionContract.actionRuleList.push({
  ...duplicatePrimary.actionContract.actionRuleList[0],
  actionId: 'action.other', backendIdentity: 'button:object:action_other', actionKey: 'action_other',
});
duplicatePrimary.statusContract.buttonStatus.push({ btnId: 'action.other', visible: true, disabled: false });
assert.throws(() => presentContractV2Form(createContractV2Store(duplicatePrimary), 'edit'), /MULTIPLE_PRIMARY_ACTIONS/);

const normalizedAction = snapshot().actionContract.actionRuleList[0];
const readonlySaveSnapshot = snapshot();
readonlySaveSnapshot.actionContract.actionRuleList = [{
  ...readonlySaveSnapshot.actionContract.actionRuleList[0],
  actionId: 'form.save', backendIdentity: 'contract_action:form.save',
  visibleProfiles: ['create', 'edit', 'readonly'],
}];
readonlySaveSnapshot.statusContract.buttonStatus = [{ btnId: 'form.save', visible: true, disabled: false }];
assert.equal(
  presentContractV2Form(createContractV2Store(readonlySaveSnapshot), 'readonly').actionBar[0]?.visible,
  false,
  'readonly routes must not expose the generic save mutation even when the normalized rule lists readonly',
);
assert.equal(
  presentContractV2Form(createContractV2Store(readonlySaveSnapshot), 'edit').actionBar[0]?.visible,
  true,
  'the same normalized save action remains available in edit mode',
);
const contractAction = {
  key: 'action_submit', backendIdentity: 'button:object:action_submit', label: 'Submit', kind: 'object',
  level: 'header', selection: 'none', actionId: null, methodName: 'action_submit', targetModel: 'x.document',
  context: {}, domainRaw: '', target: '', url: '', enabled: true, hint: '', intent: '', semantic: '',
  sourceWidgetId: 'page.root', clientMode: '', visibleProfiles: ['edit', 'readonly'], requiredParams: [], requiresReason: false,
} satisfies ContractAction;
assert.deepEqual(
  resolveCanonicalFormActionExecution(
    { ...normalizedAction, actionId: 'form.save', backendIdentity: 'contract_action:form.save' },
    [],
  ),
  { kind: 'save' },
  'standard normalized form.save must use the existing unified save executor',
);
assert.deepEqual(
  resolveCanonicalFormActionExecution(normalizedAction, [contractAction]),
  { kind: 'contract-action', action: contractAction },
  'business actions must resolve only by their normalized backend identity',
);
assert.deepEqual(
  resolveCanonicalFormActionExecution(normalizedAction, []),
  { kind: 'error', reasonCode: 'CANONICAL_FORM_ACTION_EXECUTION_ADAPTER_MISSING' },
  'an unmapped normalized action must fail closed',
);
assert.deepEqual(
  resolveCanonicalFormActionExecution(normalizedAction, [contractAction, { ...contractAction }]),
  { kind: 'error', reasonCode: 'CANONICAL_FORM_ACTION_REFERENCE_AMBIGUOUS' },
  'a duplicated normalized backend identity must fail closed',
);
assert.equal(
  validateCanonicalFormActionExecutors([
    { visible: true, enabled: true, actionRef: { ...normalizedAction, actionId: 'form.save', backendIdentity: 'contract_action:form.save' } },
    { visible: true, enabled: false, actionRef: { ...normalizedAction, enabled: true, disabled: false, backendIdentity: 'button:object:unmapped_disabled' } },
  ], []),
  null,
  'save and visible disabled actions keep the canonical page usable without inventing an executor',
);
assert.deepEqual(
  validateCanonicalFormActionExecutors([{ visible: true, enabled: true, actionRef: normalizedAction }], []),
  {
    reasonCode: 'CANONICAL_FORM_ACTION_EXECUTION_ADAPTER_MISSING',
    actionId: 'action.submit',
    backendIdentity: 'button:object:action_submit',
  },
  'an executable action without an exact unified executor adapter must block canonical cutover',
);

console.log('[canonical_form_presenter_test] PASS cases=45');
