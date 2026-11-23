import {
  FieldDescriptorDecodeError,
  decodeContractV2FieldDescriptor,
  decodeContractV2FieldDescriptorMap,
} from './contracts/v2/fieldDescriptor';
import type {
  ContractV2Dictionary,
  ContractV2FieldDescriptor,
  ContractV2FieldDescriptorDecodeResult,
  ContractV2PageBlockDataContract,
  ContractV2PageBlockFieldRef,
  ContractV2PageBlockDataRow,
} from './contracts/v2/types';

export type SemanticTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral';
export type SemanticProgress = 'overdue' | 'blocked' | 'pending' | 'running' | 'completed';

export interface PageOrchestrationAction {
  key: string;
  label?: string;
  intent?: string;
  target?: Record<string, unknown>;
}

export interface PageOrchestrationBlock {
  key: string;
  block_type: string;
  title?: string;
  subtitle?: string;
  priority?: number;
  importance?: string;
  tone?: SemanticTone | string;
  progress?: SemanticProgress | string;
  data_source?: string;
  payload?: Record<string, unknown>;
  actions?: PageOrchestrationAction[];
}

export interface PageOrchestrationZone {
  key: string;
  title?: string;
  description?: string;
  zone_type?: string;
  display_mode?: string;
  priority?: number;
  blocks?: PageOrchestrationBlock[];
}

export interface PageOrchestrationPage {
  key?: string;
  title?: string;
  subtitle?: string;
  page_type?: string;
  layout_mode?: string;
  audience?: string[];
  priority_model?: string;
  status?: string;
  header?: {
    badges?: Array<{ label?: string; tone?: SemanticTone | string }>;
  };
  global_actions?: PageOrchestrationAction[];
  context?: Record<string, unknown>;
}

export interface PageOrchestrationContract {
  schema_version?: string;
  contract_version?: string;
  scene_key?: string;
  page?: PageOrchestrationPage;
  zones?: PageOrchestrationZone[];
  data_sources?: Record<string, unknown>;
  state_schema?: Record<string, unknown>;
  action_schema?: Record<string, unknown>;
  render_hints?: Record<string, unknown>;
  meta?: Record<string, unknown>;
  block_field_descriptors?: Record<string, ContractV2FieldDescriptor>;
  block_data_contracts?: Record<string, ContractV2PageBlockDataContract>;
}

export interface PageBlockActionEvent {
  actionKey: string;
  blockKey: string;
  zoneKey: string;
  item?: Record<string, unknown>;
  intent?: string;
  target?: Record<string, unknown>;
}

export interface PageBlockDataResolvedRow {
  rowKey: string;
  values: ContractV2Dictionary;
  fieldDescriptors: Record<string, ContractV2FieldDescriptor>;
  registryResolution: Record<string, ContractV2FieldDescriptorDecodeResult['registryResolution']>;
  context: ContractV2PageBlockDataContract['context'];
}

export function overlayPageBlockDataRows(
  rows: PageBlockDataResolvedRow[],
  legacyRows: Array<Record<string, unknown>>,
): Array<Record<string, unknown>> {
  const legacyByKey = new Map<string, Record<string, unknown>>();
  const duplicateKeys = new Set<string>();
  legacyRows.forEach((item) => {
    const key = String(item.key || item.id || '').trim();
    if (!key) return;
    if (legacyByKey.has(key)) duplicateKeys.add(key);
    else legacyByKey.set(key, item);
  });
  const duplicate = rows.find((row) => duplicateKeys.has(row.rowKey));
  if (duplicate) {
    throw new PageOrchestrationDecodeError([{
      path: `page_block_data.rows.${duplicate.rowKey}`,
      message: 'legacy row identity is duplicated; stable rowKey matching is ambiguous',
    }]);
  }
  return rows.map((row) => {
    const legacy = legacyByKey.get(row.rowKey) || {};
    const merged = { ...legacy };
    Object.keys(row.fieldDescriptors).forEach((slotKey) => {
      if (!Object.prototype.hasOwnProperty.call(row.values, slotKey)) {
        delete merged[slotKey];
      }
    });
    return {
      ...merged,
      ...row.values,
      __pageBlockData: row,
    };
  });
}

