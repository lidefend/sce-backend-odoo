import assert from 'node:assert/strict';
import { createContractV2Store } from '../src/app/contracts/v2/store';
import type { ContractV2Snapshot } from '../src/app/contracts/v2/types';
import { presentContractV2Form } from '../src/app/presentation/contractFormPresenter';

function snapshot(): ContractV2Snapshot {
  const action = {
    actionId: 'action.submit',
    backendIdentity: 'button:object:action_submit',
    triggerType: 'click' as const,
    sourceWidgetId: 'page.root',
    targetIds: [],
    dispatchMode: 'serverBlocking' as const,
    targetScope: 'page' as const,
    refreshMode: 'full' as const,
    actionKey: 'action_submit',
    label: 'Submit',
    allowed: true,
    enabled: true,
    disabled: false,
    visibleProfiles: ['edit', 'readonly'],
    presentation: { tier: 'primary' },
    actionSafety: { level: 'danger', requiresConfirmation: true },
  };
  return {
    pageInfo: {
      pageId: 'page.x.document.form', sceneKey: 'x.document.form', pageName: 'Document',
      model: 'x.document', viewType: 'form', layoutType: 'form', renderMode: 'governed',
      contractVersion: '2', clientType: 'web_pc',
    },
    layoutContract: {
      pageId: 'page.x.document.form', layoutType: 'form', adaptMode: 'pc',
      layoutHints: { mobileColumns: 1 },
      componentRegistry: { 'sc.input.text': { componentKey: 'sc.input.text' } },
      containerTree: [{
        containerId: 'sheet', containerType: 'sheet', type: 'sheet', title: '', span: 24,
        children: [{
          containerId: 'section.identity', containerType: 'group', type: 'group', title: 'Identity', span: 24,
          children: [{
            containerId: 'field.name', containerType: 'field', type: 'field', name: 'name', title: '', span: 12,
            children: [], widgetList: [{
              widgetId: 'field.name', widgetType: 'char', fieldCode: 'name', label: 'Name', span: 12,
              componentKey: 'sc.input.text', capabilities: [], componentConfig: { dependencyFields: ['state'] },
              fieldType: 'char',
            }],
          }, {
            containerId: 'field.state', containerType: 'field', type: 'field', name: 'state', title: '', span: 12,
            children: [], widgetList: [{
              widgetId: 'field.state', widgetType: 'selection', fieldCode: 'state', label: 'State', span: 12,
              componentKey: 'sc.display.status', capabilities: [], componentConfig: {}, fieldType: 'selection',
            }],
          }],
          // Aggregated widget lists must not duplicate descendant fields.
          widgetList: [{
            widgetId: 'field.name', widgetType: 'char', fieldCode: 'name', label: 'Name', span: 12,
            componentKey: 'sc.input.text', capabilities: [], componentConfig: { dependencyFields: ['state'] }, fieldType: 'char',
          }],
        }],
        widgetList: [],
      }, {
        containerId: 'native.notebook', containerType: 'notebook', type: 'notebook', title: 'Related', span: 24,
        sourceAuthority: { projection_only: true, no_business_fact_authority: true },
        children: [{
          containerId: 'relation.lines', containerType: 'field', type: 'field', name: 'line_ids', title: '', span: 24,
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
    actionContract: { actionRuleList: [action], dependencyGraph: { 'action.submit': ['field.name'] } },
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
      mainData: { name: 'D-001', state: 'draft', line_ids: [7] }, tableRows: {}, relationRows: {}, dictData: {}, pagination: {},
      dataSource: {}, dataMeta: {},
    },
    runtimeContract: { patchStrategy: 'full', cachePolicy: 'snapshot', optimistic: false, lazyContainer: [], virtualization: {}, retryPolicy: {} },
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

const source = snapshot();
const before = JSON.stringify(source);
const store = createContractV2Store(source);
const model = presentContractV2Form(store, 'edit');
assert.equal(JSON.stringify(source), before, 'presenter must not mutate normalized input');
assert.equal(model.identity.sourceContractSha256, 'contract-sha');
assert.equal(model.zones.primary.length, 1);
assert.deepEqual(model.zones.subordinate.map((node) => node.kind), ['notebook', 'attachment', 'chatter']);
const fields = [...model.zones.primary, ...model.zones.subordinate]
  .flatMap(function walk(node): typeof node.fields {
    return [...node.fields, ...node.children.flatMap(walk)];
  });
assert.deepEqual(fields.map((field) => field.fieldCode), ['name', 'state', 'line_ids']);
assert.equal(fields.find((field) => field.fieldCode === 'name')?.value, 'D-001');
assert.equal(fields.find((field) => field.fieldCode === 'name')?.required, true);
assert.equal(fields.find((field) => field.fieldCode === 'state')?.visible, false);
assert.equal(fields.find((field) => field.fieldCode === 'state')?.disabled, true);
assert.equal(model.actionBar[0]?.actionRef, source.actionContract.actionRuleList[0], 'action reference must remain identical');
assert.equal(model.actionBar[0]?.tier, 'primary');
assert.deepEqual(model.actionBar[0]?.safety, { level: 'danger', requiresConfirmation: true });
assert.equal(model.actionBar[0]?.enabled, true);
assert.equal(presentContractV2Form(store, 'create').actionBar[0]?.visible, false);
assert.deepEqual(presentContractV2Form(store, 'edit'), model, 'presenter must be deterministic');

const missingIdentity = snapshot();
delete missingIdentity.actionContract.actionRuleList[0].backendIdentity;
assert.throws(
  () => presentContractV2Form(createContractV2Store(missingIdentity), 'edit'),
  /CANONICAL_FORM_ACTION_REFERENCE_MISSING/,
);

const duplicatePrimary = snapshot();
duplicatePrimary.actionContract.actionRuleList.push({
  ...duplicatePrimary.actionContract.actionRuleList[0],
  actionId: 'action.other', backendIdentity: 'button:object:action_other', actionKey: 'action_other',
});
duplicatePrimary.statusContract.buttonStatus.push({ btnId: 'action.other', visible: true, disabled: false });
assert.throws(
  () => presentContractV2Form(createContractV2Store(duplicatePrimary), 'edit'),
  /CANONICAL_FORM_MULTIPLE_PRIMARY_ACTIONS/,
);

console.log('[canonical_form_presenter_test] PASS');
