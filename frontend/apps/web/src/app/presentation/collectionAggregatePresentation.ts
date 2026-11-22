export type CollectionAggregateEntry = Record<string, unknown>;

export type CollectionAggregateCurrencyIdentity = Readonly<{
  id: number;
  label: string;
}>;

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

function positiveRecordId(value: unknown): number | null {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0 ? value : null;
}

function currencyRelationIdentity(value: unknown): CollectionAggregateCurrencyIdentity | null {
  if (Array.isArray(value)) {
    const id = positiveRecordId(value[0]);
    const label = String(value[1] ?? '').trim();
    return id && label ? Object.freeze({ id, label }) : null;
  }
  if (value && typeof value === 'object') {
    const row = value as Record<string, unknown>;
    const id = positiveRecordId(row.id);
    const label = String(row.name || row.display_name || row.symbol || '').trim();
    return id && label ? Object.freeze({ id, label }) : null;
  }
  return null;
}

/**
 * Resolve the display label for an already-proven monetary aggregate.
 *
 * The backend proves currency equality over the complete aggregate domain. The
 * frontend only maps the returned currency record id to a relation label from a
 * row in the same rendered scope. It never uses that row to prove aggregate
 * scope or invents a currency when the id or matching label is absent.
 */
export function resolveCollectionAggregateCurrencyIdentity(
  aggregate: CollectionAggregateEntry | null | undefined,
  declaredCurrencyField: string,
  rows: readonly Record<string, unknown>[] | null | undefined,
): CollectionAggregateCurrencyIdentity | null {
  if (!aggregate || String(aggregate.aggregate || '').trim() !== 'sum') return null;
  if (String(aggregate.data_type || '').trim().toLowerCase() !== 'monetary') return null;
  const currencyField = String(aggregate.currency_field || '').trim();
  const expectedCurrencyField = String(declaredCurrencyField || '').trim();
  if (!currencyField || !expectedCurrencyField || currencyField !== expectedCurrencyField) return null;
  const currencyId = positiveRecordId(aggregate.currency_id);
  if (!currencyId) return null;
  for (const row of rows || []) {
    const identity = currencyRelationIdentity(row?.[currencyField]);
    if (identity?.id === currencyId) return identity;
  }
  return null;
}
