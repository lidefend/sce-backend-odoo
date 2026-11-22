import assert from 'node:assert/strict';
import { decodeContractV2FieldDescriptor } from '../src/app/contracts/v2/fieldDescriptor';
import { decodeContractCarrierCapabilities } from '../src/app/contracts/v2/carrierCapabilities';
import {
  PageOrchestrationDecodeError,
  decodePageOrchestrationContract,
  overlayPageBlockDataRows,
  resolvePageBlockData,
  resolvePageBlockCurrencyLabel,
} from '../src/app/pageOrchestration';

const readyMoney = {
  schemaVersion: '1.0.0',
  fieldCode: 'payment.pending_amount',
  label: '待付款金额',
  fieldType: 'monetary',
  widgetType: 'monetary',
  componentKey: 'sc.value.money',
  semanticType: 'money',
  digits: [16, 2],
  currencyField: 'currency_id',
};

const ready = decodeContractV2FieldDescriptor(readyMoney);
assert.deepEqual(ready.registryResolution.widget, {
  widgetType: 'monetary',
  widgetStatus: 'ready',
  fallbackReasonCode: null,
});
assert.equal('widgetStatus' in ready.descriptor, false);
assert.equal('fallbackReasonCode' in ready.descriptor, false);

const fallback = decodeContractV2FieldDescriptor({
  schemaVersion: '1.0.0',
  fieldCode: 'project.is_favorite',
  label: '收藏',
  fieldType: 'boolean',
  widgetType: 'boolean_toggle',
  componentKey: 'sc.input.boolean',
  semanticType: 'boolean',
});

const carrierCapabilities = decodeContractCarrierCapabilities({
  negotiationVersion: '1.0.0',
  status: 'current',
  contractVersion: '2.6.0',
  pageOrchestrationVersion: '2.1.0',
  carriers: {
    'page_block_data.v1': { schemaVersion: '1.0.0', enabled: true },
    'attachment_fact.v1': { schemaVersion: '1.0.0', enabled: false },
    'page_block_action.v1': { schemaVersion: '1.0.0', enabled: false },
  },
});
assert.equal(carrierCapabilities.carriers['page_block_data.v1'].enabled, true);
assert.equal(carrierCapabilities.carriers['attachment_fact.v1'].enabled, false);
assert.equal(carrierCapabilities.carriers['page_block_action.v1'].enabled, false);
assert.throws(
  () => decodeContractCarrierCapabilities({
    ...carrierCapabilities,
    carriers: {
      ...carrierCapabilities.carriers,
      'mystery_carrier.v1': { schemaVersion: '1.0.0', enabled: true },
    },
  }),
  /CONTRACT_CARRIER_CAPABILITIES_INVALID/,
);
assert.throws(
  () => decodeContractCarrierCapabilities({
    ...carrierCapabilities,
    carriers: {
      ...carrierCapabilities.carriers,
      'attachment_fact.v1': { schemaVersion: '1.0.0', enabled: true },
    },
  }),
  /CONTRACT_CARRIER_CAPABILITIES_INVALID:combination/,
);
assert.throws(
  () => decodeContractCarrierCapabilities({
    ...carrierCapabilities,
    negotiationVersion: '2.0.0',
  }),
  /CONTRACT_CARRIER_CAPABILITIES_INVALID:negotiationVersion/,
);
assert.deepEqual(fallback.registryResolution.widget, {
  widgetType: 'boolean_toggle',
  widgetStatus: 'fallback',
  fallbackReasonCode: 'NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK',
});

assert.throws(
  () => decodeContractV2FieldDescriptor({ ...readyMoney, widgetType: 'domain' }),
  /FIELD_DESCRIPTOR_WIDGET_UNSUPPORTED/,
);
assert.throws(
  () => decodeContractV2FieldDescriptor({ ...readyMoney, widgetType: 'mystery' }),
  /FIELD_DESCRIPTOR_WIDGET_UNKNOWN/,
);

