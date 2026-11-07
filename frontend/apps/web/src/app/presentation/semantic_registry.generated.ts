// GENERATED CONTRACT-RUNTIME CARRIER - do not edit by hand.
//
// Declaration authority: contracts/registry/semantic.yaml -> contracts/registry/component.yaml
// Regenerate with: python3 scripts/contract/generate_semantic_registry.py
//
// Drift between this carrier and the declaration is a lint failure
// (`make verify.semantic.registry.lint`).  This is the *only* frontend
// component vocabulary: `professionalComponentRegistry.ts` builds its
// registrations from these rows and must not carry a second hand-written list.

export type SemanticRegistryReadiness = 'ready' | 'readable_fallback' | 'fail_closed';

export type SemanticRegistryRow = {
  readonly componentKey: string;
  readonly semanticType: string;
  readonly supportedFieldTypes: readonly string[];
  readonly readiness: SemanticRegistryReadiness;
  readonly renderer: string;
  readonly rendererVersion: string;
  readonly supportedContractVersion: string;
  readonly requiredCapabilities: readonly string[];
};

export const SEMANTIC_REGISTRY_VERSION = 1;

export const RENDERER_CAPABILITY_PROVIDERS: Readonly<Record<string, string>> = Object.freeze({
  'form.relation.one2many': 'FormSection.relationAdapter',
});

export const SEMANTIC_REGISTRY_ROWS: readonly SemanticRegistryRow[] = [
  {componentKey: 'sc.input.text', semanticType: 'text', supportedFieldTypes: ['char'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.input.binary', semanticType: 'binary', supportedFieldTypes: ['binary'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.input.textarea', semanticType: 'long_text', supportedFieldTypes: ['text', 'html'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.input.number', semanticType: 'number', supportedFieldTypes: ['integer', 'float', 'monetary'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.select.remote', semanticType: 'choice', supportedFieldTypes: ['selection'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.input.boolean', semanticType: 'boolean', supportedFieldTypes: ['boolean'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.input.date', semanticType: 'date', supportedFieldTypes: ['date'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.input.datetime', semanticType: 'datetime', supportedFieldTypes: ['datetime'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.table.data', semanticType: 'detail_table', supportedFieldTypes: ['one2many', 'many2many'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.tree.data', semanticType: 'hierarchical_collection', supportedFieldTypes: ['one2many', 'many2many'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.relation.many2one', semanticType: 'relation', supportedFieldTypes: ['many2one'], readiness: 'ready', renderer: 'ProfessionalRelationFieldControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.relation.many2many', semanticType: 'relation_collection', supportedFieldTypes: ['many2many'], readiness: 'ready', renderer: 'ProfessionalRelationFieldControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.relation.table', semanticType: 'detail_collection', supportedFieldTypes: ['one2many'], readiness: 'ready', renderer: 'ProfessionalDetailCollectionControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.select.tags', semanticType: 'tag_collection', supportedFieldTypes: ['many2many'], readiness: 'ready', renderer: 'ProfessionalRelationFieldControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.button.action', semanticType: 'action', supportedFieldTypes: ['action'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.auth.credential_entry', semanticType: 'credential_entry', supportedFieldTypes: ['char'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.auth.secret_confirmation', semanticType: 'secret_confirmation', supportedFieldTypes: ['char'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.auth.challenge_status', semanticType: 'challenge_status', supportedFieldTypes: ['char', 'selection', 'text'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.auth.one_time_secret', semanticType: 'one_time_secret', supportedFieldTypes: ['char', 'text'], readiness: 'fail_closed', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.auth.support_action', semanticType: 'support_action', supportedFieldTypes: ['action'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.value.money', semanticType: 'money', supportedFieldTypes: ['monetary'], readiness: 'ready', renderer: 'ProfessionalBusinessValueControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.value.percentage', semanticType: 'percentage', supportedFieldTypes: ['float', 'integer'], readiness: 'ready', renderer: 'ProfessionalBusinessValueControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.display.status', semanticType: 'status', supportedFieldTypes: ['selection', 'char'], readiness: 'ready', renderer: 'ProfessionalBusinessValueControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.value.duration', semanticType: 'duration', supportedFieldTypes: ['float', 'integer'], readiness: 'ready', renderer: 'ProfessionalBusinessValueControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
  {componentKey: 'sc.display.text', semanticType: 'readable_value', supportedFieldTypes: ['*'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.3.0', requiredCapabilities: []},
];

export const NODE_COMPONENT_REGISTRATIONS: Readonly<Record<string, {kind: 'node'; version: string}>> = Object.freeze({
  'sc.feedback.message': {kind: 'node', version: '1.0.0'},
  'sc.navigation.anchor': {kind: 'node', version: '1.0.0'},
});
