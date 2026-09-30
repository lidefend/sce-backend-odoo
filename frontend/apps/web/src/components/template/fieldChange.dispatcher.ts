import type { FormSectionFieldChange } from './formSection.types';

// Handlers receive the occurrence identity of the emitting control alongside
// the field name, so the record-form runtime can decide the edit for that
// position instead of for every position that shares the field code.
export type FieldChangeDispatcherHandlers = {
  onBoolean: (name: string, value: boolean, occurrenceKey: string) => void;
  onSelection: (name: string, value: string, occurrenceKey: string) => void;
  onMany2one: (name: string, descriptor: FormSectionFieldChange['descriptor'], value: string, occurrenceKey: string) => void;
  onText: (name: string, value: string, occurrenceKey: string) => void;
};

function normalizeText(value: string | number | boolean | null): string {
  if (value === null || value === undefined) return '';
  return String(value);
}

function normalizeBoolean(value: string | number | boolean | null): boolean {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number') return value !== 0;
  const normalized = String(value ?? '').trim().toLowerCase();
  return normalized === '1' || normalized === 'true' || normalized === 'yes' || normalized === 'on';
}

export function dispatchTemplateFieldChange(
  payload: FormSectionFieldChange,
  handlers: FieldChangeDispatcherHandlers,
): void {
  const fieldName = String(payload.name || '').trim();
  if (!fieldName) return;
  const occurrenceKey = String(payload.occurrenceKey || '').trim();
  const type = String(payload.type || '').trim().toLowerCase();
  if (type === 'many2one' && payload.action && payload.action !== 'change') {
    handlers.onMany2one(fieldName, payload.descriptor, normalizeText(payload.value), occurrenceKey);
    return;
  }
  switch (type) {
    case 'boolean': {
      handlers.onBoolean(fieldName, normalizeBoolean(payload.value), occurrenceKey);
      return;
    }
    case 'selection': {
      handlers.onSelection(fieldName, normalizeText(payload.value), occurrenceKey);
      return;
    }
    case 'many2one': {
      handlers.onMany2one(fieldName, payload.descriptor, normalizeText(payload.value), occurrenceKey);
      return;
    }
    case 'date':
    case 'datetime':
    case 'char':
    case 'text':
    default: {
      handlers.onText(fieldName, normalizeText(payload.value), occurrenceKey);
    }
  }
}
