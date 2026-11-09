import { contractGapError } from '../contract/contractGap';
import {
  FIELD_VALUE_EMPTY_TEXT,
  FIELD_VALUE_FALSE_TEXT,
  FIELD_VALUE_TRUE_TEXT,
  formatTemporalFieldValue,
  isEmptyFieldValue,
  normalizeFieldType,
  numericFieldValue,
} from '../../utils/fieldSemantics';
import {
  resolveCollectionStatusPresentation,
  type CollectionStatusTone,
} from './collectionStatusPresentation';

export type BusinessValueSemantic =
  | 'money'
  | 'percentage'
  | 'duration'
  | 'status'
  | 'date'
  | 'datetime'
  | 'selection'
  | 'boolean'
  | 'empty'
  | 'plain';

export type BusinessValueSelection = Array<
  { value: string | number; label: string } | readonly [string, string]
>;

export type DeclaredBusinessField = {
  name?: string;
  type?: string;
  ttype?: string;
  componentKey?: string;
  dataType?: string;
  widget?: string;
  cellRole?: string;
  selection?: BusinessValueSelection;
  digits?: [number, number];
  currencyField?: string;
  currencyLabel?: string;
};

export type DeclaredBusinessValuePresentation = {
  kind: BusinessValueSemantic;
  text: string;
  tone: CollectionStatusTone;
  badgeSemantic: 'default' | 'info' | 'success' | 'warning' | 'danger';
};

export function toneToBadgeSemantic(
  tone: CollectionStatusTone,
): 'default' | 'info' | 'success' | 'warning' | 'danger' {
  return tone === 'neutral' ? 'default' : tone;
}

export function statusBadgeSemantic(value: unknown): 'default' | 'info' | 'success' | 'warning' | 'danger' {
  return toneToBadgeSemantic(resolveCollectionStatusPresentation({ value }).tone);
}

export function normalizeMonetaryDigits(value: unknown): [number, number] | undefined {
  if (!Array.isArray(value) || value.length !== 2) return undefined;
  const precision = Number(value[0]);
  const scale = Number(value[1]);
  if (!Number.isInteger(precision) || !Number.isInteger(scale) || precision <= 0 || scale < 0 || scale > 20 || scale > precision) {
    return undefined;
  }
  return [precision, scale];
}

export function resolveCurrencyDisplayLabel(value: unknown): string {
  if (Array.isArray(value)) return String(value[1] || '').trim();
  if (value && typeof value === 'object') {
    const row = value as Record<string, unknown>;
    return String(row.name || row.display_name || row.symbol || '').trim();
  }
  return typeof value === 'string' ? value.trim() : '';
}

export function resolveMonetaryScale(digits?: [number, number], currencyLabel = ''): number | undefined {
  if (digits) return digits[1];
  const currencyCode = /^[A-Z]{3}$/.test(currencyLabel) ? currencyLabel : '';
  if (!currencyCode) return undefined;
  try {
    return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: currencyCode })
      .resolvedOptions().maximumFractionDigits;
  } catch {
    return undefined;
  }
}

export function monetaryInputStep(digits?: [number, number], currencyLabel = ''): string {
  const scale = resolveMonetaryScale(digits, currencyLabel);
  if (!Number.isInteger(scale)) return 'any';
  return scale === 0 ? '1' : `0.${'0'.repeat(Math.max(0, scale - 1))}1`;
}

export function formatMonetaryInputValue(
  value: unknown,
  digits?: [number, number],
  currencyLabel = '',
): string | number {
  if (value === null || value === undefined || value === '') return '';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  const scale = resolveMonetaryScale(digits, currencyLabel);
  return Number.isInteger(scale) ? numeric.toFixed(scale) : value as string | number;
}

export function formatMonetaryDisplayValue(
  value: unknown,
  digits?: [number, number],
  currencyLabel = '',
  locale = 'zh-CN',
  emptyText = FIELD_VALUE_EMPTY_TEXT,
): string {
  if (value === null || value === undefined || value === false || value === '') return emptyText;
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return emptyText;
  const scale = resolveMonetaryScale(digits, currencyLabel);
  const options: Intl.NumberFormatOptions = Number.isInteger(scale)
    ? { minimumFractionDigits: scale, maximumFractionDigits: scale }
    : {};
  const currencyCode = /^[A-Z]{3}$/.test(currencyLabel) ? currencyLabel : '';
  if (currencyCode) {
    return new Intl.NumberFormat(locale, { ...options, style: 'currency', currency: currencyCode }).format(numeric);
  }
  const formatted = new Intl.NumberFormat(locale, options).format(numeric);
  return currencyLabel ? `${formatted} ${currencyLabel}` : formatted;
}

