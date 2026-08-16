import type { ContractV2ActionRule } from '../../app/contracts/v2/types';
import type { ContractAction } from './types';

export type CanonicalFormActionExecution =
  | { kind: 'save' }
  | { kind: 'contract-action'; action: ContractAction }
  | { kind: 'error'; reasonCode: 'CANONICAL_FORM_ACTION_REFERENCE_MISSING' | 'CANONICAL_FORM_ACTION_EXECUTION_ADAPTER_MISSING' | 'CANONICAL_FORM_ACTION_REFERENCE_AMBIGUOUS' };

/**
 * Resolves a normalized action reference to an existing ContractForm executor.
 * It never infers from labels, methods, models, roles, or workflow state.
 */
export function resolveCanonicalFormActionExecution(
  actionRef: ContractV2ActionRule,
  contractActions: ContractAction[],
): CanonicalFormActionExecution {
  const actionId = String(actionRef.actionId || '').trim();
  const backendIdentity = String(actionRef.backendIdentity || '').trim();
  if (!actionId || !backendIdentity) return { kind: 'error', reasonCode: 'CANONICAL_FORM_ACTION_REFERENCE_MISSING' };
  if (actionId === 'form.save') return { kind: 'save' };

  const candidates = contractActions.filter((candidate) => (
    String(candidate.backendIdentity || '').trim() === backendIdentity
  ));
  if (!candidates.length) return { kind: 'error', reasonCode: 'CANONICAL_FORM_ACTION_EXECUTION_ADAPTER_MISSING' };
  if (candidates.length > 1) return { kind: 'error', reasonCode: 'CANONICAL_FORM_ACTION_REFERENCE_AMBIGUOUS' };
  return { kind: 'contract-action', action: candidates[0] };
}

export function validateCanonicalFormActionExecutors(
  actionRefs: ContractV2ActionRule[],
  contractActions: ContractAction[],
): { reasonCode: Extract<CanonicalFormActionExecution, { kind: 'error' }>['reasonCode']; actionId: string; backendIdentity: string } | null {
  for (const actionRef of actionRefs) {
    if (actionRef.visible === false || actionRef.enabled === false || actionRef.disabled === true) continue;
    const resolution = resolveCanonicalFormActionExecution(actionRef, contractActions);
    if (resolution.kind === 'error') {
      return {
        reasonCode: resolution.reasonCode,
        actionId: String(actionRef.actionId || '').trim(),
        backendIdentity: String(actionRef.backendIdentity || '').trim(),
      };
    }
  }
  return null;
}
