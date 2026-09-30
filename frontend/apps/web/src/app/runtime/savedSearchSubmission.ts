export type SavedSearchSubmissionResult = { saved: boolean; message: string };

/** A refresh failure must never be reported as a failed write or retried as one. */
export async function settleSavedSearchSubmission(
  write: () => Promise<unknown>,
  refresh: () => Promise<unknown>,
): Promise<SavedSearchSubmissionResult> {
  try {
    await write();
  } catch {
    return { saved: false, message: '收藏保存未完成，请检查网络或权限后重试。输入已保留。' };
  }
  try {
    await refresh();
    return { saved: true, message: '收藏已保存' };
  } catch {
    return { saved: true, message: '收藏已保存，但列表刷新失败，请刷新页面查看。无需再次保存。' };
  }
}
