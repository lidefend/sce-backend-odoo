import assert from 'node:assert/strict';
import {
  PROFESSIONAL_RELATION_COMPONENT_KEYS,
  isProfessionalRelationField,
  relationFieldAuthority,
  resolveProfessionalMany2oneDisplayValue,
  resolveProfessionalMany2oneQueryKeyword,
  resolveProfessionalMany2oneRecordValue,
} from '../src/components/professional-fields/professionalRelationFieldModel';

const modes = ['task', 'workspace'] as const;
const profiles = ['create', 'edit', 'readonly'] as const;
let matrix = 0;
for (const presentationMode of modes) {
  for (const renderProfile of profiles) {
    for (const componentKey of PROFESSIONAL_RELATION_COMPONENT_KEYS) {
      const type = componentKey === 'sc.relation.many2one' ? 'many2one' : 'many2many';
      const field = {
        componentKey, type, presentationMode, renderProfile,
        descriptor: { relation: 'x.related' }, relationCreateMode: 'dialog',
        many2oneOpenToken: '__open__', many2oneSearchToken: '__search__', many2oneCreateToken: '__create__',
      } as never;
      assert.equal(isProfessionalRelationField(field), true);
      const authority = relationFieldAuthority(field);
      assert.equal(authority.relationModel, 'x.related');
      assert.equal(authority.createMode, 'dialog');
      assert.equal(authority.canOpenRecord, true);
      assert.equal(authority.canSearch, true);
      assert.equal(authority.canCreate, true);
      matrix += 1;
    }
  }
}
assert.equal(matrix, 18);
assert.equal(isProfessionalRelationField({ componentKey: 'sc.relation.many2one', type: 'many2many' } as never), false);
assert.equal(isProfessionalRelationField({ componentKey: 'sc.select.remote', type: 'many2one' } as never), true);
assert.throws(() => relationFieldAuthority({ componentKey: 'sc.relation.many2many', type: 'char' } as never), /PROFESSIONAL_RELATION_FIELD_UNSUPPORTED/);

// Display value: the selected record always wins over a transient keyword.
assert.equal(resolveProfessionalMany2oneDisplayValue({
  many2oneTextValue: ' 搜索词B ', inputValue: 13, relationOptions: [{ id: 13, label: ' 客户A ' }],
}), '客户A');
assert.equal(resolveProfessionalMany2oneDisplayValue({
  many2oneTextValue: ' 权威投影 ', inputValue: 13, relationOptions: [],
}), '权威投影');
assert.equal(resolveProfessionalMany2oneDisplayValue({ inputValue: false, relationOptions: [] }), '');
assert.equal(resolveProfessionalMany2oneDisplayValue({
  inputValue: 99, relationOptions: [{ id: 13, label: '不匹配' }],
}), '');
assert.equal(resolveProfessionalMany2oneDisplayValue({
  inputValue: 'false', relationOptions: [{ id: 13, label: '不匹配' }],
}), '');
// Record value projection is the single authority for the selected id.
assert.equal(resolveProfessionalMany2oneRecordValue({ inputValue: 13 }), '13');
assert.equal(resolveProfessionalMany2oneRecordValue({ inputValue: false }), '');
assert.equal(resolveProfessionalMany2oneRecordValue({ inputValue: 'false' }), '');
assert.equal(resolveProfessionalMany2oneRecordValue({ inputValue: null }), '');
assert.equal(resolveProfessionalMany2oneRecordValue({ inputValue: undefined }), '');
// Query keyword channel never falls back to the display projection.
assert.equal(resolveProfessionalMany2oneQueryKeyword({ relationQueryKeyword: '  客户B  ' }), '客户B');
assert.equal(resolveProfessionalMany2oneQueryKeyword({ relationQueryKeyword: '' }), '');
assert.equal(resolveProfessionalMany2oneQueryKeyword({}), '');

console.log(`[professional_relation_field_model_test] PASS matrix=${matrix} counterexamples=13`);
