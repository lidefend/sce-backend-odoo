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
  rendererByFieldType: Readonly<Record<string, string>>;
  fallback: string | null;
  readiness: ProfessionalComponentReadiness;
};

export type ProfessionalComponentResolution = ProfessionalComponentRegistration & {
  fieldType: string;
  contractAdapter: string;
  contractVersion: string;
  contractFallback: string | null;
};

const FORM_MODES = ['task', 'workspace'] as const;
const FORM_PROFILES = ['create', 'edit', 'readonly'] as const;

function registration(
  componentKey: string,
  semanticType: string,
  supportedFieldTypes: readonly string[],
  readiness: ProfessionalComponentReadiness = 'ready',
  renderer = 'FormSectionField',
): ProfessionalComponentRegistration {
  const rendererByFieldType = Object.freeze(Object.fromEntries(
    (renderer === 'FormSectionField' ? supportedFieldTypes : [])
      .filter((fieldType) => ['char', 'text', 'html', 'integer', 'float', 'date', 'datetime', 'boolean', 'selection'].includes(fieldType))
      .map((fieldType) => [fieldType, 'ProfessionalBaseFieldControl']),
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

const REGISTRATIONS = [
  registration('sc.input.text', 'text', ['char']),
  registration('sc.input.binary', 'binary', ['binary']),
  registration('sc.input.textarea', 'long_text', ['text', 'html']),
  registration('sc.input.number', 'number', ['integer', 'float', 'monetary']),
  registration('sc.select.remote', 'choice', ['selection']),
  registration('sc.input.boolean', 'boolean', ['boolean']),
  registration('sc.input.date', 'date', ['date']),
  registration('sc.input.datetime', 'datetime', ['datetime']),
  registration('sc.table.data', 'detail_collection', ['one2many', 'many2many']),
  registration('sc.tree.data', 'hierarchical_collection', ['one2many', 'many2many']),
  registration('sc.relation.many2one', 'relation', ['many2one'], 'ready', 'ProfessionalRelationFieldControl'),
  registration('sc.relation.many2many', 'relation_collection', ['many2many'], 'ready', 'ProfessionalRelationFieldControl'),
  registration('sc.relation.table', 'detail_collection', ['one2many'], 'ready', 'ProfessionalDetailCollectionControl'),
  registration('sc.payment.settlement_detail_collection', 'payment_settlement_detail_collection', ['one2many'], 'ready', 'PaymentSettlementDetailCollectionControl'),
  registration('sc.select.tags', 'tag_collection', ['many2many'], 'ready', 'ProfessionalRelationFieldControl'),
  registration('sc.button.action', 'action', ['action']),
  registration('sc.auth.credential_entry', 'credential_entry', ['char']),
  registration('sc.auth.secret_confirmation', 'secret_confirmation', ['char']),
  registration('sc.auth.challenge_status', 'challenge_status', ['char', 'selection', 'text']),
  registration('sc.auth.one_time_secret', 'one_time_secret', ['char', 'text'], 'fail_closed'),
  registration('sc.auth.support_action', 'support_action', ['action']),
  registration('sc.value.money', 'money', ['monetary'], 'ready', 'ProfessionalBusinessValueControl'),
  registration('sc.value.currency', 'currency', ['many2one'], 'ready', 'ProfessionalBusinessValueControl'),
  registration('sc.value.percentage', 'percentage', ['float', 'integer'], 'ready', 'ProfessionalBusinessValueControl'),
  registration('sc.display.status', 'status', ['selection', 'char'], 'ready', 'ProfessionalBusinessValueControl'),
  registration('sc.value.duration', 'duration', ['float', 'integer'], 'ready', 'ProfessionalBusinessValueControl'),
  registration('sc.value.user', 'user', ['many2one'], 'ready', 'ProfessionalBusinessValueControl'),
  registration('sc.value.company', 'company', ['many2one'], 'ready', 'ProfessionalBusinessValueControl'),
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

export type ContractProfessionalComponentResolutionInput = ProfessionalComponentResolutionInput & {
  clientType: string;
  contractRegistryEntry: unknown;
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function contractComponentBinding(input: ContractProfessionalComponentResolutionInput) {
  const entry = asRecord(input.contractRegistryEntry);
  if (!Object.keys(entry).length) throw new Error(`PROFESSIONAL_COMPONENT_CONTRACT_REGISTRY_MISSING:${input.componentKey}`);
  const version = String(entry.version || '').trim();
  if (!version) throw new Error(`PROFESSIONAL_COMPONENT_CONTRACT_VERSION_MISSING:${input.componentKey}`);
  const adapters = asRecord(entry.adapter);
  const fallback = String(entry.fallback || '').trim();
  const selected = String(
    entry.selectedAdapter || entry.selected_adapter || adapters[input.clientType] || fallback || adapters.web_pc || '',
  ).trim();
  if (!selected) throw new Error(`PROFESSIONAL_COMPONENT_CONTRACT_ADAPTER_MISSING:${input.componentKey}:${input.clientType}`);
  return Object.freeze({ contractAdapter: selected, contractVersion: version, contractFallback: fallback || null });
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
    contractAdapter: '',
    contractVersion: '',
    contractFallback: null,
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
