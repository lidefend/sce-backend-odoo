import assert from 'node:assert/strict';
import { decodeContractV2FieldDescriptor } from '../src/app/contracts/v2/fieldDescriptor';
import { decodeContractCarrierCapabilities } from '../src/app/contracts/v2/carrierCapabilities';
import { presentDeclaredBusinessValue } from '../src/app/presentation/businessValuePresentation';
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
const pageBlockSourceAuthority = {
  kind: 'page_block_data_producer',
  authorities: ['odoo_model_fields', 'page_orchestration', 'semantic_registry'],
  projectionOnly: true,
  noFrontendDefaults: true,
  carrier: 'page-block-data.v1',
  schemaVersion: '1.0.0',
};

const ready = decodeContractV2FieldDescriptor(readyMoney);
assert.deepEqual(ready.registryResolution.widget, {
  widgetType: 'monetary',
  widgetStatus: 'ready',
  fallbackReasonCode: null,
});
assert.equal('widgetStatus' in ready.descriptor, false);
assert.equal('fallbackReasonCode' in ready.descriptor, false);

const paymentDetailCollection = decodeContractV2FieldDescriptor({
  schemaVersion: '1.0.0',
  fieldCode: 'outflow_line_ids',
  label: '付款申请明细',
  fieldType: 'one2many',
  widgetType: 'one2many',
  componentKey: 'sc.payment.settlement_detail_collection',
  semanticType: 'payment_settlement_detail_collection',
  relation: 'payment.request.line',
  relationField: 'request_id',
});
assert.equal(
  paymentDetailCollection.descriptor.componentKey,
  'sc.payment.settlement_detail_collection',
);
assert.throws(
  () => decodeContractV2FieldDescriptor({
    ...paymentDetailCollection.descriptor,
    componentKey: 'sc.relation.table',
  }),
  /FIELD_DESCRIPTOR_SEMANTIC_MISMATCH/,
);

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
  clientType: 'web_pc',
  compatibilityMode: 'page_block_data_v1',
  acceptedContractVersions: ['2.5.x', '2.6.x'],
  clientContractCapabilities: ['page_block_data.v1'],
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
assert.throws(
  () => decodeContractCarrierCapabilities({
    ...carrierCapabilities,
    carriers: {
      ...carrierCapabilities.carriers,
      'page_block_data.v1': {
        schemaVersion: '1.0.0',
        enabled: true,
        unexpected: true,
      },
    },
  }),
  /CONTRACT_CARRIER_CAPABILITIES_INVALID:page_block_data\.v1\.unexpected/,
);
const missingClientType = { ...carrierCapabilities } as Record<string, unknown>;
delete missingClientType.clientType;
assert.throws(
  () => decodeContractCarrierCapabilities(missingClientType),
  /CONTRACT_CARRIER_CAPABILITIES_INVALID:clientType/,
);
assert.deepEqual(fallback.registryResolution.widget, {
  widgetType: 'boolean_toggle',
  widgetStatus: 'fallback',
  fallbackReasonCode: 'NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK',
});

const activityCollection = decodeContractV2FieldDescriptor({
  schemaVersion: '1.0.0',
  fieldCode: 'activity_ids',
  label: '活动',
  fieldType: 'one2many',
  widgetType: 'list_activity',
  componentKey: 'sc.relation.activity',
  semanticType: 'activity_collection',
  relation: 'mail.activity',
  relationField: 'res_id',
  relationEntry: {
    model: 'mail.activity',
    can_create: true,
    can_open: false,
    page_size: 20,
  },
});
assert.deepEqual(activityCollection.registryResolution.widget, {
  widgetType: 'list_activity',
  widgetStatus: 'fallback',
  fallbackReasonCode: 'NATIVE_WIDGET_PLATFORM_COMPONENT_SUBSTITUTION',
});
assert.equal(activityCollection.descriptor.componentKey, 'sc.relation.activity');
assert.equal(activityCollection.descriptor.relationEntry?.page_size, 20);

const accountTypeChoice = decodeContractV2FieldDescriptor({
  schemaVersion: '1.0.0',
  fieldCode: 'account_type',
  label: '类型',
  fieldType: 'selection',
  widgetType: 'account_type_selection',
  componentKey: 'sc.select.remote',
  semanticType: 'choice',
  selection: [['asset_cash', '银行和现金']],
});
assert.deepEqual(accountTypeChoice.registryResolution.widget, {
  widgetType: 'account_type_selection',
  widgetStatus: 'fallback',
  fallbackReasonCode: 'NATIVE_WIDGET_PLATFORM_COMPONENT_SUBSTITUTION',
});
assert.equal(accountTypeChoice.descriptor.componentKey, 'sc.select.remote');

