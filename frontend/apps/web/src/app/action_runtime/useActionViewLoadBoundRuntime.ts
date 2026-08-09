type Dict = Record<string, unknown>;

type BeginResult = {
  startedAt: number;
  shouldReturn: boolean;
};

type UseActionViewLoadBoundRuntimeOptions = {
  executeLoadBeginPhase: (input: { input: Dict }) => BeginResult;
  executeLoadMainBound: (input: { startedAt: number; loadGeneration: number }) => Promise<{ stopped: boolean }>;
};

export function useActionViewLoadBoundRuntime(options: UseActionViewLoadBoundRuntimeOptions) {
  async function executeLoad(loadGeneration: number): Promise<{ stopped: boolean }> {
    const beginState = options.executeLoadBeginPhase({ input: {} });
    if (beginState.shouldReturn) {
      return { stopped: true };
    }

    const loadMainPhaseResult = await options.executeLoadMainBound({ startedAt: beginState.startedAt, loadGeneration });
    return loadMainPhaseResult;
  }

  return {
    executeLoad,
  };
}
