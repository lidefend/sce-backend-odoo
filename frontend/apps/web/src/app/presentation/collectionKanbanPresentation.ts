import { FIELD_VALUE_EMPTY_TEXT } from '../../utils/fieldSemantics';
import { contractGapError } from '../contract/contractGap';
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

export function presentCollectionKanbanTitle(input: {
  titleField: string;
  value: unknown;
  columnOptions?: readonly CollectionKanbanFieldOption[];
}): string {
  const titleField = String(input.titleField || '').trim();
  if (!titleField) {
    throw contractGapError({
      kind: 'contract_defect',
      missing: 'kanban_profile.title_field',
      requiredDeclarationLayer: 'P0:smart_core:kanban_profile_projection',
    }, '看板缺少标题字段声明');
  }
  const option = (input.columnOptions || []).find((candidate) => candidate.name === titleField);
  if (!option || !String(option.type || option.dataType || '').trim()) {
    throw contractGapError({
      kind: 'contract_defect',
      missing: `kanban_profile.title_field.${titleField}.field_descriptor`,
      requiredDeclarationLayer: 'P0:smart_core:kanban_profile_projection',
    }, `看板标题字段 ${titleField} 缺少字段描述符`);
  }
  return presentCollectionKanbanCell({
    field: titleField,
    value: input.value,
    columnOptions: input.columnOptions,
  }).text;
}
