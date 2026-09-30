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

export type SavedSearchDeleteAction = {
  intent: 'search.favorite.delete';
  enabled: true;
  label: string;
  params: { filter_id: number; model: string; action_id: number | false };
};

export function resolveSavedSearchDeleteAction(value: unknown): SavedSearchDeleteAction | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const row = value as Record<string, unknown>;
  const params = row.params as Record<string, unknown> | undefined;
  if (row.intent !== 'search.favorite.delete' || row.enabled !== true || !params || typeof params !== 'object' || Array.isArray(params)
    || !Number.isInteger(params.filter_id) || Number(params.filter_id) <= 0
    || typeof params.model !== 'string' || !params.model.trim()
    || !(params.action_id === false || (Number.isInteger(params.action_id) && Number(params.action_id) >= 0))) return null;
  return { intent: 'search.favorite.delete', enabled: true,
    label: typeof row.label === 'string' && row.label.trim() ? row.label.trim() : '删除收藏',
    params: { filter_id: Number(params.filter_id), model: params.model, action_id: params.action_id as number | false } };
}

export type SavedSearchDeletionResult = { deleted: boolean; message: string };
export async function settleSavedSearchDeletion(
  remove: () => Promise<unknown>, refresh: () => Promise<unknown>,
): Promise<SavedSearchDeletionResult> {
  try { await remove(); }
  catch { return { deleted: false, message: '收藏删除未完成，请检查网络或权限后重试。' }; }
  try { await refresh(); return { deleted: true, message: '收藏已删除' }; }
  catch { return { deleted: true, message: '收藏已删除，但列表刷新失败，请刷新页面查看。无需再次删除。' }; }
}