export function formatBusinessPercentage(value: unknown, emptyText = FIELD_VALUE_EMPTY_TEXT): string {
  const numeric = numericFieldValue(value);
  if (numeric === null) return emptyText;
  return `${new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(numeric)}%`;
}

/**
 * Format an Odoo float_time value with the platform's Chinese business copy.
 *
 * Rounding and carry follow Odoo 17's authoritative `formatFloatTime`:
 * - false/null/undefined are empty, never numeric zero;
 * - minutes use the rounded millisecond remainder;
 * - a rounded 60th minute carries into the next hour;
 * - the sign belongs to the whole duration.
 *
 * The contract's `float_time` widget selects this semantic. No frontend-only
 * precision declaration is introduced.
 */
export function formatBusinessDuration(
  value: unknown,
  emptyText = FIELD_VALUE_EMPTY_TEXT,
): string {
  if (value === false || value === null || value === undefined || value === '') return emptyText;
  const numeric = numericFieldValue(value);
  if (numeric === null) return emptyText;
  const negative = numeric < 0;
  const absolute = Math.abs(numeric);
  let hours = Math.floor(absolute);
  const milliSecondsWithinHour = Math.round(absolute * 3_600_000) - hours * 3_600_000;
  let minutes = Math.round(milliSecondsWithinHour / 60_000);
  if (minutes === 60) {
    hours += 1;
    minutes = 0;
  }
  const sign = negative ? '-' : '';
  if (hours === 0 && minutes === 0) return '0 小时';
  if (hours === 0) return `${sign}${minutes} 分钟`;
  if (minutes === 0) return `${sign}${hours} 小时`;
  return `${sign}${hours} 小时 ${minutes} 分钟`;
}

function normalizedSelection(field: DeclaredBusinessField): Array<{ value: string; label: string }> {
  if (!Array.isArray(field.selection)) return [];
  return field.selection.flatMap((item) => {
    if (Array.isArray(item) && item.length >= 2) {
      const value = String(item[0] ?? '').trim();
      const label = String(item[1] ?? '').trim();
      return value && label ? [{ value, label }] : [];
    }
    if (item && typeof item === 'object' && !Array.isArray(item)) {
      const objectItem = item as { value?: unknown; label?: unknown };
      const value = String(objectItem.value ?? '').trim();
      const label = String(objectItem.label ?? '').trim();
      return value && label ? [{ value, label }] : [];
    }
    return [];
  });
}

function selectionValue(value: unknown): string {
  if (Array.isArray(value)) return String(value[0] ?? '').trim();
  return String(value ?? '').trim();
}

function resolveDeclaredStatusContract(field: DeclaredBusinessField): {
  statusType: 'selection' | 'char';
  selection: Array<{ value: string; label: string }>;
} {
  const statusType = declaredBusinessFieldType(field);
  if (statusType !== 'selection' && statusType !== 'char') {
    throw contractGapError({
      kind: 'contract_defect',
      missing: `field.${field.name || '(unknown)'}.status.type`,
      requiredDeclarationLayer: 'P0:smart_core:field_type',
    }, `状态字段 ${field.name || field.componentKey || '(unknown)'} 缺少 selection 或 char 类型声明`);
  }
  const selection = normalizedSelection(field);
  if (statusType === 'selection' && !selection.length) {
    throw contractGapError({
      kind: 'contract_defect',
      missing: `field.${field.name || '(unknown)'}.selection`,
      requiredDeclarationLayer: 'P0:smart_core:field_selection_projection',
    }, `状态字段 ${field.name || field.componentKey || '(unknown)'} 缺少有效选择项投影`);
  }
  return { statusType, selection };
}

function declaredBusinessFieldType(field: DeclaredBusinessField): ReturnType<typeof normalizeFieldType> {
  const nativeType = normalizeFieldType(field);
  if (nativeType !== 'unknown') return nativeType;
  return normalizeFieldType(String(field.dataType || ''));
}

export function declaredBusinessValueKind(
  field: DeclaredBusinessField,
  status = false,
): BusinessValueSemantic {
  const type = declaredBusinessFieldType(field);
  const componentKey = String(field.componentKey || '').trim();
  const cellRole = String(field.cellRole || '').trim().toLowerCase();
  if (componentKey === 'sc.value.money' || type === 'monetary') return 'money';
  if (componentKey === 'sc.value.percentage') return 'percentage';
  if (componentKey === 'sc.value.duration' || String(field.widget || '').trim().toLowerCase() === 'float_time') return 'duration';
  if (status || componentKey === 'sc.display.status' || cellRole === 'status') return 'status';
  if (type === 'date') return 'date';
  if (type === 'datetime') return 'datetime';
  if (type === 'selection' || normalizedSelection(field).length) return 'selection';
  if (type === 'boolean') return 'boolean';
  return 'plain';
}

