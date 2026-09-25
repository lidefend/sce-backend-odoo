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

/**
 * Selected-record display text. Derives from the selected option first so a
 * transient search keyword can never be presented as the selected record.
 */
export function resolveProfessionalMany2oneDisplayValue(
  field: Pick<FormSectionFieldSchema, 'many2oneTextValue' | 'inputValue' | 'relationOptions'>,
): string {
  const value = resolveProfessionalMany2oneRecordValue(field);
  const option = value
    ? (field.relationOptions || [])
      .filter(Boolean)
      .find((item) => String(item.id ?? item.value) === value)
    : undefined;
  return String(option?.label || field.many2oneTextValue || '').trim();
}

/**
 * Transient search keyword owned by the relation runtime. This is an explicit
 * state channel; it is never a field value and never a display name.
 */
export function resolveProfessionalMany2oneQueryKeyword(
  field: Pick<FormSectionFieldSchema, 'relationQueryKeyword'>,
): string {
  return String(field.relationQueryKeyword ?? '').trim();
}

/** Selected relation record id projected as a plain string, `''` when unset. */
export function resolveProfessionalMany2oneRecordValue(
  field: Pick<FormSectionFieldSchema, 'inputValue'>,
): string {
  const raw = field.inputValue;
  if (raw === null || raw === undefined || raw === false) return '';
  const value = String(raw).trim();
  return value === 'false' ? '' : value;
}
