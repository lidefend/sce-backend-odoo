import { contractGapError, requireDeclaredNumber, requireDeclaredText } from '../contract/contractGap';

export type DeclaredAssigneeOptionsQuery = {
  model: string;
  fields: string[];
  domain: unknown[];
  order: string;
  limit: number;
};

export function resolveDeclaredAssigneeQuery(contract: unknown): DeclaredAssigneeOptionsQuery {
  const source = contract && typeof contract === 'object' && !Array.isArray(contract)
    ? contract as Record<string, unknown>
    : {};
  const layer = 'P0:smart_core:list_surface.batch_policy.assignee_options';
  const fields = Array.isArray(source.fields)
    ? source.fields.map((item) => String(item || '').trim()).filter(Boolean)
    : [];
  if (!fields.length) throw contractGapError({
    kind: 'contract_defect',
    missing: 'list_profile.batch_policy.assignee_options.fields',
    requiredDeclarationLayer: layer,
  }, 'Assignee options require declared fields');
  if (!Array.isArray(source.domain)) throw contractGapError({
    kind: 'contract_defect',
    missing: 'list_profile.batch_policy.assignee_options.domain',
    requiredDeclarationLayer: layer,
  }, 'Assignee options require a declared domain');
  const limit = requireDeclaredNumber(source.limit, {
    missing: 'list_profile.batch_policy.assignee_options.limit',
    requiredDeclarationLayer: layer,
  });
  if (!Number.isInteger(limit) || limit <= 0) throw contractGapError({
    kind: 'contract_defect',
    missing: 'list_profile.batch_policy.assignee_options.limit',
    requiredDeclarationLayer: layer,
  }, 'Assignee options limit must be a positive integer');
  return {
    model: requireDeclaredText(source.model, {
      missing: 'list_profile.batch_policy.assignee_options.model',
      requiredDeclarationLayer: layer,
    }),
    fields,
    domain: source.domain,
    order: requireDeclaredText(source.order, {
      missing: 'list_profile.batch_policy.assignee_options.order',
      requiredDeclarationLayer: layer,
    }),
    limit,
  };
}
