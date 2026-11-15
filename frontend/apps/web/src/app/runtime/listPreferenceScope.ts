export type ListColumnPreferenceScope = {
  action_id?: number;
  model: string;
  view_type: 'list';
  preference_key: 'list_columns';
};

function positiveInteger(value: unknown): number {
  const parsed = Number(value || 0);
  if (!Number.isFinite(parsed) || parsed <= 0) return 0;
  return Math.trunc(parsed);
}

/**
 * Build the list-preference lookup identity for the current action.
 *
 * When an action id is available, the action is the authoritative source for
 * its model. A model projected from the previous page may still be mounted
 * while the next action's contract is loading, so it must not be paired with
 * the new action id. The backend resolves the model from the action and keeps
 * rejecting any genuinely inconsistent request.
 */
export function resolveListColumnPreferenceScope(input: {
  actionId?: unknown;
  model?: unknown;
}): ListColumnPreferenceScope {
  const actionId = positiveInteger(input.actionId);
  const model = actionId > 0 ? '' : String(input.model || '').trim();
  return {
    action_id: actionId || undefined,
    model,
    view_type: 'list',
    preference_key: 'list_columns',
  };
}
