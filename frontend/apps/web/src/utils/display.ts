import {
  ATTACHMENT_REFERENCE_URL_SOURCE,
  FIELD_VALUE_EMPTY_TEXT,
  FIELD_VALUE_FALSE_TEXT,
  FIELD_VALUE_TRUE_TEXT,
  containsAttachmentReference,
  containsAttachmentReferenceIn,
  isEmptyFieldValue,
  normalizeFieldType,
} from './fieldSemantics.ts';
import {
  presentDeclaredBusinessValue,
  type DeclaredBusinessField,
} from '../app/presentation/businessValuePresentation.ts';
import {
  resolveLocalizedDisplayValue,
  type LocalizedDisplayOptions,
} from './localizedDisplay.ts';

export { resolveLocalizedDisplayValue };

export type DisplayFormatOptions = LocalizedDisplayOptions & {
  booleanTrueText?: string;
  booleanFalseText?: string;
  currencyLabel?: string;
};

const DEFAULT_OPTIONS: Required<DisplayFormatOptions> = {
  emptyText: FIELD_VALUE_EMPTY_TEXT,
  booleanTrueText: FIELD_VALUE_TRUE_TEXT,
  booleanFalseText: FIELD_VALUE_FALSE_TEXT,
  locale: '',
  fallbackLocales: ['zh_CN', 'en_US'],
  currencyLabel: '',
};

function normalizeOptions(options?: DisplayFormatOptions): Required<DisplayFormatOptions> {
  return {
    emptyText: options?.emptyText ?? DEFAULT_OPTIONS.emptyText,
    booleanTrueText: options?.booleanTrueText ?? DEFAULT_OPTIONS.booleanTrueText,
    booleanFalseText: options?.booleanFalseText ?? DEFAULT_OPTIONS.booleanFalseText,
    locale: options?.locale ?? DEFAULT_OPTIONS.locale,
    fallbackLocales: options?.fallbackLocales ?? DEFAULT_OPTIONS.fallbackLocales,
    currencyLabel: options?.currencyLabel ?? DEFAULT_OPTIONS.currencyLabel,
  };
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

export function stripInternalMigrationMetadata(value: string): string {
  return String(value || '').replace(
    /^\s*\[migration:[a-z0-9_.:-]+\](?:[ \t]+legacy_record_id=[^\s\r\n]+)?(?:[ \t]*\r?\n|[ \t]+)?/i,
    '',
  ).trimStart();
}

export function parseAttachmentReferenceLinks(value: unknown): Array<{ name: string; url: string }> {
  const rawItems = Array.isArray(value) ? value.map((item) => String(item ?? '')) : [String(value ?? '')];
  const seen = new Set<string>();
  const links: Array<{ name: string; url: string }> = [];
  const urlStartPattern = ATTACHMENT_REFERENCE_URL_SOURCE;
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

type DeclaredDisplayField = DeclaredBusinessField;

function normalizeDeclaredValue(
  value: unknown,
  field: DeclaredDisplayField,
  options: Required<DisplayFormatOptions>,
): unknown {
  const fieldType = normalizeFieldType(field);
  if (fieldType === 'json') return value;
  if (fieldType === 'many2one' || fieldType === 'many2many' || fieldType === 'one2many') return value;
  return resolveLocalizedDisplayValue(value, options);
}

function formatDeclaredDisplayValue(
  value: unknown,
  field: DeclaredDisplayField,
  options: Required<DisplayFormatOptions>,
): string {
  const normalizedValue = normalizeDeclaredValue(value, field, options);
  const presentation = presentDeclaredBusinessValue({
    field: {
      name: field.name,
      type: field.type,
      ttype: field.ttype,
      dataType: field.dataType,
      componentKey: field.componentKey,
      widget: field.widget,
      cellRole: field.cellRole,
      selection: field.selection,
      digits: field.digits,
      currencyField: field.currencyField || field.currency_field,
      currencyLabel: field.currencyLabel,
      relation: field.relation,
    },
    value: normalizedValue,
    currencyLabel: options.currencyLabel,
    emptyText: options.emptyText,
    temporalProfile: 'full',
    locale: options.locale,
    fallbackLocales: options.fallbackLocales,
  });
  if (presentation.kind === 'plain') {
    const text = stripInternalMigrationMetadata(presentation.text);
    if (containsAttachmentReference(text)) return formatAttachmentReferenceValue(text) || text;
    return text || options.emptyText;
  }
  return presentation.text;
}

function formatUndeclaredDisplayValue(
  value: unknown,
  options: Required<DisplayFormatOptions>,
): string {
  value = resolveLocalizedDisplayValue(value, options);
  if (isEmptyFieldValue(value)) return options.emptyText;
  if (typeof value === 'boolean') return value ? String(value) : options.emptyText;
  if (Array.isArray(value)) {
    if (!value.length) return options.emptyText;
    const relationalLabel = relationalTupleDisplayValue(value, options);
    if (relationalLabel !== null) return relationalLabel;
    const attachmentText = formatAttachmentReferenceValue(value);
    if (attachmentText && containsAttachmentReferenceIn(value)) return attachmentText;
    return value.map((item) => String(item)).join(', ');
  }
  if (typeof value === 'object') return options.emptyText;
  const rawText = stripInternalMigrationMetadata(String(value));
  if (!rawText) return options.emptyText;
  if (containsAttachmentReference(rawText)) {
    return formatAttachmentReferenceValue(rawText) || rawText;
  }
  return rawText;
}

export function formatDisplayValue(
  value: unknown,
  field?: DeclaredDisplayField,
  options?: DisplayFormatOptions,
): string {
  const normalized = normalizeOptions(options);
  return field
    ? formatDeclaredDisplayValue(value, field, normalized)
    : formatUndeclaredDisplayValue(value, normalized);
}
