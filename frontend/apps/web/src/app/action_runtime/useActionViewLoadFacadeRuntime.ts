type ExecuteLoadResult = {
  stopped: boolean;
};

type UseActionViewLoadFacadeRuntimeOptions = {
  executeLoad: (loadGeneration: number) => Promise<ExecuteLoadResult>;
};

export function useActionViewLoadFacadeRuntime(options: UseActionViewLoadFacadeRuntimeOptions) {
  async function loadPage(loadGeneration: number): Promise<void> {
    const loadMainPhaseResult = await options.executeLoad(loadGeneration);
    if (loadMainPhaseResult.stopped) {
      return;
    }
  }

  return {
    loadPage,
  };
}
