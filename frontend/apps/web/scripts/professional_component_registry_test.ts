import { strict as assert } from 'node:assert';
import {
  professionalComponentRegistry,
  resolveProfessionalComponent,
  resolveProfessionalComponentRegistration,
  type ProfessionalComponentRegistration,
} from '../src/app/presentation/professionalComponentRegistry';

const ready = resolveProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
});
assert.equal(ready.readiness, 'ready');
assert.equal(ready.renderer, 'FormSectionField');

const fallback = resolveProfessionalComponent({
  componentKey: 'sc.tree.data', fieldType: 'one2many', presentationMode: 'workspace', renderProfile: 'readonly',
});
assert.equal(fallback.readiness, 'readable_fallback');
assert.equal(fallback.fallback, 'ReadableFieldValue');

assert.throws(() => resolveProfessionalComponent({
  componentKey: 'sc.unknown', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
}), /PROFESSIONAL_COMPONENT_UNREGISTERED/);
assert.throws(() => resolveProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'many2one', presentationMode: 'task', renderProfile: 'edit',
}), /PROFESSIONAL_COMPONENT_FIELD_TYPE_MISMATCH/);

const restricted: ProfessionalComponentRegistration = {
  ...ready,
  componentKey: 'sc.test.restricted',
  supportedPresentationModes: ['task'],
  supportedRenderProfiles: ['edit'],
  requiredCapabilities: ['relation.read'],
};
const testRegistry = new Map([[restricted.componentKey, restricted]]);
assert.throws(() => resolveProfessionalComponentRegistration(testRegistry, {
  componentKey: restricted.componentKey, fieldType: 'char', presentationMode: 'workspace', renderProfile: 'edit',
}), /PROFESSIONAL_COMPONENT_PRESENTATION_MODE_MISMATCH/);
assert.throws(() => resolveProfessionalComponentRegistration(testRegistry, {
  componentKey: restricted.componentKey, fieldType: 'char', presentationMode: 'task', renderProfile: 'readonly',
}), /PROFESSIONAL_COMPONENT_RENDER_PROFILE_MISMATCH/);
assert.throws(() => resolveProfessionalComponentRegistration(testRegistry, {
  componentKey: restricted.componentKey, fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
}), /PROFESSIONAL_COMPONENT_CAPABILITY_MISSING/);
assert.equal(resolveProfessionalComponentRegistration(testRegistry, {
  componentKey: restricted.componentKey,
  fieldType: 'char',
  presentationMode: 'task',
  renderProfile: 'edit',
  capabilities: ['relation.read'],
}).componentKey, restricted.componentKey);

assert.equal(professionalComponentRegistry.size, 16);
console.log('[professional_component_registry_test] PASS cases=9');
