import { resolveLocalizedDisplayValue } from '../../utils/display.ts';
import { resolveStatusTone } from '../../app/presentation/collectionStatusPresentation.ts';
import { presentDeclaredBusinessValue } from '../../app/presentation/businessValuePresentation.ts';
import {
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
  dataType?: string;
  componentKey?: string;
  widget?: string;
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
  } = input;
  const displayRaw = resolveLocalizedDisplayValue(raw, { emptyText });
  if (column.componentKey === 'sc.value.duration') {
    const presentation = presentDeclaredBusinessValue({
      field: {
        name: column.field,
        type: column.type,
        dataType: column.dataType,
        componentKey: column.componentKey,
        widget: column.widget,
        cellRole: column.cellRole,
      },
      value: displayRaw,
      emptyText,
      temporalProfile: 'compact',
    });
    return { text: presentation.text, tone: presentation.tone };
  }
  const temporalText = formatListTemporalValue(displayRaw, column);
  const fieldType = normalized(column.type).toLowerCase();
  const rawText = typeof displayRaw === 'string' ? displayRaw : '';
  const missing = displayRaw === null || displayRaw === undefined || displayRaw === '';
  let text: string;
  if (selectionText) text = selectionText;
  else if (missing) text = emptyText;
  else if ((displayRaw === false || rawText.trim() === FIELD_VALUE_EMPTY_TEXT) && numeric) text = emptyText;
  else if (typeof displayRaw === 'boolean') text = fieldType === 'boolean' ? (displayRaw ? trueText : falseText) : emptyText;
  else text = attachmentText || temporalText || numericText || String(displayRaw);
  // A status badge colour is a frontend presentation decision, resolved from
  // the authoritative status value rather than from the displayed label.
  const tone = isListStatusColumn(column) ? resolveStatusTone(raw) : 'neutral';
  return { text, tone };
}
