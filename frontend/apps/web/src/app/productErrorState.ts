import { contractGapError } from './contract/contractGap';

export type ProductErrorState = {
  kind: string;
  title: string;
  message: string;
  statuses: number[];
  reasons: string[];
  action: { kind: 'route' | 'retry' | 'none'; label: string; path: string | null };
};
export type ErrorStateContract = { schema_version: string; default_kind: string; states: ProductErrorState[] };

export function requireErrorStateContract(value: unknown): ErrorStateContract {
  const contract = value as ErrorStateContract | null;
  const gap = () => { throw contractGapError({ kind: 'contract_defect', missing: 'page_contracts.error_states', requiredDeclarationLayer: 'P0:smart_core:error_state_contract' }, 'ContractGapError: page_contracts.error_states'); };
  if (!contract || contract.schema_version !== '1.0.0' || !Array.isArray(contract.states) || !contract.states.length) return gap();
  const identities = new Set<string>();
  const statuses = new Set<number>();
  const reasons = new Set<string>();
  for (const row of contract.states) {
    if (!row || ![row.kind, row.title, row.message, row.action?.label].every(text => typeof text === 'string' && text.trim())
      || identities.has(row.kind) || !Array.isArray(row.statuses) || !row.statuses.every(Number.isInteger)
      || !Array.isArray(row.reasons) || !row.reasons.every(reason => typeof reason === 'string' && reason.length)
      || !['route', 'retry', 'none'].includes(row.action?.kind)
      || (row.action.kind === 'route' && (typeof row.action.path !== 'string' || !/^\/(?!\/)/.test(row.action.path) || /[\\\s]/.test(row.action.path)))) return gap();
    for (const status of row.statuses) { if (statuses.has(status)) return gap(); statuses.add(status); }
    for (const reason of row.reasons) { if (reasons.has(reason)) return gap(); reasons.add(reason); }
    identities.add(row.kind);
  }
  if (!identities.has(contract.default_kind)) return gap();
  return contract;
}

// Interpret declared selectors only; no frontend status-to-product mapping.
export function resolveProductErrorState(input: { status?: number | string | null; message?: string; reasonCode?: string }, declaration: unknown): ProductErrorState {
  const contract = requireErrorStateContract(declaration);
  const reason = String(input.reasonCode || '').trim().toUpperCase();
  const hasStatus = input.status !== undefined && input.status !== null && String(input.status).trim() !== '';
  return contract.states.find(row => row.reasons.includes(reason))
    || contract.states.find(row => hasStatus && row.statuses.includes(Number(input.status)))
    || contract.states.find(row => row.kind === contract.default_kind)!;
}
