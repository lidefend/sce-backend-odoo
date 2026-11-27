import {
  NATIVE_WIDGET_REGISTRY,
  SEMANTIC_COMPONENT_REGISTRY,
  SEMANTIC_FIELD_TYPES,
} from '../../presentation/semantic_registry.generated';
import type {
  ContractV2FieldDescriptor,
  ContractV2FieldDescriptorDecodeResult,
  ContractV2FieldDescriptorMap,
  ContractV2ModifierExpression,
  ContractV2ModifierOperand,
  ContractV2ModifierValue,
  ContractV2RegistryWidgetResolution,
  ContractV2RelationActiveActions,
} from './types';

type UnknownRecord = Record<string, unknown>;

export interface FieldDescriptorDecodeIssue {
  path: string;
  code: string;
  message: string;
}

export class FieldDescriptorDecodeError extends Error {
  issues: FieldDescriptorDecodeIssue[];

  constructor(issues: FieldDescriptorDecodeIssue[]) {
    super(`invalid ContractV2FieldDescriptor: ${issues.map((item) => `${item.path} ${item.code}`).join('; ')}`);
    this.name = 'FieldDescriptorDecodeError';
    this.issues = issues;
  }
}

const REQUIRED_KEYS = [
  'schemaVersion',
  'fieldCode',
  'label',
  'fieldType',
  'widgetType',
  'semanticType',
] as const;

const OPTIONAL_KEYS = [
  'required',
  'readonly',
  'invisible',
  'relation',
  'relationField',
  'referenceModelField',
  'selection',
  'domain',
  'domainExpression',
  'context',
  'relationEntry',
  'relationActiveActions',
  'widgetOptions',
  'subview',
  'filename',
  'surfaceRole',
  'help',
  'uiUsage',
  'changeDefault',
  'definitionRecord',
  'definitionRecordField',
  'groupOperator',
  'searchable',
  'sortable',
  'store',
  'translate',
  'trim',
  'related',
  'technical',
  'formStructureRole',
  'digits',
  'currencyField',
  'size',
  'unit',
  'temporal',
  'attachmentRole',
] as const;

const FIELD_TYPES = new Set([
  'char', 'text', 'html', 'integer', 'float', 'monetary', 'boolean', 'date',
  'datetime', 'selection', 'many2one', 'one2many', 'many2many', 'binary',
  'json', 'many2one_reference', 'reference',
]);
const FIXED_RELATION_FIELD_TYPES = new Set([
  'many2one', 'one2many', 'many2many',
]);
const FORM_STRUCTURE_ROLES = new Set([
  'summary', 'task', 'context', 'risk', 'relation', 'activity', 'audit',
]);
const UNIT_KINDS = new Set(['percent', 'duration', 'count', 'quantity']);
const MODIFIER_OPERATORS = new Set([
  '=', '==', '!=', '<>', '>', '>=', '<', '<=', 'in', 'not in', 'like', 'ilike',
]);
const MODIFIER_UNSUPPORTED_REASONS = new Set(['unsupported_domain', 'unsupported_expression']);
const FIXED_SEMANTIC_BY_FIELD_TYPE: Readonly<Record<string, string>> = Object.freeze({
  date: 'date',
  datetime: 'datetime',
  monetary: 'money',
  boolean: 'boolean',
});
const ALLOWED_KEYS = new Set<string>([...REQUIRED_KEYS, ...OPTIONAL_KEYS]);