assert.throws(
  () => decodeContractV2FieldDescriptor({ ...readyMoney, widgetType: 'domain' }),
  /FIELD_DESCRIPTOR_WIDGET_UNSUPPORTED/,
);
assert.throws(
  () => decodeContractV2FieldDescriptor({ ...readyMoney, widgetType: 'mystery' }),
  /FIELD_DESCRIPTOR_WIDGET_UNKNOWN/,
);
assert.throws(
  () => decodeContractV2FieldDescriptor({
    ...readyMoney,
    unit: { kind: 'percent', code: 'percent', label: '%', unexpected: true },
  }),
  /FIELD_DESCRIPTOR_UNKNOWN_KEY/,
);
assert.throws(
  () => decodeContractV2FieldDescriptor({
    ...readyMoney,
    temporal: { kind: 'datetime', timezoneAuthority: 'user', unexpected: true },
  }),
  /FIELD_DESCRIPTOR_UNKNOWN_KEY/,
);
assert.throws(
  () => decodeContractV2FieldDescriptor({
    ...readyMoney,
    formStructureRole: { role: 'summary', slot: 'identity', group: 'main', unexpected: true },
  }),
  /FIELD_DESCRIPTOR_UNKNOWN_KEY/,
);
assert.throws(
  () => decodeContractV2FieldDescriptor({ ...readyMoney, required: 'yes' }),
  /FIELD_DESCRIPTOR_TYPE_INVALID/,
);
assert.throws(
  () => decodeContractV2FieldDescriptor({ ...readyMoney, relationEntry: [] }),
  /FIELD_DESCRIPTOR_TYPE_INVALID/,
);
assert.throws(
  () => decodeContractV2FieldDescriptor({ ...readyMoney, widgetOptions: [] }),
  /FIELD_DESCRIPTOR_TYPE_INVALID/,
);
assert.throws(
  () => decodeContractV2FieldDescriptor({ ...readyMoney, subview: [] }),
  /FIELD_DESCRIPTOR_TYPE_INVALID/,
);
assert.throws(
  () => decodeContractV2FieldDescriptor({ ...readyMoney, surfaceRole: 7 }),
  /FIELD_DESCRIPTOR_TYPE_INVALID/,
);
assert.throws(
  () => decodeContractV2FieldDescriptor({ ...readyMoney, technical: 'false' }),
  /FIELD_DESCRIPTOR_TYPE_INVALID/,
);
assert.throws(
  () => decodeContractV2FieldDescriptor({ ...readyMoney, currencyField: 7 }),
  /FIELD_DESCRIPTOR_TYPE_INVALID/,
);
assert.throws(
  () => decodeContractV2FieldDescriptor({
    ...readyMoney,
    currencyField: readyMoney.fieldCode,
  }),
  /FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED/,
);
const moneyWithoutObservedCurrencyPrecision = { ...readyMoney } as Record<string, unknown>;
delete moneyWithoutObservedCurrencyPrecision.digits;
assert.equal(
  decodeContractV2FieldDescriptor(moneyWithoutObservedCurrencyPrecision).descriptor.currencyField,
  readyMoney.currencyField,
  'a monetary field may declare its native currency binding before a current currency fact exists',
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
    'metric.currency': {
      schemaVersion: '1.0.0',
      fieldCode: 'currency_id',
      label: '币种',
      fieldType: 'many2one',
      widgetType: 'many2one',
      componentKey: 'sc.relation.many2one',
      semanticType: 'relation',
      relation: 'res.currency',
    },
  },
  block_data_contracts: {
    ds_metrics: {
      schemaVersion: '1.0.0',
      fieldRefs: {
        value: { kind: 'descriptor', descriptorId: 'metric.value', rawValuePath: 'value' },
        currency_id: { kind: 'descriptor', descriptorId: 'metric.currency', rawValuePath: 'currency_id' },
        active: { kind: 'descriptor', descriptorId: 'metric.active', rawValuePath: 'active' },
        note: { kind: 'descriptor', descriptorId: 'metric.note', rawValuePath: 'note' },
      },
      rows: [
        { rowKey: 'money', values: { value: 0, currency_id: 7, active: false, note: '' } },
        { rowKey: 'null', values: { value: null, currency_id: 7, active: null, note: null } },
        { rowKey: 'missing', values: {} },
      ],
      context: {
        currencies: { '7': { id: 7, code: 'CNY', symbol: '¥' } },
        timezone: 'Asia/Shanghai',
      },
      sourceAuthority: pageBlockSourceAuthority,
    },
  },
});
const resolved = resolvePageBlockData(pageContract, 'ds_metrics');
assert.equal(resolved[0].values.value, 0);
assert.equal(resolved[0].values.active, false);
assert.equal(resolved[0].values.note, '');
assert.equal(resolved[0].fieldDescriptors.value.semanticType, 'money');
assert.equal(resolvePageBlockCurrencyLabel(resolved[0], 'currency_id'), 'CNY');
const moneyText = presentDeclaredBusinessValue({
  field: {
    name: resolved[0].fieldDescriptors.value.fieldCode,
    type: resolved[0].fieldDescriptors.value.fieldType,
    componentKey: resolved[0].fieldDescriptors.value.componentKey,
    widget: resolved[0].fieldDescriptors.value.widgetType,
    digits: [16, 2],
    currencyLabel: resolvePageBlockCurrencyLabel(resolved[0], 'currency_id'),
  },
  value: 1234.5,
}).text;
assert.match(moneyText, /1,234\.50/);
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
const reordered = overlayPageBlockDataRows(
  [resolved[0], resolved[1]],
  [
    { key: 'null', title: 'Null row', value: 9, action_key: 'wrong-null' },
    { key: 'external', title: 'External row', value: 8, action_key: 'wrong-external' },
    { key: 'money', title: 'Money row', value: 1, action_key: 'money-action' },
  ],
);
assert.equal(reordered[0].title, 'Money row');
assert.equal(reordered[0].action_key, 'money-action');
assert.equal(reordered[1].title, 'Null row');
assert.equal(reordered[1].action_key, 'wrong-null');
const unmatched = overlayPageBlockDataRows(
  [resolved[2]],
  [{ key: 'external', title: 'External row', value: 8, action_key: 'wrong-external' }],
);
assert.equal('title' in unmatched[0], false);
assert.equal('action_key' in unmatched[0], false);
assert.equal('value' in unmatched[0], false);
assert.throws(
  () => overlayPageBlockDataRows(
    [resolved[0]],
    [{ key: 'money', title: 'First' }, { key: 'money', title: 'Second' }],
  ),
  /stable rowKey matching is ambiguous/,
);

