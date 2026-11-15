export type LoadingProgressPresentation = {
  elapsedLabel: string;
  hint: string;
};

export function formatLoadingProgress(elapsedMs: number): LoadingProgressPresentation {
  const elapsedSeconds = Math.max(0, Math.floor(Number(elapsedMs || 0) / 1000));
  return {
    elapsedLabel: `已等待 ${elapsedSeconds} 秒`,
    hint: elapsedSeconds < 5
      ? '正在读取页面契约与业务数据'
      : '业务数据仍在加载，请稍候',
  };
}
