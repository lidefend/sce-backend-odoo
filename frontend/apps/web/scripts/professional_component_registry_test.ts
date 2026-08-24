import { strict as assert } from 'node:assert';
import {
  professionalComponentRegistrations,
  resolveProfessionalComponent,
  resolveProfessionalComponentRegistration,
  type ProfessionalComponentRegistration,
} from '../src/app/presentation/professionalComponentRegistry';

const ready = resolveProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
});
assert.equal(ready.readiness, 'ready');
assert.equal(ready.renderer, 'ProfessionalBaseFieldControl');

assert.throws(() => resolveProfessionalComponent({
  componentKey: 'sc.unknown', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit',
}), /PROFESSIONAL_COMPONENT_UNREGISTERED/);
assert.throws(() => resolveProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: 'many2one', presentationMode: 'task', renderProfile: 'edit',
}), /PROFESSIONAL_COMPONENT_FIELD_TYPE_MISMATCH/);
assert.throws(() => resolveProfessionalComponent({
  componentKey: 'sc.input.text', fieldType: '', presentationMode: 'task', renderProfile: 'edit',
}), /PROFESSIONAL_COMPONENT_FIELD_TYPE_MISSING/);

const restricted: ProfessionalComponentRegistration = {
  ...ready,
  componentKey: 'sc.test.restricted',
  supportedPresentationModes: ['task'],
  supportedRenderProfiles: ['edit'],
  requiredCapabilities: ['relation.read'],
  rendererByFieldType: {},
};
const testRegistry = new Map([[restricted.componentKey, restricted]]);
const fallbackRegistry = new Map([["sc.test.fallback", {
  ...restricted,
  componentKey: 'sc.test.fallback',
  readiness: 'readable_fallback' as const,
  fallback: 'ReadableFieldValue',
}]]);
assert.equal(resolveProfessionalComponentRegistration(fallbackRegistry, {
  componentKey: 'sc.test.fallback', fieldType: 'char', presentationMode: 'task', renderProfile: 'edit', capabilities: ['relation.read'],
}).fallback, 'ReadableFieldValue');
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

assert.equal(professionalComponentRegistrations.length, 16);
console.log('[professional_component_registry_test] PASS cases=10');
