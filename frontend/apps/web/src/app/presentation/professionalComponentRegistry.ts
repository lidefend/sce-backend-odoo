import type { CanonicalFormPresentationMode, CanonicalFormRenderMode } from './canonicalFormRenderModel';
import { PROFESSIONAL_BASE_FIELD_TYPES } from '../../components/professional-fields/professionalBaseFieldModel';
import { SEMANTIC_REGISTRY_ROWS } from './semantic_registry.generated';
import type { SemanticRegistryReadiness } from './semantic_registry.generated';

/**
 * The readiness vocabulary is projected from the contract declaration; this
 * alias keeps the name the rest of the codebase already imports while leaving
 * exactly one definition.
 */
export type ProfessionalComponentReadiness = SemanticRegistryReadiness;

/**
 * Every renderer name a registration may hand to the field renderer.
 *
 * ``FormSectionField`` is the deliberate sentinel for "no professional control
 * owns this field; the section's own type-directed control renders it". Naming
 * it in the union is what keeps a drifted renderer from compiling: once an
 * arbitrary string reaches the template it is indistinguishable from the
 * sentinel, which is exactly the silent fallback phase 6 forbids. A renderer
 * that is added here without a branch in ``FormSection.vue`` fails the
 * registry guard.
 */
export const PROFESSIONAL_COMPONENT_RENDERERS = Object.freeze([
  'FormSectionField',
  'ProfessionalBaseFieldControl',
  'ProfessionalBusinessValueControl',
  'ProfessionalRelationFieldControl',
  'ProfessionalDetailCollectionControl',
  'PaymentSettlementDetailCollectionControl',
] as const);

export type ProfessionalComponentRenderer = typeof PROFESSIONAL_COMPONENT_RENDERERS[number];

/** The sentinel that routes a field to the section's own type-directed control. */
export const FORM_SECTION_TYPE_DIRECTED_RENDERER: ProfessionalComponentRenderer = 'FormSectionField';

export type ProfessionalComponentRegistration = {
  componentKey: string;
  semanticType: string;
  supportedFieldTypes: readonly string[];
  supportedPresentationModes: readonly CanonicalFormPresentationMode[];
  supportedRenderProfiles: readonly CanonicalFormRenderMode[];
  requiredCapabilities: readonly string[];
  renderer: ProfessionalComponentRenderer;
  rendererByFieldType: Readonly<Record<string, ProfessionalComponentRenderer>>;
  fallback: string | null;
  readiness: ProfessionalComponentReadiness;
};

export type ProfessionalComponentResolution = ProfessionalComponentRegistration & {
  fieldType: string;
  contractVersion: string;
};

const FORM_MODES = ['task', 'workspace'] as const;
const FORM_PROFILES = ['create', 'edit', 'readonly'] as const;

function registration(
  componentKey: string,
  semanticType: string,
  supportedFieldTypes: readonly string[],
  readiness: ProfessionalComponentReadiness = 'ready',
  renderer: ProfessionalComponentRenderer = FORM_SECTION_TYPE_DIRECTED_RENDERER,
): ProfessionalComponentRegistration {
  const rendererByFieldType: Readonly<Record<string, ProfessionalComponentRenderer>> = Object.freeze(Object.fromEntries(
    (renderer === FORM_SECTION_TYPE_DIRECTED_RENDERER ? supportedFieldTypes : [])
      .filter((fieldType) => (PROFESSIONAL_BASE_FIELD_TYPES as readonly string[]).includes(fieldType))
      .map((fieldType) => [fieldType, 'ProfessionalBaseFieldControl'] as [string, ProfessionalComponentRenderer]),
  ));
  return Object.freeze({
    componentKey, semanticType, supportedFieldTypes,
    supportedPresentationModes: FORM_MODES,
    supportedRenderProfiles: FORM_PROFILES,
    requiredCapabilities: Object.freeze([]),
    renderer,
    rendererByFieldType,
    fallback: readiness === 'readable_fallback' ? 'ReadableFieldValue' : null,
    readiness,
  });
}

/**
 * The component vocabulary lives in the contract declaration and is projected
 * into ``semantic_registry.generated.ts``.  This module owns the *behaviour*
 * around those rows -- presentation-mode profiles, the type-directed renderer
 * derivation, the readiness fallback -- and must not carry a second
 * hand-written list of component keys.
 */
const RENDERER_NAMES: ReadonlySet<string> = new Set(PROFESSIONAL_COMPONENT_RENDERERS);

function declaredRenderer(value: string): ProfessionalComponentRenderer {
  if (!RENDERER_NAMES.has(value)) {
    throw new Error(`SEMANTIC_REGISTRY_UNKNOWN_RENDERER:${value}`);
  }
  return value as ProfessionalComponentRenderer;
}

