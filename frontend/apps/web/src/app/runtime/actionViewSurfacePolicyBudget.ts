import { contractGapError, requireDeclaredNumber } from '../contract/contractGap';

export type ActionViewSurfaceBudgetKey = 'filters_max' | 'filters_primary_max' | 'actions_primary_max';

export function resolveDeclaredSurfaceBudget(
  surfacePolicies: Record<string, unknown>,
  key: ActionViewSurfaceBudgetKey,
): number {
  const missing = `surface_policies.${key}`;
  const value = requireDeclaredNumber(surfacePolicies[key], {
    missing,
    requiredDeclarationLayer: 'P0:smart_core:contract_governance_user_surface',
    min: 0,
  });
  if (!Number.isInteger(value) || value < 0) throw contractGapError({
    kind: 'contract_defect',
    missing,
    requiredDeclarationLayer: 'P0:smart_core:contract_governance_user_surface',
  }, `${key} must be a non-negative integer`);
  return value;
}
