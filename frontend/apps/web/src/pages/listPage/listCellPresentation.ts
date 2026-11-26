import { resolveLocalizedDisplayValue } from '../../utils/display.ts';
import { presentDeclaredBusinessValue } from '../../app/presentation/businessValuePresentation.ts';
import { FIELD_VALUE_EMPTY_TEXT } from '../../utils/fieldSemantics.ts';

export type ListStatusTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

export type ColumnSemanticInput = {
  field: string;
  label: string;
  type?: string;
  dataType?: string;
  componentKey?: string;
  widget?: string;
  cellRole?: string;
  relation?: string;
  attachmentRole?: string;
  digits?: [number, number];
  currencyField?: string;
  currencyLabel?: string;
  selection?: Array<{ value: string; label: string }>;
};

export function resolveListDisplayField(
  field: string,
  option?: { displayField?: string } | null,
): string {
  return String(option?.displayField || field).trim() || field;
}

export function normalizeListRelationValue(
  displayValue: unknown,
  underlyingValue: unknown,
): unknown {
  if (
    displayValue === false
    || displayValue === null
    || displayValue === undefined
    || displayValue === 0
    || displayValue === '0'
  ) return displayValue;
  if (Array.isArray(displayValue)) return displayValue;
  if (
    displayValue
    && typeof displayValue === 'object'
    && !Array.isArray(displayValue)
    && 'id' in displayValue
  ) return displayValue;
  if (
    underlyingValue === false
    || underlyingValue === null
    || underlyingValue === undefined
    || underlyingValue === 0
    || underlyingValue === '0'
  ) {
    return displayValue;
  }
  return [underlyingValue, displayValue];
}

type CellPresentationInput = {
  raw: unknown;
  column: ColumnSemanticInput;
  relationItems?: Array<{ id: number; label: string }>;
  currencyLabel?: string;
  attachmentText?: string;
  emptyText?: string;
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
  return presentDeclaredBusinessValue({
    field: {
      name: input.field,
      type: input.type,
      dataType: input.dataType,
      componentKey: input.componentKey,
      widget: input.widget,
      cellRole: input.cellRole,
      digits: input.digits,
      selection: input.selection,
    },
    value,
    temporalProfile: 'compact',
  }).text;
}

export function isListStatusColumn(input: ColumnSemanticInput) {
  const role = normalized(input.cellRole).toLowerCase();
  return role === 'status';
}

export function isListBusinessIdentifierColumn(input: ColumnSemanticInput) {
  const role = normalized(input.cellRole).toLowerCase();
  return role === 'identity';
}

export function isListAttachmentCountColumn(input: ColumnSemanticInput) {
  return normalized(input.cellRole).toLowerCase() === 'attachment-count';
}

export function presentListCell(input: CellPresentationInput) {
  const {
    raw,
    column,
    relationItems = [],
    currencyLabel = '',
    attachmentText = '',
    emptyText = FIELD_VALUE_EMPTY_TEXT,
  } = input;
  const fieldType = normalized(column.type || column.dataType).toLowerCase();
  const relationValue = fieldType === 'many2many' && relationItems.length
    ? relationItems.map((item) => [item.id, item.label] as const)
    : raw;
  const value = ['many2one', 'many2many', 'one2many', 'json'].includes(fieldType)
    ? relationValue
    : resolveLocalizedDisplayValue(relationValue, { emptyText });
  const presentation = presentDeclaredBusinessValue({
    field: {
      name: column.field,
      type: column.type,
      dataType: column.dataType,
      componentKey: column.componentKey,
      widget: column.widget,
      cellRole: column.cellRole,
      selection: column.selection,
      digits: column.digits,
      currencyField: column.currencyField,
      currencyLabel: column.currencyLabel,
    },
    value,
    currencyLabel: currencyLabel || column.currencyLabel,
    emptyText,
    status: isListStatusColumn(column),
    temporalProfile: 'compact',
  });
  return {
    text: attachmentText || presentation.text,
    tone: presentation.tone,
  };
}
