import type {
  ContractV2CanonicalFormSemanticRole,
  ContractV2FormStructureRoleName,
} from './types';

export const CONTRACT_V2_FORM_STRUCTURE_ROLE_TO_CANONICAL = Object.freeze({
  summary: 'summary',
  task: 'task',
  context: 'context',
  risk: 'risk',
  relation: 'relation',
  activity: 'activity',
  audit: 'audit',
} satisfies Record<ContractV2FormStructureRoleName, ContractV2CanonicalFormSemanticRole>);

export const CONTRACT_V2_FORM_STRUCTURE_ROLES = Object.freeze(
  Object.keys(CONTRACT_V2_FORM_STRUCTURE_ROLE_TO_CANONICAL) as ContractV2FormStructureRoleName[],
);

export function canonicalRoleForFormStructureRole(
  role: ContractV2FormStructureRoleName,
): ContractV2CanonicalFormSemanticRole {
  return CONTRACT_V2_FORM_STRUCTURE_ROLE_TO_CANONICAL[role];
}