const pageContract = decodePageOrchestrationContract({
  contract_version: '2.1.0',
  schema_version: '2.1.0',
  scene_key: 'workspace.home',
  page: { key: 'workspace.home', title: '角色首页' },
  zones: [{ key: 'main', blocks: [{ key: 'metrics', block_type: 'metric', data_source: 'ds_metrics' }] }],
  block_field_descriptors: {
    'metric.value': {
      schemaVersion: '1.0.0',
      fieldCode: 'payment.pending_amount',
      label: '待付款金额',
      fieldType: 'monetary',
      widgetType: 'monetary',
      componentKey: 'sc.value.money',
      semanticType: 'money',
      digits: [16, 2],
      currencyField: 'currency_id',
    },
    'metric.active': {
      schemaVersion: '1.0.0',
      fieldCode: 'project.active',
      label: '启用',
      fieldType: 'boolean',
      widgetType: 'boolean',
      componentKey: 'sc.input.boolean',
      semanticType: 'boolean',
    },
    'metric.note': {
      schemaVersion: '1.0.0',
      fieldCode: 'project.note',
      label: '说明',
      fieldType: 'char',
      widgetType: 'input',
      componentKey: 'sc.input.text',
      semanticType: 'text',
    },
  },
  block_data_contracts: {
    ds_metrics: {
      schemaVersion: '1.0.0',
      fieldRefs: {
        value: { kind: 'descriptor', descriptorId: 'metric.value', rawValuePath: 'value' },
        active: { kind: 'descriptor', descriptorId: 'metric.active', rawValuePath: 'active' },
        note: { kind: 'descriptor', descriptorId: 'metric.note', rawValuePath: 'note' },
      },
      rows: [
        { rowKey: 'money', values: { value: 0, active: false, note: '' } },
        { rowKey: 'null', values: { value: null, active: null, note: null } },
        { rowKey: 'missing', values: {} },
      ],
      context: {
        currencies: { CNY: { code: 'CNY', symbol: '¥' } },
        timezone: 'Asia/Shanghai',
      },
      sourceAuthority: { kind: 'test' },
    },
  },
});
const resolved = resolvePageBlockData(pageContract, 'ds_metrics');
assert.equal(resolved[0].values.value, 0);
assert.equal(resolved[0].values.active, false);
assert.equal(resolved[0].values.note, '');
assert.equal(resolved[0].fieldDescriptors.value.semanticType, 'money');
assert.equal(resolved[1].values.value, null);
assert.equal(resolved[1].values.active, null);
assert.equal(resolved[1].values.note, null);
assert.equal(resolved[2].values.value, undefined);
assert.equal('value' in resolved[2].values, false);
const overlaid = overlayPageBlockDataRows(
  [resolved[0], resolved[2]],
  [
    { key: 'money', value: 99 },
    { key: 'missing', value: 99 },
  ],
);
assert.equal(overlaid[0].value, 0);
assert.equal(overlaid[1].value, undefined);

const currencyRow = {
  ...resolved[0],
  values: { ...resolved[0].values, currency_id: 7 },
  context: {
    currencies: { '7': { code: 'CNY', symbol: '¥' } },
    timezone: 'Asia/Shanghai',
  },
};
assert.equal(resolvePageBlockCurrencyLabel(currencyRow, 'currency_id'), 'CNY');
assert.equal(resolvePageBlockCurrencyLabel(
  { ...currencyRow, values: { value: 0 } },
  'currency_id',
), '');

const widgetBackedContract = decodePageOrchestrationContract({
  contract_version: '2.1.0',
  schema_version: '2.1.0',
  page: { key: 'widget-backed' },
  zones: [],
  block_field_descriptors: { 'anchor.descriptor': readyMoney },
  block_data_contracts: {
    ds_widget: {
      schemaVersion: '1.0.0',
      fieldRefs: {
        value: { kind: 'widget', widgetId: 'widget.money', rawValuePath: 'value' },
      },
      rows: [{ rowKey: 'widget', values: { value: 0 } }],
      context: { currencies: {}, timezone: 'UTC' },
      sourceAuthority: { kind: 'test' },
    },
  },
});
const widgetResolved = resolvePageBlockData(widgetBackedContract, 'ds_widget', {
  'widget.money': {
    ...readyMoney,
    schemaVersion: '1.0.0',
  },
});
assert.equal(widgetResolved[0].values.value, 0);
assert.equal(widgetResolved[0].fieldDescriptors.value.semanticType, 'money');

assert.throws(
  () => decodePageOrchestrationContract({
    contract_version: '2.0.0',
    schema_version: '2.0.0',
    block_data_contracts: {},
  }),
  /2\.0\.0 cannot contain page-block-data carriers/,
);
assert.throws(
  () => decodePageOrchestrationContract({
    contract_version: '2.1.0',
    schema_version: '2.1.0',
    block_field_descriptors: {},
    block_data_contracts: {},
  }),
  (error: unknown) => error instanceof PageOrchestrationDecodeError,
);

console.log('P0_A_DESCRIPTOR_AND_PAGE_BLOCK_DATA=PASS');
