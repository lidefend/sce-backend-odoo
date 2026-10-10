import type { ContractAction } from './types';
import {
  contractV2SurfaceAuthorizationAllows,
  resolveContractV2FormStructureContract,
  resolveContractV2SourceContext,
} from '../../app/contracts/v2/store';
import type { ContractV2FormStructureSurface, ContractV2NormalizedStore } from '../../app/contracts/v2/types';
import { normalizeRouteDefault } from './valueUtils';

export type FormContractReadiness = {
  usable: boolean;
  issues: string[];
  fieldCount: number;
  layoutFieldCount: number;
  visibleCandidateCount: number;
};

/**
 * Return only the server-projected context carried by the normalized action
 * contract. Route/query context is intentionally excluded: record reads may
 * consume the formal action authority, but must not trust arbitrary client
 * context as an ORM override.
 */
export function resolveContractFormReadContext(store: ContractV2NormalizedStore | null) {
  const context = resolveContractV2SourceContext(store).context;
  return context ? { ...context } : {};
}

export function buildRouteContractContext(routeQuery: Record<string, unknown>) {
  const context: Record<string, unknown> = {};
  Object.entries(routeQuery).forEach(([key, value]) => {
    if (key.startsWith('default_')) context[key] = normalizeRouteDefault(value);
  });
  [
    'current_business_category_code',
    'default_business_category_code',
    'allowed_business_category_codes',
    'current_business_category_label',
    'default_business_category_label',
  ].forEach((key) => {
    const value = routeQuery[key];
    if (value === undefined || value === null || value === '') return;
    if (Array.isArray(value)) {
      const items = value.map((item) => String(item || '').trim()).filter((item) => item !== '');
      if (items.length) context[key] = items;
      return;
    }
    const text = String(value).trim();
    if (text) context[key] = text;
  });
  const intakeMode = String(routeQuery.intake_mode || '').trim().toLowerCase();
  if (intakeMode === 'quick' || intakeMode === 'standard') context.intake_mode = intakeMode;
  return context;
}

export function collectRuntimeCapabilities(session: {
  capabilities?: unknown[];
  capabilityCatalog?: Record<string, { key?: unknown; state?: unknown; capability_state?: unknown }>;
}) {
  const out = new Set<string>();
  (session.capabilities || []).forEach((key) => {
    const normalized = String(key || '').trim();
    if (normalized) out.add(normalized);
  });
  Object.values(session.capabilityCatalog || {}).forEach((meta) => {
    const key = String(meta?.key || '').trim();
    if (!key) return;
    const state = String(meta?.state || '').trim().toUpperCase();
    const capState = String(meta?.capability_state || '').trim().toLowerCase();
    if (state === 'LOCKED' || capState === 'deny') return;
    out.add(key);
  });
  return out;
}

export function normalizeContractWarnings(rows: unknown) {
  if (!Array.isArray(rows)) return [];
  return rows
    .map((row) => {
      if (typeof row === 'string') return row;
      if (row && typeof row === 'object') {
        return String((row as Record<string, unknown>).message || (row as Record<string, unknown>).code || '');
      }
      return '';
    })
    .map((item) => item.trim())
    .filter((item) => Boolean(item) && !item.startsWith('access_policy:'));
}

export function normalizeSearchFilters(rows: unknown) {
  if (!Array.isArray(rows)) return [];
  return rows
    .map((row) => {
      const item = row && typeof row === 'object' && !Array.isArray(row)
        ? row as Record<string, unknown>
        : {};
      return {
        key: String(item.key || '').trim(),
        label: String(item.label || item.key || '').trim(),
        domainRaw: String(item.domain_raw || '').trim(),
        contextRaw: String(item.context_raw || '').trim(),
      };
    })
    .filter((row) => row.key && row.label);
}

export function resolveBusinessCategoryContext(params: {
  contractRecord: unknown;
  routeQuery: Record<string, unknown>;
  relationBusinessCategoryLabel: string;
  relationBusinessCategorySelected: boolean;
}) {
  const query = params.routeQuery;
  return {
    label: String(
      query.current_business_category_label
      || query.default_business_category_label
      || (params.relationBusinessCategorySelected ? params.relationBusinessCategoryLabel : '')
      || '',
    ).trim(),
    code: String(
      query.current_business_category_code
      || query.default_business_category_code
      || '',
    ).trim(),
  };
}