export function resolvePageBlockCurrencyLabel(
  row: PageBlockDataResolvedRow,
  currencyField?: string,
): string {
  const field = String(currencyField || '').trim();
  if (!field) return '';
  const currencySlot = Object.entries(row.fieldDescriptors)
    .find(([slotKey, descriptor]) => slotKey === field || descriptor.fieldCode === field);
  const currencyValue = currencySlot ? row.values[currencySlot[0]] : row.values[field];
  let identity = '';
  if (Array.isArray(currencyValue)) {
    identity = String(currencyValue[0] ?? '').trim();
  } else if (currencyValue && typeof currencyValue === 'object') {
    const currency = currencyValue as Record<string, unknown>;
    identity = String(currency.id ?? '').trim();
  } else if (currencyValue !== undefined && currencyValue !== null) {
    identity = String(currencyValue).trim();
  }
  if (!identity) return '';
  const currency = row.context.currencies[identity];
  if (!currency || typeof currency !== 'object') return '';
  return String(currency.code || currency.symbol || currency.label || '').trim();
}

export class PageOrchestrationDecodeError extends Error {
  issues: Array<{ path: string; message: string }>;

  constructor(issues: Array<{ path: string; message: string }>) {
    super(`invalid page orchestration contract: ${issues.map((item) => `${item.path} ${item.message}`).join('; ')}`);
    this.name = 'PageOrchestrationDecodeError';
    this.issues = issues;
  }
}

const PAGE_ORCHESTRATION_KEYS = new Set([
  'schema_version', 'contract_version', 'scene_key', 'page', 'zones',
  'data_sources', 'state_schema', 'action_schema', 'render_hints', 'meta',
  'block_field_descriptors', 'block_data_contracts',
]);
const PAGE_BLOCK_DATA_KEYS = new Set([
  'schemaVersion', 'fieldRefs', 'rows', 'context', 'sourceAuthority',
]);
const PAGE_BLOCK_CONTEXT_KEYS = new Set(['currencies', 'timezone']);
const CURRENCY_KEYS = new Set(['id', 'code', 'label', 'symbol']);
const SOURCE_AUTHORITY_KEYS = new Set([
  'kind',
  'authorities',
  'projectionOnly',
  'noFrontendDefaults',
  'carrier',
  'schemaVersion',
]);
const PAGE_BLOCK_SOURCE_KIND = 'page_block_data_producer';
const PAGE_BLOCK_SOURCE_AUTHORITIES = [
  'odoo_model_fields',
  'page_orchestration',
  'semantic_registry',
] as const;
const PAGE_BLOCK_SOURCE_CARRIER = 'page-block-data.v1';
const PAGE_BLOCK_SOURCE_SCHEMA_VERSION = '1.0.0';
const FIELD_REF_BASE_KEYS = new Set(['kind', 'rawValuePath']);
const DESCRIPTOR_REF_KEYS = new Set([...FIELD_REF_BASE_KEYS, 'descriptorId']);
const WIDGET_REF_KEYS = new Set([...FIELD_REF_BASE_KEYS, 'widgetId']);
const ROW_KEYS = new Set(['rowKey', 'values']);
const FIELD_IDENTIFIER_PATTERN = /^[A-Za-z_][A-Za-z0-9_.:-]*$/;
const FORBIDDEN_PATH_SEGMENTS = new Set(['__proto__', 'constructor', 'prototype']);

function asRecord(value: unknown): ContractV2Dictionary {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as ContractV2Dictionary
    : {};
}

