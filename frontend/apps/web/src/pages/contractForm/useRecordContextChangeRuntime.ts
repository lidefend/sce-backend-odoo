export function useRecordContextChangeRuntime(params: {
  isActive: () => boolean;
  reload: () => void | Promise<void>;
}) {
  function handleRecordContextChanged(): void {
    if (!params.isActive()) return;
    void params.reload();
  }

  return {
    handleRecordContextChanged,
  };
}
