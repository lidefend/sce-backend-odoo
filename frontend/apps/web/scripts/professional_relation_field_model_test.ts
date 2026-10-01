import assert from 'node:assert/strict';
import {
  PROFESSIONAL_RELATION_COMPONENT_KEYS,
  isProfessionalRelationField,
  relationFieldAuthority,
  resolveProfessionalMany2oneDisplayValue,
  resolveProfessionalMany2oneQueryKey,
  resolveProfessionalMany2oneQueryKeyword,
  resolveProfessionalMany2oneRecordValue,
  resolveProfessionalMany2oneSearchInput,
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
// Query keyword channel never falls back to the display projection, and it is
// the exact typed text: it is the controlled value of the official Select's
// search input, so normalizing it deletes characters that are still in flight.
assert.equal(resolveProfessionalMany2oneQueryKeyword({ relationQueryKeyword: '  客户B  ' }), '  客户B  ');
assert.equal(resolveProfessionalMany2oneQueryKeyword({ relationQueryKeyword: '' }), '');
assert.equal(resolveProfessionalMany2oneQueryKeyword({}), '');

// Counterexample (defect 2026-09-29): a controlled search input whose stored
// keyword is trimmed loses the space the moment it is typed, so a multi-word
// keyword degrades to a single word and the request can never match
// "FE Project". Replay the keystrokes through the projections that own each side.
let displayedKeyword = '';
let requestKeyword = '';
for (const character of 'FE Project A') {
  const typed = `${displayedKeyword}${character}`;
  // The Select is fully controlled by the stored keyword, so the next keystroke
  // lands on whatever the previous projection published.
  displayedKeyword = resolveProfessionalMany2oneSearchInput(typed);
  requestKeyword = resolveProfessionalMany2oneQueryKey(typed);
}
assert.equal(displayedKeyword, 'FE Project A');
assert.equal(requestKeyword, 'FE Project A');
assert.equal(resolveProfessionalMany2oneQueryKeyword({ relationQueryKeyword: 'FE ' }), 'FE ');
assert.equal(resolveProfessionalMany2oneSearchInput('FE Project'), 'FE Project');
assert.equal(resolveProfessionalMany2oneQueryKey('  FE Project  '), 'FE Project');
assert.equal(resolveProfessionalMany2oneQueryKey('   '), '');

console.log(`[professional_relation_field_model_test] PASS matrix=${matrix} counterexamples=17`);