function asText(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function rejectUnknownKeys(
  value: ContractV2Dictionary,
  allowed: Set<string>,
  path: string,
): void {
  const unknown = Object.keys(value).filter((key) => !allowed.has(key));
  if (unknown.length) {
    throw new PageOrchestrationDecodeError(
      unknown.map((key) => ({ path: `${path}.${key}`, message: 'is not allowed' })),
    );
  }
}

function decodeRawValuePath(value: unknown, path: string): string {
  const rawValuePath = asText(value);
  const segments = Array.from(rawValuePath.matchAll(/[^.]+/g), (match) => match[0]);
  if (
    !rawValuePath
    || rawValuePath.startsWith('.')
    || rawValuePath.endsWith('.')
    || rawValuePath.includes('..')
    || segments.some((segment) => !segment || FORBIDDEN_PATH_SEGMENTS.has(segment))
  ) {
    throw new PageOrchestrationDecodeError([{
      path,
      message: 'must be a non-empty safe object path',
    }]);
  }
  return rawValuePath;
}

function decodeFieldRef(value: unknown, path: string): ContractV2PageBlockFieldRef {
  const row = asRecord(value);
  const kind = asText(row.kind);
  const rawValuePath = decodeRawValuePath(row.rawValuePath, `${path}.rawValuePath`);
  if (kind === 'descriptor') {
    rejectUnknownKeys(row, DESCRIPTOR_REF_KEYS, path);
    const descriptorId = asText(row.descriptorId);
    if (!descriptorId) {
      throw new PageOrchestrationDecodeError([{ path, message: 'descriptor ref requires descriptorId only' }]);
    }
    return { kind, descriptorId, rawValuePath };
  }
  if (kind === 'widget') {
    rejectUnknownKeys(row, WIDGET_REF_KEYS, path);
    const widgetId = asText(row.widgetId);
    if (!widgetId) {
      throw new PageOrchestrationDecodeError([{ path, message: 'widget ref requires widgetId only' }]);
    }
    return { kind, widgetId, rawValuePath };
  }
  throw new PageOrchestrationDecodeError([{ path: `${path}.kind`, message: 'must be widget or descriptor' }]);
}

function decodeDataRows(value: unknown, path: string): ContractV2PageBlockDataRow[] {
  if (!Array.isArray(value)) {
    throw new PageOrchestrationDecodeError([{ path, message: 'must be an array' }]);
  }
  if (!value.length) {
    throw new PageOrchestrationDecodeError([{ path, message: 'must not be empty' }]);
  }
  const seen = new Set<string>();
  return value.map((raw, index) => {
    const row = asRecord(raw);
    rejectUnknownKeys(row, ROW_KEYS, `${path}[${index}]`);
    const rowKey = asText(row.rowKey);
    if (!rowKey || seen.has(rowKey)) {
      throw new PageOrchestrationDecodeError([{
        path: `${path}[${index}].rowKey`,
        message: 'must be unique and non-empty',
      }]);
    }
    seen.add(rowKey);
    if (!row.values || typeof row.values !== 'object' || Array.isArray(row.values)) {
      throw new PageOrchestrationDecodeError([{ path: `${path}[${index}].values`, message: 'must be an object' }]);
    }
    return { rowKey, values: row.values as ContractV2Dictionary };
  });
}

function decodeSourceAuthority(value: unknown, path: string): ContractV2Dictionary {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new PageOrchestrationDecodeError([{ path, message: 'must be an object' }]);
  }
  const authority = value as ContractV2Dictionary;
  rejectUnknownKeys(authority, SOURCE_AUTHORITY_KEYS, path);
  if (asText(authority.kind) !== PAGE_BLOCK_SOURCE_KIND) {
    throw new PageOrchestrationDecodeError([{
      path: `${path}.kind`,
      message: `must be ${PAGE_BLOCK_SOURCE_KIND}`,
    }]);
  }
  if (authority.projectionOnly !== true) {
    throw new PageOrchestrationDecodeError([{ path: `${path}.projectionOnly`, message: 'must be true' }]);
  }
  if (authority.noFrontendDefaults !== true) {
    throw new PageOrchestrationDecodeError([{ path: `${path}.noFrontendDefaults`, message: 'must be true' }]);
  }
  if (asText(authority.carrier) !== PAGE_BLOCK_SOURCE_CARRIER) {
    throw new PageOrchestrationDecodeError([{
      path: `${path}.carrier`,
      message: `must be ${PAGE_BLOCK_SOURCE_CARRIER}`,
    }]);
  }
  if (asText(authority.schemaVersion) !== PAGE_BLOCK_SOURCE_SCHEMA_VERSION) {
    throw new PageOrchestrationDecodeError([{
      path: `${path}.schemaVersion`,
      message: `must be ${PAGE_BLOCK_SOURCE_SCHEMA_VERSION}`,
    }]);
  }
  if (
    !Array.isArray(authority.authorities)
    || authority.authorities.length !== PAGE_BLOCK_SOURCE_AUTHORITIES.length
    || authority.authorities.some((item, index) => item !== PAGE_BLOCK_SOURCE_AUTHORITIES[index])
  ) {
    throw new PageOrchestrationDecodeError([{
      path: `${path}.authorities`,
      message: `must exactly be ${PAGE_BLOCK_SOURCE_AUTHORITIES.join(', ')}`,
    }]);
  }
  return authority;
}