const REGISTRATIONS: readonly ProfessionalComponentRegistration[] = SEMANTIC_REGISTRY_ROWS.map((row) => registration(
  row.componentKey,
  row.semanticType,
  row.supportedFieldTypes,
  row.readiness,
  declaredRenderer(row.renderer),
));

export const professionalComponentRegistrations: readonly ProfessionalComponentRegistration[] = Object.freeze([...REGISTRATIONS]);
const professionalComponentRegistry: ReadonlyMap<string, ProfessionalComponentRegistration> = new Map(
  professionalComponentRegistrations.map((entry) => [entry.componentKey, entry]),
);

/**
 * The runtime semantic index: what a field *means* -> the registration that
 * renders it.  Derived from the generated rows, so it is the same single
 * vocabulary as the component map above and never a second table.
 *
 * A duplicate semantic would silently shadow a registration, so the index
 * refuses to build rather than drop a row: the declaration lint already
 * rejects duplicates, and this keeps a hand-edited carrier from degrading into
 * a silent last-one-wins lookup.
 */
const professionalSemanticIndex: ReadonlyMap<string, ProfessionalComponentRegistration> = (() => {
  const index = new Map<string, ProfessionalComponentRegistration>();
  for (const entry of professionalComponentRegistrations) {
    if (index.has(entry.semanticType)) {
      throw new Error(`SEMANTIC_REGISTRY_DUPLICATE_SEMANTIC:${entry.semanticType}`);
    }
    index.set(entry.semanticType, entry);
  }
  return index;
})();

/**
 * Resolve a declared field semantic to its registration.
 *
 * Returns ``null`` for an undeclared semantic instead of silently falling back
 * to a default control: an unknown meaning is a contract defect, and the caller
 * (not this lookup) decides how the fail-closed surface is presented.
 */
export function resolveSemanticRegistration(
  semantic: string,
): ProfessionalComponentRegistration | null {
  const key = String(semantic || '').trim().toLowerCase();
  return key ? professionalSemanticIndex.get(key) || null : null;
}

/** The component key a declared semantic renders through (``null`` when undeclared). */
export function componentKeyForSemantic(semantic: string): string | null {
  return resolveSemanticRegistration(semantic)?.componentKey ?? null;
}

export type ProfessionalComponentResolutionInput = {
  componentKey: string;
  fieldType: string;
  presentationMode: CanonicalFormPresentationMode;
  renderProfile: CanonicalFormRenderMode;
  capabilities?: readonly string[];
};

export type ContractProfessionalComponentResolutionInput = ProfessionalComponentResolutionInput & {
  clientType: string;
  contractRegistryEntry: unknown;
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

// How a component renders is a frontend decision.  The contract declares the
// component identity and its version; it must never name a framework component,
// pre-select a per-client adapter or offer a rendering fallback, because that
// would give the product a second, driftable component vocabulary.
const CONTRACT_FORBIDDEN_RENDER_KEYS = ['adapter', 'selectedAdapter', 'selected_adapter', 'fallback'] as const;

function contractComponentBinding(input: ContractProfessionalComponentResolutionInput) {
  const entry = asRecord(input.contractRegistryEntry);
  if (!Object.keys(entry).length) throw new Error(`PROFESSIONAL_COMPONENT_CONTRACT_REGISTRY_MISSING:${input.componentKey}`);
  const version = String(entry.version || '').trim();
  if (!version) throw new Error(`PROFESSIONAL_COMPONENT_CONTRACT_VERSION_MISSING:${input.componentKey}`);
  CONTRACT_FORBIDDEN_RENDER_KEYS.forEach((key) => {
    if (Object.prototype.hasOwnProperty.call(entry, key)) {
      throw new Error(`PROFESSIONAL_COMPONENT_CONTRACT_RENDER_TRAIT_FORBIDDEN:${input.componentKey}:${key}`);
    }
  });
  return Object.freeze({ contractVersion: version });
}

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
  return Object.freeze({
    ...entry,
    renderer: entry.rendererByFieldType[fieldType] || entry.renderer,
    fieldType,
    contractVersion: '',
  });
}

export function resolveProfessionalComponent(
  input: ProfessionalComponentResolutionInput,
): ProfessionalComponentResolution {
  return resolveProfessionalComponentRegistration(professionalComponentRegistry, input);
}

export function resolveContractProfessionalComponent(
  input: ContractProfessionalComponentResolutionInput,
): ProfessionalComponentResolution {
  const local = resolveProfessionalComponentRegistration(professionalComponentRegistry, input);
  return Object.freeze({ ...local, ...contractComponentBinding(input) });
}
