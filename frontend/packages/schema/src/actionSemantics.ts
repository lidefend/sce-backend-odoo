/** Terminal-independent meaning. Execution target and applicability stay on the
 * existing action rule; this declaration grants no capability or permission. */
export const ACTION_PURPOSES = Object.freeze([
  'save_draft',
  'submit',
  'approve',
  'reject',
  'cancel_record',
  'start_execution',
  'complete',
  'reopen',
  'discard_changes',
  'return',
] as const);

export type ActionPurpose = (typeof ACTION_PURPOSES)[number];

/** Purposes owned by platform persistence and the shared client commands. The
 * business subset below is derived from this, so the vocabulary is never
 * restated: a purpose is added in ACTION_PURPOSES and classified here. */
export const NON_BUSINESS_PURPOSES = Object.freeze(['save_draft', 'discard_changes', 'return'] as const);

/** Purposes a business action may declare. Persistence (`record.save`) and the
 * client commands keep their own kind, so they are excluded from this subset. */
export const DECLARED_BUSINESS_PURPOSES = Object.freeze(
  ACTION_PURPOSES.filter((purpose) => !(NON_BUSINESS_PURPOSES as readonly string[]).includes(purpose)),
);

export type ActionSemantics = {
  kind: 'persistence' | 'business' | 'interaction';
  purpose: ActionPurpose;
  executor: 'record.save' | 'contract.action' | 'client.back' | 'client.discard';
  origin: string;
  operation?: 'create' | 'write';
};

export const formClientCommands = Object.freeze({
  back: Object.freeze({ actionId: 'form.back', event: 'back', actionSemantics: {
    kind: 'interaction', purpose: 'return', executor: 'client.back', origin: 'shared_client_commands',
  } as const }),
  discard: Object.freeze({ actionId: 'form.discard', event: 'discard', actionSemantics: {
    kind: 'interaction', purpose: 'discard_changes', executor: 'client.discard', origin: 'shared_client_commands',
  } as const }),
});

/** Single compatibility boundary: only the historical platform form.save ID +
 * backend identity is recognized. Explicit malformed declarations never fall
 * back to legacy inference. Unknown actions retain their original binding. */
export function normalizeActionSemantics(rule: {
  actionId: string; backendIdentity?: string; actionSemantics?: unknown;
  intent?: string; target?: Record<string, unknown>; visibleProfiles?: string[];
}): ActionSemantics | undefined {
  const raw = rule.actionSemantics;
  if (raw === undefined) {
    if (rule.actionId !== 'form.save' || rule.backendIdentity !== 'contract_action:form.save'
      || (rule.intent !== undefined && rule.intent !== 'api.data')) return undefined;
    return { kind: 'persistence', purpose: 'save_draft', executor: 'record.save',
      origin: 'legacy:contract_action:form.save',
      ...(rule.visibleProfiles?.length === 1 && rule.visibleProfiles[0] === 'create' ? { operation: 'create' as const }
        : rule.visibleProfiles?.length === 1 && rule.visibleProfiles[0] === 'edit' ? { operation: 'write' as const } : {}),
    };
  }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return undefined;
  const row = raw as Record<string, unknown>;
  if (typeof row.origin !== 'string' || !row.origin.trim()) return undefined;
  if (row.kind === 'persistence' && row.purpose === 'save_draft' && row.executor === 'record.save'
    && rule.actionId === 'form.save' && rule.backendIdentity === 'contract_action:form.save'
    && row.origin === 'platform_form_action'
    && rule.intent === 'api.data' && (row.operation === 'create' || row.operation === 'write')
    && rule.target?.operation === row.operation && typeof rule.target?.model === 'string' && rule.target.model) {
    return { kind: row.kind, purpose: row.purpose, executor: row.executor, origin: row.origin, operation: row.operation };
  }
  if (row.kind === 'business' && row.executor === 'contract.action'
    && (DECLARED_BUSINESS_PURPOSES as readonly string[]).includes(String(row.purpose))) {
    return { kind: row.kind, purpose: row.purpose as ActionPurpose, executor: row.executor, origin: row.origin };
  }
  if (row.kind === 'interaction' && ((row.purpose === 'return' && row.executor === 'client.back')
    || (row.purpose === 'discard_changes' && row.executor === 'client.discard'))) {
    return { kind: row.kind, purpose: row.purpose, executor: row.executor, origin: row.origin };
  }
  return undefined;
}
