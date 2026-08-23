import type { FieldDescriptor } from '@sc/schema';
import type { FormSectionFieldSchema, TemplateSelectOption } from './formSection.types';

export type ResolveTemplateInputValueOptions = {
  fieldName: string;
  fieldType: string;
  rawValue: unknown;
  resolveMany2oneValue: (fieldName: string) => string;
  normalizeDateInputValue: (value: unknown) => string;
  normalizeDatetimeInputValue: (value: unknown) => string;
  resolveTextInputValue: (fieldName: string) => string;
};

export type FormSectionMapperFieldNode = {
  key: string;
  name: string;
  label: string;
  widget?: string;
  widgetSemantics?: Record<string, unknown>;
  required: boolean;
  readonly: boolean;
  descriptor?: FieldDescriptor;
};

export type BuildFormSectionFieldSchemasOptions = {
  resolveFieldType: (descriptor?: FieldDescriptor) => string;
  resolveRequired: (field: FormSectionMapperFieldNode) => boolean;
  resolveSpanClass: (field: FormSectionMapperFieldNode) => string;
  resolveInputValue: (fieldName: string, fieldType: string) => string | number | boolean | null;
  resolveRawValue: (fieldName: string) => unknown;
  resolveInputPlaceholder: (fieldLabel: string) => string;
  resolveHelpText?: (field: FormSectionMapperFieldNode) => string;
  resolveErrorText?: (field: FormSectionMapperFieldNode) => string;
  resolveSelectionOptions: (descriptor?: FieldDescriptor) => TemplateSelectOption[];
  resolveRelationOptions: (fieldName: string) => TemplateSelectOption[];
  resolveRelationCreateMode: (fieldName: string, descriptor?: FieldDescriptor) => 'none' | 'quick' | 'page' | 'dialog';
  resolveRelationInlineCreate: (fieldName: string, descriptor?: FieldDescriptor) => FormSectionFieldSchema['relationInlineCreate'];
  resolveRelationTextValue: (fieldName: string) => string;
  resolveCanOpenRelationRecord: (fieldName: string, descriptor?: FieldDescriptor) => boolean;
  resolveRelationRecordOpenLabel: (fieldName: string, descriptor?: FieldDescriptor) => string;
  resolveRelationSearchLabel: (fieldName: string, descriptor?: FieldDescriptor) => string;
  resolveRelationCreateLabel: (fieldName: string, descriptor?: FieldDescriptor) => string;
  resolveRelationInlineCreateLabel: (fieldName: string, descriptor?: FieldDescriptor, keyword?: string) => string;
  many2oneCreateToken?: string;
  many2oneSearchToken?: string;
  many2oneOpenToken?: string;
};

type Many2oneCapabilityProjectionOptions = {
  fieldName: string;
  descriptor?: FieldDescriptor;
  resolveRelationCreateMode: BuildFormSectionFieldSchemasOptions['resolveRelationCreateMode'];
  resolveRelationInlineCreate: BuildFormSectionFieldSchemasOptions['resolveRelationInlineCreate'];
  resolveCanOpenRelationRecord: BuildFormSectionFieldSchemasOptions['resolveCanOpenRelationRecord'];
  resolveRelationRecordOpenLabel: BuildFormSectionFieldSchemasOptions['resolveRelationRecordOpenLabel'];
  resolveRelationSearchLabel: BuildFormSectionFieldSchemasOptions['resolveRelationSearchLabel'];
  resolveRelationCreateLabel: BuildFormSectionFieldSchemasOptions['resolveRelationCreateLabel'];
  resolveRelationInlineCreateLabel: BuildFormSectionFieldSchemasOptions['resolveRelationInlineCreateLabel'];
  relationTextValue: string;
  many2oneCreateToken?: string;
  many2oneSearchToken?: string;
  many2oneOpenToken?: string;
};

export function projectMany2oneCapabilities(
  options: Many2oneCapabilityProjectionOptions,
): Pick<FormSectionFieldSchema,
  | 'relationCreateMode'
  | 'relationInlineCreate'
  | 'many2oneCreateToken'
  | 'many2oneSearchToken'
  | 'many2oneOpenToken'
  | 'many2oneOpenLabel'
  | 'many2oneSearchLabel'
  | 'many2oneCreateLabel'
  | 'many2oneInlineCreateLabel'
> {
  const { fieldName, descriptor } = options;
  return {
    relationCreateMode: options.resolveRelationCreateMode(fieldName, descriptor),
    relationInlineCreate: options.resolveRelationInlineCreate(fieldName, descriptor),
    many2oneCreateToken: options.many2oneCreateToken,
    many2oneSearchToken: options.many2oneSearchToken,
    many2oneOpenToken: options.resolveCanOpenRelationRecord(fieldName, descriptor)
      ? options.many2oneOpenToken
      : undefined,
    many2oneOpenLabel: options.resolveRelationRecordOpenLabel(fieldName, descriptor),
    many2oneSearchLabel: options.resolveRelationSearchLabel(fieldName, descriptor),
    many2oneCreateLabel: options.resolveRelationCreateLabel(fieldName, descriptor),
    many2oneInlineCreateLabel: options.resolveRelationInlineCreateLabel(
      fieldName,
      descriptor,
      options.relationTextValue,
    ),
  };
}

export function normalizeMonetaryDigits(value: unknown): [number, number] | undefined {
  if (!Array.isArray(value) || value.length !== 2) return undefined;
  const precision = Number(value[0]);
  const scale = Number(value[1]);
  if (!Number.isInteger(precision) || !Number.isInteger(scale) || precision <= 0 || scale < 0 || scale > 20 || scale > precision) {
    return undefined;
  }
  return [precision, scale];
}

