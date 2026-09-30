/** Terminal-independent meaning. Execution target and applicability stay on the
 * existing action rule; this declaration grants no capability or permission. */
export type ActionSemantics = {
  kind: 'persistence' | 'business' | 'interaction';
  purpose: 'save_draft' | 'submit' | 'approve' | 'reject' | 'cancel_record' | 'discard_changes' | 'return';
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
    && ['submit', 'approve', 'reject', 'cancel_record'].includes(String(row.purpose))) {
    return { kind: row.kind, purpose: row.purpose as ActionSemantics['purpose'], executor: row.executor, origin: row.origin };
  }
  if (row.kind === 'interaction' && ((row.purpose === 'return' && row.executor === 'client.back')
    || (row.purpose === 'discard_changes' && row.executor === 'client.discard'))) {
    return { kind: row.kind, purpose: row.purpose, executor: row.executor, origin: row.origin };
  }
  return undefined;
}
