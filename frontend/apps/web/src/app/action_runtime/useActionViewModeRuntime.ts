type UseActionViewModeRuntimeOptions = {
  strictContractMode: { value: boolean };
  strictViewModeLabelMap: { value: Record<string, string> };
  pageText: (key: string, fallback: string) => string;
  preferredViewMode: { value: string };
  viewMode: { value: string };
  normalizeActionViewMode: (mode: string) => string;
  resolveActionViewModeLabel: (input: {
    mode: string;
    strictContractMode: boolean;
    strictLabelMap: Record<string, string>;
    pageText: (key: string, fallback: string) => string;
    contract?: Record<string, unknown> | null;
  }) => string;
  contract: { value: Record<string, unknown> | null };
  persistMode?: (mode: string) => void;
  load: () => Promise<void>;
};

export function useActionViewModeRuntime(options: UseActionViewModeRuntimeOptions) {
  function viewModeLabel(mode: string) {
    return options.resolveActionViewModeLabel({
      mode,
      strictContractMode: options.strictContractMode.value,
      strictLabelMap: options.strictViewModeLabelMap.value,
      pageText: options.pageText,
      contract: options.contract.value,
    });
  }

  function switchViewMode(mode: string) {
    const normalized = options.normalizeActionViewMode(mode);
    if (!normalized || normalized === options.viewMode.value) return;
    options.preferredViewMode.value = normalized;
    if (options.persistMode) {
      options.persistMode(normalized);
      return;
    }
    void options.load();
  }

  return {
    viewModeLabel,
    switchViewMode,
  };
}
