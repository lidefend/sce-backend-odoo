import { FIELD_VALUE_EMPTY_TEXT } from '../../utils/fieldSemantics';
import {
  presentDeclaredBusinessValue,
  resolveCurrencyDisplayLabel,
} from './businessValuePresentation';

export type CollectionKanbanFieldOption = {
  name: string;
  type?: string;
  dataType?: string;
  componentKey?: string;
  widget?: string;
  cellRole?: string;
  selection?: Array<{ value: string; label: string }>;
  digits?: [number, number];
  currencyField?: string;
};

export function presentCollectionKanbanCell(input: {
  field: string;
  value: unknown;
  row?: Record<string, unknown>;
  statusFields?: readonly string[];
  fieldSelections?: Record<string, Array<{ value: string; label: string }>>;
  columnOptions?: readonly CollectionKanbanFieldOption[];
}) {
  const option = (input.columnOptions || []).find((candidate) => candidate.name === input.field);
  const currencyField = String(option?.currencyField || '').trim();
  return presentDeclaredBusinessValue({
    field: {
      name: input.field,
      type: option?.type,
      dataType: option?.dataType,
      componentKey: option?.componentKey,
      widget: option?.widget,
      cellRole: option?.cellRole,
      selection: option?.selection || input.fieldSelections?.[input.field],
      digits: option?.digits,
      currencyField,
    },
    value: input.value,
    currencyLabel: currencyField
      ? resolveCurrencyDisplayLabel(input.row?.[currencyField])
      : '',
    emptyText: FIELD_VALUE_EMPTY_TEXT,
    status: (input.statusFields || []).includes(input.field),
    temporalProfile: 'compact',
  });
}
