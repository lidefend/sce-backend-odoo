type Dict = Record<string, unknown>;

type BuildLoadSuccessPhaseInputOptions = {
  loadGeneration: number;
  result: Dict;
  contractColumns: string[];
  startedAt: number;
};

export function useActionViewLoadSuccessPhaseInputRuntime() {
  function buildLoadSuccessPhaseInput(input: BuildLoadSuccessPhaseInputOptions): Dict {
    return {
      loadGeneration: input.loadGeneration,
      result: input.result,
      contractColumns: input.contractColumns,
      startedAt: input.startedAt,
    };
  }

  return {
    buildLoadSuccessPhaseInput,
  };
}