assert.equal(resolvePageBlockCurrencyLabel(
  { ...resolved[0], values: { value: 0 } },
  'currency_id',
), '');

const widgetBackedContract = decodePageOrchestrationContract({
  contract_version: '2.1.0',
  schema_version: '2.1.0',
  page: { key: 'widget-backed' },
  zones: [],
  block_field_descriptors: {
    'anchor.descriptor': readyMoney,
    'anchor.currency': {
      schemaVersion: '1.0.0',
      fieldCode: 'currency_id',
      label: '币种',
      fieldType: 'many2one',
      widgetType: 'many2one',
      componentKey: 'sc.relation.many2one',
      semanticType: 'relation',
      relation: 'res.currency',
    },
  },
  block_data_contracts: {
    ds_widget: {
      schemaVersion: '1.0.0',
      fieldRefs: {
        value: { kind: 'widget', widgetId: 'widget.money', rawValuePath: 'value' },
        currency_id: { kind: 'descriptor', descriptorId: 'anchor.currency', rawValuePath: 'currency_id' },
      },
      rows: [{ rowKey: 'widget', values: { value: 0, currency_id: 7 } }],
      context: { currencies: { '7': { id: 7, code: 'CNY', symbol: '¥' } }, timezone: 'UTC' },
      sourceAuthority: pageBlockSourceAuthority,
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
  /2\.0\.0 cannot contain semantic carriers/,
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

function cloneContract<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

const missingAuthority = cloneContract(pageContract as Record<string, unknown>);
delete (((missingAuthority.block_data_contracts as Record<string, Record<string, unknown>>).ds_metrics).sourceAuthority);
assert.throws(
  () => decodePageOrchestrationContract(missingAuthority),
  /sourceAuthority must be an object/,
);

const unknownAuthority = cloneContract(pageContract as Record<string, unknown>);
((unknownAuthority.block_data_contracts as Record<string, Record<string, unknown>>).ds_metrics).sourceAuthority = {
  ...pageBlockSourceAuthority,
  unexpected: true,
};
assert.throws(
  () => decodePageOrchestrationContract(unknownAuthority),
  /sourceAuthority\.unexpected is not allowed/,
);

for (const [label, mutator, pattern] of [
  [
    'missing authorities',
    (authority: Record<string, unknown>) => { delete authority.authorities; },
    /authorities must exactly be/,
  ],
  [
    'wrong kind',
    (authority: Record<string, unknown>) => { authority.kind = 'test'; },
    /kind must be page_block_data_producer/,
  ],
  [
    'wrong carrier',
    (authority: Record<string, unknown>) => { authority.carrier = 'attachment-fact.v1'; },
    /carrier must be page-block-data\.v1/,
  ],
  [
    'wrong schema',
    (authority: Record<string, unknown>) => { authority.schemaVersion = '2.0.0'; },
    /schemaVersion must be 1\.0\.0/,
  ],
  [
    'frontend defaults enabled',
    (authority: Record<string, unknown>) => { authority.noFrontendDefaults = false; },
    /noFrontendDefaults must be true/,
  ],
] as const) {
  const invalidAuthority = cloneContract(pageContract as Record<string, unknown>);
  const authority = (((invalidAuthority.block_data_contracts as Record<string, Record<string, unknown>>).ds_metrics).sourceAuthority) as Record<string, unknown>;
  mutator(authority);
  assert.throws(
    () => decodePageOrchestrationContract(invalidAuthority),
    pattern,
    label,
  );
}

const unknownFieldRef = cloneContract(pageContract as Record<string, unknown>);
const fieldRefs = (((unknownFieldRef.block_data_contracts as Record<string, Record<string, unknown>>).ds_metrics).fieldRefs) as Record<string, Record<string, unknown>>;
fieldRefs.value.unexpected = true;
assert.throws(
  () => decodePageOrchestrationContract(unknownFieldRef),
  /fieldRefs\.value\.unexpected is not allowed/,
);

const unknownRowEnvelope = cloneContract(pageContract as Record<string, unknown>);
const rows = (((unknownRowEnvelope.block_data_contracts as Record<string, Record<string, unknown>>).ds_metrics).rows) as Array<Record<string, unknown>>;
rows[0].unexpected = true;
assert.throws(
  () => decodePageOrchestrationContract(unknownRowEnvelope),
  /rows\[0\]\.unexpected is not allowed/,
);

const unknownContext = cloneContract(pageContract as Record<string, unknown>);
const context = (((unknownContext.block_data_contracts as Record<string, Record<string, unknown>>).ds_metrics).context) as Record<string, unknown>;
context.unexpected = true;
assert.throws(
  () => decodePageOrchestrationContract(unknownContext),
  /context\.unexpected is not allowed/,
);

const unknownCurrency = cloneContract(pageContract as Record<string, unknown>);
const currencies = ((((unknownCurrency.block_data_contracts as Record<string, Record<string, unknown>>).ds_metrics).context) as Record<string, unknown>).currencies as Record<string, Record<string, unknown>>;
currencies['7'].unexpected = true;
assert.throws(
  () => decodePageOrchestrationContract(unknownCurrency),
  /currencies\.7\.unexpected is not allowed/,
);

const missingCurrencyIdentity = cloneContract(pageContract as Record<string, unknown>);
delete (((missingCurrencyIdentity.block_data_contracts as Record<string, Record<string, unknown>>).ds_metrics).fieldRefs as Record<string, unknown>).currency_id;
const decodedMissingCurrency = decodePageOrchestrationContract(missingCurrencyIdentity);
assert.throws(
  () => resolvePageBlockData(decodedMissingCurrency, 'ds_metrics'),
  /money value requires exactly one currency descriptor/,
);

const wrongCurrencyDescriptor = cloneContract(pageContract as Record<string, unknown>);
const wrongCurrencyFields = wrongCurrencyDescriptor.block_field_descriptors as Record<string, Record<string, unknown>>;
wrongCurrencyFields['metric.currency'].relation = 'res.partner';
assert.throws(
  () => resolvePageBlockData(
    decodePageOrchestrationContract(wrongCurrencyDescriptor),
    'ds_metrics',
  ),
  /money value requires exactly one currency descriptor/,
);

const duplicateCurrencyDescriptor = cloneContract(pageContract as Record<string, unknown>);
const duplicateFields = duplicateCurrencyDescriptor.block_field_descriptors as Record<string, Record<string, unknown>>;
duplicateFields['metric.currency.duplicate'] = {
  ...duplicateFields['metric.currency'],
};
const duplicateData = (duplicateCurrencyDescriptor.block_data_contracts as Record<string, Record<string, unknown>>).ds_metrics;
(duplicateData.fieldRefs as Record<string, unknown>).currency_id_duplicate = {
  kind: 'descriptor',
  descriptorId: 'metric.currency.duplicate',
  rawValuePath: 'currency_id',
};
assert.throws(
  () => resolvePageBlockData(
    decodePageOrchestrationContract(duplicateCurrencyDescriptor),
    'ds_metrics',
  ),
  /money value requires exactly one currency descriptor/,
);

console.log('P0_A_DESCRIPTOR_AND_PAGE_BLOCK_DATA=PASS');