function decodeCurrencies(value: unknown, path: string): Record<string, ContractV2Dictionary> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new PageOrchestrationDecodeError([{ path, message: 'must be an object' }]);
  }
  const decoded: Record<string, ContractV2Dictionary> = {};
  Object.entries(value as Record<string, unknown>).forEach(([identity, raw]) => {
    if (!identity.trim() || FORBIDDEN_PATH_SEGMENTS.has(identity)) {
      throw new PageOrchestrationDecodeError([{ path: `${path}.${identity}`, message: 'identity is invalid' }]);
    }
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
      throw new PageOrchestrationDecodeError([{ path: `${path}.${identity}`, message: 'must be an object' }]);
    }
    const currency = raw as ContractV2Dictionary;
    rejectUnknownKeys(currency, CURRENCY_KEYS, `${path}.${identity}`);
    if (currency.id !== undefined && String(currency.id).trim() !== identity) {
      throw new PageOrchestrationDecodeError([{
        path: `${path}.${identity}.id`,
        message: 'must match the currency identity key',
      }]);
    }
    for (const key of ['id', 'code', 'label', 'symbol']) {
      if (currency[key] !== undefined && String(currency[key]).trim() === '') {
        throw new PageOrchestrationDecodeError([{
          path: `${path}.${identity}.${key}`,
          message: 'must be non-empty when present',
        }]);
      }
    }
    if (!['code', 'label', 'symbol'].some((key) => asText(currency[key]))) {
      throw new PageOrchestrationDecodeError([{
        path: `${path}.${identity}`,
        message: 'must declare at least one of code, label or symbol',
      }]);
    }
    decoded[identity] = currency;
  });
  return decoded;
}

function decodePageBlockDataContract(
  raw: unknown,
  path: string,
): ContractV2PageBlockDataContract {
  const source = asRecord(raw);
  rejectUnknownKeys(source, PAGE_BLOCK_DATA_KEYS, path);
  if (asText(source.schemaVersion) !== '1.0.0') {
    throw new PageOrchestrationDecodeError([{ path: `${path}.schemaVersion`, message: 'must be 1.0.0' }]);
  }
  const refsRaw = asRecord(source.fieldRefs);
  const fieldRefs = Object.fromEntries(
    Object.entries(refsRaw).map(([key, value]) => {
      if (!FIELD_IDENTIFIER_PATTERN.test(key) || FORBIDDEN_PATH_SEGMENTS.has(key)) {
        throw new PageOrchestrationDecodeError([{
          path: `${path}.fieldRefs.${key}`,
          message: 'field ref identity is invalid',
        }]);
      }
      return [key, decodeFieldRef(value, `${path}.fieldRefs.${key}`)];
    }),
  );
  if (!Object.keys(fieldRefs).length) {
    throw new PageOrchestrationDecodeError([{ path: `${path}.fieldRefs`, message: 'must not be empty' }]);
  }
  const context = asRecord(source.context);
  rejectUnknownKeys(context, PAGE_BLOCK_CONTEXT_KEYS, `${path}.context`);
  const currencies = decodeCurrencies(context.currencies, `${path}.context.currencies`);
  const timezone = asText(context.timezone);
  if (!timezone) {
    throw new PageOrchestrationDecodeError([{ path: `${path}.context.timezone`, message: 'must be non-empty' }]);
  }
  return {
    schemaVersion: '1.0.0',
    fieldRefs,
    rows: decodeDataRows(source.rows, `${path}.rows`),
    context: { currencies, timezone },
    sourceAuthority: decodeSourceAuthority(source.sourceAuthority, `${path}.sourceAuthority`),
  };
}

