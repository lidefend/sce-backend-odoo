import type { ActionContract } from '@sc/schema';
import {
  resolveUnifiedPageContractV2MainData,
  resolveUnifiedPageContractV2SourceContext,
} from '../../app/contracts/unifiedPageContractV2';
import type { ContractV2NormalizedStore } from '../../app/contracts/v2/types';
import { normalizeRouteDefault } from './valueUtils';

export function formCreateContext(params: {
  contract: ActionContract | null;
  v2ContractStore: ContractV2NormalizedStore | null;
}) {
  const storeContext = resolveUnifiedPageContractV2SourceContext(params.v2ContractStore);
  return (Object.keys(storeContext).length ? storeContext : resolveUnifiedPageContractV2SourceContext(params.contract)).context || {};
}

export function resolveCreateDefaults(params: {
  contract: ActionContract | null;
  routeQuery: Record<string, unknown>;
  selectedProject?: Record<string, unknown> | null;
  v2ContractStore: ContractV2NormalizedStore | null;
}) {
  const storeMainData = resolveUnifiedPageContractV2MainData(params.v2ContractStore);
  const defaults: Record<string, unknown> = {
    ...(Object.keys(storeMainData).length ? storeMainData : resolveUnifiedPageContractV2MainData(params.contract)),
  };
  Object.entries(params.routeQuery).forEach(([key, value]) => {
    if (key.startsWith('default_')) {
      defaults[key.replace(/^default_/, '')] = normalizeRouteDefault(value);
    }
  });
  const context = formCreateContext(params);
  Object.entries(context).forEach(([key, value]) => {
    if (key.startsWith('default_') && !(key.replace(/^default_/, '') in defaults)) {
      defaults[key.replace(/^default_/, '')] = value;
    }
  });
  const validator = params.contract?.validator as Record<string, unknown> | undefined;
  const defaultsSample = validator?.defaults_sample;
  if (defaultsSample && typeof defaultsSample === 'object' && !Array.isArray(defaultsSample)) {
    Object.entries(defaultsSample as Record<string, unknown>).forEach(([key, value]) => {
      if (!(key in defaults)) {
        defaults[key] = value === 'dynamic' ? '' : value;
      }
    });
  }
  return defaults;
}