function isRecord(value: unknown): value is UnknownRecord {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function push(issues: FieldDescriptorDecodeIssue[], path: string, code: string, message: string): void {
  issues.push({ path, code, message });
}

function rejectNestedUnknownKeys(
  value: UnknownRecord,
  allowed: readonly string[],
  path: string,
  issues: FieldDescriptorDecodeIssue[],
): void {
  Object.keys(value).forEach((key) => {
    if (!allowed.includes(key)) {
      push(issues, `${path}.${key}`, 'FIELD_DESCRIPTOR_UNKNOWN_KEY', 'unknown nested descriptor property');
    }
  });
}

function decodeOptionalBoolean(
  raw: UnknownRecord,
  key: string,
  path: string,
  issues: FieldDescriptorDecodeIssue[],
): boolean | undefined {
  if (raw[key] === undefined) return undefined;
  if (typeof raw[key] !== 'boolean') {
    push(issues, `${path}.${key}`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'must be boolean');
    return undefined;
  }
  return raw[key] as boolean;
}

function decodeOptionalText(
  raw: UnknownRecord,
  key: string,
  path: string,
  issues: FieldDescriptorDecodeIssue[],
): string | undefined {
  if (raw[key] === undefined) return undefined;
  if (typeof raw[key] !== 'string' || !raw[key].trim()) {
    push(issues, `${path}.${key}`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'must be a non-empty string');
    return undefined;
  }
  return raw[key].trim();
}

function decodeOptionalStringList(
  raw: UnknownRecord,
  key: string,
  path: string,
  issues: FieldDescriptorDecodeIssue[],
): string[] | undefined {
  if (raw[key] === undefined) return undefined;
  if (!Array.isArray(raw[key]) || !raw[key].length) {
    push(issues, `${path}.${key}`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'must be a non-empty string array');
    return undefined;
  }
  const values = raw[key].map((item: unknown) => (
    typeof item === 'string' ? item.trim() : ''
  ));
  if (values.some((item) => !item) || new Set(values).size !== values.length) {
    push(issues, `${path}.${key}`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'must contain unique non-empty strings');
    return undefined;
  }
  return values;
}

function decodeOptionalPositiveInteger(
  raw: UnknownRecord,
  key: string,
  path: string,
  issues: FieldDescriptorDecodeIssue[],
): number | undefined {
  if (raw[key] === undefined) return undefined;
  if (!Number.isInteger(raw[key]) || Number(raw[key]) < 1) {
    push(issues, `${path}.${key}`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'must be a positive integer');
    return undefined;
  }
  return Number(raw[key]);
}

function applicableFieldSemantics(): Set<string> {
  return new Set(
    Object.entries(SEMANTIC_FIELD_TYPES)
      .filter(([, fieldTypes]) => fieldTypes.some((fieldType) => fieldType !== 'action'))
      .map(([semanticType]) => semanticType),
  );
}

function decodeWidgetResolution(
  widgetType: string,
  path: string,
  issues: FieldDescriptorDecodeIssue[],
): ContractV2RegistryWidgetResolution | null {
  const declaration = NATIVE_WIDGET_REGISTRY[widgetType];
  if (!declaration) {
    push(issues, `${path}.widgetType`, 'FIELD_DESCRIPTOR_WIDGET_UNKNOWN', 'Widget is not declared by native_widgets');
    return null;
  }
  if (declaration.status === 'unsupported') {
    push(issues, `${path}.widgetType`, 'FIELD_DESCRIPTOR_WIDGET_UNSUPPORTED', 'Unsupported Widget cannot enter a normal Field Descriptor');
    return null;
  }
  if (declaration.status === 'fallback' && !declaration.reasonCode.trim()) {
    push(
      issues,
      `${path}.widgetType`,
      'FIELD_DESCRIPTOR_WIDGET_FALLBACK_REASON_MISSING',
      'Fallback Widget requires a registry reasonCode',
    );
    return null;
  }
  if (declaration.status !== 'ready' && declaration.status !== 'fallback') {
    push(issues, `${path}.widgetType`, 'FIELD_DESCRIPTOR_WIDGET_STATUS_INVALID', 'Widget status is not recognized');
    return null;
  }
  return {
    widgetType,
    widgetStatus: declaration.status,
    fallbackReasonCode: declaration.status === 'fallback' ? declaration.reasonCode : null,
  };
}

function decodeDigits(
  value: unknown,
  path: string,
  issues: FieldDescriptorDecodeIssue[],
): [number, number] | undefined {
  if (!Array.isArray(value) || value.length !== 2) {
    push(issues, path, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'digits must contain [total, scale]');
    return undefined;
  }
  const [total, scale] = value;
  if (
    typeof total !== 'number' || !Number.isInteger(total) || total < 1
    || typeof scale !== 'number' || !Number.isInteger(scale) || scale < 0 || scale > total
  ) {
    push(issues, path, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'digits require total > 0 and 0 <= scale <= total');
    return undefined;
  }
  return [total, scale];
}

function decodeSelection(
  value: unknown,
  path: string,
  issues: FieldDescriptorDecodeIssue[],
): Array<[string, string]> | undefined {
  if (!Array.isArray(value) || value.length === 0) {
    push(issues, path, 'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED', 'selection must be a non-empty key/label list');
    return undefined;
  }
  const out: Array<[string, string]> = [];
  value.forEach((item, index) => {
    if (!Array.isArray(item) || item.length !== 2 || !text(item[0]) || !text(item[1])) {
      push(issues, `${path}[${index}]`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'selection item must be [key, label]');
      return;
    }
    out.push([text(item[0]), text(item[1])]);
  });
  return out.length === value.length ? out : undefined;
}

function decodeUnit(
  value: unknown,
  path: string,
  issues: FieldDescriptorDecodeIssue[],
): ContractV2FieldDescriptor['unit'] | undefined {
  if (!isRecord(value)) {
    push(issues, path, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'unit must be an object');
    return undefined;
  }
  rejectNestedUnknownKeys(value, ['kind', 'code', 'label'], path, issues);
  const kind = text(value.kind);
  const code = text(value.code);
  const label = text(value.label);
  if (!UNIT_KINDS.has(kind) || !code || !label) {
    push(issues, path, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'unit requires a known kind, code and label');
    return undefined;
  }
  return {
    kind: kind as NonNullable<ContractV2FieldDescriptor['unit']>['kind'],
    code,
    label,
  };
}

function decodeTemporal(
  value: unknown,
  path: string,
  issues: FieldDescriptorDecodeIssue[],
): ContractV2FieldDescriptor['temporal'] | undefined {
  if (!isRecord(value)) {
    push(issues, path, 'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED', 'temporal must be an object');
    return undefined;
  }
  rejectNestedUnknownKeys(value, ['kind', 'timezoneAuthority'], path, issues);
  const kind = text(value.kind);
  const timezoneAuthority = text(value.timezoneAuthority);
  if (kind === 'date' && timezoneAuthority === 'not_applicable') {
    return { kind, timezoneAuthority };
  }
  if (kind === 'datetime' && (timezoneAuthority === 'user' || timezoneAuthority === 'record')) {
    return { kind, timezoneAuthority };
  }
  push(issues, path, 'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED', 'temporal kind and timezoneAuthority are inconsistent');
  return undefined;
}

function decodeFormStructureRole(
  value: unknown,
  path: string,
  issues: FieldDescriptorDecodeIssue[],
): ContractV2FieldDescriptor['formStructureRole'] | undefined {
  if (!isRecord(value)) {
    push(issues, path, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'formStructureRole must be an object');
    return undefined;
  }
  rejectNestedUnknownKeys(value, ['role', 'slot', 'group'], path, issues);
  const role = text(value.role);
  const slot = text(value.slot);
  const group = text(value.group);
  if (!FORM_STRUCTURE_ROLES.has(role) || !slot || !group) {
    push(issues, path, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'formStructureRole is incomplete');
    return undefined;
  }
  return {
    role: role as NonNullable<ContractV2FieldDescriptor['formStructureRole']>['role'],
    slot,
    group,
  };
}

function decodeModifierOperand(
  value: unknown,
  path: string,
  issues: FieldDescriptorDecodeIssue[],
): ContractV2ModifierOperand | undefined {
  if (!isRecord(value)) {
    push(issues, path, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'modifier operand must be an object');
    return undefined;
  }
  const kind = text(value.kind);
  if (kind === 'context_get') {
    rejectNestedUnknownKeys(value, ['kind', 'key', 'default'], path, issues);
    const key = text(value.key);
    if (!key) {
      push(issues, `${path}.key`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'context operand requires a non-empty key');
      return undefined;
    }
    return {
      kind,
      key,
      ...(Object.prototype.hasOwnProperty.call(value, 'default') ? { default: value.default } : {}),
    };
  }
  if (kind === 'field_value') {
    rejectNestedUnknownKeys(value, ['kind', 'field'], path, issues);
    const field = text(value.field);
    if (!field) {
      push(issues, `${path}.field`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'field operand requires a non-empty field');
      return undefined;
    }
    return { kind, field };
  }
  if (kind === 'literal') {
    rejectNestedUnknownKeys(value, ['kind', 'value'], path, issues);
    if (!Object.prototype.hasOwnProperty.call(value, 'value')) {
      push(issues, `${path}.value`, 'FIELD_DESCRIPTOR_REQUIRED', 'literal operand requires value');
      return undefined;
    }
    return { kind, value: value.value };
  }
  push(issues, `${path}.kind`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'modifier operand kind is not recognized');
  return undefined;
}

function decodeModifierValue(
  value: unknown,
  path: string,
  issues: FieldDescriptorDecodeIssue[],
): ContractV2ModifierValue | undefined {
  if (typeof value === 'boolean') return value;
  if (!isRecord(value)) {
    push(issues, path, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'relation action must be boolean or a modifier expression');
    return undefined;
  }
  const kind = text(value.kind);
  const raw = value.raw === undefined ? undefined : text(value.raw);
  if (value.raw !== undefined && !raw) {
    push(issues, `${path}.raw`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'modifier raw source must be a non-empty string');
  }
  if (kind === 'static') {
    rejectNestedUnknownKeys(value, ['kind', 'value', 'raw'], path, issues);
    if (typeof value.value !== 'boolean') {
      push(issues, `${path}.value`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'static modifier value must be boolean');
      return undefined;
    }
    return { kind, value: value.value, ...(raw ? { raw } : {}) };
  }
  if (kind === 'field_truthy') {
    rejectNestedUnknownKeys(value, ['kind', 'field', 'semantics', 'raw'], path, issues);
    const field = text(value.field);
    if (!field) {
      push(issues, `${path}.field`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'field_truthy requires a non-empty field');
      return undefined;
    }
    if (value.semantics !== undefined && value.semantics !== 'python') {
      push(issues, `${path}.semantics`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'field_truthy semantics must be python');
      return undefined;
    }
    return {
      kind,
      field,
      ...(value.semantics === 'python' ? { semantics: 'python' as const } : {}),
      ...(raw ? { raw } : {}),
    };
  }
  if (kind === 'field_compare') {
    rejectNestedUnknownKeys(
      value,
      ['kind', 'field', 'operator', 'semantics', 'value', 'value_field', 'raw'],
      path,
      issues,
    );
    const field = text(value.field);
    const operator = text(value.operator);
    const valueField = text(value.value_field);
    const hasValue = Object.prototype.hasOwnProperty.call(value, 'value');
    if (!field) {
      push(issues, `${path}.field`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'field_compare requires a non-empty field');
    }
    if (!MODIFIER_OPERATORS.has(operator)) {
      push(issues, `${path}.operator`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'field_compare operator is not supported');
    }
    if (value.semantics !== undefined && value.semantics !== 'python') {
      push(issues, `${path}.semantics`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'field_compare semantics must be python');
    }
    if (hasValue === Boolean(valueField)) {
      push(
        issues,
        path,
        'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED',
        'field_compare requires exactly one of value or value_field',
      );
    }
    if (!field || !MODIFIER_OPERATORS.has(operator) || hasValue === Boolean(valueField)) return undefined;
    return {
      kind,
      field,
      operator: operator as Extract<ContractV2ModifierExpression, { kind: 'field_compare' }>['operator'],
      ...(value.semantics === 'python' ? { semantics: 'python' as const } : {}),
      ...(hasValue ? { value: value.value } : {}),
      ...(valueField ? { value_field: valueField } : {}),
      ...(raw ? { raw } : {}),
    };
  }
  if (kind === 'not') {
    rejectNestedUnknownKeys(value, ['kind', 'expr', 'raw'], path, issues);
    const expr = decodeModifierValue(value.expr, `${path}.expr`, issues);
    if (!expr) {
      push(issues, `${path}.expr`, 'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED', 'not requires a modifier expression');
      return undefined;
    }
    return { kind, expr, ...(raw ? { raw } : {}) };
  }
  if (kind === 'all' || kind === 'any') {
    rejectNestedUnknownKeys(value, ['kind', 'exprs', 'raw'], path, issues);
    if (!Array.isArray(value.exprs) || !value.exprs.length) {
      push(issues, `${path}.exprs`, 'FIELD_DESCRIPTOR_TYPE_INVALID', `${kind} requires at least one expression`);
      return undefined;
    }
    const exprs = value.exprs.map((expr, index) => (
      decodeModifierValue(expr, `${path}.exprs[${index}]`, issues)
    ));
    if (exprs.some((expr) => !expr)) return undefined;
    return {
      kind,
      exprs: exprs as ContractV2ModifierValue[],
      ...(raw ? { raw } : {}),
    };
  }
  if (kind === 'value_truthy') {
    rejectNestedUnknownKeys(value, ['kind', 'semantics', 'value_expr', 'raw'], path, issues);
    if (value.semantics !== 'python') {
      push(issues, `${path}.semantics`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'value_truthy semantics must be python');
      return undefined;
    }
    const operand = decodeModifierOperand(value.value_expr, `${path}.value_expr`, issues);
    if (!operand || operand.kind !== 'context_get') {
      push(issues, `${path}.value_expr`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'value_truthy requires a context_get operand');
      return undefined;
    }
    return { kind, semantics: 'python', value_expr: operand, ...(raw ? { raw } : {}) };
  }
  if (kind === 'value_compare') {
    rejectNestedUnknownKeys(
      value,
      ['kind', 'semantics', 'operator', 'left', 'right', 'raw'],
      path,
      issues,
    );
    const operator = text(value.operator);
    if (value.semantics !== 'python' || !MODIFIER_OPERATORS.has(operator)) {
      push(issues, path, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'value_compare requires python semantics and a supported operator');
      return undefined;
    }
    const left = decodeModifierOperand(value.left, `${path}.left`, issues);
    const right = decodeModifierOperand(value.right, `${path}.right`, issues);
    if (!left || !right) return undefined;
    return {
      kind,
      semantics: 'python',
      operator: operator as Extract<ContractV2ModifierExpression, { kind: 'value_compare' }>['operator'],
      left,
      right,
      ...(raw ? { raw } : {}),
    };
  }
  if (kind === 'unsupported') {
    rejectNestedUnknownKeys(value, ['kind', 'raw', 'reason'], path, issues);
    const reason = text(value.reason);
    if (!raw || !MODIFIER_UNSUPPORTED_REASONS.has(reason)) {
      push(issues, path, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'unsupported modifier requires raw source and a known reason');
      return undefined;
    }
    return { kind, raw, reason: reason as 'unsupported_domain' | 'unsupported_expression' };
  }
  push(issues, `${path}.kind`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'modifier expression kind is not recognized');
  return undefined;
}

function decodeRelationActiveActions(
  value: unknown,
  path: string,
  issues: FieldDescriptorDecodeIssue[],
): ContractV2RelationActiveActions | undefined {
  if (!isRecord(value)) {
    push(issues, path, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'relationActiveActions must be an object');
    return undefined;
  }
  rejectNestedUnknownKeys(value, ['create', 'write'], path, issues);
  const out: ContractV2RelationActiveActions = {};
  (['create', 'write'] as const).forEach((key) => {
    if (!Object.prototype.hasOwnProperty.call(value, key)) return;
    const decoded = decodeModifierValue(value[key], `${path}.${key}`, issues);
    if (decoded !== undefined) out[key] = decoded;
  });
  if (!Object.keys(out).length) {
    push(issues, path, 'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED', 'relationActiveActions must declare create or write');
    return undefined;
  }
  return out;
}

export function decodeContractV2FieldDescriptor(
  raw: unknown,
  path = 'fieldDescriptor',
): ContractV2FieldDescriptorDecodeResult {
  const issues: FieldDescriptorDecodeIssue[] = [];
  if (!isRecord(raw)) {
    throw new FieldDescriptorDecodeError([{ path, code: 'FIELD_DESCRIPTOR_REQUIRED', message: 'must be an object' }]);
  }
  Object.keys(raw).forEach((key) => {
    if (!ALLOWED_KEYS.has(key)) {
      push(issues, `${path}.${key}`, 'FIELD_DESCRIPTOR_UNKNOWN_KEY', 'unknown descriptor property');
    }
  });
  REQUIRED_KEYS.forEach((key) => {
    if (!(key in raw)) {
      push(issues, `${path}.${key}`, 'FIELD_DESCRIPTOR_REQUIRED', 'required property is missing');
    }
  });
  const schemaVersion = text(raw.schemaVersion);
  if (schemaVersion !== '1.0.0') {
    push(issues, `${path}.schemaVersion`, 'FIELD_DESCRIPTOR_VERSION_UNSUPPORTED', 'only schemaVersion 1.0.0 is accepted');
  }
  const fieldCode = text(raw.fieldCode);
  const label = text(raw.label);
  const fieldType = text(raw.fieldType);
  const widgetType = text(raw.widgetType);
  const semanticType = text(raw.semanticType);
  if (!fieldCode) push(issues, `${path}.fieldCode`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'fieldCode must be non-empty');
  if (!label) push(issues, `${path}.label`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'label must be non-empty');
  if (!FIELD_TYPES.has(fieldType)) {
    push(issues, `${path}.fieldType`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'fieldType is not a field value type');
  }
  const applicable = applicableFieldSemantics();
  if (!applicable.has(semanticType)) {
    push(
      issues,
      `${path}.semanticType`,
      'FIELD_DESCRIPTOR_SEMANTIC_MISMATCH',
      'semanticType is not declared and applicable to Field Descriptors',
    );
  }
  const fixedSemantic = FIXED_SEMANTIC_BY_FIELD_TYPE[fieldType];
  if (fixedSemantic && semanticType !== fixedSemantic) {
    push(
      issues,
      `${path}.semanticType`,
      'FIELD_DESCRIPTOR_SEMANTIC_MISMATCH',
      `fieldType ${fieldType} requires semanticType ${fixedSemantic}`,
    );
  }
  const declaredFieldTypes = SEMANTIC_FIELD_TYPES[semanticType] || [];
  if (
    declaredFieldTypes.length
    && !declaredFieldTypes.includes('*')
    && !declaredFieldTypes.includes(fieldType)
  ) {
    push(issues, `${path}.fieldType`, 'FIELD_DESCRIPTOR_SEMANTIC_MISMATCH', 'semanticType does not support fieldType');
  }
  const widgetResolution = widgetType
    ? decodeWidgetResolution(widgetType, path, issues)
    : null;
  const required = decodeOptionalBoolean(raw, 'required', path, issues);
  const readonly = decodeOptionalBoolean(raw, 'readonly', path, issues);
  const invisible = decodeOptionalBoolean(raw, 'invisible', path, issues);
  const technical = decodeOptionalBoolean(raw, 'technical', path, issues);
  const relation = decodeOptionalText(raw, 'relation', path, issues) || '';
  const relationField = decodeOptionalText(raw, 'relationField', path, issues);
  const referenceModelField = decodeOptionalText(raw, 'referenceModelField', path, issues);
  if (raw.referenceModelField !== undefined && (
    typeof raw.referenceModelField !== 'string'
    || !/^[A-Za-z_][A-Za-z0-9_]*$/.test(raw.referenceModelField)
    || raw.referenceModelField === fieldCode
  )) {
    push(issues, `${path}.referenceModelField`, 'FIELD_DESCRIPTOR_REFERENCE_MODEL_FIELD_INVALID', 'must name a distinct same-record model pointer field');
  }
  const currencyField = decodeOptionalText(raw, 'currencyField', path, issues) || '';
  const filename = decodeOptionalText(raw, 'filename', path, issues);
  const surfaceRole = decodeOptionalText(raw, 'surfaceRole', path, issues);
  const helpText = decodeOptionalText(raw, 'help', path, issues);
  const uiUsage = decodeOptionalText(raw, 'uiUsage', path, issues);
  const normalizedUiUsage: 'fact' | 'interaction' | undefined = uiUsage === 'fact' || uiUsage === 'interaction'
    ? uiUsage
    : undefined;
  const changeDefault = decodeOptionalBoolean(raw, 'changeDefault', path, issues);
  const searchable = decodeOptionalBoolean(raw, 'searchable', path, issues);
  const sortable = decodeOptionalBoolean(raw, 'sortable', path, issues);
  const store = decodeOptionalBoolean(raw, 'store', path, issues);
  const translate = decodeOptionalBoolean(raw, 'translate', path, issues);
  const trim = decodeOptionalBoolean(raw, 'trim', path, issues);
  const definitionRecord = decodeOptionalText(raw, 'definitionRecord', path, issues);
  const definitionRecordField = decodeOptionalText(raw, 'definitionRecordField', path, issues);
  const groupOperator = decodeOptionalText(raw, 'groupOperator', path, issues);
  const related = decodeOptionalStringList(raw, 'related', path, issues);
  const size = decodeOptionalPositiveInteger(raw, 'size', path, issues);
  if (uiUsage !== undefined && !['fact', 'interaction'].includes(uiUsage)) {
    push(issues, `${path}.uiUsage`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'must be fact or interaction');
  }
  const attachmentRole = decodeOptionalText(raw, 'attachmentRole', path, issues) || '';
  for (const key of ['relationEntry', 'widgetOptions', 'subview'] as const) {
    if (raw[key] !== undefined && !isRecord(raw[key])) {
      push(issues, `${path}.${key}`, 'FIELD_DESCRIPTOR_TYPE_INVALID', 'must be an object');
    }
  }
  const digits = raw.digits === undefined ? undefined : decodeDigits(raw.digits, `${path}.digits`, issues);
  const selection = raw.selection === undefined
    ? undefined
    : decodeSelection(raw.selection, `${path}.selection`, issues);
  const unit = raw.unit === undefined ? undefined : decodeUnit(raw.unit, `${path}.unit`, issues);
  const temporal = raw.temporal === undefined ? undefined : decodeTemporal(raw.temporal, `${path}.temporal`, issues);
  const formStructureRole = raw.formStructureRole === undefined
    ? undefined
    : decodeFormStructureRole(raw.formStructureRole, `${path}.formStructureRole`, issues);
  const relationActiveActions = raw.relationActiveActions === undefined
    ? undefined
    : decodeRelationActiveActions(raw.relationActiveActions, `${path}.relationActiveActions`, issues);

  if (fieldType === 'monetary' || semanticType === 'money') {
    if (
      !['monetary', 'float'].includes(fieldType)
      || semanticType !== 'money'
      || !currencyField
      || currencyField === fieldCode
    ) {
      push(issues, path, 'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED', 'money requires monetary or float fieldType and currencyField');
    }
    if (raw.unit !== undefined || raw.temporal !== undefined || raw.attachmentRole !== undefined) {
      push(issues, path, 'FIELD_DESCRIPTOR_SEMANTIC_MISMATCH', 'money cannot declare unit, temporal or attachmentRole');
    }
  }
  if (semanticType === 'percentage') {
    if (!digits || unit?.kind !== 'percent' || unit.code !== 'percent' || currencyField) {
      push(issues, path, 'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED', 'percentage requires digits and percent unit');
    }
  }
  if (semanticType === 'duration') {
    if (!digits || unit?.kind !== 'duration' || currencyField) {
      push(issues, path, 'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED', 'duration requires digits and duration unit');
    }
  }
  if (fieldType === 'date' || semanticType === 'date') {
    if (fieldType !== 'date' || semanticType !== 'date' || temporal?.kind !== 'date') {
      push(issues, path, 'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED', 'date requires matching fieldType and temporal date');
    }
  }
  if (fieldType === 'datetime' || semanticType === 'datetime') {
    if (fieldType !== 'datetime' || semanticType !== 'datetime' || temporal?.kind !== 'datetime') {
      push(issues, path, 'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED', 'datetime requires matching fieldType and temporal datetime');
    }
  }
  if (FIXED_RELATION_FIELD_TYPES.has(fieldType) && !relation) {
    push(issues, path, 'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED', 'fixed relation field types require relation');
  }
  if (raw.relationActiveActions !== undefined && !['many2one', 'many2many'].includes(fieldType)) {
    push(
      issues,
      `${path}.relationActiveActions`,
      'FIELD_DESCRIPTOR_SEMANTIC_MISMATCH',
      'relationActiveActions is only valid for many2one or many2many fields',
    );
  }
  if (raw.relationActiveActions !== undefined && fieldType === 'many2many' && widgetType !== 'many2many_tags') {
    push(
      issues,
      `${path}.relationActiveActions`,
      'FIELD_DESCRIPTOR_SEMANTIC_MISMATCH',
      'many2many relation actions require the declared many2many_tags widget',
    );
  }
  if (fieldType === 'many2one_reference' && !referenceModelField) {
    push(issues, path, 'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED', 'many2one_reference requires referenceModelField');
  }
  if (relation === 'ir.attachment' && !attachmentRole) {
    push(issues, path, 'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED', 'ir.attachment requires attachmentRole');
  }
  if (relation !== 'ir.attachment' && raw.attachmentRole !== undefined) {
    push(issues, path, 'FIELD_DESCRIPTOR_SEMANTIC_MISMATCH', 'attachmentRole is only valid for ir.attachment');
  }
  if (fieldType === 'selection' && !selection) {
    push(issues, path, 'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED', 'selection fieldType requires selection pairs');
  }
  if (issues.length || !widgetResolution) {
    throw new FieldDescriptorDecodeError(issues);
  }

  const descriptor: ContractV2FieldDescriptor = {
    schemaVersion: '1.0.0',
    fieldCode,
    label,
    fieldType,
    widgetType,
    componentKey: SEMANTIC_COMPONENT_REGISTRY[semanticType] || '',
    semanticType,
    ...(required !== undefined ? { required } : {}),
    ...(readonly !== undefined ? { readonly } : {}),
    ...(invisible !== undefined ? { invisible } : {}),
    ...(relation ? { relation } : {}),
    ...(relationField ? { relationField } : {}),
    ...(referenceModelField ? { referenceModelField } : {}),
    ...(selection ? { selection } : {}),
    ...(raw.domain !== undefined ? { domain: raw.domain } : {}),
    ...(raw.domainExpression !== undefined ? { domainExpression: raw.domainExpression } : {}),
    ...(raw.context !== undefined ? { context: raw.context } : {}),
    ...(isRecord(raw.relationEntry) ? { relationEntry: raw.relationEntry } : {}),
    ...(relationActiveActions ? { relationActiveActions } : {}),
    ...(isRecord(raw.widgetOptions) ? { widgetOptions: raw.widgetOptions } : {}),
    ...(isRecord(raw.subview) ? { subview: raw.subview } : {}),
    ...(filename ? { filename } : {}),
    ...(surfaceRole ? { surfaceRole } : {}),
    ...(helpText ? { help: helpText } : {}),
    ...(normalizedUiUsage ? { uiUsage: normalizedUiUsage } : {}),
    ...(changeDefault !== undefined ? { changeDefault } : {}),
    ...(definitionRecord ? { definitionRecord } : {}),
    ...(definitionRecordField ? { definitionRecordField } : {}),
    ...(groupOperator ? { groupOperator } : {}),
    ...(searchable !== undefined ? { searchable } : {}),
    ...(sortable !== undefined ? { sortable } : {}),
    ...(store !== undefined ? { store } : {}),
    ...(translate !== undefined ? { translate } : {}),
    ...(trim !== undefined ? { trim } : {}),
    ...(related ? { related } : {}),
    ...(size ? { size } : {}),
    ...(technical !== undefined ? { technical } : {}),
    ...(formStructureRole ? { formStructureRole } : {}),
    ...(digits ? { digits } : {}),
    ...(currencyField ? { currencyField } : {}),
    ...(unit ? { unit } : {}),
    ...(temporal ? { temporal } : {}),
    ...(attachmentRole ? { attachmentRole } : {}),
  };
  return {
    descriptor,
    registryResolution: {
      widget: widgetResolution,
    },
  };
}

export function decodeContractV2FieldDescriptorMap(
  raw: unknown,
  path = 'block_field_descriptors',
): { descriptors: ContractV2FieldDescriptorMap; registryResolution: Record<string, ContractV2FieldDescriptorDecodeResult['registryResolution']> } {
  if (!isRecord(raw)) {
    throw new FieldDescriptorDecodeError([{ path, code: 'FIELD_DESCRIPTOR_REQUIRED', message: 'must be an object' }]);
  }
  const descriptors: ContractV2FieldDescriptorMap = {};
  const registryResolution: Record<string, ContractV2FieldDescriptorDecodeResult['registryResolution']> = {};
  Object.entries(raw).forEach(([descriptorId, descriptor]) => {
    const result = decodeContractV2FieldDescriptor(descriptor, `${path}.${descriptorId}`);
    descriptors[descriptorId] = result.descriptor;
    registryResolution[descriptorId] = result.registryResolution;
  });
  return { descriptors, registryResolution };
}
