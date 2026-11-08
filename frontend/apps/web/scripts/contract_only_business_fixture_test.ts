import assert from 'node:assert/strict';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import { createContractV2Store } from '../src/app/contracts/v2/store';
import type { ContractV2Snapshot } from '../src/app/contracts/v2/types';
import { presentContractV2Form } from '../src/app/presentation/contractFormPresenter';
import type { CanonicalFormNode } from '../src/app/presentation/canonicalFormRenderModel';
import { canonicalFieldToFormSection } from '../src/pages/contractForm/canonicalFormRenderer';
import { resolveContractBaseComponentBinding } from '../src/components/professional-fields/contractComponentBindings';

function fieldContainer(
  name: string,
  widgetType: string,
  componentKey: string,
  fieldType: string,
) {
  return {
    containerId: `field.${name}`,
    containerType: 'field',
    type: 'field',
    name,
    title: '',
    span: 8,
    children: [],
    widgetList: [{
      widgetId: `field.${name}`,
      widgetType,
      fieldCode: name,
      label: name,
      span: 8,
      componentKey,
      capabilities: [],
      componentConfig: { fieldType },
      ownerContainerId: `field.${name}`,
    }],
  };
}

function snapshot(): ContractV2Snapshot {
  return {
    pageInfo: {
      pageId: 'page.x.ordinary_business.form',
      sceneKey: 'x.ordinary_business.form',
      pageName: 'Ordinary business',
      model: 'x.ordinary_business',
      viewType: 'form',
      layoutType: 'form',
      renderMode: 'governed',
      contractVersion: '2.2.0',
      clientType: 'web_pc',
    },
    layoutContract: {
      pageId: 'page.x.ordinary_business.form',
      layoutType: 'form',
      adaptMode: 'pc',
      layoutHints: { mobileColumns: 1 },
      componentRegistry: {
        'sc.input.text': { version: '1.0' },
        'sc.input.textarea': { version: '1.0' },
        'sc.select.remote': { version: '1.0' },
        'sc.input.number': { version: '1.0' },
        'sc.input.date': { version: '1.0' },
        'sc.input.datetime': { version: '1.0' },
        'sc.input.boolean': { version: '1.0' },
      },
      containerTree: [{
        containerId: 'section.ordinary',
        containerType: 'group',
        type: 'group',
        title: 'Ordinary fields',
        span: 24,
        columns: 3,
        children: [
          fieldContainer('name', 'input', 'sc.input.text', 'char'),
          fieldContainer('summary', 'textarea', 'sc.input.textarea', 'text'),
          fieldContainer('state', 'select', 'sc.select.remote', 'selection'),
          fieldContainer('quantity', 'number', 'sc.input.number', 'integer'),
          fieldContainer('start_date', 'date', 'sc.input.date', 'date'),
          fieldContainer('start_at', 'datetime', 'sc.input.datetime', 'datetime'),
          fieldContainer('active', 'checkbox', 'sc.input.boolean', 'boolean'),
        ],
        widgetList: [],
      }],
    },
    actionContract: {
      actionRuleList: [],
      dependencyGraph: {},
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
        { widgetId: 'field.summary', visible: true, readonly: false, required: false, disabled: false },
        { widgetId: 'field.state', visible: true, readonly: false, required: false, disabled: false },
        { widgetId: 'field.quantity', visible: true, readonly: false, required: false, disabled: false },
        { widgetId: 'field.start_date', visible: true, readonly: false, required: false, disabled: false },
        { widgetId: 'field.start_at', visible: true, readonly: false, required: false, disabled: false },
        { widgetId: 'field.active', visible: true, readonly: false, required: false, disabled: false },
      ],
      buttonStatus: [],
      containerStatus: [],
      selectorStatus: [],
    },
    dataContract: {
      mainData: {
        name: 'FIXTURE-001',
        summary: 'Contract-only',
        state: 'draft',
        quantity: 3,
        start_date: '2026-11-08',
        start_at: '2026-11-08 09:30:00',
        active: true,
      },
      tableRows: {},
      relationRows: {},
      dictData: {},
      pagination: {},
      dataSource: {},
      dataMeta: {},
    },
    runtimeContract: {
      patchStrategy: 'full',
      cachePolicy: 'snapshot',
      optimistic: false,
      lazyContainer: [],
      virtualization: {},
      retryPolicy: {},
    },
    meta: {
      etag: 'fixture-etag',
      snapshotId: 'fixture-snapshot',
      traceId: 'fixture-trace',
      requestId: 'fixture-request',
      sourceType: 'ui.contract',
      lifecycle: {
        lifecycleVersion: '1',
        stage: 'sealed',
        definition: {
          schemaId: 'v2',
          schemaVersion: '2',
          schemaSha256: 'schema',
          contractVersion: '2',
          normativeStatus: 'active',
        },
        generation: {
          generator: 'contract-only-fixture',
          generatorVersion: '1',
          sourceType: 'test',
          sourceSha256: 'source',
        },
        runtime: {
          requestId: 'fixture-request',
          traceId: 'fixture-trace',
          clientType: 'web_pc',
          traceSource: 'test',
        },
        integrity: { algorithm: 'sha256', contractSha256: 'fixture-contract' },
        authority: {},
      },
    },
  };
}

function collectFields(nodes: CanonicalFormNode[]) {
  return nodes.flatMap((node) => [...node.fields, ...collectFields(node.children)]);
}

const source = snapshot();
const store = createContractV2Store(decodeContractV2Snapshot(source));
const model = presentContractV2Form(store, 'edit');
const fields = collectFields([...model.zones.primary, ...model.zones.subordinate]);
const expected = new Map([
  ['name', ['sc.input.text', 'ScInput']],
  ['summary', ['sc.input.textarea', 'ScTextarea']],
  ['state', ['sc.select.remote', 'ScSelect']],
  ['quantity', ['sc.input.number', 'ScNumberInput']],
  ['start_date', ['sc.input.date', 'ScDateField']],
  ['start_at', ['sc.input.datetime', 'ScDateField']],
  ['active', ['sc.input.boolean', 'ScCheckbox']],
]);

assert.equal(fields.length, expected.size);
for (const field of fields) {
  const contractExpectation = expected.get(field.fieldCode);
  assert.ok(contractExpectation, `unexpected field ${field.fieldCode}`);
  const [componentKey, implementation] = contractExpectation;
  assert.equal(field.componentResolution.componentKey, componentKey);
  const projected = canonicalFieldToFormSection(field);
  assert.equal(projected.componentKey, componentKey);
  assert.equal(resolveContractBaseComponentBinding(projected)?.implementation, implementation);
}

console.log('[contract_only_business_fixture_test] PASS model=x.ordinary_business fields=7 frontendProductSourceChanges=0');
