import type {
  ContractV2ActionRule,
  ContractV2Dictionary,
  ContractV2NormalizedStore,
  ContractV2RuntimeContract,
} from './types';

export interface ContractV2RuntimeActionPlan {
  action: ContractV2ActionRule;
  params: ContractV2Dictionary;
}

export interface ContractV2RuntimeDataSourcePlan {
  dataKey: string;
  source: ContractV2Dictionary;
  params: ContractV2Dictionary;
}

/**
 * A snapshot policy explicitly permits local snapshot reuse. `etag` requires a
 * server revalidation round-trip and `none` forbids reuse, so neither may enter
 * the in-memory snapshot cache.
 */
export function permitsContractV2SnapshotReuse(runtime: ContractV2RuntimeContract): boolean {
  return runtime.cachePolicy === 'snapshot';
}

export function resolveContractV2ActionPlan(
  store: ContractV2NormalizedStore,
  actionId: string,
  params: ContractV2Dictionary = {},
): ContractV2RuntimeActionPlan | null {
  const action = store.actionsById.get(actionId);
  if (!action) return null;
  return { action, params };
}

export function resolveContractV2DataSourcePlan(
  store: ContractV2NormalizedStore,
  dataKey: string,
  params: ContractV2Dictionary = {},
): ContractV2RuntimeDataSourcePlan | null {
  const source = store.snapshot.dataContract.dataSource[dataKey];
  if (!source) return null;
  return { dataKey, source, params };
}
