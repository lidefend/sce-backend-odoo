import { parseMaybeJsonRecord } from './contractRuntime';
import {
  resolveContractV2EffectiveFormCapabilities,
  resolveContractV2PageAccessVerdict,
  type ContractV2NormalizedStore,
} from './contracts/v2';

export type ContractAccessPolicyMode = 'allow' | 'degrade' | 'block';

export interface ContractAccessPolicySnapshot {
  mode: ContractAccessPolicyMode;
  reasonCode: string;
}

export function resolveContractViewMode(store: ContractV2NormalizedStore | null) {
  const mode = String(store?.snapshot.pageInfo.viewType || '').trim();
  return mode === 'list' ? 'tree' : mode;
}

export function resolveContractAccessPolicy(store: ContractV2NormalizedStore | null): ContractAccessPolicySnapshot {
  const verdict = resolveContractV2PageAccessVerdict(store);
  return verdict.blocked
    ? { mode: 'block', reasonCode: verdict.reasonCode }
    : { mode: 'allow', reasonCode: '' };
}

export function resolveContractReadRight(store: ContractV2NormalizedStore | null) {
  if (resolveContractAccessPolicy(store).mode === 'block') return false;
  const capabilities = resolveContractV2EffectiveFormCapabilities(store);
  if (capabilities) return capabilities.read;
  return true;
}

export function parseContractContextRaw(raw: unknown) {
  return parseMaybeJsonRecord(raw);
}
