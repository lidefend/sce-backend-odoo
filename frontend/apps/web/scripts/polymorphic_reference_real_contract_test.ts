import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import { decodeContractV2FieldDescriptor } from '../src/app/contracts/v2/fieldDescriptor';

const evidence = JSON.parse(fs.readFileSync('.runtime/polymorphic-reference/real-contract.json', 'utf8'));
interface EvidenceWidget { fieldCode?: string; fieldDescriptor: Record<string, unknown> }
interface EvidenceNode { widgetList?: EvidenceWidget[]; children?: EvidenceNode[] }
function sourceWidget(contract: unknown): EvidenceWidget {
  function walk(rows: EvidenceNode[]): EvidenceWidget | undefined {
    for (const row of rows) {
      const found = (row.widgetList || []).find((widget) => widget.fieldCode === 'sc_source_res_id');
      if (found) return found;
      const child = walk(row.children || []);
      if (child) return child;
    }
    return undefined;
  }
  const found = walk((contract as { layoutContract: { containerTree: EvidenceNode[] } }).layoutContract.containerTree);
  assert.ok(found, 'real contract must include the native polymorphic occurrence');
  return found;
}
test('real notification contract decodes and preserves the model pointer, value and renderer semantics', () => {
  assert.ok(evidence.producer_evidence.receipt);
  const snapshot = decodeContractV2Snapshot(evidence.notification);
  const descriptor = sourceWidget(snapshot).fieldDescriptor;
  assert.equal(descriptor.referenceModelField, 'sc_source_model');
  assert.equal(descriptor.fieldType, 'many2one_reference');
  assert.equal(descriptor.relation, undefined);
  assert.equal(descriptor.componentKey, 'sc.display.text');
  assert.equal(snapshot.dataContract.mainData.sc_source_model, 'project.project');
  assert.equal(snapshot.dataContract.mainData.sc_source_res_id, evidence.notification.dataContract.mainData.sc_source_res_id);
  const broken = structuredClone(evidence.notification);
  delete sourceWidget(broken).fieldDescriptor.referenceModelField;
  assert.throws(() => decodeContractV2Snapshot(broken), /sc_source_res_id.*FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED/);
});
test('native Reference descriptor has no fixed relation and the native value keeps its model identity', () => {
  const descriptor = decodeContractV2FieldDescriptor(evidence.native_reference).descriptor;
  assert.equal(descriptor.fieldType, 'reference');
  assert.equal(descriptor.relation, undefined);
  assert.equal(descriptor.componentKey, 'sc.display.text');
  assert.match(evidence.native_reference_value, /^ir\.actions\.act_window,[1-9][0-9]*$/);
});
