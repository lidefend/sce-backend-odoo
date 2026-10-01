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
 * The transient search keyword exactly as the user typed it.
 *
 * This text is the controlled value of the official Select's search input, so
 * it must round-trip byte for byte. Normalizing it (for example trimming it)
 * while it is still being typed deletes the character the user just entered:
 * a fully controlled input whose stored keyword is trimmed turns the ``FE ``
 * keystroke into ``FE``, so the next ``P`` lands as ``FEP`` and
 * ``FE Project`` silently degrades to ``FEProject``. Normalization belongs to
 * `resolveProfessionalMany2oneQueryKey`, i.e. the point where the keyword stops
 * being typed text and becomes a request key.
 */
export function resolveProfessionalMany2oneQueryKeyword(
  field: Pick<FormSectionFieldSchema, 'relationQueryKeyword'>,
): string {
  return resolveProfessionalMany2oneSearchInput(field.relationQueryKeyword);
}

/** The typed search keyword, preserved exactly (presentation/interaction state). */
export function resolveProfessionalMany2oneSearchInput(keyword: unknown): string {
  return String(keyword ?? '');
}

/**
 * The search keyword as a request/comparison key. Only this projection is
 * trimmed; it is never fed back into the controlled input.
 */
export function resolveProfessionalMany2oneQueryKey(keyword: unknown): string {
  return String(keyword ?? '').trim();
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
