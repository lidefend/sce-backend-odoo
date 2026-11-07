import type { FormSectionFieldSchema } from '../template/formSection.types';
import { FIELD_VALUE_EMPTY_TEXT } from '../../utils/fieldSemantics';
import { formatBusinessPercentage } from '../../app/presentation/businessValuePresentation';

export const PROFESSIONAL_BUSINESS_VALUE_KEYS = Object.freeze([
  'sc.value.money',
  'sc.value.percentage',
  'sc.display.status',
  'sc.value.duration',
] as const);

export type ProfessionalBusinessValueKey = typeof PROFESSIONAL_BUSINESS_VALUE_KEYS[number];

export type ProfessionalBusinessValueChoiceOption = {
  id?: string | number;
  value?: string | number;
  label: string;
};

const KEY_FIELD_TYPES: Readonly<Record<ProfessionalBusinessValueKey, readonly string[]>> = Object.freeze({
  'sc.value.money': Object.freeze(['monetary']),
  'sc.value.percentage': Object.freeze(['float', 'integer']),
  'sc.display.status': Object.freeze(['selection', 'char']),
  'sc.value.duration': Object.freeze(['float', 'integer']),
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

export function formatPercentage(value: unknown): string {
  return formatBusinessPercentage(value, FIELD_VALUE_EMPTY_TEXT);
}

export function formatDuration(value: unknown): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return FIELD_VALUE_EMPTY_TEXT;
  const hours = Math.trunc(numeric);
  const minutes = Math.round((numeric - hours) * 60);
  return minutes ? `${hours} 小时 ${minutes} 分钟` : `${hours} 小时`;
}
