function normalizedFields(fields: unknown): string[] {
  return Array.isArray(fields)
    ? fields.map((field) => String(field || '').trim()).filter(Boolean)
    : [];
}

export function persistIntakeAutosavePayload(key: string, values: Record<string, unknown>, fields: unknown) {
  const storageKey = String(key || '').trim();
  if (!storageKey || typeof window === 'undefined') return;
  try {
    const payload = {
      saved_at: Date.now(),
      values: normalizedFields(fields).reduce<Record<string, unknown>>((acc, field) => {
        const fallback = field.endsWith('_id') ? false : '';
        acc[field] = values[field] ?? fallback;
        return acc;
      }, {}),
    };
    window.localStorage.setItem(storageKey, JSON.stringify(payload));
  } catch {
    // ignore storage exceptions
  }
}

export function restoreIntakeAutosavePayload(key: string, fields: unknown) {
  const storageKey = String(key || '').trim();
  if (!storageKey || typeof window === 'undefined') return {};
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as { values?: Record<string, unknown> };
    const values = parsed?.values;
    if (!values || typeof values !== 'object') return {};
    return normalizedFields(fields).reduce<Record<string, unknown>>((acc, field) => {
      if (!(field in values)) return acc;
      const nextValue = values[field];
      if (nextValue === null || nextValue === undefined || nextValue === '') return acc;
      acc[field] = nextValue;
      return acc;
    }, {});
  } catch {
    return {};
  }
}

export function clearIntakeAutosavePayload(key: string) {
  const storageKey = String(key || '').trim();
  if (!storageKey || typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(storageKey);
  } catch {
    // ignore storage exceptions
  }
}
