import type { ListColumnPreference } from '../../api/preferences';
import type { UserViewPreferenceContract } from '@sc/schema';
import { contractGapError, requireDeclaredBoolean } from '../contract/contractGap';

function gap(missing: string): never {
  throw contractGapError({ kind: 'contract_defect', missing,
    requiredDeclarationLayer: 'P0:smart_core:list_preference_projection' }, `Missing preference declaration: ${missing}`);
}

export function readStoredListPreference(result: UserViewPreferenceContract): ListColumnPreference {
  if (result.projection !== 'stored' || result.policy_source !== 'current_page_contract') gap('preference.projection');
  if (!result.preference || typeof result.preference !== 'object') gap('preference.value');
  return result.preference as ListColumnPreference;
}

export function readListPreferencePolicy(value: unknown) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) gap('list_profile.preference_policy');
  const raw = value as Record<string, unknown>;
  const names = (key: string) => {
    const rows = raw[key];
    if (!Array.isArray(rows) || rows.some(item => typeof item !== 'string' || !item.trim())) gap(`preference_policy.${key}`);
    return rows as string[];
  };
  const declared = (key: string) => requireDeclaredBoolean(raw[key], {
    missing: `preference_policy.${key}`, requiredDeclarationLayer: 'P0:smart_core:list_preference_projection',
  });
  return { scope: raw.scope as string | undefined,
    allow_visibility: declared('allow_visibility'), allow_order: declared('allow_order'), allow_width: declared('allow_width'),
    locked_columns: names('locked_columns'), must_request_columns: names('must_request_columns') };
}

/** Apply declared presentation policy; stored choices never add contract columns. */
export function projectStoredListPreference(value: ListColumnPreference, policyValue: unknown, columns: string[]): ListColumnPreference {
  const policy = readListPreferencePolicy(policyValue);
  const allowed = new Set(columns);
  const locked = new Set(policy.locked_columns);
  const keep = (rows: string[] | undefined) => (rows || []).filter(name => allowed.has(name));
  return {
    visible_columns: policy.allow_visibility ? keep(value.visible_columns) : [],
    hidden_columns: policy.allow_visibility ? keep(value.hidden_columns).filter(name => !locked.has(name)) : [],
    column_order: policy.allow_order ? keep(value.column_order) : [],
    column_widths: policy.allow_width ? Object.fromEntries(Object.entries(value.column_widths || {}).filter(([name]) => allowed.has(name))) : {},
  };
}
