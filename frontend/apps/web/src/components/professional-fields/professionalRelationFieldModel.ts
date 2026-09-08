import type { FormSectionFieldSchema } from '../template/formSection.types';

export const PROFESSIONAL_RELATION_COMPONENT_KEYS = Object.freeze([
  'sc.relation.many2one',
  'sc.relation.many2many',
  'sc.select.tags',
] as const);

export function isProfessionalRelationField(field: FormSectionFieldSchema): boolean {
  const key = String(field.componentKey || '');
  const type = String(field.type || '').trim().toLowerCase();
  // 如果字段类型是many2one，直接返回true，不依赖componentKey
  if (type === 'many2one') return true;
  if (!PROFESSIONAL_RELATION_COMPONENT_KEYS.includes(key as never)) return false;
  if (key === 'sc.relation.many2one') return type === 'many2one';
  return type === 'many2many';
}

export function relationFieldAuthority(field: FormSectionFieldSchema) {
  if (!isProfessionalRelationField(field)) {
    throw new Error(`PROFESSIONAL_RELATION_FIELD_UNSUPPORTED:${field.componentKey || '(missing)'}:${field.type || '(missing)'}`);
  }
  return Object.freeze({
    componentKey: String(field.componentKey),
    relationType: String(field.type),
    relationModel: String(field.descriptor?.relation || ''),
    createMode: field.relationCreateMode || 'none',
    canOpenRecord: Boolean(field.many2oneOpenToken),
    canSearch: Boolean(field.many2oneSearchToken),
    canCreate: Boolean(field.many2oneCreateToken || field.relationInlineCreate),
  });
}

export function resolveProfessionalMany2oneTextValue(
  field: Pick<FormSectionFieldSchema, 'many2oneTextValue' | 'inputValue' | 'relationOptions'>,
): string {
  const projected = String(field.many2oneTextValue ?? '').trim();
  if (projected) return projected;
  const value = String(field.inputValue ?? '').trim();
  if (!value) return '';
  const option = (field.relationOptions || [])
    .filter(Boolean)
    .find((item) => String(item.id ?? item.value) === value);
  return String(option?.label || '').trim();
}
