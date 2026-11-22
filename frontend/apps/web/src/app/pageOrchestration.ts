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
  return rows.map((row, index) => {
    const legacy = legacyRows.find((item) => (
      String(item.key || item.id || '').trim() === row.rowKey
    )) || legacyRows[index] || {};
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
  const candidates: string[] = [];
  const currencySlot = Object.entries(row.fieldDescriptors)
    .find(([slotKey, descriptor]) => slotKey === field || descriptor.fieldCode === field);
  const currencyValue = currencySlot ? row.values[currencySlot[0]] : row.values[field];
  if (Array.isArray(currencyValue)) {
    candidates.push(String(currencyValue[0] ?? '').trim());
  } else if (currencyValue && typeof currencyValue === 'object') {
    const identity = currencyValue as Record<string, unknown>;
    candidates.push(String(identity.id ?? '').trim());
  } else if (currencyValue !== undefined && currencyValue !== null) {
    candidates.push(String(currencyValue).trim());
  }
  candidates.push(field);
  const identity = candidates.find((candidate) => candidate && row.context.currencies[candidate]);
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

function asRecord(value: unknown): ContractV2Dictionary {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as ContractV2Dictionary
    : {};
}

function asText(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function decodeFieldRef(value: unknown, path: string): ContractV2PageBlockFieldRef {
  const row = asRecord(value);
  const kind = asText(row.kind);
  const rawValuePath = asText(row.rawValuePath);
  if (!rawValuePath) {
    throw new PageOrchestrationDecodeError([{ path: `${path}.rawValuePath`, message: 'must be non-empty' }]);
  }
  if (kind === 'descriptor') {
    const descriptorId = asText(row.descriptorId);
    if (!descriptorId || asText(row.widgetId)) {
      throw new PageOrchestrationDecodeError([{ path, message: 'descriptor ref requires descriptorId only' }]);
    }
    return { kind, descriptorId, rawValuePath };
  }
  if (kind === 'widget') {
    const widgetId = asText(row.widgetId);
    if (!widgetId || asText(row.descriptorId)) {
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
  const seen = new Set<string>();
  return value.map((raw, index) => {
    const row = asRecord(raw);
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

function decodePageBlockDataContract(
  raw: unknown,
  path: string,
): ContractV2PageBlockDataContract {
  const source = asRecord(raw);
  if (asText(source.schemaVersion) !== '1.0.0') {
    throw new PageOrchestrationDecodeError([{ path: `${path}.schemaVersion`, message: 'must be 1.0.0' }]);
  }
  const refsRaw = asRecord(source.fieldRefs);
  const fieldRefs = Object.fromEntries(
    Object.entries(refsRaw).map(([key, value]) => [key, decodeFieldRef(value, `${path}.fieldRefs.${key}`)]),
  );
  if (!Object.keys(fieldRefs).length) {
    throw new PageOrchestrationDecodeError([{ path: `${path}.fieldRefs`, message: 'must not be empty' }]);
  }
  const context = asRecord(source.context);
  const currencies = asRecord(context.currencies) as Record<string, ContractV2Dictionary>;
  const timezone = asText(context.timezone);
  if (!timezone) {
    throw new PageOrchestrationDecodeError([{ path: `${path}.context.timezone`, message: 'must be non-empty' }]);
  }
  return {
    schemaVersion: '1.0.0',
    fieldRefs,
    rows: decodeDataRows(source.rows, `${path}.rows`),
    context: { currencies, timezone },
    sourceAuthority: asRecord(source.sourceAuthority),
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
    if (!current || typeof current !== 'object' || Array.isArray(current) || !(segment in current)) {
      return { found: false, value: undefined };
    }
    current = (current as Record<string, unknown>)[segment];
  }
  return { found: true, value: current };
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
    return {
      rowKey: row.rowKey,
      values,
      fieldDescriptors,
      registryResolution,
      context: block.context,
    };
  });
}