export function decodePageOrchestrationContract(raw: unknown): PageOrchestrationContract {
  const source = asRecord(raw);
  const version = asText(source.contract_version);
  const schemaVersion = asText(source.schema_version);
  const issues: Array<{ path: string; message: string }> = [];
  if (version !== '2.0.0' && version !== '2.1.0') {
    issues.push({ path: 'page_orchestration.contract_version', message: 'must be 2.0.0 or 2.1.0' });
  }
  if (schemaVersion !== version) {
    issues.push({ path: 'page_orchestration.schema_version', message: 'must match contract_version' });
  }
  Object.keys(source).forEach((key) => {
    if (!PAGE_ORCHESTRATION_KEYS.has(key)) {
      issues.push({ path: `page_orchestration.${key}`, message: 'is not allowed' });
    }
  });
  if (version === '2.0.0' && (
    source.block_field_descriptors !== undefined || source.block_data_contracts !== undefined
  )) {
    issues.push({ path: 'page_orchestration', message: '2.0.0 cannot contain page-block-data carriers' });
  }
  if (issues.length) throw new PageOrchestrationDecodeError(issues);
  if (version === '2.0.0') {
    return {
      ...source,
      schema_version: schemaVersion,
      contract_version: version,
    } as PageOrchestrationContract;
  }
  if (!Object.keys(asRecord(source.block_field_descriptors)).length) {
    throw new PageOrchestrationDecodeError([{
      path: 'page_orchestration.block_field_descriptors',
      message: '2.1.0 requires at least one descriptor',
    }]);
  }
  if (!Object.keys(asRecord(source.block_data_contracts)).length) {
    throw new PageOrchestrationDecodeError([{
      path: 'page_orchestration.block_data_contracts',
      message: '2.1.0 requires at least one page-block-data contract',
    }]);
  }
  let decodedDescriptors;
  try {
    decodedDescriptors = decodeContractV2FieldDescriptorMap(
      source.block_field_descriptors,
      'page_orchestration.block_field_descriptors',
    );
  } catch (error) {
    if (error instanceof FieldDescriptorDecodeError) {
      throw new PageOrchestrationDecodeError(error.issues.map((item) => ({ path: item.path, message: item.code })));
    }
    throw error;
  }
  const rawDataContracts = asRecord(source.block_data_contracts);
  const dataContracts = Object.fromEntries(
    Object.entries(rawDataContracts).map(([key, value]) => [
      key,
      decodePageBlockDataContract(value, `page_orchestration.block_data_contracts.${key}`),
    ]),
  );
  return {
    ...source,
    schema_version: schemaVersion,
    contract_version: version,
    block_field_descriptors: decodedDescriptors.descriptors,
    block_data_contracts: dataContracts,
  } as PageOrchestrationContract;
}

