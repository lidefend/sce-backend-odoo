import assert from 'node:assert/strict';
import formPayload from '../../../../artifacts/p0_contract_producer_01/ui-contract-v2-project-form.json';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';

let strictDescriptorCount = 0;

const formSnapshot = decodeContractV2Snapshot(formPayload);
assert.equal(formSnapshot.pageInfo.contractVersion, '2.6.0');
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

console.log(
  `P0_A_REAL_CONTRACT_V2_DECODE=PASS strictDescriptors=${strictDescriptorCount} `
  + 'audience=form',
);
