import { resolveContractV2PageAccessVerdict } from '../../app/contracts/v2/store';
import type { ContractV2NormalizedStore } from '../../app/contracts/v2/types';
import type { ContractAccessPolicy } from './types';

function normalizePolicyRows(value: unknown) {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (!item || typeof item !== 'object' || Array.isArray(item)) return null;
      const row = item as Record<string, unknown>;
      return {
        field: String(row.field || '').trim(),
        model: String(row.model || '').trim(),
        reasonCode: String(row.reason_code || '').trim(),
      };
    })
    .filter((item): item is { field: string; model: string; reasonCode: string } => Boolean(item));
}

export function normalizeContractAccessPolicy(raw: unknown): ContractAccessPolicy {
  const row = raw && typeof raw === 'object' && !Array.isArray(raw)
    ? raw as Record<string, unknown>
    : {};
  const modeRaw = String(row.mode || '').trim().toLowerCase();
  const mode: 'allow' | 'degrade' | 'block' = modeRaw === 'block' || modeRaw === 'degrade' ? modeRaw : 'allow';
  return {
    mode,
    reasonCode: String(row.reason_code || '').trim(),
    message: String(row.message || '').trim(),
    blockedFields: normalizePolicyRows(row.blocked_fields),
    degradedFields: normalizePolicyRows(row.degraded_fields),
  };
}

/**
 * The page-level access decision has exactly one source of truth: the v2
 * contract's `statusContract.globalStatus`.  The frontend only projects that
 * fact here.  When the contract declares `pageVisible:false` / `pageAuth:none`
 * the page becomes `block` and keeps the contract's own reason code, so the
 * record page lifecycle raises `ContractAccessPolicyError` instead of silently
 * rendering a form the role was never granted.
 */
export function resolveContractPageAccessPolicy(
  store: ContractV2NormalizedStore | null,
): ContractAccessPolicy {
  const verdict = resolveContractV2PageAccessVerdict(store);
  if (!verdict.blocked) return normalizeContractAccessPolicy(undefined);
  return normalizeContractAccessPolicy({ mode: 'block', reason_code: verdict.reasonCode });
}
