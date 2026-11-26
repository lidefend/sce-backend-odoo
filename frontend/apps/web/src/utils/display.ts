import {
  ATTACHMENT_REFERENCE_URL_SOURCE,
  FIELD_VALUE_EMPTY_TEXT,
  FIELD_VALUE_FALSE_TEXT,
  FIELD_VALUE_TRUE_TEXT,
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
import { contractGapError } from '../app/contract/contractGap.ts';

export { resolveLocalizedDisplayValue };

export type DisplayFormatOptions = LocalizedDisplayOptions & {
  booleanTrueText?: string;
  booleanFalseText?: string;
  currencyLabel?: string;
  timeZone?: string;
};

const DEFAULT_OPTIONS: Required<DisplayFormatOptions> = {
  emptyText: FIELD_VALUE_EMPTY_TEXT,
  booleanTrueText: FIELD_VALUE_TRUE_TEXT,
  booleanFalseText: FIELD_VALUE_FALSE_TEXT,
  locale: '',
  fallbackLocales: ['zh_CN', 'en_US'],
  currencyLabel: '',
  timeZone: '',
};

function normalizeOptions(options?: DisplayFormatOptions): Required<DisplayFormatOptions> {
  return {
    emptyText: options?.emptyText ?? DEFAULT_OPTIONS.emptyText,
    booleanTrueText: options?.booleanTrueText ?? DEFAULT_OPTIONS.booleanTrueText,
    booleanFalseText: options?.booleanFalseText ?? DEFAULT_OPTIONS.booleanFalseText,
    locale: options?.locale ?? DEFAULT_OPTIONS.locale,
    fallbackLocales: options?.fallbackLocales ?? DEFAULT_OPTIONS.fallbackLocales,
    currencyLabel: options?.currencyLabel ?? DEFAULT_OPTIONS.currencyLabel,
    timeZone: options?.timeZone ?? DEFAULT_OPTIONS.timeZone,
  };
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
      temporal: field.temporal,
      currencyField: field.currencyField || field.currency_field,
      currencyLabel: field.currencyLabel,
      relation: field.relation,
    },
    value: normalizedValue,
    currencyLabel: options.currencyLabel,
    emptyText: options.emptyText,
    temporalProfile: 'full',
    timeZone: options.timeZone,
    locale: options.locale,
    fallbackLocales: options.fallbackLocales,
  });
  if (presentation.kind === 'plain') {
    const text = stripInternalMigrationMetadata(presentation.text);
    return text || options.emptyText;
  }
  return presentation.text;
}

export function formatDisplayValue(
  value: unknown,
  field?: DeclaredDisplayField,
  options?: DisplayFormatOptions,
): string {
  const normalized = normalizeOptions(options);
  if (!field) {
    throw contractGapError({
      kind: 'contract_defect',
      missing: 'fieldDescriptor',
      requiredDeclarationLayer: 'P0:smart_core:field_descriptor_projection',
    }, '业务值缺少字段描述符，前端不得按值外形推断格式');
  }
  return formatDeclaredDisplayValue(value, field, normalized);
}
