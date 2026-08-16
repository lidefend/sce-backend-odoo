import assert from 'node:assert/strict';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import { createContractV2Store } from '../src/app/contracts/v2/store';
import type { ContractV2Snapshot } from '../src/app/contracts/v2/types';
import { presentContractV2Form } from '../src/app/presentation/contractFormPresenter';

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

const readonlyModel = presentContractV2Form(store, 'readonly');
assert.equal(
  collectFields(readonlyModel.zones.primary).find((field) => field.fieldCode === 'name')?.readonly,
  true,
  'readonly route mode must remain authoritative even when the widget status is editable',
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

const invalidNativeChild = snapshot() as ContractV2Snapshot & { layoutContract: { containerTree: Array<Record<string, unknown>> } };
invalidNativeChild.layoutContract.containerTree[0].children = [{ children: [], widgetList: [] }];
assert.throws(() => decodeContractV2Snapshot(invalidNativeChild), /requires a stable native identity/);

const invalidExplicitSpan = snapshot();
invalidExplicitSpan.layoutContract.containerTree[0].span = 0;
assert.throws(() => decodeContractV2Snapshot(invalidExplicitSpan), /span must be an integer between 1 and 24/);

const missingIdentity = snapshot();
delete missingIdentity.actionContract.actionRuleList[0].backendIdentity;
assert.throws(() => presentContractV2Form(createContractV2Store(missingIdentity), 'edit'), /ACTION_REFERENCE_MISSING/);

const duplicatePrimary = snapshot();
duplicatePrimary.actionContract.actionRuleList.push({
  ...duplicatePrimary.actionContract.actionRuleList[0],
  actionId: 'action.other', backendIdentity: 'button:object:action_other', actionKey: 'action_other',
});
duplicatePrimary.statusContract.buttonStatus.push({ btnId: 'action.other', visible: true, disabled: false });
assert.throws(() => presentContractV2Form(createContractV2Store(duplicatePrimary), 'edit'), /MULTIPLE_PRIMARY_ACTIONS/);

console.log('[canonical_form_presenter_test] PASS cases=17');
