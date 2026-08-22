import assert from 'node:assert/strict';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import {
  createContractV2Store, resolveContractV2EffectiveFormCapabilities, resolveContractV2FieldDescriptorMap,
} from '../src/app/contracts/v2/store';
import type { ContractV2Snapshot } from '../src/app/contracts/v2/types';
import { presentContractV2Form } from '../src/app/presentation/contractFormPresenter';
import { composeCanonicalFormFloorplan } from '../src/app/presentation/canonicalFormFloorplan';
import {
  canonicalFieldToFormSection,
  canonicalNodeHasContent,
  canonicalSectionFields,
  visibleCanonicalChildren,
} from '../src/pages/contractForm/canonicalFormRenderer';
import {
  collectCanonicalFormActions,
  resolveCanonicalFormActionExecution,
  validateCanonicalFormActionExecutors,
} from '../src/pages/contractForm/canonicalFormActionExecutor';
import type { ContractAction } from '../src/pages/contractForm/types';
import { contractActionConfirmationPrompt } from '../src/pages/contractForm/actionContract';
import { canonicalFormActionIconClass } from '../src/pages/contractForm/canonicalFormActionIcon';
import { buildCanonicalNativeFormBridge } from '../src/pages/contractForm/canonicalNativeFormBridge';
import { normalizeContractFieldValue } from '../src/pages/contractForm/valueUtils';
import {
  formatMonetaryDisplayValue,
  monetaryInputStep,
  normalizeMonetaryDigits,
  resolveCurrencyDisplayLabel,
} from '../src/components/template/formSection.mapper';