function readPath(value: unknown, path: string): { found: boolean; value: unknown } {
  let current = value;
  for (const segment of Array.from(path.matchAll(/[^.]+/g), (match) => match[0])) {
    if (
      !current
      || typeof current !== 'object'
      || Array.isArray(current)
      || !Object.prototype.hasOwnProperty.call(current, segment)
    ) {
      return { found: false, value: undefined };
    }
    current = (current as Record<string, unknown>)[segment];
  }
  return { found: true, value: current };
}

function currencyIdentityOf(value: unknown): string {
  if (Array.isArray(value)) return String(value[0] ?? '').trim();
  if (value && typeof value === 'object') {
    return String((value as Record<string, unknown>).id ?? '').trim();
  }
  return value === undefined || value === null ? '' : String(value).trim();
}

function validateMoneyCurrency(
  dataSourceKey: string,
  row: PageBlockDataResolvedRow,
): void {
  Object.entries(row.fieldDescriptors).forEach(([slotKey, descriptor]) => {
    if (descriptor.semanticType !== 'money') return;
    const value = row.values[slotKey];
    if (
      !Object.prototype.hasOwnProperty.call(row.values, slotKey)
      || value === null
      || value === false
      || value === ''
    ) return;
    const currencyField = asText(descriptor.currencyField);
    const currencySlots = Object.entries(row.fieldDescriptors)
      .filter(([candidateSlot, candidate]) => (
        candidateSlot !== slotKey
        && (candidateSlot === currencyField || candidate.fieldCode === currencyField)
        && candidate.semanticType === 'relation'
        && candidate.relation === 'res.currency'
      ));
    if (currencySlots.length !== 1) {
      throw new PageOrchestrationDecodeError([{
        path: `block_data_contracts.${dataSourceKey}.rows.${row.rowKey}.${slotKey}`,
        message: 'money value requires exactly one currency descriptor',
      }]);
    }
    const identity = currencyIdentityOf(row.values[currencySlots[0][0]]);
    if (!currencyField || !identity || !row.context.currencies[identity]) {
      throw new PageOrchestrationDecodeError([{
        path: `block_data_contracts.${dataSourceKey}.rows.${row.rowKey}.${slotKey}`,
        message: 'money value requires a uniquely resolvable currency identity',
      }]);
    }
  });
}

export function resolvePageBlockData(
  contract: PageOrchestrationContract,
  dataSourceKey: string,
  widgetFieldDescriptors: Record<string, ContractV2FieldDescriptor> = {},
): PageBlockDataResolvedRow[] {
  const block = contract.block_data_contracts?.[dataSourceKey];
  if (!block) return [];
  return block.rows.map((row) => {
    const values: ContractV2Dictionary = {};
    const fieldDescriptors: Record<string, ContractV2FieldDescriptor> = {};
    const registryResolution: PageBlockDataResolvedRow['registryResolution'] = {};
    Object.entries(block.fieldRefs).forEach(([slotKey, ref]) => {
      const located = readPath(row.values, ref.rawValuePath);
      const descriptor = ref.kind === 'descriptor'
        ? contract.block_field_descriptors?.[ref.descriptorId]
        : widgetFieldDescriptors[ref.widgetId];
      if (!descriptor) {
        throw new PageOrchestrationDecodeError([{
          path: `block_data_contracts.${dataSourceKey}.fieldRefs.${slotKey}`,
          message: `${ref.kind} descriptor cannot be resolved`,
        }]);
      }
      if (located.found) values[slotKey] = located.value;
      fieldDescriptors[slotKey] = descriptor;
      try {
        registryResolution[slotKey] = decodeContractV2FieldDescriptor(descriptor, `descriptor.${slotKey}`).registryResolution;
      } catch (error) {
        if (error instanceof FieldDescriptorDecodeError) {
          throw new PageOrchestrationDecodeError(error.issues.map((item) => ({ path: item.path, message: item.code })));
        }
        throw error;
      }
    });
    const resolved = {
      rowKey: row.rowKey,
      values,
      fieldDescriptors,
      registryResolution,
      context: block.context,
    };
    validateMoneyCurrency(dataSourceKey, resolved);
    return resolved;
  });
}
