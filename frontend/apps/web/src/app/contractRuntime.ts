export function toPositiveInt(raw: unknown): number | null {
  // Strict positive-integer parsing for record/action/menu ids.  Number() here
  // would coerce `true` to 1 and accept `379.5`, so a malformed contract could
  // make a hidden create entry clickable or misroute it.  Only integer numbers
  // and decimal digit strings without a leading zero are accepted.
  if (typeof raw === 'number') {
    return Number.isSafeInteger(raw) && raw > 0 ? raw : null;
  }
  if (typeof raw === 'string') {
    const text = raw.trim();
    if (!/^[1-9][0-9]*$/.test(text)) return null;
    const parsed = Number(text);
    return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
  }
  return null;
}

export function parseMaybeJsonRecord(raw: unknown): Record<string, unknown> {
  if (!raw) return {};
  if (typeof raw === 'object' && !Array.isArray(raw)) {
    return raw as Record<string, unknown>;
  }
  if (typeof raw !== 'string') return {};
  const text = raw.trim();
  if (!text) return {};
  try {
    const parsed = JSON.parse(text);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    return {};
  }
  return {};
}

export function detectObjectMethodFromActionKey(key: string, fallback = ''): string {
  if (fallback) return fallback;
  const match = key.match(/^obj_([^_]+(?:_[^_]+)*)_/);
  return match?.[1] || '';
}

export function normalizeActionKind(kind: unknown): string {
  return String(kind || '').trim().toLowerCase();
}

