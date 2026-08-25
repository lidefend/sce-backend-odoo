export type CollectionAggregateEntry = Record<string, unknown>;

export function resolveCollectionAggregateEntry(
  aggregates: Record<string, CollectionAggregateEntry> | null | undefined,
  displayField: string,
  aggregationField: string,
): CollectionAggregateEntry {
  if (!aggregates || typeof aggregates !== 'object') return {};
  const displayKey = String(displayField || '').trim();
  const sourceKey = String(aggregationField || '').trim();
  const displayEntry = displayKey ? aggregates[displayKey] : null;
  if (displayEntry && typeof displayEntry === 'object') return displayEntry;
  const sourceEntry = sourceKey ? aggregates[sourceKey] : null;
  return sourceEntry && typeof sourceEntry === 'object' ? sourceEntry : {};
}
