import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { decodeContractV2Snapshot } from '../src/app/contracts/v2/schema';
import { createContractV2Store, resolveContractV2FormFieldMap } from '../src/app/contracts/v2/store';
import {
  evaluateNativeModifierValue,
  resolveNativeRelationActiveActions,
} from '../src/pages/contractForm/nativeLayoutUtils';

const evidence = JSON.parse(
  fs.readFileSync('.runtime/relation-active-actions/real-contract.json', 'utf8'),
);
const values = { state: 'done' };
const evaluate = (value: unknown) => evaluateNativeModifierValue(
  value,
  (field) => values[field],
);

interface EvidenceWidget {
  fieldCode: string;
  fieldDescriptor: Record<string, unknown>;
  componentConfig: Record<string, unknown>;
}
interface EvidenceNode {
  widgetList?: EvidenceWidget[];
  children?: EvidenceNode[];
}

function widgets(rows: EvidenceNode[]): EvidenceWidget[] {
  return rows.flatMap((row) => [
    ...(row.widgetList || []),
    ...widgets(row.children || []),
  ]);
}

function findWidget(rows: EvidenceNode[], fieldCode: string): EvidenceWidget {
  const found = widgets(rows).find((widget) => widget.fieldCode === fieldCode);
  assert.ok(found, `real contract must include widget ${fieldCode}`);
  return found;
}

test('real assembler output decodes occurrence relation actions and the consumer reads descriptors only', () => {
  assert.ok(evidence.producer_evidence.receipt);
  assert.equal(evidence.producer_evidence.relation_descriptors, 3);
  const snapshot = decodeContractV2Snapshot(evidence.contract);
  const formFields = resolveContractV2FormFieldMap(createContractV2Store(snapshot));
  const rows = snapshot.layoutContract.containerTree as EvidenceNode[];
  const first = findWidget(rows, 'partner_id');
  const second = findWidget(rows, 'reviewer_id');
  const tags = findWidget(rows, 'tag_ids');

  assert.deepEqual(first.fieldDescriptor.relationActiveActions, {
    create: false,
    write: true,
  });
  assert.deepEqual(second.fieldDescriptor.relationActiveActions, {
    create: {
      kind: 'field_compare',
      semantics: 'python',
      field: 'state',
      operator: '!=',
      value: 'done',
      raw: "state != 'done'",
    },
  });
  assert.deepEqual(tags.fieldDescriptor.relationActiveActions, { create: true });
  assert.deepEqual(formFields.partner_id.relationActiveActions, {
    create: false,
    write: true,
  }, 'ContractV2FormFieldDescriptor compatibility projection preserves the descriptor declaration');
  assert.deepEqual(formFields.tag_ids.relationActiveActions, { create: true });

  assert.deepEqual(resolveNativeRelationActiveActions(first, evaluate), {
    create: false,
    write: true,
  });
  assert.deepEqual(resolveNativeRelationActiveActions(second, evaluate), {
    create: false,
    write: null,
  });
  assert.deepEqual(resolveNativeRelationActiveActions(tags, evaluate), {
    create: true,
    write: null,
  });

  const conflicting = {
    ...first,
    componentConfig: {
      ...first.componentConfig,
      relationActiveActions: { create: true, write: false },
    },
  };
  assert.deepEqual(resolveNativeRelationActiveActions(conflicting, evaluate), {
    create: false,
    write: true,
  }, 'componentConfig cannot override or become a fallback for descriptor declarations');
  assert.deepEqual(resolveNativeRelationActiveActions({
    componentConfig: { relationActiveActions: { create: true, write: true } },
  }, evaluate), {
    create: null,
    write: null,
  }, 'legacy config without a descriptor declaration is not consumed');
});
