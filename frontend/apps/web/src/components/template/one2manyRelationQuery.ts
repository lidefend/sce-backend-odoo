export type One2manyRelationOption = {
  value: number;
  label: string;
};

export function createOne2manyRelationRequestAuthority() {
  const revisions = new Map<string, number>();
  return {
    begin(key: string) {
      const revision = (revisions.get(key) || 0) + 1;
      revisions.set(key, revision);
      return revision;
    },
    isCurrent(key: string, revision: number) {
      return revisions.get(key) === revision;
    },
    invalidate(key: string) {
      const revision = (revisions.get(key) || 0) + 1;
      revisions.set(key, revision);
      return revision;
    },
    clear() {
      revisions.clear();
    },
  };
}

export function preserveSelectedOne2manyRelationOption(params: {
  incoming: One2manyRelationOption[];
  previous: One2manyRelationOption[];
  currentValue: unknown;
}) {
  const currentId = Number(Array.isArray(params.currentValue) ? params.currentValue[0] : params.currentValue);
  if (!Number.isFinite(currentId) || currentId <= 0) return params.incoming;
  const normalizedId = Math.trunc(currentId);
  if (params.incoming.some((option) => option.value === normalizedId)) return params.incoming;
  const selected = params.previous.find((option) => option.value === normalizedId);
  return selected ? [selected, ...params.incoming] : params.incoming;
}

export function one2manyRelationDependencyKey(params: {
  relation: string;
  canRead: boolean;
  domainSupported: boolean;
  dependencies: string[];
  resolveValue: (dependency: string) => unknown;
}) {
  return JSON.stringify({
    relation: String(params.relation || '').trim(),
    canRead: params.canRead === true,
    domainSupported: params.domainSupported === true,
    dependencies: params.dependencies.map((dependency) => [dependency, params.resolveValue(dependency)]),
  });
}
