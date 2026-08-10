type Dict = Record<string, unknown>;

type UseActionViewLoadMainBoundRuntimeOptions = {
  buildLoadMainPhaseInput: (input: { startedAt: number; loadGeneration: number }) => Dict;
  executeLoadMainPhase: (input: Dict) => Promise<{ stopped: boolean }>;
};

export function useActionViewLoadMainBoundRuntime(options: UseActionViewLoadMainBoundRuntimeOptions) {
  async function executeLoadMainBound(input: { startedAt: number; loadGeneration: number }): Promise<{ stopped: boolean }> {
    return options.executeLoadMainPhase(options.buildLoadMainPhaseInput(input));
  }

  return {
    executeLoadMainBound,
  };
}
