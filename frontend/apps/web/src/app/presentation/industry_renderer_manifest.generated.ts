// GENERATED INDUSTRY RENDERER MANIFEST - do not edit by hand.
//
// Declaration authority: contracts/registry/semantic.yaml -> contracts/registry/component.yaml
// Regenerate with: python3 scripts/contract/generate_semantic_registry.py
//
// Drift between this manifest and the declaration is a lint failure
// (`make verify.semantic.registry.lint`). This carrier contains only
// industry-category component identities. The platform carrier and FormSection
// never import an industry component; the extension registration entry consumes
// these rows and registers their components before the application mounts.

import type { SemanticRegistryRow } from './semantic_registry.generated';

export const INDUSTRY_RENDERER_MANIFEST_VERSION = 1;

export const INDUSTRY_RENDERER_ROWS: readonly SemanticRegistryRow[] = [
  {componentKey: 'sc.payment.settlement_detail_collection', semanticType: 'payment_settlement_detail_collection', supportedFieldTypes: ['one2many'], readiness: 'ready', renderer: 'PaymentSettlementDetailCollectionControl'},
];
