import type { FieldDescriptor } from '@sc/schema';
import type { CanonicalFormField, CanonicalFormNode, CanonicalRelationValue } from '../../app/presentation/canonicalFormRenderModel';
import type { FormSectionFieldSchema, TemplateSelectOption } from '../../components/template/formSection.types';
import type { RelationFieldAdapter } from '../../components/template/relationField.types';
import {
  normalizeMonetaryDigits,
  projectMany2oneCapabilities,
  resolveCurrencyDisplayLabel,
} from '../../components/template/formSection.mapper';
import {
  MANY2ONE_CREATE_OPTION,
  MANY2ONE_OPEN_RECORD_OPTION,
  MANY2ONE_SEARCH_MORE_OPTION,
} from './types';

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function text(value: unknown): string {
  return String(value ?? '').trim();
}

function selectionOptions(value: unknown): TemplateSelectOption[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (Array.isArray(item) && item.length >= 2) {
      return [{ value: String(item[0] ?? ''), label: String(item[1] ?? item[0] ?? '') }];
    }
    const row = asRecord(item);
    const optionValue = text(row.value || row.key || row.id);
    if (!optionValue) return [];
    return [{ value: optionValue, label: text(row.label || row.name || optionValue) }];
  });
}

function inputValue(value: unknown): string | number | boolean | null {
  if (value === null || value === undefined || value === false) return value as null | boolean;
  if (Array.isArray(value)) return value.length > 1 ? String(value[1] ?? '') : String(value[0] ?? '');
  if (['string', 'number', 'boolean'].includes(typeof value)) return value as string | number | boolean;
  return String(value);
}

function relationValue(value: unknown): CanonicalRelationValue | null {
  const row = asRecord(value);
  if (!Object.prototype.hasOwnProperty.call(row, 'id')) return null;
  return {
    id: row.id as string | number,
    displayName: text(row.displayName),
    model: text(row.model),
  };
}

function fieldDescriptor(field: CanonicalFormField): FieldDescriptor {
  const config = asRecord(field.componentConfig);
  const canonicalDescriptor = asRecord(field.fieldDescriptor);
  const selection = selectionOptions(config.selection).map((option) => [option.value, option.label] as [string, string]);
  return {
    ...canonicalDescriptor,
    name: field.fieldCode,
    string: field.label,
    type: field.fieldType,
    ttype: field.fieldType,
    required: field.required,
    readonly: field.readonly || field.disabled,
    ...(selection.length ? { selection } : {}),
    ...(text(config.relation || config.relationModel || config.relation_model)
      ? { relation: text(config.relation || config.relationModel || config.relation_model) }
      : text(canonicalDescriptor.relation)
        ? { relation: text(canonicalDescriptor.relation) }
      : {}),
    ...(text(config.filename) ? { filename: text(config.filename) } : {}),
    ...(normalizeMonetaryDigits(config.digits) ? { digits: normalizeMonetaryDigits(config.digits) } : {}),
    ...(text(config.currencyField || config.currency_field)
      ? { currency_field: text(config.currencyField || config.currency_field) }
      : {}),
    ...(canonicalDescriptor.subview ? { subview: canonicalDescriptor.subview } : {}),
    ...(canonicalDescriptor.relation_entry ? { relation_entry: canonicalDescriptor.relation_entry } : {}),
    ...(canonicalDescriptor.widget_options ? { widget_options: canonicalDescriptor.widget_options } : {}),
  };
}

type CanonicalRelationProjection = Pick<
  RelationFieldAdapter,
  | 'relationKeyword'
  | 'filteredRelationOptions'
  | 'selectedRelationOptions'
  | 'relationCreateMode'
  | 'relationInlineCreate'
  | 'relationCreateLabel'
  | 'relationInlineCreateLabel'
  | 'canOpenRelationRecord'
  | 'relationOpenLabel'
  | 'relationSearchLabel'
>;