assert.deepEqual(normalizeMonetaryDigits([16, 2]), [16, 2]);
assert.equal(normalizeMonetaryDigits([16, -1]), undefined);
assert.equal(normalizeMonetaryDigits([2, 3]), undefined);
assert.equal(resolveCurrencyDisplayLabel([7, 'USD']), 'USD');
assert.equal(resolveCurrencyDisplayLabel({ id: 7, symbol: '€', name: 'EUR' }), 'EUR');
assert.equal(monetaryInputStep([16, 2]), '0.01');
assert.equal(monetaryInputStep(undefined), 'any');
assert.equal(formatMonetaryDisplayValue(1234.5, [16, 2], 'USD', 'en-US'), '$1,234.50');
assert.equal(formatMonetaryDisplayValue(1234.5, [16, 1], '元', 'en-US'), '1,234.5 元');
assert.equal(formatMonetaryDisplayValue('', [16, 2], 'USD', 'en-US'), '-');
assert.equal(normalizeContractFieldValue({
  name: 'amount', value: '12.345', descriptor: { type: 'monetary', digits: [16, 2] } as never,
  originalValue: 0, buildOne2manyValue: () => [],
}), 12.35);

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
          label: 'Name', nolabel: true,
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
        disabled: false, visibleProfiles: ['edit', 'readonly'], presentation: { tier: 'primary', icon: 'fa-check' },
        actionSafety: { level: 'danger', requiresConfirmation: true },
      }], dependencyGraph: { 'action.submit': ['field.name'] },
    },
    statusContract: {
      globalStatus: {
        pageVisible: true,
        pageAuth: 'edit',
        reasonCode: '',
        modelRights: { read: true, write: true, create: true, unlink: true, duplicate: true },
        recordRights: { read: true, write: true, create: true, unlink: true, duplicate: true },
        viewCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        entryCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        effectiveRecordCapabilities: { read: true, write: true, create: true, unlink: true, duplicate: true },
        effectiveRenderProfile: 'edit',
      },
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

function collectTexts(nodes: ReturnType<typeof presentContractV2Form>['zones']['primary']): string[] {
  return nodes.flatMap((node) => [node.text, ...collectTexts(node.children)]).filter(Boolean);
}

const source = snapshot();
const before = JSON.stringify(source);
const store = createContractV2Store(decodeContractV2Snapshot(source));
assert.deepEqual(resolveContractV2EffectiveFormCapabilities(store), {
  read: true, write: true, create: true, unlink: true, duplicate: true,
});
assert.equal(store.snapshot.statusContract.globalStatus.effectiveRenderProfile, 'edit');
const descriptorSelectionSnapshot = snapshot();
descriptorSelectionSnapshot.layoutContract.containerTree[0].children[1].widgetList[0].fieldDescriptor = {
  name: 'state', type: 'selection', widget: 'statusbar', selection: [['draft', 'Draft'], ['done', 'Done']],
};
assert.deepEqual(
  resolveContractV2FieldDescriptorMap(createContractV2Store(descriptorSelectionSnapshot)).state?.selection,
  [['draft', 'Draft'], ['done', 'Done']],
  'native fieldDescriptor selection must remain available to statusbar rendering',
);
const model = presentContractV2Form(store, 'edit');
assert.equal(JSON.stringify(source), before, 'presenter must not mutate normalized input');
assert.equal(model.identity.sourceContractSha256, 'contract-sha');
assert.deepEqual(model.zones.subordinate.map((node) => node.kind), ['notebook', 'attachment', 'chatter']);
const fields = collectFields([...model.zones.primary, ...model.zones.subordinate]);
assert.deepEqual(fields.map((field) => field.fieldCode), ['name', 'state', 'line_ids']);
assert.equal(fields.find((field) => field.fieldCode === 'name')?.required, true);
assert.equal(fields.find((field) => field.fieldCode === 'name')?.hideLabel, true);
assert.equal(fields.find((field) => field.fieldCode === 'state')?.hideLabel, false);
assert.equal(canonicalFieldToFormSection(fields.find((field) => field.fieldCode === 'name')!).hideLabel, true);
assert.equal(fields.find((field) => field.fieldCode === 'state')?.visible, false);
assert.equal(model.actionBar[0]?.actionRef, store.snapshot.actionContract.actionRuleList[0]);
assert.deepEqual(model.actionBar[0]?.actionRef, source.actionContract.actionRuleList[0]);
assert.equal(model.actionBar[0]?.enabled, true);
assert.equal(model.actionBar[0]?.icon, 'fa-check');
assert.equal(canonicalFormActionIconClass(model.actionBar[0]?.icon || ''), 'check');
assert.equal(canonicalFormActionIconClass('fa-check injected-class'), '');
assert.equal(canonicalFormActionIconClass('oi-check'), '');
assert.equal(presentContractV2Form(store, 'create').actionBar[0]?.visible, false);

const bodyActionSnapshot = structuredClone(snapshot());
bodyActionSnapshot.layoutContract.containerTree[0].children.push({
  containerId: 'button.action_open_lines', containerType: 'button', type: 'button', title: 'Open Lines', span: 24,
  action: { actionId: 'action.open_lines', backendIdentity: 'window_action:91' },
  children: [], widgetList: [],
});
bodyActionSnapshot.actionContract.actionRuleList.push({
  actionId: 'action.open_lines', backendIdentity: 'window_action:91', triggerType: 'click',
  sourceWidgetId: 'button.action_open_lines', targetIds: [], dispatchMode: 'clientRoute', targetScope: 'page',
  refreshMode: 'none', actionKey: 'open_lines', label: 'Open Lines', allowed: true, enabled: true,
  disabled: false, visibleProfiles: ['edit', 'readonly'], presentation: { tier: 'overflow' },
});
bodyActionSnapshot.statusContract.buttonStatus.push({ btnId: 'action.open_lines', visible: true, disabled: false });
const bodyActionModel = presentContractV2Form(createContractV2Store(bodyActionSnapshot), 'readonly');
const bodyActionNode = bodyActionModel.zones.primary[0].children.find((node) => node.nodeId === 'button.action_open_lines');
assert.equal(bodyActionNode?.action?.actionRef.backendIdentity, 'window_action:91');
assert.equal(canonicalNodeHasContent(bodyActionNode!), true);
assert.deepEqual(bodyActionModel.actionBar.map((action) => action.key), ['action_submit']);
const nativeBridge = buildCanonicalNativeFormBridge(bodyActionModel);
assert.deepEqual(
  nativeBridge.subordinateNodes.map((node) => node.type),
  ['notebook', 'container'],
  'canonical native bridge must keep notebook/attachment structure while collaboration stays in its governed panel',
);
const notebookPage = nativeBridge.subordinateNodes[0].children?.[0];
assert.equal(notebookPage?.type, 'page', 'a native notebook without explicit pages must retain its children in a stable default page');
assert.deepEqual(
  nativeBridge.fieldSchemasForNodes(notebookPage?.children || []).map((field) => [field.key, field.name]),
  [['field.line_ids', 'line_ids']],
  'canonical widget occurrence identity and record field name must remain separate through the native renderer bridge',
);
const bridgedBodyAction = nativeBridge.primaryNodes[0].children?.find((node) => node.type === 'button');
assert.equal(
  nativeBridge.actionForPayload(bridgedBodyAction?.action || {})?.backendIdentity,
  'window_action:91',
  'body action execution must resolve through the same canonical backend identity after native structure rendering',
);
assert.deepEqual(
  nativeBridge.actionStateForNode(bridgedBodyAction || {} as never),
  { disabled: false, title: '' },
  'canonical button status must remain authoritative when the native renderer asks for interaction state',
);

const nativeOccurrenceActionSnapshot = structuredClone(snapshot());
nativeOccurrenceActionSnapshot.layoutContract.containerTree[0].children.push({
  containerId: 'button.native.submit', containerType: 'button', type: 'button', title: 'Submit Native', span: 24,
  action: { native_identity: { type: 'object', name: 'action_submit', native_locator: '/form/header/button[1]', occurrence_index: 1 } },
  children: [], widgetList: [],
});
nativeOccurrenceActionSnapshot.actionContract.actionRuleList[0].nativeIdentity = {
  type: 'object', name: 'action_submit', native_locator: '/form/header/button[1]', occurrence_index: 1,
};
const nativeOccurrenceModel = presentContractV2Form(createContractV2Store(nativeOccurrenceActionSnapshot), 'edit');
assert.equal(
  nativeOccurrenceModel.zones.primary[0].children.find((node) => node.nodeId === 'button.native.submit')?.action?.actionRef.backendIdentity,
  'button:object:action_submit',
  'native snake-case occurrence identity must resolve to the canonical action rule',
);
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

const semanticReadonlySnapshot = snapshot();
semanticReadonlySnapshot.layoutContract.containerTree[0].children[0].formStructureRole = {
  role: 'summary', slot: 'identity', group: 'identity',
};
semanticReadonlySnapshot.layoutContract.containerTree[0].children[1].widgetList[0].formStructureRole = {
  role: 'risk', slot: 'identity', group: 'identity',
};
semanticReadonlySnapshot.statusContract.widgetStatus[1] = {
  widgetId: 'field.state', visible: true, readonly: true, required: false, disabled: false,
};
const semanticReadonlyFloorplan = composeCanonicalFormFloorplan(presentContractV2Form(
  createContractV2Store(semanticReadonlySnapshot),
  'readonly',
));
assert.deepEqual(
  collectFields(semanticReadonlyFloorplan.summaryNodes).map((field) => [field.fieldCode, field.semanticRole]),
  [['name', 'summary']],
  'readonly summary must be projected mechanically from the normalized field-node formStructureRole',
);
assert.deepEqual(
  collectFields(semanticReadonlyFloorplan.riskNodes).map((field) => [field.fieldCode, field.semanticRole]),
  [['state', 'risk']],
  'readonly risk facts must not fall back into the task canvas',
);
assert.deepEqual(semanticReadonlyFloorplan.taskNodes, []);
assert.deepEqual(semanticReadonlyFloorplan.contextNodes, []);
const mixedSemanticTextModel = presentContractV2Form(createContractV2Store(semanticReadonlySnapshot), 'readonly');
const mixedSemanticTextRoot = mixedSemanticTextModel.zones.primary[0];
mixedSemanticTextRoot.text = 'unassigned native guidance';
const taskProjectionChild = mixedSemanticTextRoot.children.find((node) => node.semanticRole === 'summary')!;
taskProjectionChild.semanticRole = 'task';
taskProjectionChild.fields = taskProjectionChild.fields.map((field) => ({ ...field, semanticRole: 'task' }));
const mixedSemanticTextFloorplan = composeCanonicalFormFloorplan(mixedSemanticTextModel);
assert.deepEqual(
  collectTexts([...mixedSemanticTextFloorplan.taskNodes, ...mixedSemanticTextFloorplan.riskNodes]),
  [],
  'unassigned native text must not duplicate across semantic Floorplan projections',
);
const mixedRoleModel = presentContractV2Form(createContractV2Store(semanticReadonlySnapshot), 'readonly');
const mixedRoleParent = mixedRoleModel.zones.primary[0].children.find((node) => node.semanticRole === 'summary');
assert.ok(mixedRoleParent, 'semantic summary parent is required for mixed-role projection coverage');
const mixedRoleChild = structuredClone(mixedRoleParent);
mixedRoleChild.nodeId = `${mixedRoleParent.nodeId}.audit-override`;
mixedRoleChild.semanticRole = 'audit';
mixedRoleChild.fields = mixedRoleChild.fields.map((field) => ({
  ...field,
  widgetId: `${field.widgetId}.audit-override`,
  semanticRole: 'audit',
}));
mixedRoleChild.children = [];
mixedRoleParent.children.push(mixedRoleChild);
const mixedRoleFloorplan = composeCanonicalFormFloorplan(mixedRoleModel);
assert.equal(
  collectFields(mixedRoleFloorplan.summaryNodes).some((field) => field.widgetId.endsWith('.audit-override')),
  false,
  'a parent role must not absorb a descendant semantic override',
);
assert.equal(
  collectFields(mixedRoleFloorplan.auditNodes).some((field) => field.widgetId.endsWith('.audit-override')),
  true,
  'a descendant semantic override must project into its declared Floorplan region',
);
const repeatedSummaryModel = presentContractV2Form(createContractV2Store(semanticReadonlySnapshot), 'readonly');
const repeatedSummaryRoot = structuredClone(repeatedSummaryModel.zones.primary[0]);
repeatedSummaryRoot.nodeId = `${repeatedSummaryRoot.nodeId}.repeated-occurrence`;
repeatedSummaryModel.zones.primary.push(repeatedSummaryRoot);
assert.deepEqual(
  collectFields(composeCanonicalFormFloorplan(repeatedSummaryModel).summaryNodes).map((field) => field.fieldCode),
  ['name'],
  'product summary must project one fact per canonical field even when the native layout repeats an occurrence',
);

const semanticContextSnapshot = structuredClone(semanticReadonlySnapshot);
function addContextGroup(groupId: string, fieldCodes: string[]) {
  const children = fieldCodes.map((fieldCode) => ({
    containerId: `field.${fieldCode}`, containerType: 'field', type: 'field', name: fieldCode, title: '', span: 12,
    children: [], widgetList: [{
      widgetId: `field.${fieldCode}`, widgetType: 'char', fieldCode, label: fieldCode, span: 12,
      componentKey: 'sc.display.text', capabilities: [], componentConfig: {}, fieldType: 'char',
    }],
  }));
  semanticContextSnapshot.layoutContract.containerTree.splice(-3, 0, {
    containerId: groupId, containerType: 'group', type: 'group', title: groupId, span: 24,
    children, widgetList: [],
  });
  fieldCodes.forEach((fieldCode) => {
    semanticContextSnapshot.statusContract.widgetStatus.push({
      widgetId: `field.${fieldCode}`, visible: true, readonly: true, required: false, disabled: false,
    });
    semanticContextSnapshot.dataContract.mainData[fieldCode] = fieldCode;
  });
}
for (let index = 1; index <= 23; index += 1) addContextGroup(`context.group.${index}`, [`context_${index}`]);
addContextGroup('context.group.boundary', ['context_24', 'context_25']);
addContextGroup('context.group.trailing', ['context_26']);
addContextGroup('governed.audit.section', [
  'approval_fact', 'decision_note', 'source_reference', 'source_timestamp',
]);
semanticContextSnapshot.layoutContract.containerTree
  .find((node) => node.containerId === 'context.group.trailing')!
  .children[0].widgetList[0].formStructureRole = { role: 'relation' };
semanticContextSnapshot.layoutContract.containerTree
  .find((node) => node.containerId === 'governed.audit.section')!
  .formStructureRole = { role: 'audit' };
const semanticContextModel = presentContractV2Form(createContractV2Store(semanticContextSnapshot), 'readonly');
const semanticContextFloorplan = composeCanonicalFormFloorplan(semanticContextModel);
assert.deepEqual(
  collectFields(semanticContextFloorplan.contextNodes).map((field) => field.fieldCode),
  Array.from({ length: 23 }, (_, index) => `context_${index + 1}`),
  'default context must stop before a whole block would exceed the 24-fact limit',
);
assert.deepEqual(
  collectFields(semanticContextFloorplan.overflowContextNodes).map((field) => field.fieldCode),
  ['context_24', 'context_25'],
  'overflow must retain complete blocks and all subsequent context in original order',
);
assert.deepEqual(
  collectFields(semanticContextFloorplan.relationNodes).map((field) => field.fieldCode),
  ['context_26', 'line_ids'],
  'relation-capable canonical facts must form an independent relation region',
);
assert.deepEqual(
  collectFields(semanticContextFloorplan.auditNodes).map((field) => field.fieldCode),
  ['approval_fact', 'decision_note', 'source_reference', 'source_timestamp'],
  'a generic declared audit section must enter the audit region as a complete canonical block',
);
assert.equal(
  collectFields([...semanticContextFloorplan.contextNodes, ...semanticContextFloorplan.overflowContextNodes])
    .some((field) => ['approval_fact', 'decision_note', 'source_reference', 'source_timestamp'].includes(field.fieldCode)),
  false,
  'audit-section fields must not leak into ordinary context regions',
);
assert.deepEqual(
  semanticContextFloorplan.subordinateNodes.map((node) => node.kind),
  ['attachment', 'chatter'],
  'audit classification must not absorb relation, attachment, or chatter zones',
);
assert.equal(
  collectFields(semanticContextFloorplan.relationNodes).some((relationField) => (
    collectFields(semanticContextFloorplan.subordinateNodes)
      .some((subordinateField) => subordinateField.widgetId === relationField.widgetId)
  )),
  false,
  'relation and subordinate regions must not duplicate canonical widget identities',
);
const semanticAtomicFields = collectFields([
  ...semanticContextFloorplan.summaryNodes,
  ...semanticContextFloorplan.taskNodes,
  ...semanticContextFloorplan.riskNodes,
  ...semanticContextFloorplan.contextNodes,
  ...semanticContextFloorplan.overflowContextNodes,
  ...semanticContextFloorplan.auditNodes,
  ...semanticContextFloorplan.relationNodes,
  ...semanticContextFloorplan.subordinateNodes,
]);
assert.deepEqual(
  new Set(semanticAtomicFields.map((field) => field.widgetId)).size,
  semanticAtomicFields.length,
  'floorplan regions must not duplicate canonical widget identities',
);
assert.deepEqual(
  new Set(semanticAtomicFields.map((field) => field.widgetId)),
  new Set(collectFields([...semanticContextModel.zones.primary, ...semanticContextModel.zones.subordinate])
    .map((field) => field.widgetId)),
  'floorplan organization must preserve 100% of canonical atomic fields',
);

const createFloorplanSnapshot = snapshot();
createFloorplanSnapshot.layoutContract.containerTree[0].children.push({
  containerId: 'field.empty_context', containerType: 'field', type: 'field', name: 'empty_context', title: '', span: 12,
  children: [], widgetList: [{
    widgetId: 'field.empty_context', widgetType: 'char', fieldCode: 'empty_context', label: 'Empty context', span: 12,
    componentKey: 'sc.display.text', capabilities: [], componentConfig: {}, fieldType: 'char',
  }],
});
createFloorplanSnapshot.statusContract.widgetStatus.push({
  widgetId: 'field.empty_context', visible: true, readonly: true, required: false, disabled: false,
});
createFloorplanSnapshot.dataContract.mainData.empty_context = false;
createFloorplanSnapshot.actionContract.actionRuleList = [{
  ...createFloorplanSnapshot.actionContract.actionRuleList[0],
  actionId: 'form.save', backendIdentity: 'contract_action:form.save', actionKey: 'form.save',
  visibleProfiles: ['create', 'edit'], presentation: { tier: 'secondary' },
}];
createFloorplanSnapshot.statusContract.buttonStatus = [{ btnId: 'form.save', visible: true, disabled: false }];
const createFloorplan = composeCanonicalFormFloorplan(presentContractV2Form(
  createContractV2Store(createFloorplanSnapshot),
  'create',
));
assert.equal(
  collectFields(createFloorplan.taskNodes).some((field) => field.fieldCode === 'empty_context'),
  false,
  'create floorplan must not reserve a control for an empty readonly fact',
);
assert.equal(createFloorplan.effectivePrimaryKey, 'form.save', 'create save must occupy the effective primary slot');
assert.deepEqual(createFloorplan.directActions.map((action) => action.key), ['form.save']);
assert.deepEqual(createFloorplan.overflowActions, []);

const unresolvedCreateIdentitySnapshot = structuredClone(createFloorplanSnapshot);
unresolvedCreateIdentitySnapshot.dataContract.mainData.name = 'New';
unresolvedCreateIdentitySnapshot.statusContract.widgetStatus = unresolvedCreateIdentitySnapshot.statusContract.widgetStatus
  .map((status) => status.widgetId === 'field.name' ? { ...status, readonly: true, required: false } : status);
assert.equal(
  collectFields(composeCanonicalFormFloorplan(presentContractV2Form(
    createContractV2Store(unresolvedCreateIdentitySnapshot),
    'create',
  )).taskNodes).some((field) => field.fieldCode === 'name'),
  false,
  'create floorplan must not expose an unresolved platform identity placeholder',
);

const createBackendPrimarySnapshot = structuredClone(createFloorplanSnapshot);
createBackendPrimarySnapshot.actionContract.actionRuleList.push({
  ...createBackendPrimarySnapshot.actionContract.actionRuleList[0],
  actionId: 'action.submit', backendIdentity: 'button:object:action_submit', actionKey: 'action.submit',
  presentation: { tier: 'primary' },
}, {
  ...createBackendPrimarySnapshot.actionContract.actionRuleList[0],
  actionId: 'action.navigation', backendIdentity: 'window_action:91', actionKey: 'action.navigation',
  presentation: { tier: 'overflow' },
});
createBackendPrimarySnapshot.statusContract.buttonStatus.push({
  btnId: 'action.submit', visible: true, disabled: false,
}, {
  btnId: 'action.navigation', visible: true, disabled: false,
});
const createBackendPrimaryModel = presentContractV2Form(
  createContractV2Store(createBackendPrimarySnapshot),
  'create',
);
assert.deepEqual(
  createBackendPrimaryModel.actionBar.map((action) => action.key),
  ['form.save', 'action.submit', 'action.navigation'],
  'iteration one must preserve the cb6e276 canonical form action collection and order',
);
const createBackendPrimaryFloorplan = composeCanonicalFormFloorplan(presentContractV2Form(
  createContractV2Store(createBackendPrimarySnapshot),
  'create',
));
assert.equal(
  createBackendPrimaryFloorplan.effectivePrimaryKey,
  'action.submit',
  'an enabled backend primary must always outrank the platform create-save fallback',
);
assert.deepEqual(createBackendPrimaryFloorplan.directActions.map((action) => action.key), ['action.submit']);
assert.deepEqual(createBackendPrimaryFloorplan.overflowActions.map((action) => action.key), ['form.save', 'action.navigation']);

const createBlockedPrimarySnapshot = structuredClone(createBackendPrimarySnapshot);
createBlockedPrimarySnapshot.statusContract.buttonStatus = [
  { btnId: 'form.save', visible: true, disabled: false },
  { btnId: 'action.submit', visible: true, disabled: true, reasonCode: 'ACTION_NOT_AVAILABLE_IN_STATE' },
];
const createBlockedPrimaryFloorplan = composeCanonicalFormFloorplan(presentContractV2Form(
  createContractV2Store(createBlockedPrimarySnapshot),
  'create',
));
assert.equal(
  createBlockedPrimaryFloorplan.effectivePrimaryKey,
  '',
  'a disabled backend primary must block create-save promotion instead of failing open',
);
assert.deepEqual(createBlockedPrimaryFloorplan.directActions, []);
assert.deepEqual(createBlockedPrimaryFloorplan.blockedActions.map((action) => action.key), ['action.submit']);
assert.deepEqual(
  createBlockedPrimaryFloorplan.overflowActions.map((action) => action.key),
  ['form.save', 'action.navigation'],
  'blocked primary handling must not remove any other cb6e276 action',
);

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
assert.equal(normalizedNativeChild.title, '', 'native identity must not become a visible title');
assert.equal(normalizedNativeChild.span, 24);

const anonymousNativeContainer = snapshot() as ContractV2Snapshot & { layoutContract: { containerTree: Array<Record<string, unknown>> } };
const anonymousGroup = anonymousNativeContainer.layoutContract.containerTree[0].children[0] as Record<string, unknown>;
anonymousGroup.containerId = 'container.native.0.children.0';
anonymousGroup.containerType = 'group';
anonymousGroup.type = 'group';
delete anonymousGroup.title;
delete anonymousGroup.label;
delete anonymousGroup.string;
anonymousGroup.name = 'native_internal_group';
assert.equal(
  decodeContractV2Snapshot(anonymousNativeContainer).layoutContract.containerTree[0].children[0].title,
  '',
  'anonymous native container identity must remain non-visual',
);

const anonymousNativeRoot = snapshot();
anonymousNativeRoot.layoutContract.containerTree[0].title = '';
assert.equal(
  decodeContractV2Snapshot(anonymousNativeRoot).layoutContract.containerTree[0].title,
  '',
  'anonymous native root container must support an explicitly empty display title',
);

const mixedNativeContent = snapshot();
mixedNativeContent.layoutContract.containerTree[0].children.splice(1, 0, {
  containerId: 'text.native.identity.separator',
  containerType: 'text',
  type: 'text',
  title: '',
  text: '· 状态',
  span: 24,
  children: [],
  widgetList: [],
});
mixedNativeContent.statusContract.containerStatus.push({
  containerId: 'text.native.identity.separator', visible: true, disabled: false,
});
const mixedNativeModel = presentContractV2Form(createContractV2Store(mixedNativeContent), 'edit');
assert.deepEqual(
  mixedNativeModel.zones.primary[0].children.map((node) => [node.kind, node.text]),
  [['field', ''], ['text', '· 状态'], ['field', '']],
  'canonical presenter must preserve mixed native field/text order',
);

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

const duplicateOccurrences = snapshot();
const duplicateRoot = duplicateOccurrences.layoutContract.containerTree[0];
const duplicateBaseWidget = duplicateRoot.children[0].widgetList[0];
duplicateRoot.widgetList = [];
duplicateRoot.children = [
  {
    ...duplicateRoot.children[0],
    fieldCode: 'name',
    widgetId: 'field.name.occ.first',
    nativeLocator: 'form/field[name=name][1]',
    occurrenceIndex: 1,
    sourcePosition: 1,
    widgetList: [{
      ...duplicateBaseWidget,
      widgetId: 'field.name.occ.first',
      fieldDescriptor: { name: 'name', type: 'char' },
      componentConfig: {
        ...duplicateBaseWidget.componentConfig,
        native_locator: 'form/field[name=name][1]',
        occurrence_index: 1,
        source_position: 1,
      },
    }],
  },
  {
    ...duplicateRoot.children[0],
    fieldCode: 'name',
    widgetId: 'field.name.occ.second',
    nativeLocator: 'form/field[name=name][2]',
    occurrenceIndex: 2,
    sourcePosition: 2,
    widgetList: [{
      ...duplicateBaseWidget,
      widgetId: 'field.name.occ.second',
      fieldDescriptor: { name: 'name', type: 'char' },
      componentConfig: {
        ...duplicateBaseWidget.componentConfig,
        native_locator: 'form/field[name=name][2]',
        occurrence_index: 2,
        source_position: 2,
      },
    }],
  },
];
duplicateOccurrences.statusContract.widgetStatus = [
  { widgetId: 'field.name.occ.first', visible: true, readonly: true, required: false, disabled: false, auth: 'read' },
  { widgetId: 'field.name.occ.second', visible: true, readonly: false, required: true, disabled: false, auth: 'edit' },
];
const decodedDuplicateOccurrences = decodeContractV2Snapshot(duplicateOccurrences);
const duplicateOccurrenceStore = createContractV2Store(decodedDuplicateOccurrences);
assert.equal(duplicateOccurrenceStore.widgetsByFieldCodeAll.get('name')?.length, 2);
const duplicateOccurrenceFields = collectFields(
  presentContractV2Form(duplicateOccurrenceStore, 'edit').zones.primary,
);
assert.deepEqual(
  duplicateOccurrenceFields.map((field) => [field.widgetId, field.readonly, field.required]),
  [
    ['field.name.occ.first', true, false],
    ['field.name.occ.second', false, true],
  ],
  'canonical form must preserve same-field occurrences and their independent status',
);
const equivalentCreateOccurrences = structuredClone(duplicateOccurrences);
equivalentCreateOccurrences.statusContract.widgetStatus = [
  { widgetId: 'field.name.occ.first', visible: true, readonly: false, required: true, disabled: false, auth: 'edit' },
  { widgetId: 'field.name.occ.second', visible: true, readonly: false, required: true, disabled: false, auth: 'edit' },
];
assert.deepEqual(
  collectFields(composeCanonicalFormFloorplan(presentContractV2Form(
    createContractV2Store(decodeContractV2Snapshot(equivalentCreateOccurrences)),
    'create',
  )).taskNodes).map((field) => field.widgetId),
  ['field.name.occ.second'],
  'create floorplan must merge equivalent occurrences while preserving the retained canonical identity',
);

const duplicateOccurrenceStatus = snapshot();
const duplicateStatusRoot = duplicateOccurrenceStatus.layoutContract.containerTree[0];
duplicateStatusRoot.widgetList = [];
duplicateStatusRoot.children = [
  { ...duplicateStatusRoot.children[0], widgetId: 'field.name.occ.same', nativeLocator: 'form/field[name=name][1]', occurrenceIndex: 1, sourcePosition: 1, widgetList: [] },
  { ...duplicateStatusRoot.children[0], widgetId: 'field.name.occ.same', nativeLocator: 'form/field[name=name][2]', occurrenceIndex: 2, sourcePosition: 2, widgetList: [] },
];
duplicateOccurrenceStatus.statusContract.widgetStatus = [
  { widgetId: 'field.name.occ.same', visible: true, readonly: false, required: false, disabled: false },
];
assert.throws(() => decodeContractV2Snapshot(duplicateOccurrenceStatus), /duplicate form occurrence widgetId/);

const missingOccurrenceStatus = snapshot();
const missingStatusRoot = missingOccurrenceStatus.layoutContract.containerTree[0];
missingStatusRoot.widgetList = [];
missingStatusRoot.children = [{ ...missingStatusRoot.children[0], widgetId: 'field.name.occ.missing', nativeLocator: 'form/field[name=name]', occurrenceIndex: 1, sourcePosition: 1, widgetList: [] }];
missingOccurrenceStatus.statusContract.widgetStatus = [];
assert.throws(() => decodeContractV2Snapshot(missingOccurrenceStatus), /requires exactly one status/);

const orphanOccurrenceStatus = snapshot();
orphanOccurrenceStatus.statusContract.widgetStatus.push({ widgetId: 'field.name.occ.orphan', visible: true, readonly: false, required: false, disabled: false });
assert.throws(() => decodeContractV2Snapshot(orphanOccurrenceStatus), /orphan form widget status/);

const renderedName = canonicalFieldToFormSection(deDuplicatedFields[0]);
assert.deepEqual(
  { key: renderedName.key, name: renderedName.name, value: renderedName.value, readonly: renderedName.readonly },
  { key: 'field.name', name: 'name', value: 'D-001', readonly: false },
  'renderer mapping must preserve canonical widget identity and state without native layout input',
);
assert.equal(canonicalNodeHasContent(model.zones.subordinate.find((node) => node.kind === 'chatter')!), true);
assert.deepEqual(
  canonicalSectionFields(model.zones.primary[0]).map((field) => field.fieldCode),
  [],
  'a parent must not hoist fields out of native child-node order',
);
assert.equal(
  visibleCanonicalChildren(model.zones.primary[0]).some((node) => node.kind === 'field'),
  true,
  'leaf field nodes must remain in native child-node order',
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
    icon: 'fa-check',
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

const resolvedDuplicateSubmit = snapshot();
resolvedDuplicateSubmit.actionContract.actionRuleList[0] = {
  ...resolvedDuplicateSubmit.actionContract.actionRuleList[0],
  actionId: 'action.native_submit',
  actionKey: 'native_submit',
  backendIdentity: 'native_button:object:action_submit:/form[1]/header[1]/button[1]:1',
  sourceWidgetId: 'page.header',
  button: { name: 'action_submit', type: 'object' },
};
resolvedDuplicateSubmit.actionContract.actionRuleList.push({
  ...resolvedDuplicateSubmit.actionContract.actionRuleList[0],
  actionId: 'action.weak_submit',
  actionKey: 'weak_submit',
  backendIdentity: 'button:object:action_submit',
  sourceWidgetId: 'page.root',
  presentation: { tier: 'secondary' },
});
resolvedDuplicateSubmit.actionContract.primaryResolution = {
  policy: 'single_effective_primary_per_record_state',
  winner: 'native_button:object:action_submit:/form[1]/header[1]/button[1]:1',
  demoted: [{
    actionId: 'action.weak_submit',
    backendIdentity: 'button:object:action_submit',
    previousTier: 'primary',
    effectiveTier: 'secondary',
  }],
};
resolvedDuplicateSubmit.statusContract.buttonStatus = [
  {
    btnId: 'btn.native_submit', visible: true, disabled: false,
    backendIdentity: 'native_button:object:action_submit:/form[1]/header[1]/button[1]:1',
  },
  {
    btnId: 'btn.weak_submit', visible: true, disabled: false,
    backendIdentity: 'button:object:action_submit',
  },
];
const decodedResolvedDuplicateSubmit = decodeContractV2Snapshot(resolvedDuplicateSubmit);
assert.deepEqual(
  decodedResolvedDuplicateSubmit.actionContract.primaryResolution,
  resolvedDuplicateSubmit.actionContract.primaryResolution,
  'the normalized store must retain the backend primary-action verdict',
);
assert.deepEqual(
  presentContractV2Form(createContractV2Store(decodedResolvedDuplicateSubmit), 'readonly')
    .actionBar.map((action) => action.actionRef.actionId),
  ['action.native_submit'],
  'a backend-demoted duplicate must not become a second product action',
);

const normalizedAction = snapshot().actionContract.actionRuleList[0];
assert.deepEqual(
  contractActionConfirmationPrompt({
    key: 'action_submit', label: 'Submit', hint: '',
    actionSafety: {
      classification: 'danger', requiresConfirm: true,
      confirmMessage: 'Submit this document?', reasonCode: 'NATIVE_BUTTON_DANGEROUS_ACTION',
    },
  } as never),
  { actionLabel: 'Submit', message: 'Submit this document?' },
  'native confirm message must reach the confirmation interaction unchanged',
);
assert.equal(
  contractActionConfirmationPrompt({
    key: 'action_help', label: 'Help', hint: 'Descriptive help only',
  } as never),
  null,
  'button help must never manufacture a confirmation prompt',
);
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
  'iteration one must retain the cb6e276 readonly save suppression behavior',
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

assert.deepEqual(
  collectCanonicalFormActions(bodyActionModel).map((action) => action.actionRef.backendIdentity),
  ['button:object:action_submit', 'window_action:91'],
  'body-node actions must join actionBar actions in exact executor validation',
);
assert.deepEqual(
  validateCanonicalFormActionExecutors(collectCanonicalFormActions(bodyActionModel), [contractAction]),
  {
    reasonCode: 'CANONICAL_FORM_ACTION_EXECUTION_ADAPTER_MISSING',
    actionId: 'action.open_lines',
    backendIdentity: 'window_action:91',
  },
  'an executable body-node action without an adapter must fail closed',
);

console.log('[canonical_form_presenter_test] PASS cases=53');
