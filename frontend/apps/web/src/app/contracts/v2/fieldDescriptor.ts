import {
  NATIVE_WIDGET_REGISTRY,
  SEMANTIC_COMPONENT_REGISTRY,
  SEMANTIC_FIELD_TYPES,
} from '../../presentation/semantic_registry.generated';
import type {
  ContractV2FieldDescriptor,
  ContractV2FieldDescriptorDecodeResult,
  ContractV2FieldDescriptorMap,
  ContractV2RegistryWidgetResolution,
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
  'selection',
  'domain',
  'domainExpression',
  'context',
  'relationEntry',
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
const RELATION_FIELD_TYPES = new Set([
  'many2one', 'one2many', 'many2many', 'many2one_reference', 'reference',
]);
const FORM_STRUCTURE_ROLES = new Set([
  'summary', 'task', 'context', 'risk', 'relation', 'activity', 'audit',
]);
const UNIT_KINDS = new Set(['percent', 'duration', 'count', 'quantity']);
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
  if (RELATION_FIELD_TYPES.has(fieldType) && !relation) {
    push(issues, path, 'FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED', 'relation field types require relation');
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
    ...(selection ? { selection } : {}),
    ...(raw.domain !== undefined ? { domain: raw.domain } : {}),
    ...(raw.domainExpression !== undefined ? { domainExpression: raw.domainExpression } : {}),
    ...(raw.context !== undefined ? { context: raw.context } : {}),
    ...(isRecord(raw.relationEntry) ? { relationEntry: raw.relationEntry } : {}),
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
