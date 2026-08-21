import type { SceneField, SceneUiKitId } from '@sc/ui/form';
import type { FormSectionFieldChange, FormSectionFieldSchema } from './formSection.types';

export function normalizeContractFormDriverValue(value: unknown, fieldType = ''): string {
  if (value === false || value === null || value === undefined) return '';
  const normalized = String(value);
  return ['date', 'datetime'].includes(String(fieldType || '').trim().toLowerCase())
    && normalized.trim().toLowerCase() === 'false'
    ? ''
    : normalized;
}

export function usesContractFormDriverField(field: FormSectionFieldSchema, kit: SceneUiKitId): boolean {
  if (kit === 'sc-native') return false;
  const type = String(field.type || '').trim().toLowerCase();
  const widget = String(field.widget || '').trim().toLowerCase();
  return ['char', 'text', 'date', 'selection'].includes(type) && widget !== 'radio' && widget !== 'daterange';
}

export function toContractFormSceneField(
  field: FormSectionFieldSchema,
  controlId: string,
  placeholder: string,
): SceneField {
  const type = String(field.type || '').trim().toLowerCase();
  const value = normalizeContractFormDriverValue(field.inputValue, type);
  return {
    id: controlId,
    label: field.label,
    value,
    kind: type === 'selection' ? 'select' : type === 'text' ? 'textarea' : type === 'date' ? 'date' : 'text',
    required: field.required,
    readonly: field.readonly,
    invalid: field.invalid,
    placeholder,
    options: (field.selectionOptions || []).map((option) => ({ key: String(option.value), label: option.label })),
  };
}

export function toContractFormDriverFieldChange(
  field: FormSectionFieldSchema,
  value: FormSectionFieldChange['value'],
): FormSectionFieldChange {
  return { occurrenceKey: field.key, name: field.name, type: field.type, widget: field.widget, value, descriptor: field.descriptor };
}
