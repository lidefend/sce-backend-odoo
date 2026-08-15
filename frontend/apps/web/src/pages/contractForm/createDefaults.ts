import type { ActionContract } from '@sc/schema';
import {
  resolveUnifiedPageContractV2MainData,
  resolveUnifiedPageContractV2SourceContext,
} from '../../app/contracts/unifiedPageContractV2';
import type { ContractV2NormalizedStore } from '../../app/contracts/v2/types';
import { normalizeRouteDefault } from './valueUtils';

function createDefaultFieldType(contract: ActionContract | null, fieldName: string): string {
  const descriptor = contract?.fields?.[fieldName] as Record<string, unknown> | undefined;
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

export function formCreateContext(params: {
  contract: ActionContract | null;
  v2ContractStore: ContractV2NormalizedStore | null;
}) {
  const storeContext = resolveUnifiedPageContractV2SourceContext(params.v2ContractStore);
  return (Object.keys(storeContext).length ? storeContext : resolveUnifiedPageContractV2SourceContext(params.contract)).context || {};
}

export function resolveCreateDefaults(params: {
  contract: ActionContract | null;
  routeQuery: Record<string, unknown>;
  v2ContractStore: ContractV2NormalizedStore | null;
}) {
  const storeMainData = resolveUnifiedPageContractV2MainData(params.v2ContractStore);
  const defaults: Record<string, unknown> = {
    ...(Object.keys(storeMainData).length ? storeMainData : resolveUnifiedPageContractV2MainData(params.contract)),
  };
  Object.entries(params.routeQuery).forEach(([key, value]) => {
    if (!key.startsWith('default_')) return;
    const fieldName = routeDefaultFieldName(key);
    if (!fieldName || hasCreateDefaultValue(defaults[fieldName], createDefaultFieldType(params.contract, fieldName))) return;
    defaults[fieldName] = normalizeRouteDefault(value);
  });
  const context = formCreateContext(params);
  Object.entries(context).forEach(([key, value]) => {
    if (!key.startsWith('default_')) return;
    const fieldName = routeDefaultFieldName(key);
    if (!fieldName || hasCreateDefaultValue(defaults[fieldName], createDefaultFieldType(params.contract, fieldName))) return;
    defaults[fieldName] = value;
  });
  const validator = params.contract?.validator as Record<string, unknown> | undefined;
  const defaultsSample = validator?.defaults_sample;
  if (defaultsSample && typeof defaultsSample === 'object' && !Array.isArray(defaultsSample)) {
    Object.entries(defaultsSample as Record<string, unknown>).forEach(([key, value]) => {
      if (!hasCreateDefaultValue(defaults[key], createDefaultFieldType(params.contract, key))) {
        defaults[key] = value === 'dynamic' ? '' : value;
      }
    });
  }
  return defaults;
}

export function resolveCreateRouteRelationLabels(
  contract: ActionContract | null,
  routeQuery: Record<string, unknown>,
  defaults: Record<string, unknown>,
): Record<string, string> {
  return Object.entries(routeQuery).reduce<Record<string, string>>((labels, [key, value]) => {
    if (!key.startsWith('default_') || !key.endsWith('_label')) return labels;
    const fieldName = key.replace(/^default_/, '').replace(/_label$/, '').trim();
    if (createDefaultFieldType(contract, fieldName) !== 'many2one') return labels;
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
