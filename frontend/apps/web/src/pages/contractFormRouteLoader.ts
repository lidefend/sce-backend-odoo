// P0 transport deadline, not a business SLA or permission decision.
export const ASSET_LOAD_TIMEOUT_MS = 15_000;

export type ContractFormRouteLoadResult<T> =
  | { module: T }
  | { error: unknown }
  | { cancelled: true };

export function createContractFormRouteLoader<T>(
  loadPage: () => Promise<T>,
  timeoutMs = ASSET_LOAD_TIMEOUT_MS,
) {
  let generation = 0;
  let pending: {
    generation: number;
    promise: Promise<ContractFormRouteLoadResult<T>>;
  } | null = null;

  function invalidate() {
    generation += 1;
    pending = null;
  }

  function load(): Promise<ContractFormRouteLoadResult<T>> {
    if (pending?.generation === generation) return pending.promise;
    const requestGeneration = generation;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    const run = (async (): Promise<ContractFormRouteLoadResult<T>> => {
      try {
        const timeout = new Promise<never>((_, reject) => {
          timeoutId = setTimeout(() => {
            reject(new Error('record_route_asset_load_timeout'));
          }, timeoutMs);
        });
        const module = await Promise.race([loadPage(), timeout]);
        if (requestGeneration !== generation) return { cancelled: true };
        return { module };
      } catch (error) {
        if (requestGeneration !== generation) return { cancelled: true };
        return { error };
      } finally {
        if (timeoutId !== null) clearTimeout(timeoutId);
      }
    })();
    pending = { generation, promise: run };
    void run.finally(() => {
      if (pending?.generation === requestGeneration) pending = null;
    });
    return run;
  }

  return { invalidate, load };
}
