import assert from 'node:assert/strict';
import fs from 'node:fs';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';

let strictDescriptorCount = 0;

const formPayload = JSON.parse(fs.readFileSync(
  process.env.P0A_FORM_CONTRACT_PATH
    || '.runtime/p0-contract-producer-evidence/ui-contract-v2-project-form.json',
  'utf8',
));
const formSnapshot = decodeContractV2Snapshot(formPayload);
assert.equal(formSnapshot.pageInfo.contractVersion, '2.7.0');
function assertNoWireComponentIdentity(value: unknown, path = '$'): void {
  const opaqueValueKeys = new Set([
    'dataContract', 'dataPatch', 'dataMeta', 'mainData', 'datasets',
    'payload', 'actionPayload', 'context', 'domain', 'options', 'optionsRaw',
    'values', 'value', 'value_json', 'valueJson', 'default_vals',
  ]);
  if (Array.isArray(value)) {
    value.forEach((item, index) => assertNoWireComponentIdentity(item, `${path}[${index}]`));
    return;
  }
  if (!value || typeof value !== 'object') return;
  Object.entries(value as Record<string, unknown>).forEach(([key, child]) => {
    assert.ok(
      key !== 'componentKey' && key !== 'component_key' && key !== 'componentRegistry',
      `V2.7 wire leaked frontend implementation identity at ${path}.${key}`,
    );
    if (opaqueValueKeys.has(key)) return;
    assertNoWireComponentIdentity(child, `${path}.${key}`);
  });
}
assertNoWireComponentIdentity(formPayload);
const dateStartDescriptors: Array<Record<string, unknown>> = [];
function walkForm(rows: unknown): void {
  if (!Array.isArray(rows)) return;
  rows.forEach((row) => {
    if (!row || typeof row !== 'object') return;
    const record = row as Record<string, unknown>;
    const widgets = Array.isArray(record.widgetList) ? record.widgetList : [];
    widgets.forEach((widget) => {
      if (!widget || typeof widget !== 'object') return;
      const descriptor = (widget as Record<string, unknown>).fieldDescriptor;
      if (!descriptor || typeof descriptor !== 'object') return;
      strictDescriptorCount += 1;
      if ((widget as Record<string, unknown>).fieldCode === 'date_start') {
        dateStartDescriptors.push(descriptor as Record<string, unknown>);
      }
    });
    walkForm(record.children);
  });
}
walkForm(formSnapshot.layoutContract.containerTree);
assert.equal(dateStartDescriptors.length, 1);
assert.equal(dateStartDescriptors[0].widgetType, 'daterange');
assert.equal(dateStartDescriptors[0].semanticType, 'date');
assert.equal(dateStartDescriptors[0].componentKey, 'sc.input.date');
assert.deepEqual(dateStartDescriptors[0].temporal, {
  kind: 'date',
  timezoneAuthority: 'not_applicable',
});

function firstContractWidget(payload: Record<string, unknown>): Record<string, unknown> {
  const queue = [...((payload.layoutContract as Record<string, unknown>).containerTree as unknown[])];
  while (queue.length) {
    const row = queue.shift();
    if (!row || typeof row !== 'object') continue;
    const record = row as Record<string, unknown>;
    const widgets = Array.isArray(record.widgetList) ? record.widgetList : [];
    if (widgets.length) return widgets[0] as Record<string, unknown>;
    queue.push(...(Array.isArray(record.children) ? record.children : []));
  }
  throw new Error('contract fixture has no widget');
}

const injectedComponent = JSON.parse(JSON.stringify(formPayload)) as Record<string, unknown>;
firstContractWidget(injectedComponent).componentKey = 'sc.input.date';
assert.throws(
  () => decodeContractV2Snapshot(injectedComponent),
  /frontend implementation identity/,
  'an existing registered component key must remain illegal in V2.7',
);

const missingDescriptorSemantic = JSON.parse(JSON.stringify(formPayload)) as Record<string, unknown>;
const missingDescriptorWidget = firstContractWidget(missingDescriptorSemantic);
delete (missingDescriptorWidget.fieldDescriptor as Record<string, unknown>).semanticType;
assert.throws(
  () => decodeContractV2Snapshot(missingDescriptorSemantic),
  /FIELD_DESCRIPTOR_SEMANTIC_MISMATCH/,
  'V2.7 strict field-descriptor validation must still run',
);

const missingOccurrenceLocator = JSON.parse(JSON.stringify(formPayload)) as Record<string, unknown>;
delete firstContractWidget(missingOccurrenceLocator).nativeLocator;
assert.throws(
  () => decodeContractV2Snapshot(missingOccurrenceLocator),
  /nativeLocator and occurrenceIndex must be supplied together/,
  'V2.7 strict widget occurrence validation must still run',
);

const missingActionOccurrence = JSON.parse(JSON.stringify(formPayload)) as Record<string, unknown>;
const actionContract = missingActionOccurrence.actionContract as Record<string, unknown>;
const actionRules = actionContract.actionRuleList as Array<Record<string, unknown>>;
const actionWithNativeIdentity = actionRules.find((row) => (
  row.nativeIdentity && typeof row.nativeIdentity === 'object'
));
assert.ok(actionWithNativeIdentity, 'fixture must contain a native action identity');
delete (actionWithNativeIdentity.nativeIdentity as Record<string, unknown>).occurrenceKey;
assert.throws(
  () => decodeContractV2Snapshot(missingActionOccurrence),
  /occurrenceKey/,
  'V2.7 strict action native-identity validation must still run',
);

console.log(
  `P0_A_REAL_CONTRACT_V2_DECODE=PASS strictDescriptors=${strictDescriptorCount} `
  + 'audience=form',
);
