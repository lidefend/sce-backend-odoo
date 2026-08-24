import type { CanonicalFormPresentationMode, CanonicalFormRenderMode } from './canonicalFormRenderModel';

export type ProfessionalComponentReadiness = 'ready' | 'readable_fallback' | 'fail_closed';

export type ProfessionalComponentRegistration = {
  componentKey: string;
  semanticType: string;
  supportedFieldTypes: readonly string[];
  supportedPresentationModes: readonly CanonicalFormPresentationMode[];
  supportedRenderProfiles: readonly CanonicalFormRenderMode[];
  requiredCapabilities: readonly string[];
  renderer: string;
  fallback: string | null;
  readiness: ProfessionalComponentReadiness;
};

export type ProfessionalComponentResolution = ProfessionalComponentRegistration & {
  fieldType: string;
};

const FORM_MODES = ['task', 'workspace'] as const;
const FORM_PROFILES = ['create', 'edit', 'readonly'] as const;

function registration(
  componentKey: string,
  semanticType: string,
  supportedFieldTypes: readonly string[],
  readiness: ProfessionalComponentReadiness = 'ready',
): ProfessionalComponentRegistration {
  return Object.freeze({
    componentKey, semanticType, supportedFieldTypes,
    supportedPresentationModes: FORM_MODES,
    supportedRenderProfiles: FORM_PROFILES,
    requiredCapabilities: Object.freeze([]),
    renderer: 'FormSectionField',
    fallback: readiness === 'readable_fallback' ? 'ReadableFieldValue' : null,
    readiness,
  });
}

const REGISTRATIONS = [
  registration('sc.input.text', 'text', ['char']),
  registration('sc.input.binary', 'binary', ['binary']),
  registration('sc.input.textarea', 'long_text', ['text', 'html']),
  registration('sc.input.number', 'number', ['integer', 'float', 'monetary']),
  registration('sc.select.remote', 'choice_or_relation', ['selection', 'many2one']),
  registration('sc.input.boolean', 'boolean', ['boolean']),
  registration('sc.input.date', 'date', ['date']),
  registration('sc.input.datetime', 'datetime', ['datetime']),
  registration('sc.table.data', 'detail_collection', ['one2many', 'many2many']),
  registration('sc.tree.data', 'hierarchical_collection', ['one2many', 'many2many']),
  registration('sc.relation.many2one', 'relation', ['many2one']),
  registration('sc.relation.table', 'detail_collection', ['one2many', 'many2many']),
  registration('sc.select.tags', 'tag_collection', ['many2many']),
  registration('sc.button.action', 'action', ['action']),
  registration('sc.display.status', 'status', ['selection', 'char']),
  registration('sc.display.text', 'readable_value', ['*']),
] as const;

export const professionalComponentRegistrations: readonly ProfessionalComponentRegistration[] = Object.freeze([...REGISTRATIONS]);
const professionalComponentRegistry: ReadonlyMap<string, ProfessionalComponentRegistration> = new Map(
  professionalComponentRegistrations.map((entry) => [entry.componentKey, entry]),
);

export type ProfessionalComponentResolutionInput = {
  componentKey: string;
  fieldType: string;
  presentationMode: CanonicalFormPresentationMode;
  renderProfile: CanonicalFormRenderMode;
  capabilities?: readonly string[];
};

export function resolveProfessionalComponentRegistration(
  registry: ReadonlyMap<string, ProfessionalComponentRegistration>,
  input: ProfessionalComponentResolutionInput,
): ProfessionalComponentResolution {
  const entry = registry.get(input.componentKey);
  if (!entry || entry.readiness === 'fail_closed') throw new Error(`PROFESSIONAL_COMPONENT_UNREGISTERED:${input.componentKey}`);
  const fieldType = input.fieldType.trim().toLowerCase();
  if (!fieldType) throw new Error(`PROFESSIONAL_COMPONENT_FIELD_TYPE_MISSING:${input.componentKey}`);
  if (!entry.supportedFieldTypes.includes('*') && !entry.supportedFieldTypes.includes(fieldType)) {
    throw new Error(`PROFESSIONAL_COMPONENT_FIELD_TYPE_MISMATCH:${input.componentKey}:${fieldType}`);
  }
  if (!entry.supportedPresentationModes.includes(input.presentationMode)) {
    throw new Error(`PROFESSIONAL_COMPONENT_PRESENTATION_MODE_MISMATCH:${input.componentKey}:${input.presentationMode}`);
  }
  if (!entry.supportedRenderProfiles.includes(input.renderProfile)) {
    throw new Error(`PROFESSIONAL_COMPONENT_RENDER_PROFILE_MISMATCH:${input.componentKey}:${input.renderProfile}`);
  }
  const capabilities = new Set(input.capabilities || []);
  const missing = entry.requiredCapabilities.filter((capability) => !capabilities.has(capability));
  if (missing.length) throw new Error(`PROFESSIONAL_COMPONENT_CAPABILITY_MISSING:${input.componentKey}:${missing.join(',')}`);
  return Object.freeze({ ...entry, fieldType });
}

export function resolveProfessionalComponent(
  input: ProfessionalComponentResolutionInput,
): ProfessionalComponentResolution {
  return resolveProfessionalComponentRegistration(professionalComponentRegistry, input);
}
