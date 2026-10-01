/** Readonly blocks consume declared requests; callers supply a dedicated intent allowlist. */
export type ReadonlyBlockRequest = { intent: string; params: Record<string, string | number> };
export type ReadonlyBlockResolution =
  | { status: 'ready'; request: ReadonlyBlockRequest }
  | { status: 'empty' | 'invalid' };

type ParameterRule = { kind: 'id' | 'string'; required?: boolean };

export function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value)
    && [Object.prototype, null].includes(Object.getPrototypeOf(value)));
}

export function readonlyBlockData(dataset: unknown): Record<string, unknown> {
  return isPlainRecord(dataset) && isPlainRecord(dataset.data) ? dataset.data : {};
}

export function resolveReadonlyBlockRequest(
  declaration: unknown,
  expectedIntent: string,
  rules: Record<string, ParameterRule>,
): ReadonlyBlockResolution {
  if (!isPlainRecord(declaration)) return { status: 'invalid' };
  if (declaration.fetch_intent === undefined && declaration.fetch_params === undefined) return { status: 'empty' };
  if (declaration.fetch_intent !== expectedIntent || declaration.readonly === false || !isPlainRecord(declaration.fetch_params)) {
    return { status: 'invalid' };
  }
  const raw = declaration.fetch_params;
  if (Object.keys(raw).some(key => !Object.hasOwn(rules, key))) return { status: 'invalid' };
  const params: Record<string, string | number> = {};
  let missingContext = false;
  let positiveIds = 0;
  for (const [key, rule] of Object.entries(rules)) {
    const value = raw[key];
    if (value === undefined) {
      if (rule.required) missingContext = true;
      continue;
    }
    if (rule.kind === 'string') {
      if (typeof value !== 'string' || !value.trim()) return { status: 'invalid' };
      params[key] = value;
    } else {
      if (typeof value !== 'number' && !(typeof value === 'string' && /^(0|[1-9]\d*)$/.test(value))) return { status: 'invalid' };
      const id = Number(value);
      if (!Number.isSafeInteger(id) || id < 0) return { status: 'invalid' };
      params[key] = id;
      if (id > 0) positiveIds += 1;
      else if (rule.required) missingContext = true;
    }
  }
  if (missingContext || positiveIds === 0) return { status: 'empty' };
  return { status: 'ready', request: { intent: expectedIntent, params } };
}

/** Every transition invalidates success, failure and finally from older requests. */
export function createReadonlyBlockLoader<T>(hooks: {
  reset: (loading: boolean) => void;
  success: (value: T) => void;
  error: (error: unknown) => void;
  settled: () => void;
}) {
  let generation = 0;
  let disposed = false;
  return {
    async load(fetcher: ((isCurrent: () => boolean) => Promise<T>) | null): Promise<void> {
      const current = ++generation;
      if (disposed) return;
      hooks.reset(Boolean(fetcher));
      if (!fetcher) return;
      try {
        const value = await fetcher(() => !disposed && generation === current);
        if (!disposed && generation === current) hooks.success(value);
      } catch (error) {
        if (!disposed && generation === current) hooks.error(error);
      } finally {
        if (!disposed && generation === current) hooks.settled();
      }
    },
    dispose() { disposed = true; generation += 1; },
  };
}
