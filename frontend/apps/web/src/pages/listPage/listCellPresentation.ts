import { resolveLocalizedDisplayValue } from '../../utils/display';

export type ListStatusTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

export type ColumnSemanticInput = {
  field: string;
  label: string;
  type?: string;
  cellRole?: string;
};

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
  const text = normalized(value);
  if (!text || !isListTemporalColumn(input)) return '';
  const match = text.match(/^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?(?:Z|[+-]\d{2}:?\d{2})?$/);
  if (!match) return '';
  const [, date, hour = '00', minute = '00', second = '00'] = match;
  if (`${hour}:${minute}:${second}` === '00:00:00') return date;
  return `${date} ${hour}:${minute}`;
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
    emptyText = '--',
    trueText = '是',
    falseText = '否',
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
  else if (missing) text = numeric ? '0' : emptyText;
  else if ((displayRaw === false || rawText.trim() === '--') && numeric) text = '0';
  else if (typeof displayRaw === 'boolean') text = fieldType === 'boolean' ? (displayRaw ? trueText : falseText) : emptyText;
  else text = attachmentText || temporalText || numericText || String(displayRaw);
  const toneKey = normalized(displayRaw);
  const tone = isListStatusColumn(column)
    ? (toneByValue[toneKey] || 'neutral')
    : 'neutral';
  return { text, tone };
}