export function presentDeclaredBusinessValue(input: {
  field: DeclaredBusinessField;
  value: unknown;
  currencyLabel?: string;
  emptyText?: string;
  status?: boolean;
  temporalProfile?: 'compact' | 'full';
}): DeclaredBusinessValuePresentation {
  const emptyText = input.emptyText ?? FIELD_VALUE_EMPTY_TEXT;
  const kind = declaredBusinessValueKind(input.field, input.status);
  const statusContract = kind === 'status'
    ? resolveDeclaredStatusContract(input.field)
    : null;
  if (isEmptyFieldValue(input.value)) {
    return Object.freeze({ kind: 'empty', text: emptyText, tone: 'neutral', badgeSemantic: 'default' });
  }
  if (kind === 'money') {
    const text = formatMonetaryDisplayValue(
      input.value,
      input.field.digits,
      input.currencyLabel || input.field.currencyLabel || '',
      'zh-CN',
      emptyText,
    );
    return Object.freeze({
      kind: text === emptyText ? 'empty' : 'money',
      text,
      tone: 'neutral',
      badgeSemantic: 'default',
    });
  }
  if (kind === 'percentage') {
    return Object.freeze({
      kind: 'percentage',
      text: formatBusinessPercentage(input.value, emptyText),
      tone: 'neutral',
      badgeSemantic: 'default',
    });
  }
  if (kind === 'duration') {
    const text = formatBusinessDuration(input.value, emptyText);
    return Object.freeze({
      kind: text === emptyText ? 'empty' : 'duration',
      text,
      tone: 'neutral',
      badgeSemantic: 'default',
    });
  }
  if (kind === 'status') {
    const key = selectionValue(input.value);
    const selection = statusContract?.selection ?? [];
    const presentation = resolveCollectionStatusPresentation({
      value: input.value,
      ...(selection.length ? { selection } : {}),
    });
    if (selection.length && !selection.some((item) => item.value === key)) {
      throw contractGapError({
        kind: 'contract_defect',
        missing: `field.${input.field.name || '(unknown)'}.selection`,
        requiredDeclarationLayer: 'P0:smart_core:field_selection_projection',
      }, `状态字段 ${input.field.name || input.field.componentKey || '(unknown)'} 的记录值缺少有效选择项标签`);
    }
    return Object.freeze({
      kind: 'status',
      text: presentation.label,
      tone: presentation.tone,
      badgeSemantic: toneToBadgeSemantic(presentation.tone),
    });
  }
  if (kind === 'date' || kind === 'datetime') {
    const temporalText = formatTemporalFieldValue(
      input.value,
      input.temporalProfile || (kind === 'date' ? 'compact' : 'full'),
    );
    const text = kind === 'date' ? temporalText.split(' ', 1)[0] : temporalText;
    return Object.freeze({
      kind: text ? kind : 'empty',
      text: text || emptyText,
      tone: 'neutral',
      badgeSemantic: 'default',
    });
  }
  if (kind === 'selection') {
    const key = selectionValue(input.value);
    const selection = normalizedSelection(input.field);
    const label = selection.find((item) => item.value === key)?.label;
    if (!label) {
      throw contractGapError({
        kind: 'contract_defect',
        missing: `field.${input.field.name || '(unknown)'}.selection`,
        requiredDeclarationLayer: 'P0:smart_core:field_selection_projection',
      }, `字段 ${input.field.name || '(unknown)'} 的记录值缺少有效选择项标签`);
    }
    return Object.freeze({ kind: 'selection', text: label, tone: 'neutral', badgeSemantic: 'default' });
  }
  if (kind === 'boolean') {
    return Object.freeze({
      kind: 'boolean',
      text: input.value ? FIELD_VALUE_TRUE_TEXT : FIELD_VALUE_FALSE_TEXT,
      tone: 'neutral',
      badgeSemantic: 'default',
    });
  }
  if (Array.isArray(input.value)) {
    if (input.value.length > 1 && input.value[1] !== null && input.value[1] !== undefined) {
      return Object.freeze({ kind: 'plain', text: String(input.value[1]), tone: 'neutral', badgeSemantic: 'default' });
    }
    return Object.freeze({
      kind: input.value.length ? 'plain' : 'empty',
      text: input.value.length ? String(input.value[0] ?? emptyText) : emptyText,
      tone: 'neutral',
      badgeSemantic: 'default',
    });
  }
  if (typeof input.value === 'object') {
    const row = input.value as Record<string, unknown>;
    const text = String(row.display_name || row.label || row.name || '').trim();
    return Object.freeze({
      kind: text ? 'plain' : 'empty',
      text: text || emptyText,
      tone: 'neutral',
      badgeSemantic: 'default',
    });
  }
  return Object.freeze({
    kind: 'plain',
    text: String(input.value),
    tone: 'neutral',
    badgeSemantic: 'default',
  });
}
