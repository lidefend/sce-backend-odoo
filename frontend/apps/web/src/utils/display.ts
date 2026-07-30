import type { FieldDescriptor } from '@sc/schema';

export type DisplayFormatOptions = {
  emptyText?: string;
  booleanTrueText?: string;
  booleanFalseText?: string;
  locale?: string;
  fallbackLocales?: string[];
};

const DEFAULT_OPTIONS: Required<DisplayFormatOptions> = {
  emptyText: '-',
  booleanTrueText: '是',
  booleanFalseText: '否',
  locale: '',
  fallbackLocales: ['zh_CN', 'en_US'],
};

function normalizeOptions(options?: DisplayFormatOptions): Required<DisplayFormatOptions> {
  return {
    emptyText: options?.emptyText ?? DEFAULT_OPTIONS.emptyText,
    booleanTrueText: options?.booleanTrueText ?? DEFAULT_OPTIONS.booleanTrueText,
    booleanFalseText: options?.booleanFalseText ?? DEFAULT_OPTIONS.booleanFalseText,
    locale: options?.locale ?? DEFAULT_OPTIONS.locale,
    fallbackLocales: options?.fallbackLocales ?? DEFAULT_OPTIONS.fallbackLocales,
  };
}

function normalizeLocale(value: unknown): string {
  const text = String(value || '').trim().replace('-', '_');
  if (!text) return '';
  const [language, territory] = text.split('_', 2);
  return territory ? `${language.toLowerCase()}_${territory.toUpperCase()}` : language.toLowerCase();
}

function runtimeLocale(): string {
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
  options?: Pick<DisplayFormatOptions, 'locale' | 'fallbackLocales' | 'emptyText'>,
): string {
  const requested = normalizeLocale(options?.locale) || runtimeLocale();
  const candidates = [
    requested,
    requested.split('_', 1)[0],
    ...(options?.fallbackLocales || DEFAULT_OPTIONS.fallbackLocales).map(normalizeLocale),
  ];
  for (const locale of candidates) {
    if (locale && mapping[locale]) return mapping[locale];
  }
  return Object.values(mapping).find((item) => item) || options?.emptyText || '';
}

export function resolveLocalizedDisplayValue(
  value: unknown,
  options?: Pick<DisplayFormatOptions, 'locale' | 'fallbackLocales' | 'emptyText'>,
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

function numericValue(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value !== 'string') return null;
  const normalized = value.replace(/,/g, '').trim();
  if (!normalized) return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function relationalTupleDisplayValue(
  value: unknown,
  options: Required<DisplayFormatOptions>,
): string | null {
  if (!Array.isArray(value) || value.length !== 2 || typeof value[0] !== 'number') return null;
  const label = resolveLocalizedDisplayValue(value[1], options);
  if (label === null || label === undefined || typeof label === 'object') return options.emptyText;
  return String(label || value[0]);
}

export function formatAttachmentReferenceValue(value: unknown): string {
  return parseAttachmentReferenceLinks(value).map((item) => item.name).join('、');
}

export function parseAttachmentReferenceLinks(value: unknown): Array<{ name: string; url: string }> {
  const rawItems = Array.isArray(value) ? value.map((item) => String(item ?? '')) : [String(value ?? '')];
  const seen = new Set<string>();
  const links: Array<{ name: string; url: string }> = [];
  const urlStartPattern = '(?:legacy-file-id|legacy-file|https?|file):\\/\\/|\\/web\\/content\\/';
  const itemBoundary = new RegExp(`\\s+(?=[^\\s|]+\\s+\\|\\s+(?:${urlStartPattern}))`, 'i');
  const itemPattern = new RegExp(`^(.*?)\\s+\\|\\s+((?:${urlStartPattern}).+)$`, 'i');

  rawItems
    .flatMap((item) => item.split(itemBoundary))
    .forEach((item) => {
      const raw = item.trim();
      if (!raw) return;
      const match = raw.match(itemPattern);
      if (!match) return;
      const name = match[1].trim();
      const url = match[2].trim();
      const key = `${name}\n${url}`;
      if (!name || !url || seen.has(key)) return;
      seen.add(key);
      links.push({ name, url });
    });

  return links;
}

export function formatDisplayValue(
  value: unknown,
  field?: Pick<FieldDescriptor, 'ttype' | 'type' | 'selection'>,
  options?: DisplayFormatOptions,
): string {
  const normalized = normalizeOptions(options);
  const fieldType = field?.ttype || field?.type;
  value = resolveLocalizedDisplayValue(value, normalized);

  if (value === null || value === undefined || value === '') {
    return normalized.emptyText;
  }

  if (fieldType === 'boolean') {
    return value ? normalized.booleanTrueText : normalized.booleanFalseText;
  }

  if (typeof value === 'boolean') {
    return value ? String(value) : normalized.emptyText;
  }

  if (fieldType === 'selection' && Array.isArray(field?.selection)) {
    const match = field.selection.find((item) => item[0] === value);
    return match ? String(match[1]) : String(value);
  }

  if (fieldType === 'integer' || fieldType === 'float' || fieldType === 'monetary') {
    const parsed = numericValue(value);
    if (parsed !== null) {
      return parsed.toLocaleString('zh-CN', {
        maximumFractionDigits: fieldType === 'integer' ? 0 : 2,
        minimumFractionDigits: fieldType === 'integer' ? 0 : 2,
      });
    }
  }

  if (fieldType === 'many2one' && Array.isArray(value)) {
    const relationalLabel = relationalTupleDisplayValue(value, normalized);
    if (relationalLabel !== null) return relationalLabel;
    if (value[0] != null) {
      return String(value[0]);
    }
    return normalized.emptyText;
  }

  if (Array.isArray(value)) {
    if (!value.length) {
      return normalized.emptyText;
    }
    const relationalLabel = relationalTupleDisplayValue(value, normalized);
    if (relationalLabel !== null) return relationalLabel;
    const attachmentText = formatAttachmentReferenceValue(value);
    if (attachmentText && value.some((item) => /\|\s*(?:(?:legacy-file-id|legacy-file|https?|file):\/\/|\/web\/content\/)/i.test(String(item ?? '')))) {
      return attachmentText;
    }
    return value.map((item) => String(item)).join(', ');
  }

  if (typeof value === 'object') {
    return normalized.emptyText;
  }

  const rawText = String(value);
  if (/\|\s*(?:(?:legacy-file-id|legacy-file|https?|file):\/\/|\/web\/content\/)/i.test(rawText)) {
    return formatAttachmentReferenceValue(rawText) || rawText;
  }
  return rawText;
}
