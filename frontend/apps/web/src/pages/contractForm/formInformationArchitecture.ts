export type FormFieldSemanticMeta = {
  semantic_type?: string;
  surface_role?: string;
  technical?: boolean;
};

const INTERNAL_FIELD_NAMES = new Set([
  'active', 'create_uid', 'create_date', 'write_uid', 'write_date', '__last_update',
  'message_needaction', 'message_has_error', 'message_has_sms_error',
  'can_review', 'reviewer_ids', 'review_ids', 'next_review', 'need_validation',
  'validated', 'rejected', 'has_comment',
  'source_created_by', 'source_created_at', 'entry_user_id', 'entry_user_text',
  'entry_time', 'creator_name', 'created_time', 'archived',
]);
const INTERNAL_FIELD_PREFIXES = [
  'legacy_source_', 'carrier_', 'migration_', 'replay_', 'technical_', 'audit_',
];
const INTERNAL_SECTION_TOKENS = [
  '来源追溯', '来源信息', '录入与归档', '历史核对', '系统信息', '系统办理信息',
  'source trace', 'provenance', 'audit', 'technical',
];

export function isOrdinaryFormInternalField(name: string, semantic: FormFieldSemanticMeta = {}) {
  const normalized = String(name || '').trim().toLowerCase();
  if (!normalized) return true;
  if (semantic.technical || semantic.semantic_type === 'technical' || ['hidden', 'audit_only'].includes(String(semantic.surface_role || ''))) return true;
  return INTERNAL_FIELD_NAMES.has(normalized)
    || INTERNAL_FIELD_PREFIXES.some((prefix) => normalized.startsWith(prefix));
}

export function isReadonlyEmptyBusinessValue(value: unknown, fieldType = '') {
  if (value === null || value === undefined || value === '') return true;
  if (value === false) return String(fieldType || '').trim().toLowerCase() !== 'boolean';
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length === 0;
  return false;
}

export function isOrdinaryFormInternalSection(title: string) {
  const normalized = String(title || '').trim().toLowerCase();
  return Boolean(normalized) && INTERNAL_SECTION_TOKENS.some((token) => normalized.includes(token));
}