export function buildWorkflowTransitions(params: {
  rows: unknown;
  actions: ContractAction[];
  profile: 'create' | 'edit' | 'readonly';
  showHud: boolean;
}) {
  if (!Array.isArray(params.rows)) return [];
  if (params.profile === 'create') return [];
  const headerActionKeys = new Set(
    params.actions
      .filter((item) => item.level === 'header' || item.level === 'toolbar')
      .map((item) => item.key),
  );
  const transitions = params.rows.map((raw, idx) => {
    const row = raw && typeof raw === 'object' && !Array.isArray(raw)
      ? raw as Record<string, { label?: unknown; name?: unknown; kind?: unknown } | unknown>
      : {};
    const trigger = row.trigger && typeof row.trigger === 'object' && !Array.isArray(row.trigger)
      ? row.trigger as Record<string, unknown>
      : {};
    const triggerLabel = String(trigger.label || '').trim();
    const triggerName = String(trigger.name || '').trim();
    const triggerKind = String(trigger.kind || '').trim().toLowerCase();
    const action = params.actions.find((item) => {
      if (triggerKind && item.kind && item.kind !== triggerKind) return false;
      if (triggerName && (item.methodName === triggerName || item.key.includes(triggerName))) return true;
      if (triggerLabel && item.label === triggerLabel) return true;
      return false;
    }) || null;
    return {
      key: `wf_${idx}`,
      label: triggerLabel || triggerName || `transition_${idx + 1}`,
      notes: String(row.notes || ''),
      action,
    };
  });
  if (params.showHud) return transitions;
  return transitions.filter((item) => {
    const label = String(item.label || '').trim();
    if (!item.action) return false;
    if (item.action?.key && headerActionKeys.has(item.action.key)) return false;
    if (/^\d+$/.test(label)) return false;
    return true;
  });
}

export type ContractFormRuntimeRoleSurface = {
  role_code?: unknown;
  role_codes?: unknown;
};

export type ContractFormPolicyContext = {
  profile: string;
  formData: Record<string, unknown>;
  capabilities: Set<string>;
  roleCode: string;
  roleCodes: string[];
};

/** Single authority for the runtime role code carried by the session surface. */
export function resolveRuntimeRoleCode(roleSurface?: ContractFormRuntimeRoleSurface | null): string {
  return String(roleSurface?.role_code || '').trim().toLowerCase();
}

/** Runtime role codes fall back to the primary role code, then normalize each entry. */
export function resolveRuntimeRoleCodes(
  roleSurface?: ContractFormRuntimeRoleSurface | null,
  runtimeRoleCode = resolveRuntimeRoleCode(roleSurface),
): string[] {
  const configured = (roleSurface?.role_codes as unknown[]) || [];
  const roles = configured.length ? configured : [runtimeRoleCode];
  return roles.map((item) => String(item || '').trim().toLowerCase()).filter(Boolean);
}

/** Runtime policy inputs consumed by the contract form surface. */
export function buildContractFormPolicyContext(input: {
  profile: string;
  formData: Record<string, unknown>;
  session: Parameters<typeof collectRuntimeCapabilities>[0];
  roleSurface?: ContractFormRuntimeRoleSurface | null;
}): ContractFormPolicyContext {
  const roleCode = resolveRuntimeRoleCode(input.roleSurface);
  return {
    profile: input.profile,
    formData: input.formData,
    capabilities: collectRuntimeCapabilities(input.session),
    roleCode,
    roleCodes: resolveRuntimeRoleCodes(input.roleSurface, roleCode),
  };
}

/**
 * Structure authority declared by the runtime contract.  A surface whose form
 * structure is owned natively keeps its body for form facts only, no matter
 * whether the frontend composes the tree itself or the backend serves it.
 */
export function resolveNativeStructureAuthority(
  store: Parameters<typeof resolveContractV2FormStructureContract>[0],
): string {
  return String(
    resolveContractV2FormStructureContract(store)?.sourceAuthority?.governance_source?.formStructureAuthority || '',
  );
}

/**
 * Subordinate node kinds that own a collaboration surface.  This list is the
 * single declaration: `isCollaborationSurfaceKind` consumes it directly, so a
 * declared kind can never become inert data next to the predicate.
 */
export const COLLABORATION_SURFACE_KINDS = ['chatter', 'activity'] as const;

/** Single authority for "is this node kind a collaboration surface kind". */
export function isCollaborationSurfaceKind(kind: unknown): boolean {
  return (COLLABORATION_SURFACE_KINDS as readonly string[]).includes(
    String(kind || '').trim().toLowerCase(),
  );
}

/**
 * The declared collaboration surface for this identity, or null.
 * Single authority for the region: the contract declares the region or there is
 * none.  No runtime capability and no subordinate-node heuristic may open a
 * region the contract did not declare.
 *
 * `undefined` surfaces means the contract cannot declare regions at all, so
 * there is no declaration to find; an empty list means the contract declares
 * that this page publishes no surface.
 */
export function declaredCollaborationSurface(
  surfaces: readonly ContractV2FormStructureSurface[] | undefined | null,
): ContractV2FormStructureSurface | null {
  if (!Array.isArray(surfaces)) return null;
  return surfaces.find((surface) => surface.contentKind === 'collaboration-panel') || null;
}

/**
 * The role-gated audit sub-region renders only on an explicit `allow` for the
 * requesting identity.  A missing declaration, a `deny`, a `pending` or a
 * `coming_soon` all keep it hidden; runtime audit events are not an input.
 */
export function declaredAuditAuthorized(
  surfaces: readonly ContractV2FormStructureSurface[] | undefined | null,
): boolean {
  return contractV2SurfaceAuthorizationAllows(
    declaredCollaborationSurface(surfaces)?.audit?.authorization,
  );
}
