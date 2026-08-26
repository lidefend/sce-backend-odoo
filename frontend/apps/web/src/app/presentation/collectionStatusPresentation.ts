export type CollectionStatusTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

export type CollectionStatusDescriptor = {
  value: string;
  label: string;
  tone: CollectionStatusTone;
};

const TONES = new Set<CollectionStatusTone>(['neutral', 'info', 'success', 'warning', 'danger']);

function text(value: unknown): string {
  if (Array.isArray(value)) {
    if (value.length > 1 && value[1] !== null && value[1] !== undefined) return String(value[1]).trim();
    if (value.length) return String(value[0] ?? '').trim();
  }
  return String(value ?? '').trim();
}

function authorityKey(value: unknown): string {
  if (Array.isArray(value)) return String(value[0] ?? '').trim();
  return String(value ?? '').trim();
}

export function resolveCollectionStatusPresentation(input: {
  value: unknown;
  selection?: Array<{ value: string; label: string }>;
  toneByValue?: Record<string, string>;
}): CollectionStatusDescriptor {
  const value = authorityKey(input.value);
  const label = input.selection?.find((item) => item.value === value)?.label || text(input.value) || '--';
  const candidate = String(input.toneByValue?.[value] || '').trim().toLowerCase() as CollectionStatusTone;
  return {
    value,
    label,
    tone: TONES.has(candidate) ? candidate : 'neutral',
  };
}
