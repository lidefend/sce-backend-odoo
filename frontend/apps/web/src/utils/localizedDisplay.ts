export type LocalizedDisplayOptions = {
  emptyText?: string;
  locale?: string;
  fallbackLocales?: string[];
};

const DEFAULT_FALLBACK_LOCALES = ['zh_CN', 'en_US'];

export function normalizeLocale(value: unknown): string {
  const text = String(value || '').trim().replace('-', '_');
  if (!text) return '';
  const [language, territory] = text.split('_', 2);
  return territory ? `${language.toLowerCase()}_${territory.toUpperCase()}` : language.toLowerCase();
}

export function runtimeLocale(): string {
  if (typeof document !== 'undefined') {
    const documentLocale = normalizeLocale(document.documentElement.lang);
    if (documentLocale) return documentLocale;
  }
  if (typeof navigator !== 'undefined') return normalizeLocale(navigator.language);
  return '';
}

function parseQuotedValue(source: string, start: number): { value: string; end: number } | null {
  let cursor = start;
  while (cursor < source.length && /\s/.test(source[cursor] || '')) cursor += 1;
  const quote = source[cursor];
  if (quote !== "'" && quote !== '"') return null;
  cursor += 1;
  let value = '';
  while (cursor < source.length) {
    const character = source[cursor] || '';
    if (character === '\\') {
      const next = source[cursor + 1];
      if (next === undefined) return null;
      value += next === 'n' ? '\n' : next === 't' ? '\t' : next;
      cursor += 2;
      continue;
    }
    if (character === quote) return { value, end: cursor + 1 };
    value += character;
    cursor += 1;
  }
  return null;
}

function localizedMapping(value: unknown): Record<string, string> | null {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return Object.entries(value as Record<string, unknown>).reduce<Record<string, string>>((out, [key, item]) => {
      const locale = normalizeLocale(key);
      if (locale) out[locale] = String(item || '').trim();
      return out;
    }, {});
  }
  if (typeof value !== 'string') return null;
  const source = value.trim();
  if (!source.startsWith('{') || !source.endsWith('}')) return null;
  try {
    const parsed = JSON.parse(source);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return localizedMapping(parsed);
    }
  } catch {
    // Legacy imports may carry a safe, shallow Python mapping literal.
  }
  const result: Record<string, string> = {};
  const keyPattern = /(['"])([a-z]{2}(?:[_-][a-z]{2})?)\1\s*:/gi;
  for (const match of source.matchAll(keyPattern)) {
    const parsed = parseQuotedValue(source, Number(match.index || 0) + match[0].length);
    const locale = normalizeLocale(match[2]);
    if (parsed && locale) result[locale] = parsed.value.trim();
  }
  return Object.keys(result).length ? result : {};
}

function selectLocalizedMappingValue(
  mapping: Record<string, string>,
  options?: LocalizedDisplayOptions,
): string {
  const requested = normalizeLocale(options?.locale) || runtimeLocale();
  const candidates = [
    requested,
    requested.split('_', 1)[0],
    ...(options?.fallbackLocales || DEFAULT_FALLBACK_LOCALES).map(normalizeLocale),
  ];
  for (const locale of candidates) {
    if (locale && mapping[locale]) return mapping[locale];
  }
  return Object.values(mapping).find((item) => item) || options?.emptyText || '';
}

export function resolveLocalizedDisplayValue(
  value: unknown,
  options?: LocalizedDisplayOptions,
): unknown {
  const mapping = localizedMapping(value);
  if (mapping === null) {
    if (value && typeof value === 'object' && !Array.isArray(value)) return options?.emptyText ?? '';
    if (typeof value === 'string') {
      if (value.trim().startsWith('{')) return options?.emptyText ?? '';
      return value.replace(/\{[^{}]*(?:zh_CN|en_US)[^{}]*\}/g, (literal) => {
        const embedded = localizedMapping(literal);
        return embedded ? selectLocalizedMappingValue(embedded, options) : literal;
      });
    }
    return value;
  }
  return selectLocalizedMappingValue(mapping, options);
}
