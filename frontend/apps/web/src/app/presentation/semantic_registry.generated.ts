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

export const SEMANTIC_REGISTRY_VERSION = 2;

export const RENDERER_CAPABILITY_PROVIDERS: Readonly<Record<string, string>> = Object.freeze({
  'form.relation.one2many': 'FormSection.relationAdapter',
});

export const SEMANTIC_REGISTRY_ROWS: readonly SemanticRegistryRow[] = [
  {componentKey: 'sc.input.text', semanticType: 'text', supportedFieldTypes: ['char'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.input.binary', semanticType: 'binary', supportedFieldTypes: ['binary'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.input.textarea', semanticType: 'long_text', supportedFieldTypes: ['text', 'html'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.input.number', semanticType: 'number', supportedFieldTypes: ['integer', 'float', 'monetary'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.select.remote', semanticType: 'choice', supportedFieldTypes: ['selection'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.input.boolean', semanticType: 'boolean', supportedFieldTypes: ['boolean'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.input.date', semanticType: 'date', supportedFieldTypes: ['date'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.input.datetime', semanticType: 'datetime', supportedFieldTypes: ['datetime'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.table.data', semanticType: 'detail_table', supportedFieldTypes: ['one2many', 'many2many'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.tree.data', semanticType: 'hierarchical_collection', supportedFieldTypes: ['one2many', 'many2many'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.relation.many2one', semanticType: 'relation', supportedFieldTypes: ['many2one'], readiness: 'ready', renderer: 'ProfessionalRelationFieldControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.relation.many2many', semanticType: 'relation_collection', supportedFieldTypes: ['many2many'], readiness: 'ready', renderer: 'ProfessionalRelationFieldControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.relation.table', semanticType: 'detail_collection', supportedFieldTypes: ['one2many'], readiness: 'ready', renderer: 'ProfessionalDetailCollectionControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.relation.activity', semanticType: 'activity_collection', supportedFieldTypes: ['one2many'], readiness: 'ready', renderer: 'ProfessionalDetailCollectionControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.select.tags', semanticType: 'tag_collection', supportedFieldTypes: ['many2many'], readiness: 'ready', renderer: 'ProfessionalRelationFieldControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.button.action', semanticType: 'action', supportedFieldTypes: ['action'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.auth.credential_entry', semanticType: 'credential_entry', supportedFieldTypes: ['char'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.auth.secret_confirmation', semanticType: 'secret_confirmation', supportedFieldTypes: ['char'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.auth.challenge_status', semanticType: 'challenge_status', supportedFieldTypes: ['char', 'selection', 'text'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.auth.one_time_secret', semanticType: 'one_time_secret', supportedFieldTypes: ['char', 'text'], readiness: 'fail_closed', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.auth.support_action', semanticType: 'support_action', supportedFieldTypes: ['action'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.value.money', semanticType: 'money', supportedFieldTypes: ['monetary'], readiness: 'ready', renderer: 'ProfessionalBusinessValueControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.value.percentage', semanticType: 'percentage', supportedFieldTypes: ['float', 'integer'], readiness: 'ready', renderer: 'ProfessionalBusinessValueControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.display.status', semanticType: 'status', supportedFieldTypes: ['selection', 'char'], readiness: 'ready', renderer: 'ProfessionalBusinessValueControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.value.duration', semanticType: 'duration', supportedFieldTypes: ['float', 'integer'], readiness: 'ready', renderer: 'ProfessionalBusinessValueControl', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.display.text', semanticType: 'readable_value', supportedFieldTypes: ['*'], readiness: 'ready', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
  {componentKey: 'sc.unsupported.native_widget', semanticType: 'unsupported_native_widget', supportedFieldTypes: ['*'], readiness: 'fail_closed', renderer: 'FormSectionField', rendererVersion: '1.0.0', supportedContractVersion: '>=2.0.0 <2.7.0', requiredCapabilities: []},
];

export const SEMANTIC_COMPONENT_REGISTRY: Readonly<Record<string, string>> = Object.freeze({
  'action': 'sc.button.action',
  'activity_collection': 'sc.relation.activity',
  'binary': 'sc.input.binary',
  'boolean': 'sc.input.boolean',
  'challenge_status': 'sc.auth.challenge_status',
  'choice': 'sc.select.remote',
  'credential_entry': 'sc.auth.credential_entry',
  'date': 'sc.input.date',
  'datetime': 'sc.input.datetime',
  'detail_collection': 'sc.relation.table',
  'detail_table': 'sc.table.data',
  'duration': 'sc.value.duration',
  'hierarchical_collection': 'sc.tree.data',
  'long_text': 'sc.input.textarea',
  'money': 'sc.value.money',
  'number': 'sc.input.number',
  'one_time_secret': 'sc.auth.one_time_secret',
  'payment_settlement_detail_collection': 'sc.payment.settlement_detail_collection',
  'percentage': 'sc.value.percentage',
  'readable_value': 'sc.display.text',
  'reference': 'sc.display.text',
  'relation': 'sc.relation.many2one',
  'relation_collection': 'sc.relation.many2many',
  'secret_confirmation': 'sc.auth.secret_confirmation',
  'status': 'sc.display.status',
  'support_action': 'sc.auth.support_action',
  'tag_collection': 'sc.select.tags',
  'text': 'sc.input.text',
  'unsupported_native_widget': 'sc.unsupported.native_widget',
});

export const SEMANTIC_FIELD_TYPES: Readonly<Record<string, readonly string[]>> = Object.freeze({
  'action': Object.freeze(['action']),
  'activity_collection': Object.freeze(['one2many']),
  'binary': Object.freeze(['binary']),
  'boolean': Object.freeze(['boolean']),
  'challenge_status': Object.freeze(['char', 'selection', 'text']),
  'choice': Object.freeze(['selection']),
  'credential_entry': Object.freeze(['char']),
  'date': Object.freeze(['date']),
  'datetime': Object.freeze(['datetime']),
  'detail_collection': Object.freeze(['one2many']),
  'detail_table': Object.freeze(['one2many', 'many2many']),
  'duration': Object.freeze(['float', 'integer']),
  'hierarchical_collection': Object.freeze(['one2many', 'many2many']),
  'long_text': Object.freeze(['text', 'html']),
  'money': Object.freeze(['monetary']),
  'number': Object.freeze(['integer', 'float', 'monetary']),
  'one_time_secret': Object.freeze(['char', 'text']),
  'payment_settlement_detail_collection': Object.freeze(['one2many']),
  'percentage': Object.freeze(['float', 'integer']),
  'readable_value': Object.freeze(['*']),
  'relation': Object.freeze(['many2one']),
  'relation_collection': Object.freeze(['many2many']),
  'secret_confirmation': Object.freeze(['char']),
  'status': Object.freeze(['selection', 'char']),
  'support_action': Object.freeze(['action']),
  'tag_collection': Object.freeze(['many2many']),
  'text': Object.freeze(['char']),
  'unsupported_native_widget': Object.freeze(['*']),
});

export type NativeWidgetStatus = 'ready' | 'fallback' | 'unsupported';

export const NATIVE_WIDGET_REGISTRY: Readonly<Record<string, {status: NativeWidgetStatus; reasonCode: string}>> = Object.freeze({
  'account-tax-totals-field': {status: 'ready', reasonCode: ''},
  'account_type_selection': {status: 'fallback', reasonCode: 'NATIVE_WIDGET_PLATFORM_COMPONENT_SUBSTITUTION'},
  'analytic_distribution': {status: 'ready', reasonCode: ''},
  'badge': {status: 'ready', reasonCode: ''},
  'binary': {status: 'ready', reasonCode: ''},
  'boolean': {status: 'ready', reasonCode: ''},
  'boolean_favorite': {status: 'ready', reasonCode: ''},
  'boolean_toggle': {status: 'fallback', reasonCode: 'NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK'},
  'button': {status: 'ready', reasonCode: ''},
  'checkbox': {status: 'ready', reasonCode: ''},
  'date': {status: 'ready', reasonCode: ''},
  'daterange': {status: 'ready', reasonCode: ''},
  'datetime': {status: 'ready', reasonCode: ''},
  'display': {status: 'ready', reasonCode: ''},
  'domain': {status: 'unsupported', reasonCode: 'NATIVE_WIDGET_DOMAIN_EDITOR_UNSUPPORTED'},
  'email': {status: 'ready', reasonCode: ''},
  'field_partner_autocomplete': {status: 'fallback', reasonCode: 'NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK'},
  'float_time': {status: 'ready', reasonCode: ''},
  'handle': {status: 'fallback', reasonCode: 'NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK'},
  'html': {status: 'ready', reasonCode: ''},
  'image': {status: 'fallback', reasonCode: 'NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK'},
  'input': {status: 'ready', reasonCode: ''},
  'json': {status: 'ready', reasonCode: ''},
  'list_activity': {status: 'fallback', reasonCode: 'NATIVE_WIDGET_PLATFORM_COMPONENT_SUBSTITUTION'},
  'many2many': {status: 'ready', reasonCode: ''},
  'many2many_binary': {status: 'ready', reasonCode: ''},
  'many2many_tags': {status: 'ready', reasonCode: ''},
  'many2one': {status: 'ready', reasonCode: ''},
  'many2one_avatar_user': {status: 'ready', reasonCode: ''},
  'monetary': {status: 'ready', reasonCode: ''},
  'number': {status: 'ready', reasonCode: ''},
  'one2many': {status: 'ready', reasonCode: ''},
  'one2many_list': {status: 'ready', reasonCode: ''},
  'payment': {status: 'ready', reasonCode: ''},
  'percentage': {status: 'ready', reasonCode: ''},
  'percentpie': {status: 'ready', reasonCode: ''},
  'phone': {status: 'ready', reasonCode: ''},
  'radio': {status: 'ready', reasonCode: ''},
  'relation': {status: 'ready', reasonCode: ''},
  'res_partner_many2one': {status: 'fallback', reasonCode: 'NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK'},
  'select': {status: 'ready', reasonCode: ''},
  'selection': {status: 'ready', reasonCode: ''},
  'statinfo': {status: 'ready', reasonCode: ''},
  'statusbar': {status: 'ready', reasonCode: ''},
  'table': {status: 'ready', reasonCode: ''},
  'text': {status: 'ready', reasonCode: ''},
  'textarea': {status: 'ready', reasonCode: ''},
  'tier_validation': {status: 'unsupported', reasonCode: 'NATIVE_WIDGET_QWEB_RENDERER_UNSUPPORTED'},
  'tree': {status: 'ready', reasonCode: ''},
  'upload': {status: 'ready', reasonCode: ''},
  'url': {status: 'ready', reasonCode: ''},
});

export const NODE_COMPONENT_REGISTRATIONS: Readonly<Record<string, {kind: 'node'; version: string}>> = Object.freeze({
  'sc.feedback.message': {kind: 'node', version: '1.0.0'},
  'sc.navigation.anchor': {kind: 'node', version: '1.0.0'},
  'sc.display.ribbon': {kind: 'node', version: '1.0.0'},
  'sc.insight.summary': {kind: 'node', version: '1.0.0'},
  'sc.action.list': {kind: 'node', version: '1.0.0'},
  'sc.unsupported.native_node': {kind: 'node', version: '1.0.0'},
});

export const NATIVE_VIEW_WIDGET_COMPONENTS: Readonly<Record<string, {component: string; status: 'ready' | 'fallback' | 'unsupported'; reasonCode: string; payloadRequired: boolean}>> = Object.freeze({
  'sc_insight_banner': {component: 'sc.insight.summary', status: 'ready', reasonCode: '', payloadRequired: true},
  'sc_next_actions': {component: 'sc.action.list', status: 'ready', reasonCode: '', payloadRequired: true},
  'sc_stage_requirements': {component: 'sc.action.list', status: 'ready', reasonCode: '', payloadRequired: true},
  'web_ribbon': {component: 'sc.display.ribbon', status: 'ready', reasonCode: '', payloadRequired: false},
});

export const NATIVE_VIEW_WIDGET_DEFAULT = Object.freeze({
  component: 'sc.unsupported.native_node',
  status: 'unsupported' as const,
  reasonCode: 'NATIVE_VIEW_WIDGET_UNSUPPORTED',
});
