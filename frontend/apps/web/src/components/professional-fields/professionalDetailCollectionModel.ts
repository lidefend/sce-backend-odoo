import type { FormSectionFieldSchema } from '../template/formSection.types';
import type { RelationFieldAdapter } from '../template/relationField.types';
import type { RelationFieldColumn } from '../template/relationField.types';

export const PROFESSIONAL_DETAIL_COLLECTION_COMPONENT_KEY = 'sc.relation.table' as const;

export type OptionalDetailCollectionConfig = Readonly<{
  entryLabel: string;
  populatedLabel: string;
  directAmountMessage: string;
  linkedAmountMessage: string;
  lastRowRemovalActionLabel: string;
  lastRowRemovalMessage: string;
}>;

export type DetailAmountBindingConfig = Readonly<{
  mode: 'sum_when_nonempty';
  sourceField: string;
  targetField: string;
  activeField: string;
  stateField: string;
  rounding: 'currency';
  emptyBehavior: 'preserve_last_total';
}>;

export type OptionalDetailCollectionPresentation = Readonly<{
  render: boolean;
  open: boolean;
  title: string;
  linkedAmountMessage: string;
}>;

export type OptionalDetailCollectionRemovalConfirmation = Readonly<{
  actionLabel: string;
  message: string;
}>;

function text(value: unknown): string {
  return String(value || '').trim();
}

export function optionalDetailCollectionConfig(
  field: FormSectionFieldSchema,
): OptionalDetailCollectionConfig | null {
  const raw = field.componentConfig?.optionalDetails;
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const config = raw as Record<string, unknown>;
  const entryLabel = text(config.entryLabel);
  const populatedLabel = text(config.populatedLabel);
  if (!entryLabel || !populatedLabel) return null;
  return Object.freeze({
    entryLabel,
    populatedLabel,
    directAmountMessage: text(config.directAmountMessage),
    linkedAmountMessage: text(config.linkedAmountMessage),
    lastRowRemovalActionLabel: text(config.lastRowRemovalActionLabel),
    lastRowRemovalMessage: text(config.lastRowRemovalMessage),
  });
}

export function detailAmountBindingConfig(
  field: FormSectionFieldSchema,
): DetailAmountBindingConfig | null {
  const raw = field.componentConfig?.amountBinding;
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const config = raw as Record<string, unknown>;
  const sourceField = text(config.sourceField);
  const targetField = text(config.targetField);
  const activeField = text(config.activeField);
  const stateField = text(config.stateField);
  if (
    config.mode !== 'sum_when_nonempty'
    || config.rounding !== 'currency'
    || config.emptyBehavior !== 'preserve_last_total'
    || !sourceField
    || !targetField
    || !activeField
    || !stateField
    || sourceField === targetField
  ) return null;
  return Object.freeze({
    mode: config.mode,
    sourceField,
    targetField,
    activeField,
    stateField,
    rounding: config.rounding,
    emptyBehavior: config.emptyBehavior,
  });
}

export function optionalDetailCollectionPresentation(
  field: FormSectionFieldSchema,
  rowCount: number,
  amountUsesDetails = false,
  removedRowCount = 0,
): OptionalDetailCollectionPresentation | null {
  const config = optionalDetailCollectionConfig(field);
  if (!config) return null;
  const count = Math.max(0, Math.trunc(Number(rowCount) || 0));
  const pendingRemovalCount = Math.max(0, Math.trunc(Number(removedRowCount) || 0));
  return Object.freeze({
    render: field.readonly !== true || count > 0 || pendingRemovalCount > 0,
    open: count > 0 || pendingRemovalCount > 0,
    title: count > 0 ? `${config.populatedLabel}（${count} 条）` : config.entryLabel,
    linkedAmountMessage: amountUsesDetails
      ? config.linkedAmountMessage
      : config.directAmountMessage,
  });
}

export function optionalDetailCollectionRemovalConfirmation(
  field: FormSectionFieldSchema,
  rowCount: number,
): OptionalDetailCollectionRemovalConfirmation | null {
  const config = optionalDetailCollectionConfig(field);
  if (!config || Math.max(0, Math.trunc(Number(rowCount) || 0)) !== 1) return null;
  if (!config.lastRowRemovalActionLabel || !config.lastRowRemovalMessage) return null;
  return Object.freeze({
    actionLabel: config.lastRowRemovalActionLabel,
    message: config.lastRowRemovalMessage,
  });
}

export function optionalDetailCollectionSpanClass(
  field: FormSectionFieldSchema,
  configuredSpanClass: string,
): string {
  return optionalDetailCollectionConfig(field) ? 'field--full' : configuredSpanClass;
}

export function detailCollectionColumnPresentation(
  column: RelationFieldColumn,
  columnIndex: number,
  readonly: boolean,
) {
  const type = String(column.ttype || '').trim().toLowerCase();
  const amount = type === 'monetary';
  const relation = type === 'many2one';
  return Object.freeze({
    width: amount ? 140 : relation ? 260 : columnIndex === 0 ? 240 : undefined,
    align: amount ? 'right' as const : 'left' as const,
    ellipsis: readonly && ['char', 'text', 'many2one', 'selection'].includes(type),
  });
}

export function detailCollectionMobileColumnSplit(columns: RelationFieldColumn[]) {
  return Object.freeze({
    primary: Object.freeze(columns.slice(0, 6)),
    additional: Object.freeze(columns.slice(6)),
  });
}

export function isProfessionalDetailCollectionField(field: FormSectionFieldSchema): boolean {
  return field.componentKey === PROFESSIONAL_DETAIL_COLLECTION_COMPONENT_KEY
    && String(field.type || '').trim().toLowerCase() === 'one2many';
}

export function detailCollectionAuthority(field: FormSectionFieldSchema, adapter: RelationFieldAdapter) {
  if (!isProfessionalDetailCollectionField(field) && !optionalDetailCollectionConfig(field)) {
    throw new Error(`PROFESSIONAL_DETAIL_COLLECTION_UNSUPPORTED:${field.componentKey || '(missing)'}:${field.type || '(missing)'}`);
  }
  const rows = adapter.visibleOne2manyRows(field.name);
  const columns = adapter.one2manyColumns(field.name);
  return Object.freeze({
    componentKey: String(field.componentKey || PROFESSIONAL_DETAIL_COLLECTION_COMPONENT_KEY),
    relationModel: String(field.descriptor?.relation || ''),
    rowCount: rows.length,
    columnCount: columns.length,
    canCreate: adapter.one2manyCanCreate(field.name),
    canInlineEdit: adapter.one2manyCanInlineEdit(field.name),
    removedRowCount: adapter.removedOne2manyRows(field.name).length,
    validationVisible: adapter.showOne2manyErrors,
    summary: adapter.one2manySummary(field.name),
  });
}
