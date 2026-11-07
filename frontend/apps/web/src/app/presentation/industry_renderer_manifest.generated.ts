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
};

export const SEMANTIC_REGISTRY_VERSION = 1;

export const INDUSTRY_RENDERER_ROWS: readonly SemanticRegistryRow[] = [
  {componentKey: 'sc.payment.settlement_detail_collection', semanticType: 'payment_settlement_detail_collection', supportedFieldTypes: ['one2many'], readiness: 'ready', renderer: 'PaymentSettlementDetailCollectionControl'},
];
