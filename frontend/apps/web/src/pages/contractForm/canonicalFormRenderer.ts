import type { FieldDescriptor } from '@sc/schema';
import type { CanonicalFormField, CanonicalFormNode, CanonicalRelationValue } from '../../app/presentation/canonicalFormRenderModel';
import type { FormSectionFieldSchema, TemplateSelectOption } from '../../components/template/formSection.types';

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
  const selection = selectionOptions(config.selection).map((option) => [option.value, option.label] as [string, string]);
  return {
    name: field.fieldCode,
    string: field.label,
    type: field.fieldType,
    ttype: field.fieldType,
    required: field.required,
    readonly: field.readonly || field.disabled,
    ...(selection.length ? { selection } : {}),
    ...(text(config.relation || config.relationModel || config.relation_model)
      ? { relation: text(config.relation || config.relationModel || config.relation_model) }
      : {}),
    ...(text(config.filename) ? { filename: text(config.filename) } : {}),
  };
}

export function canonicalFieldToFormSection(field: CanonicalFormField): FormSectionFieldSchema {
  const config = asRecord(field.componentConfig);
  const type = text(field.fieldType || config.fieldType || config.field_type || 'char').toLowerCase() || 'char';
  const descriptor = fieldDescriptor(field);
  const relation = type === 'many2one' ? relationValue(field.value) : null;
  return {
    key: field.widgetId,
    name: field.fieldCode,
    label: field.label,
    type,
    widget: text(config.widget),
    widgetSemantics: asRecord(config.widgetSemantics || config.widget_semantics),
    required: field.required,
    readonly: field.readonly || field.disabled,
    helpText: field.reasonCode,
    spanClass: field.span >= 24 ? 'field--full' : field.span >= 16 ? 'field--wide' : 'field--normal',
    value: relation ? relation.displayName : field.value,
    inputValue: relation ? relation.id : inputValue(field.value),
    many2oneTextValue: relation?.displayName || undefined,
    selectionOptions: selectionOptions(config.selection),
    relationOptions: selectionOptions(config.options || config.relationOptions || config.relation_options),
    descriptor,
    fileName: text(config.fileName || config.file_name),
  };
}

export function visibleCanonicalFields(node: CanonicalFormNode): CanonicalFormField[] {
  return node.fields.filter((field) => field.visible);
}

function isFieldNode(node: CanonicalFormNode): boolean {
  return node.kind.trim().toLowerCase() === 'field';
}

export function canonicalSectionFields(node: CanonicalFormNode): CanonicalFormField[] {
  return [
    ...visibleCanonicalFields(node),
    ...node.children.filter(isFieldNode).flatMap(visibleCanonicalFields),
  ];
}

export function visibleCanonicalChildren(node: CanonicalFormNode): CanonicalFormNode[] {
  return node.children.filter((child) => (
    child.visible
    && canonicalNodeHasContent(child)
    && !(isFieldNode(child) && child.children.length === 0)
  ));
}

export function canonicalNodeHasContent(node: CanonicalFormNode): boolean {
  if (!node.visible) return false;
  if (visibleCanonicalFields(node).length) return true;
  if (['chatter', 'activity', 'attachment'].includes(node.kind.toLowerCase())) return true;
  return node.children.some(canonicalNodeHasContent);
}
