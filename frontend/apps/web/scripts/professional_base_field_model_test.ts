import assert from 'node:assert/strict';
import {
  PROFESSIONAL_BASE_FIELD_TYPES,
  isProfessionalBaseFieldCandidate,
  resolveProfessionalBaseFieldModel,
} from '../src/components/professional-fields/professionalBaseFieldModel';

const modes = ['task', 'workspace'] as const;
const profiles = ['create', 'edit', 'readonly'] as const;
let cases = 0;
for (const presentationMode of modes) {
  for (const renderProfile of profiles) {
    for (const fieldType of PROFESSIONAL_BASE_FIELD_TYPES) {
      const model = resolveProfessionalBaseFieldModel({ fieldType, presentationMode, renderProfile });
      assert.equal(model.fieldType, fieldType);
      assert.equal(model.presentationMode, presentationMode);
      assert.equal(model.renderProfile, renderProfile);
      assert.equal(model.controlState, renderProfile === 'readonly' ? 'readonly' : 'editable');
      cases += 1;
    }
  }
}

assert.equal(cases, 54);
assert.equal(resolveProfessionalBaseFieldModel({
  fieldType: 'char', presentationMode: 'task', renderProfile: 'edit', readonly: true,
}).controlState, 'readonly');
assert.equal(isProfessionalBaseFieldCandidate('selection', 'radio'), false);
assert.equal(isProfessionalBaseFieldCandidate('date', 'daterange'), false);
assert.equal(isProfessionalBaseFieldCandidate('many2one'), false);
assert.equal(resolveProfessionalBaseFieldModel({
  fieldType: 'char', presentationMode: 'unscoped', renderProfile: 'unscoped',
}).controlState, 'editable');
assert.throws(() => resolveProfessionalBaseFieldModel({
  fieldType: 'many2one', presentationMode: 'workspace', renderProfile: 'edit',
}), /PROFESSIONAL_BASE_FIELD_UNSUPPORTED/);

console.log(`[professional_base_field_model_test] PASS matrix=${cases} counterexamples=6`);
