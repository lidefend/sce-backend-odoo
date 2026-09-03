import type { ContractV2ActionRule } from '../../app/contracts/v2/types';
import type {
  CanonicalFormAction,
  CanonicalFormNode,
  CanonicalFormRenderModel,
} from '../../app/presentation/canonicalFormRenderModel';
import type { ContractAction } from './types';
import { nativeActionOccurrenceKey } from './nativeActionIdentity';

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

  const occurrenceKey = nativeActionOccurrenceKey(actionRef.nativeIdentity);

  const candidates = contractActions.filter((candidate) => (
    String(candidate.backendIdentity || '').trim() === backendIdentity
    && (!occurrenceKey || nativeActionOccurrenceKey(candidate.nativeIdentity) === occurrenceKey)
  ));
  if (!candidates.length) return { kind: 'error', reasonCode: 'CANONICAL_FORM_ACTION_EXECUTION_ADAPTER_MISSING' };
  if (candidates.length > 1) return { kind: 'error', reasonCode: 'CANONICAL_FORM_ACTION_REFERENCE_AMBIGUOUS' };
  return { kind: 'contract-action', action: candidates[0] };
}

export function validateCanonicalFormActionExecutors(
  actions: Array<{ visible: boolean; enabled: boolean; actionRef: ContractV2ActionRule }>,
  contractActions: ContractAction[],
): { reasonCode: Extract<CanonicalFormActionExecution, { kind: 'error' }>['reasonCode']; actionId: string; backendIdentity: string } | null {
  for (const action of actions) {
    if (!action.visible || !action.enabled) continue;
    const actionRef = action.actionRef;
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

function collectNodeActions(nodes: CanonicalFormNode[], out: CanonicalFormAction[]): void {
  for (const node of nodes) {
    if (node.action) out.push(node.action);
    collectNodeActions(node.children, out);
  }
}

/**
 * Returns every action reference reachable from the canonical form renderer.
 * Presentation placement is irrelevant here: header, footer, smart-button and
 * body-node actions all require the same exact backend-identity adapter.
 */
export function collectCanonicalFormActions(
  model: CanonicalFormRenderModel,
): CanonicalFormAction[] {
  const actions = [...model.actionBar];
  collectNodeActions([...model.zones.primary, ...model.zones.subordinate], actions);
  const seen = new Set<string>();
  return actions.filter((action) => {
    const ref = action.actionRef;
    const identity = `${String(ref.actionId || '').trim()}\u0000${String(ref.backendIdentity || '').trim()}`;
    if (seen.has(identity)) return false;
    seen.add(identity);
    return true;
  });
}
