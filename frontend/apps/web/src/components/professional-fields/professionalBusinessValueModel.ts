import type { FormSectionFieldSchema } from '../template/formSection.types';

export const PROFESSIONAL_BUSINESS_VALUE_KEYS = Object.freeze([
  'sc.value.money',
  'sc.value.currency',
  'sc.value.percentage',
  'sc.display.status',
  'sc.value.duration',
  'sc.value.user',
  'sc.value.company',
] as const);

export type ProfessionalBusinessValueKey = typeof PROFESSIONAL_BUSINESS_VALUE_KEYS[number];

export type ProfessionalBusinessValueChoiceOption = {
  id?: string | number;
  value?: string | number;
  label: string;
};

const KEY_FIELD_TYPES: Readonly<Record<ProfessionalBusinessValueKey, readonly string[]>> = Object.freeze({
  'sc.value.money': Object.freeze(['monetary']),
  'sc.value.currency': Object.freeze(['many2one']),
  'sc.value.percentage': Object.freeze(['float', 'integer']),
  'sc.display.status': Object.freeze(['selection', 'char']),
  'sc.value.duration': Object.freeze(['float', 'integer']),
  'sc.value.user': Object.freeze(['many2one']),
  'sc.value.company': Object.freeze(['many2one']),
});

export function isProfessionalBusinessValueField(field: FormSectionFieldSchema): boolean {
  const key = String(field.componentKey || '') as ProfessionalBusinessValueKey;
  const fieldType = String(field.type || '').trim().toLowerCase();
  return PROFESSIONAL_BUSINESS_VALUE_KEYS.includes(key)
    && Boolean(fieldType)
    && KEY_FIELD_TYPES[key].includes(fieldType);
}

export function businessValueKind(field: FormSectionFieldSchema): ProfessionalBusinessValueKey {
  if (!isProfessionalBusinessValueField(field)) {
    throw new Error(`PROFESSIONAL_BUSINESS_VALUE_UNSUPPORTED:${field.componentKey || '(missing)'}:${field.type || '(missing)'}`);
  }
  return field.componentKey as ProfessionalBusinessValueKey;
}

export function normalizeBusinessValueChoiceOptions(
  options: readonly ProfessionalBusinessValueChoiceOption[],
): Array<{ value: string; label: string }> {
  return options.filter(Boolean).map((option) => ({
    value: String(option.id ?? option.value ?? ''),
    label: option.label,
  }));
}

export function statusSemantic(value: unknown): 'default' | 'info' | 'success' | 'warning' | 'danger' {
  const normalized = String(value ?? '').trim().toLowerCase();
  if (['done', 'approved', 'paid', 'success', 'completed', 'closed'].includes(normalized)) return 'success';
  if (['rejected', 'cancel', 'cancelled', 'failed', 'error'].includes(normalized)) return 'danger';
  if (['pending', 'waiting', 'draft', 'warning'].includes(normalized)) return 'warning';
  return normalized ? 'info' : 'default';
}

export function formatPercentage(value: unknown): string {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${numeric.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}%` : '—';
}

export function formatDuration(value: unknown): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '—';
  const hours = Math.trunc(numeric);
  const minutes = Math.round((numeric - hours) * 60);
  return minutes ? `${hours} 小时 ${minutes} 分钟` : `${hours} 小时`;
}
