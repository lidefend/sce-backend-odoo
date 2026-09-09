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

export function createOne2manyRelationPopupAuthority() {
  const owners = new Map<string, Set<string>>();
  return {
    update(key: string, ownerId: string, visible: boolean): 'opened' | 'closed' | 'unchanged' {
      const current = owners.get(key) || new Set<string>();
      if (visible) {
        if (current.has(ownerId)) return 'unchanged';
        const wasClosed = current.size === 0;
        current.add(ownerId);
        owners.set(key, current);
        return wasClosed ? 'opened' : 'unchanged';
      }
      if (!current.delete(ownerId)) return 'unchanged';
      if (current.size) return 'unchanged';
      owners.delete(key);
      return 'closed';
    },
    clear() {
      owners.clear();
    },
    isOpen(key: string) {
      return Boolean(owners.get(key)?.size);
    },
  };
}

export function isExplicitOne2manyRelationPopupClose(trigger: string): boolean {
  return ['document', 'keydown-esc'].includes(trigger);
}

export function isExplicitOne2manyRelationPopupOpen(trigger: string): boolean {
  return trigger === 'trigger-element-click';
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
