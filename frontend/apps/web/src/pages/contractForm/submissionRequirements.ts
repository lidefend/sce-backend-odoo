import { normalizeRelationIds } from './fieldUtils';
import type { ContractAction } from './types';

/** Submission-only prerequisites; draft saving never invokes this check. */
export function submissionRequirementErrors(
  action: Pick<ContractAction, 'actionSemantics'>,
  workflow: Record<string, unknown>,
  values: Record<string, unknown>,
  pendingNativeAttachmentCount: number,
): string[] {
  if (action.actionSemantics?.kind !== 'business' || action.actionSemantics.purpose !== 'submit') return [];
  const raw = workflow.submissionRequirements;
  if (raw === undefined) return [];
  const invalid = ['提交条件契约无效，请刷新后重试。'];
  if (!Array.isArray(raw)) return invalid;
  const errors: string[] = [];
  for (const item of raw) {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return invalid;
    const rule = item as Record<string, unknown>;
    const when = rule.requiredWhen as Record<string, unknown> | undefined;
    if (rule.kind !== 'relation_required' || typeof rule.field !== 'string' || !rule.field
      || typeof rule.message !== 'string' || !rule.message || typeof rule.reasonCode !== 'string' || !rule.reasonCode
      || !when || typeof when.field !== 'string' || !when.field || typeof when.equals !== 'string'
      || (rule.pendingSource !== undefined && rule.pendingSource !== 'native_attachment')) return invalid;
    if (!Object.hasOwn(values, when.field)) return invalid;
    if (values[when.field] !== when.equals) continue;
    if (normalizeRelationIds(values[rule.field]).length > 0) continue;
    if (rule.pendingSource === 'native_attachment' && pendingNativeAttachmentCount > 0) continue;
    errors.push(rule.message);
  }
  return [...new Set(errors)];
}
