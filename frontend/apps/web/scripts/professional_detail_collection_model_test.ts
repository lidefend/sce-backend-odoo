import assert from 'node:assert/strict';
import {
  detailCollectionAuthority,
  isProfessionalDetailCollectionField,
} from '../src/components/professional-fields/professionalDetailCollectionModel';

const modes = ['task', 'workspace'] as const;
const profiles = ['create', 'edit', 'readonly'] as const;
let matrix = 0;
for (const presentationMode of modes) {
  for (const renderProfile of profiles) {
    const field = {
      componentKey: 'sc.relation.table', type: 'one2many', name: 'line_ids',
      presentationMode, renderProfile, descriptor: { relation: 'x.line' },
    } as never;
    const adapter = {
      visibleOne2manyRows: () => [{ key: '1', values: {} }],
      one2manyColumns: () => [{ name: 'name', label: 'Name', ttype: 'char', required: true }],
      one2manyCanCreate: () => renderProfile !== 'readonly',
      one2manyCanInlineEdit: () => renderProfile === 'edit',
      removedOne2manyRows: () => [],
      showOne2manyErrors: renderProfile !== 'readonly',
      one2manySummary: () => '1 line',
    } as never;
    assert.equal(isProfessionalDetailCollectionField(field), true);
    const authority = detailCollectionAuthority(field, adapter);
    assert.equal(authority.relationModel, 'x.line');
    assert.equal(authority.rowCount, 1);
    assert.equal(authority.columnCount, 1);
    assert.equal(authority.canCreate, renderProfile !== 'readonly');
    assert.equal(authority.canInlineEdit, renderProfile === 'edit');
    matrix += 1;
  }
}
assert.equal(matrix, 6);
assert.equal(isProfessionalDetailCollectionField({ componentKey: 'sc.relation.table', type: 'many2many' } as never), false);
assert.throws(() => detailCollectionAuthority({ componentKey: 'sc.table.data', type: 'one2many' } as never, {} as never), /PROFESSIONAL_DETAIL_COLLECTION_UNSUPPORTED/);
console.log(`[professional_detail_collection_model_test] PASS matrix=${matrix} counterexamples=2`);
