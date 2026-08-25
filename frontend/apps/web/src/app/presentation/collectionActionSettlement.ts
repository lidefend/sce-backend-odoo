export type CollectionBatchAction = {
  key: string;
  label: string;
  enabled: boolean;
  hint?: string;
};

export type CollectionBatchActionSettlement = {
  direct: readonly CollectionBatchAction[];
  overflow: readonly CollectionBatchAction[];
  actionKeys: readonly string[];
};

export function resolveCollectionBatchActionSettlement(
  actions: readonly CollectionBatchAction[],
): CollectionBatchActionSettlement {
  const normalized = actions.map((action) => ({
    ...action,
    key: String(action.key || '').trim(),
    label: String(action.label || '').trim(),
  }));
  if (normalized.some((action) => !action.key || !action.label)) {
    throw new Error('COLLECTION_BATCH_ACTION_IDENTITY_REQUIRED');
  }
  const actionKeys = normalized.map((action) => action.key);
  if (new Set(actionKeys).size !== actionKeys.length) {
    throw new Error('COLLECTION_BATCH_ACTION_IDENTITY_DUPLICATE');
  }
  return {
    direct: normalized.slice(0, 1),
    overflow: normalized.slice(1),
    actionKeys,
  };
}
