import assert from 'node:assert/strict';
import payload from '../../../../artifacts/p0_contract_producer_01/ui-contract-v2-project-list.json';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';

const snapshot = decodeContractV2Snapshot(payload);
assert.equal(snapshot.pageInfo.contractVersion, '2.6.0');

let strictDescriptorCount = 0;
function walk(rows: unknown): void {
  if (!Array.isArray(rows)) return;
  rows.forEach((row) => {
    if (!row || typeof row !== 'object') return;
    const record = row as Record<string, unknown>;
    const widgets = Array.isArray(record.widgetList) ? record.widgetList : [];
    widgets.forEach((widget) => {
      if (!widget || typeof widget !== 'object') return;
      const descriptor = (widget as Record<string, unknown>).fieldDescriptor;
      if (!descriptor || typeof descriptor !== 'object') return;
      assert.equal((descriptor as Record<string, unknown>).schemaVersion, '1.0.0');
      strictDescriptorCount += 1;
    });
    walk(record.children);
  });
}
walk(snapshot.layoutContract.containerTree);
assert.ok(strictDescriptorCount > 0);
console.log(`P0_A_REAL_CONTRACT_V2_DECODE=PASS strictDescriptors=${strictDescriptorCount}`);
