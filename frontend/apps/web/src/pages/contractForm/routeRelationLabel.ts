import type { LocationQuery } from 'vue-router';

type Query = LocationQuery | Record<string, unknown>;

export function applyRouteRelationLabel(
  query: Query,
  fieldName: string,
  relationId: number,
  apply: (label: string) => void,
) {
  const label = String(query[`default_${fieldName}_label`] || '').trim();
  if (relationId > 0 && label) apply(label);
}

