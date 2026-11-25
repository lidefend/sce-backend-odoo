import assert from 'node:assert/strict';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';

const runtimeContract = {
  patchStrategy: 'incremental',
  cachePolicy: 'none',
  optimistic: false,
  lazyContainer: [],
  virtualization: {},
  retryPolicy: { maxRetries: 1 },
};

function snapshot(widget: Record<string, unknown>) {
  return {
    pageInfo: {
      pageId: 'contract.form',
      sceneKey: 'contract.form',
      pageName: 'Contract',
      model: 'x.contract',
      viewType: 'form',
      layoutType: 'form',
      renderMode: 'governed',
      contractVersion: '2.7.0',
      clientType: 'web_pc',
    },
    layoutContract: {
      pageId: 'contract.form',
      layoutType: 'form',
      adaptMode: 'pc',
      containerTree: [{
        containerId: 'main.form',
        containerType: 'section',
        title: 'Contract',
        span: 24,
        children: [],
        widgetList: [widget],
      }],
      layoutHints: {},
    },
    statusContract: {
      globalStatus: { pageVisible: true, pageAuth: 'edit' },
      containerStatus: [],
      widgetStatus: [],
      buttonStatus: [],
      selectorStatus: [],
    },
    actionContract: { actionRuleList: [], dependencyGraph: {} },
    dataContract: {
      mainData: { amount: 1 },
      tableRows: {},
      relationRows: {},
      dictData: {},
      pagination: {},
      dataSource: {},
      dataMeta: {},
    },
    runtimeContract,
    meta: {
      etag: 'test',
      snapshotId: 'test',
      traceId: 'test',
      requestId: 'test',
      sourceType: 'test',
      lifecycle: {
        lifecycleVersion: '1',
        stage: 'sealed',
        definition: {
          schemaId: 'v2',
          schemaVersion: '2.7.0',
          schemaSha256: 'schema',
          contractVersion: '2.7.0',
          normativeStatus: 'active',
        },
        generation: {
          generator: 'test',
          generatorVersion: '1',
          sourceType: 'test',
          sourceSha256: 'source',
        },
        runtime: {
          requestId: 'test',
          traceId: 'test',
          clientType: 'web_pc',
          traceSource: 'test',
        },
        integrity: { algorithm: 'sha256', contractSha256: 'contract' },
        authority: {},
      },
    },
  };
}

function widget(overrides: Record<string, unknown> = {}) {
  return {
    widgetId: 'field.amount',
    widgetType: 'input',
    fieldCode: 'amount',
    label: 'Amount',
    span: 12,
    semanticType: 'text',
    capabilities: [],
    componentConfig: {
      fieldType: 'char',
      widgetProvenance: {
        nativeWidget: '',
        widgetSource: 'model_metadata_derived',
        declaredWidget: 'input',
        derivedWidgetType: 'input',
        resolvedWidgetType: 'input',
        resolutionStatus: 'not_applicable',
        reasonCode: '',
      },
    },
    fieldDescriptor: {
      schemaVersion: '1.0.0',
      fieldCode: 'amount',
      label: 'Amount',
      fieldType: 'char',
      widgetType: 'input',
      semanticType: 'text',
    },
    ownerContainerId: 'main.form',
    ...overrides,
  };
}

const decoded = decodeContractV2Snapshot(snapshot(widget()));
assert.equal(
  decoded.layoutContract.containerTree[0].widgetList[0].componentConfig.widgetProvenance.widgetSource,
  'model_metadata_derived',
);

const explicit = decodeContractV2Snapshot(snapshot(widget({
  widgetType: 'date',
  semanticType: 'date',
  componentConfig: {
    fieldType: 'date',
    nativeWidget: 'daterange',
    widgetProvenance: {
      nativeWidget: 'daterange',
      widgetSource: 'native_explicit',
      declaredWidget: 'daterange',
      derivedWidgetType: '',
      resolvedWidgetType: 'date',
      resolutionStatus: 'ready',
      reasonCode: '',
    },
  },
  fieldDescriptor: {
    schemaVersion: '1.0.0',
    fieldCode: 'amount',
    label: 'Amount',
    fieldType: 'date',
    widgetType: 'date',
    semanticType: 'date',
    temporal: { kind: 'date', timezoneAuthority: 'not_applicable' },
  },
})));
assert.equal(
  explicit.layoutContract.containerTree[0].widgetList[0].componentConfig.widgetProvenance.nativeWidget,
  'daterange',
);
assert.equal(explicit.layoutContract.containerTree[0].widgetList[0].widgetType, 'date');
assert.equal(explicit.layoutContract.containerTree[0].widgetList[0].semanticType, 'date');

const unsupported = decodeContractV2Snapshot(snapshot(widget({
  semanticType: 'unsupported_native_widget',
  componentConfig: {
    fieldType: 'char',
    nativeWidget: 'future_editor',
    widgetProvenance: {
      nativeWidget: 'future_editor',
      widgetSource: 'native_explicit',
      declaredWidget: 'future_editor',
      derivedWidgetType: '',
      resolvedWidgetType: 'input',
      resolutionStatus: 'unsupported',
      reasonCode: 'NATIVE_WIDGET_UNRECOGNIZED',
    },
  },
  fieldDescriptor: {
    schemaVersion: '1.0.0',
    fieldCode: 'amount',
    label: 'Amount',
    fieldType: 'char',
    widgetType: 'input',
    semanticType: 'unsupported_native_widget',
  },
})));
assert.equal(
  unsupported.layoutContract.containerTree[0].widgetList[0].componentConfig.widgetProvenance.resolutionStatus,
  'unsupported',
);

for (const invalid of [
  widget({
    componentConfig: {
      nativeWidget: 'future_editor',
      widgetProvenance: {
        nativeWidget: 'future_editor',
        widgetSource: 'model_metadata_derived',
        declaredWidget: 'input',
        derivedWidgetType: 'input',
        resolvedWidgetType: 'input',
        resolutionStatus: 'not_applicable',
        reasonCode: '',
      },
    },
  }),
  widget({
    semanticType: 'unsupported_native_widget',
    componentConfig: {
      widgetProvenance: {
        nativeWidget: 'future_editor',
        widgetSource: 'native_explicit',
        declaredWidget: 'future_editor',
        derivedWidgetType: '',
        resolvedWidgetType: 'input',
        resolutionStatus: 'unsupported',
        reasonCode: '',
      },
    },
    fieldDescriptor: {
      schemaVersion: '1.0.0',
      fieldCode: 'amount',
      label: 'Amount',
      fieldType: 'char',
      widgetType: 'input',
      semanticType: 'unsupported_native_widget',
    },
  }),
  widget({
    componentConfig: {
      widgetProvenance: {
        nativeWidget: '',
        widgetSource: 'generated_guess',
        declaredWidget: 'input',
        derivedWidgetType: 'input',
        resolvedWidgetType: 'input',
        resolutionStatus: 'not_applicable',
        reasonCode: '',
      },
    },
  }),
]) {
  assert.throws(() => decodeContractV2Snapshot(snapshot(invalid)), /ContractV2DecodeError/);
}

console.log('native widget provenance decoder: passed');