export function canonicalFieldToFormSection(
  field: CanonicalFormField,
  relationProjection?: CanonicalRelationProjection,
): FormSectionFieldSchema {
  const config = asRecord(field.componentConfig);
  const type = text(field.fieldType || config.fieldType || config.field_type || 'char').toLowerCase() || 'char';
  const descriptor = fieldDescriptor(field);
  const relation = type === 'many2one' ? relationValue(field.value) : null;
  const runtimeRelationOptions = type === 'many2one' && relationProjection
    ? relationProjection.filteredRelationOptions(field.fieldCode).map((option) => ({
      value: option.id,
      label: option.label,
    }))
    : [];
  const selectedRelation = type === 'many2one' && relationProjection
    ? relationProjection.selectedRelationOptions(field.fieldCode).find((option) => (
      !relation || String(option.id) === String(relation.id)
    ))
    : undefined;
  const relationKeyword = type === 'many2one' && relationProjection
    ? relationProjection.relationKeyword(field.fieldCode)
    : '';
  const many2oneCapabilities = type === 'many2one' && relationProjection
    ? projectMany2oneCapabilities({
      fieldName: field.fieldCode,
      descriptor,
      resolveRelationCreateMode: (name) => relationProjection.relationCreateMode(name),
      resolveRelationInlineCreate: (name) => relationProjection.relationInlineCreate(name),
      resolveCanOpenRelationRecord: (name) => relationProjection.canOpenRelationRecord(name),
      resolveRelationRecordOpenLabel: (name) => relationProjection.relationOpenLabel(name),
      resolveRelationSearchLabel: (name) => relationProjection.relationSearchLabel(name),
      resolveRelationCreateLabel: (name) => relationProjection.relationCreateLabel(name),
      resolveRelationInlineCreateLabel: (name) => relationProjection.relationInlineCreateLabel(name),
      relationTextValue: relationKeyword || relation?.displayName || selectedRelation?.label || '',
      many2oneCreateToken: MANY2ONE_CREATE_OPTION,
      many2oneSearchToken: MANY2ONE_SEARCH_MORE_OPTION,
      many2oneOpenToken: MANY2ONE_OPEN_RECORD_OPTION,
    })
    : { relationCreateMode: 'none' as const };
  const digits = type === 'monetary' ? normalizeMonetaryDigits(config.digits) : undefined;
  const currencyField = type === 'monetary'
    ? text(config.currencyField || config.currency_field || 'currency_id')
    : '';
  const currencyLabel = type === 'monetary'
    ? resolveCurrencyDisplayLabel(config.currencyLabel || config.currency_label || config.currencyValue || config.currency_value)
    : '';
  return {
    key: field.widgetId,
    name: field.fieldCode,
    label: field.label,
    hideLabel: field.hideLabel,
    type,
    widget: text(config.widget),
    widgetSemantics: asRecord(config.widgetSemantics || config.widget_semantics),
    componentKey: field.componentResolution.componentKey,
    componentReadiness: field.componentResolution.readiness,
    componentRenderer: field.componentResolution.renderer,
    componentFallback: field.componentResolution.fallback,
    presentationMode: field.presentationMode,
    renderProfile: field.renderProfile,
    digits,
    currencyField: currencyField || undefined,
    currencyLabel: currencyLabel || undefined,
    required: field.required,
    readonly: field.readonly || field.disabled,
    helpText: field.reasonCode,
    inputPlaceholder: field.placeholder || undefined,
    spanClass: field.span >= 24 ? 'field--full' : field.span >= 16 ? 'field--wide' : 'field--normal',
    value: relation ? relation.displayName : field.value,
    inputValue: relation ? relation.id : inputValue(field.value),
    many2oneTextValue: relationKeyword || relation?.displayName || selectedRelation?.label || undefined,
    selectionOptions: selectionOptions(config.selection),
    relationOptions: runtimeRelationOptions.length
      ? runtimeRelationOptions
      : selectionOptions(config.options || config.relationOptions || config.relation_options),
    ...many2oneCapabilities,
    descriptor,
    fileName: text(config.fileName || config.file_name),
  };
}

export function visibleCanonicalFields(node: CanonicalFormNode): CanonicalFormField[] {
  return node.fields.filter((field) => field.visible);
}

export function canonicalSectionFields(node: CanonicalFormNode): CanonicalFormField[] {
  return visibleCanonicalFields(node);
}

export function visibleCanonicalChildren(node: CanonicalFormNode): CanonicalFormNode[] {
  return node.children.filter((child) => (
    child.visible
    && canonicalNodeHasContent(child)
  ));
}

export function canonicalNodeHasContent(node: CanonicalFormNode): boolean {
  if (!node.visible) return false;
  if (visibleCanonicalFields(node).length) return true;
  if (node.text.trim()) return true;
  if (node.action || node.nativeWidget) return true;
  if (['chatter', 'activity', 'attachment'].includes(node.kind.toLowerCase())) return true;
  return node.children.some(canonicalNodeHasContent);
}
