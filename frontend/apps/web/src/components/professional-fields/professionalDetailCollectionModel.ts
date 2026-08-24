import type { FormSectionFieldSchema } from '../template/formSection.types';
import type { RelationFieldAdapter } from '../template/relationField.types';

export const PROFESSIONAL_DETAIL_COLLECTION_COMPONENT_KEY = 'sc.relation.table' as const;

export function isProfessionalDetailCollectionField(field: FormSectionFieldSchema): boolean {
  return field.componentKey === PROFESSIONAL_DETAIL_COLLECTION_COMPONENT_KEY
    && String(field.type || '').trim().toLowerCase() === 'one2many';
}

export function detailCollectionAuthority(field: FormSectionFieldSchema, adapter: RelationFieldAdapter) {
  if (!isProfessionalDetailCollectionField(field)) {
    throw new Error(`PROFESSIONAL_DETAIL_COLLECTION_UNSUPPORTED:${field.componentKey || '(missing)'}:${field.type || '(missing)'}`);
  }
  const rows = adapter.visibleOne2manyRows(field.name);
  const columns = adapter.one2manyColumns(field.name);
  return Object.freeze({
    componentKey: PROFESSIONAL_DETAIL_COLLECTION_COMPONENT_KEY,
    relationModel: String(field.descriptor?.relation || ''),
    rowCount: rows.length,
    columnCount: columns.length,
    canCreate: adapter.one2manyCanCreate(field.name),
    removedRowCount: adapter.removedOne2manyRows(field.name).length,
    validationVisible: adapter.showOne2manyErrors,
    summary: adapter.one2manySummary(field.name),
  });
}
