import {
  resolveUnifiedPageContractV2MainData,
  resolveUnifiedPageContractV2SourceContext,
} from '../../app/contracts/unifiedPageContractV2';
import type { ContractV2NormalizedStore } from '../../app/contracts/v2/types';
import { normalizeRouteDefault } from './valueUtils';

export interface CreateDefaultGetRequest {
  model: string;
  fields: string[];
  context: Record<string, unknown>;
}

function createDefaultsDictionary(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function createDefaultFieldType(store: ContractV2NormalizedStore | null, fieldName: string): string {
  const descriptor = store?.widgetsByFieldCodeAll?.get(fieldName)?.find((widget) => widget.fieldDescriptor)?.fieldDescriptor;
  return String(descriptor?.type || descriptor?.ttype || '').trim().toLowerCase();
}

function hasCreateDefaultValue(value: unknown, fieldType = ''): boolean {
  if (value === null || value === undefined || value === '') return false;
  if (value === false) return fieldType === 'boolean';
  if (typeof value === 'number') return Number.isFinite(value) && value !== 0;
  if (Array.isArray(value)) return value.length > 0;
  return true;
}

function routeDefaultFieldName(key: string): string {
  const fieldName = String(key || '').replace(/^default_/, '').trim();
  return fieldName.endsWith('_label') ? '' : fieldName;
}

export function createRouteDefaultsFingerprint(routeQuery: Record<string, unknown>): string {
  return JSON.stringify(
    Object.entries(routeQuery)
      .filter(([key]) => key.startsWith('default_'))
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, value]) => [key, normalizeRouteDefault(value)]),
  );
}

export function shouldHydrateCreateDefaults(recordId: number | null, renderProfile: string): boolean {
  return !recordId && String(renderProfile || '').trim().toLowerCase() === 'create';
}

export function resolveCreateDefaultGetRequest(params: {
  primaryDataSource: Record<string, unknown>;
  model: string;
  fieldNames: string[];
}): CreateDefaultGetRequest | null {
  const source = createDefaultsDictionary(params.primaryDataSource);
  if (!Object.keys(source).length) return null;
  const query = String(source.query || source.intent || '').trim();
  const intent = String(source.intent || source.query || '').trim();
  const sourceParams = createDefaultsDictionary(source.params);
  const operation = String(sourceParams.op || '').trim().toLowerCase();
  const sourceModel = String(sourceParams.model || '').trim();
  const expectedModel = String(params.model || '').trim();
  if (query !== 'api.data' || intent !== 'api.data' || operation !== 'default_get') {
    throw new Error('create contract primary data source must declare api.data/default_get');
  }
  if (!expectedModel || sourceModel !== expectedModel) {
    throw new Error('create contract primary data source model mismatch');
  }
  if (!Array.isArray(sourceParams.fields)) {
    throw new Error('create contract primary data source fields are required');
  }
  const allowedFields = new Set(params.fieldNames.map((name) => String(name || '').trim()).filter(Boolean));
  const fields = [...new Set(sourceParams.fields
    .map((name) => String(name || '').trim())
    .filter((name) => name && allowedFields.has(name)))]
    .sort();
  if (!fields.length) {
    throw new Error('create contract primary data source has no applicable fields');
  }
  const context = sourceParams.context;
  if (context !== undefined && (!context || typeof context !== 'object' || Array.isArray(context))) {
    throw new Error('create contract primary data source context must be an object');
  }
  return {
    model: sourceModel,
    fields,
    context: createDefaultsDictionary(context),
  };
}

export function mergeAuthoritativeCreateDefaults(params: {
  baseDefaults: Record<string, unknown>;
  authoritativeDefaults: unknown;
  fieldNames: string[];
}): Record<string, unknown> {
  const allowedFields = new Set(params.fieldNames.map((name) => String(name || '').trim()).filter(Boolean));
  const authoritative = createDefaultsDictionary(params.authoritativeDefaults);
  const merged = { ...params.baseDefaults };
  Object.entries(authoritative).forEach(([name, value]) => {
    if (allowedFields.has(name)) merged[name] = value;
  });
  return merged;
}

export async function loadAuthoritativeCreateDefaults(params: {
  primaryDataSource: Record<string, unknown>;
  model: string;
  fieldNames: string[];
  baseDefaults: Record<string, unknown>;
  fetchDefaults: (request: CreateDefaultGetRequest) => Promise<{ record?: Record<string, unknown> }>;
}): Promise<Record<string, unknown>> {
  const request = resolveCreateDefaultGetRequest(params);
  if (!request) return { ...params.baseDefaults };
  const result = await params.fetchDefaults(request);
  if (!result || !result.record || typeof result.record !== 'object' || Array.isArray(result.record)) {
    throw new Error('create default_get response record is required');
  }
  return mergeAuthoritativeCreateDefaults({
    baseDefaults: params.baseDefaults,
    authoritativeDefaults: result?.record,
    fieldNames: params.fieldNames,
  });
}

export function formCreateContext(params: {
  v2ContractStore: ContractV2NormalizedStore | null;
}) {
  const storeContext = resolveUnifiedPageContractV2SourceContext(params.v2ContractStore?.snapshot);
  return storeContext.context || {};
}

export function resolveCreateDefaults(params: {
  routeQuery: Record<string, unknown>;
  v2ContractStore: ContractV2NormalizedStore | null;
}) {
  const storeMainData = resolveUnifiedPageContractV2MainData(params.v2ContractStore?.snapshot);
  const defaults: Record<string, unknown> = { ...storeMainData };
  Object.entries(params.routeQuery).forEach(([key, value]) => {
    if (!key.startsWith('default_')) return;
    const fieldName = routeDefaultFieldName(key);
    if (!fieldName || hasCreateDefaultValue(defaults[fieldName], createDefaultFieldType(params.v2ContractStore, fieldName))) return;
    defaults[fieldName] = normalizeRouteDefault(value);
  });
  const context = formCreateContext(params);
  Object.entries(context).forEach(([key, value]) => {
    if (!key.startsWith('default_')) return;
    const fieldName = routeDefaultFieldName(key);
    if (!fieldName || hasCreateDefaultValue(defaults[fieldName], createDefaultFieldType(params.v2ContractStore, fieldName))) return;
    defaults[fieldName] = value;
  });
  return defaults;
}

export function resolveCreateRouteRelationLabels(
  store: ContractV2NormalizedStore | null,
  routeQuery: Record<string, unknown>,
  defaults: Record<string, unknown>,
): Record<string, string> {
  return Object.entries(routeQuery).reduce<Record<string, string>>((labels, [key, value]) => {
    if (!key.startsWith('default_') || !key.endsWith('_label')) return labels;
    const fieldName = key.replace(/^default_/, '').replace(/_label$/, '').trim();
    if (createDefaultFieldType(store, fieldName) !== 'many2one') return labels;
    const relationId = Number(defaults[fieldName] || 0);
    const routeRelationId = Number(normalizeRouteDefault(routeQuery[`default_${fieldName}`]) || 0);
    const label = String(Array.isArray(value) ? value[value.length - 1] : value || '').trim();
    if (
      fieldName
      && Number.isFinite(relationId)
      && relationId > 0
      && relationId === routeRelationId
      && label
    ) labels[fieldName] = label;
    return labels;
  }, {});
}
