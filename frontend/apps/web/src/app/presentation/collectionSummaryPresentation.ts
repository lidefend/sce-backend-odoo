export type CollectionSummaryTone = 'neutral' | 'danger' | 'warning' | 'success' | 'info';

const COLLECTION_SUMMARY_TONES = new Set<CollectionSummaryTone>([
  'neutral',
  'danger',
  'warning',
  'success',
  'info',
]);

export function resolveCollectionSummaryTone(value: unknown): CollectionSummaryTone {
  const normalized = typeof value === 'string' ? value.trim() : '';
  return COLLECTION_SUMMARY_TONES.has(normalized as CollectionSummaryTone)
    ? normalized as CollectionSummaryTone
    : 'neutral';
}
