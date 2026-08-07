import type { LocationQuery } from 'vue-router';
import { pickContractNavQuery } from '../../app/navigationContext';

type Query = LocationQuery | Record<string, unknown>;

export function buildFormRequestContext(query: Query, base: Record<string, unknown> = {}) {
  return {
    ...base,
    ...pickContractNavQuery(query as Record<string, unknown>),
  };
}

