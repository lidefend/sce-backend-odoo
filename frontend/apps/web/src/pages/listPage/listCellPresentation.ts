import { resolveLocalizedDisplayValue } from '../../utils/display.ts';
import {
  COLLECTION_NUMERIC_EMPTY_TEXT,
  FIELD_VALUE_EMPTY_TEXT,
  FIELD_VALUE_FALSE_TEXT,
  FIELD_VALUE_TRUE_TEXT,
  formatTemporalFieldValue,
} from '../../utils/fieldSemantics.ts';

export type ListStatusTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

export type ColumnSemanticInput = {
  field: string;
  label: string;
  type?: string;
  cellRole?: string;
};

export function resolveListDisplayField(
  field: string,
  option?: { displayField?: string } | null,
): string {
  return String(option?.displayField || field).trim() || field;
}

type CellPresentationInput = {
  raw: unknown;
  column: ColumnSemanticInput;
  selectionText?: string;
  numericText?: string;
  attachmentText?: string;
  emptyText?: string;
  trueText?: string;
  falseText?: string;
  numeric?: boolean;
  toneByValue?: Record<string, ListStatusTone | string>;
};

function normalized(input: unknown) {
  return String(input ?? '').trim();
}

export function isListTemporalColumn(input: ColumnSemanticInput) {
  const type = normalized(input.type).toLowerCase();
  const role = normalized(input.cellRole).toLowerCase();
  return ['date', 'datetime'].includes(type)
    || ['date', 'datetime'].includes(role);
}

export function formatListTemporalValue(value: unknown, input: ColumnSemanticInput) {
  if (!isListTemporalColumn(input)) return '';
  return formatTemporalFieldValue(value, 'compact');
}

export function isListStatusColumn(input: ColumnSemanticInput) {
  const role = normalized(input.cellRole).toLowerCase();
  return role === 'status';
}

export function isListBusinessIdentifierColumn(input: ColumnSemanticInput) {
  const role = normalized(input.cellRole).toLowerCase();
  return role === 'identity';
}

export function presentListCell(input: CellPresentationInput) {
  const {
    raw,
    column,
    selectionText = '',
    numericText = '',
    attachmentText = '',
    emptyText = FIELD_VALUE_EMPTY_TEXT,
    trueText = FIELD_VALUE_TRUE_TEXT,
    falseText = FIELD_VALUE_FALSE_TEXT,
    numeric = false,
    toneByValue = {},
  } = input;
  const displayRaw = resolveLocalizedDisplayValue(raw, { emptyText });
  const temporalText = formatListTemporalValue(displayRaw, column);
  const fieldType = normalized(column.type).toLowerCase();
  const rawText = typeof displayRaw === 'string' ? displayRaw : '';
  const missing = displayRaw === null || displayRaw === undefined || displayRaw === '';
  let text: string;
  if (selectionText) text = selectionText;
  else if (missing) text = numeric ? COLLECTION_NUMERIC_EMPTY_TEXT : emptyText;
  else if ((displayRaw === false || rawText.trim() === FIELD_VALUE_EMPTY_TEXT) && numeric) text = COLLECTION_NUMERIC_EMPTY_TEXT;
  else if (typeof displayRaw === 'boolean') text = fieldType === 'boolean' ? (displayRaw ? trueText : falseText) : emptyText;
  else text = attachmentText || temporalText || numericText || String(displayRaw);
  const toneKey = normalized(displayRaw);
  const tone = isListStatusColumn(column)
    ? (toneByValue[toneKey] || 'neutral')
    : 'neutral';
  return { text, tone };
}
