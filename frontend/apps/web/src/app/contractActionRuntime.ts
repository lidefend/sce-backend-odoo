import { parseMaybeJsonRecord } from './contractRuntime';
import {
  resolveContractV2EffectiveFormCapabilities,
  resolveContractV2GlobalStatus,
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
  const globalStatus = resolveContractV2GlobalStatus(store);
  const pageAuth = String(globalStatus?.pageAuth || '').trim().toLowerCase();
  if (globalStatus?.pageVisible === false || pageAuth === 'none') {
    return {
      mode: 'block',
      reasonCode: globalStatus?.reasonCode || 'UNIFIED_PAGE_CONTRACT_V2_PAGE_FORBIDDEN',
    };
  }
  return { mode: 'allow', reasonCode: '' };
}

export function resolveContractReadRight(store: ContractV2NormalizedStore | null) {
  const policy = resolveContractAccessPolicy(store);
  if (policy.mode === 'block') return false;
  const globalStatus = resolveContractV2GlobalStatus(store);
  const pageAuth = String(globalStatus?.pageAuth || '').trim().toLowerCase();
  if (globalStatus?.pageVisible === false || pageAuth === 'none') return false;
  const capabilities = resolveContractV2EffectiveFormCapabilities(store);
  if (capabilities) return capabilities.read;
  return true;
}

export function parseContractContextRaw(raw: unknown) {
  return parseMaybeJsonRecord(raw);
}