export function resolveCurrencyDisplayLabel(value: unknown): string {
  if (Array.isArray(value)) return String(value[1] || '').trim();
  if (value && typeof value === 'object') {
    const row = value as Record<string, unknown>;
    return String(row.name || row.display_name || row.symbol || '').trim();
  }
  return typeof value === 'string' ? value.trim() : '';
}

export function monetaryInputStep(digits?: [number, number]): string {
  if (!digits) return 'any';
  const scale = digits[1];
  return scale === 0 ? '1' : `0.${'0'.repeat(Math.max(0, scale - 1))}1`;
}

export function formatMonetaryDisplayValue(
  value: unknown,
  digits?: [number, number],
  currencyLabel = '',
  locale?: string,
): string {
  if (value === null || value === undefined || value === false || value === '') return '-';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '-';
  const scale = digits?.[1];
  const options: Intl.NumberFormatOptions = Number.isInteger(scale)
    ? { minimumFractionDigits: scale, maximumFractionDigits: scale }
    : {};
  const currencyCode = /^[A-Z]{3}$/.test(currencyLabel) ? currencyLabel : '';
  if (currencyCode) {
    return new Intl.NumberFormat(locale, { ...options, style: 'currency', currency: currencyCode }).format(numeric);
  }
  const formatted = new Intl.NumberFormat(locale, options).format(numeric);
  return currencyLabel ? `${formatted} ${currencyLabel}` : formatted;
}

export function buildFormSectionFieldSchemas(
  fields: FormSectionMapperFieldNode[],
  options: BuildFormSectionFieldSchemasOptions,
): FormSectionFieldSchema[] {
  return fields.map((field) => {
    const type = options.resolveFieldType(field.descriptor) || 'char';
    const descriptor = (field.descriptor || {}) as Record<string, unknown>;
    const digits = type === 'monetary' ? normalizeMonetaryDigits(descriptor.digits) : undefined;
    const currencyField = type === 'monetary'
      ? String(descriptor.currency_field || 'currency_id').trim()
      : '';
    const currencyLabel = currencyField ? resolveCurrencyDisplayLabel(options.resolveRawValue(currencyField)) : '';
    const descriptorWidget = field.descriptor && typeof field.descriptor === 'object'
      ? String((field.descriptor as Record<string, unknown>).widget || '').trim()
      : '';
    const widget = String(field.widget || descriptorWidget || '').trim().toLowerCase();
    const semantics = field.widgetSemantics && typeof field.widgetSemantics === 'object' ? field.widgetSemantics : {};
    const dateRangeEndField = widget === 'daterange' && String(semantics.kind || '').trim() === 'date_range'
      ? String(semantics.end_field || '').trim()
      : '';
    const helpText = options.resolveHelpText?.(field) || '';
    const errorText = options.resolveErrorText?.(field) || '';
    const relationTextValue = type === 'many2one' ? options.resolveRelationTextValue(field.name) : '';
    const many2oneCapabilities = type === 'many2one'
      ? projectMany2oneCapabilities({
        fieldName: field.name,
        descriptor: field.descriptor,
        resolveRelationCreateMode: options.resolveRelationCreateMode,
        resolveRelationInlineCreate: options.resolveRelationInlineCreate,
        resolveCanOpenRelationRecord: options.resolveCanOpenRelationRecord,
        resolveRelationRecordOpenLabel: options.resolveRelationRecordOpenLabel,
        resolveRelationSearchLabel: options.resolveRelationSearchLabel,
        resolveRelationCreateLabel: options.resolveRelationCreateLabel,
        resolveRelationInlineCreateLabel: options.resolveRelationInlineCreateLabel,
        relationTextValue,
        many2oneCreateToken: options.many2oneCreateToken,
        many2oneSearchToken: options.many2oneSearchToken,
        many2oneOpenToken: options.many2oneOpenToken,
      })
      : { relationCreateMode: 'none' as const };
    return {
      key: field.key,
      name: field.name,
      label: field.label,
      type,
      widget,
      widgetSemantics: semantics,
      digits,
      currencyField: currencyField || undefined,
      currencyLabel: currencyLabel || undefined,
      required: options.resolveRequired(field),
      readonly: field.readonly,
      invalid: Boolean(errorText),
      helpText: helpText || undefined,
      errorText: errorText || undefined,
      spanClass: options.resolveSpanClass(field),
      value: options.resolveRawValue(field.name),
      inputValue: options.resolveInputValue(field.name, type),
      dateRangeEndField: dateRangeEndField || undefined,
      dateRangeEndInputValue: dateRangeEndField ? options.resolveInputValue(dateRangeEndField, type) : undefined,
      inputPlaceholder: options.resolveInputPlaceholder(field.label),
      selectionOptions: options.resolveSelectionOptions(field.descriptor),
      relationOptions: options.resolveRelationOptions(field.name),
      ...many2oneCapabilities,
      many2oneTextValue: relationTextValue || undefined,
      descriptor: field.descriptor,
    };
  });
}

export function resolveTemplateInputValue(options: ResolveTemplateInputValueOptions): string | number | boolean | null {
  const type = String(options.fieldType || '').trim().toLowerCase();
  if (type === 'many2one') {
    return options.resolveMany2oneValue(options.fieldName);
  }
  const raw = options.rawValue;
  if (raw === null || raw === undefined || raw === false) {
    return '';
  }
  if (type === 'date') {
    return options.normalizeDateInputValue(raw);
  }
  if (type === 'datetime') {
    return options.normalizeDatetimeInputValue(raw);
  }
  if (typeof raw === 'number' || typeof raw === 'boolean') {
    return raw;
  }
  return options.resolveTextInputValue(options.fieldName);
}
