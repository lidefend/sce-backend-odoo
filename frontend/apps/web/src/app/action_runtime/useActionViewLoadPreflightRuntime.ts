import {
  resolveContractV2FieldWidgets,
  resolveContractV2PrimaryDataSource,
  resolveContractV2SearchContract,
} from '../contracts/v2/store';
import type { ContractV2NormalizedStore } from '../contracts/v2/types';

type Dict = Record<string, unknown>;
type SavedFilterChip = { key: string; isDefault: boolean };
type GroupByChip = { field: string; isDefault: boolean };

function collectOrderCandidateFields(value: unknown, fields: Set<string>): void {
  if (!value) return;
  if (Array.isArray(value)) {
    value.forEach((item) => collectOrderCandidateFields(item, fields));
    return;
  }
  if (typeof value !== 'object') return;
  const row = value as Dict;
  ['name', 'field', 'field_name', 'fieldCode', 'field_code'].forEach((key) => {
    const text = String(row[key] || '').trim();
    if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(text)) fields.add(text);
  });
  Object.values(row).forEach((item) => {
    if (item && typeof item === 'object') collectOrderCandidateFields(item, fields);
  });
}

function collectContractOrderFields(contract: ContractV2NormalizedStore): Set<string> {
  const fields = new Set<string>(['id', 'name', 'display_name']);
  resolveContractV2FieldWidgets(contract).forEach((widget) => fields.add(widget.fieldCode));
  collectOrderCandidateFields(resolveContractV2PrimaryDataSource(contract), fields);
  collectOrderCandidateFields(resolveContractV2SearchContract(contract), fields);
  return fields;
}

function sanitizeOrderValue(order: unknown, allowedFields: Set<string>): string {
  const clauses: string[] = [];
  String(order || '').split(',').forEach((rawClause) => {
    const text = rawClause.trim();
    if (!text) return;
    const parts = text.split(/\s+/);
    const field = String(parts[0] || '').trim();
    const direction = String(parts[1] || 'asc').trim().toLowerCase();
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(field)) return;
    if (!allowedFields.has(field)) return;
    if (direction !== 'asc' && direction !== 'desc') return;
    clauses.push(`${field} ${direction}`);
  });
  return clauses.join(', ');
}

type ExecuteLoadPreflightOptions = {
  isLoadCurrent?: () => boolean;
  sessionMenuTree: unknown;
  actionId: number;
  actionMeta: Dict | null;
  routeQueryMap: Dict;
  routeViewModeRaw: unknown;
  routeFilterRaw: unknown;
  routeSavedFilterRaw: unknown;
  routeGroupByRaw: unknown;
  routeGroupClearedRaw?: unknown;
  routeGroupValueRaw?: unknown;
  sceneReadyDefaultSortRaw: unknown;
  sceneDefaultSortRaw: unknown;
  sessionCapabilities: unknown;
  currentSortRaw: string;
  activeContractFilterKey: string;
  activeSavedFilterKey: string;
  activeGroupByField: string;
  contractSavedFilterChips: Array<Record<string, unknown>>;
  contractGroupByChips: Array<Record<string, unknown>>;
  currentPreferredViewModeRaw: string;
  buildWorkbenchRouteTarget: (input: { query: Dict }) => unknown;
  resolveWorkbenchQuery: (reason: string, payload?: { public?: Dict; diag?: Dict }) => Dict;
  buildModelFormRouteTarget: (input: { model: string; id: string; query: Dict }) => unknown;
  resolveCarryQuery: (extra?: Dict) => Dict;
  extractActionResId: (input: unknown) => number | null;
  resolveAction: (menuTree: unknown, actionId: number, actionMeta: Dict | null) => Promise<{ contract: ContractV2NormalizedStore; meta?: Dict | null }>;
  setActionMeta: (meta: Dict) => void;
  resolveContractViewMode: (contract: ContractV2NormalizedStore) => string;
  resolveActionViewType: (meta: unknown, contract: unknown) => string;
  resolvePreferredActionViewMode: (input: Dict) => string;
  resolveRouteSelectionState: (input: Dict) => Dict;
  resolveRouteSelectionApplyState: (input: { routeSelection: Dict }) => {
    activeContractFilterKey: string;
    activeSavedFilterKey: string;
    activeGroupByField: string;
  };
  resolveContractAccessPolicy: (contract: ContractV2NormalizedStore) => { reasonCode?: unknown; mode?: unknown };
  resolveContractReadRight: (contract: ContractV2NormalizedStore) => boolean;
  resolveLoadPreflightContractFlags: (input: Dict) => Dict;
  resolveContractFlagApplyState: (input: { contractFlags: Dict }) => {
    contractReadAllowed: boolean;
    contractWarningCount: number;
    contractDegraded: boolean;
  };
  resolveLoadContractReadRedirectPayload: (input: Dict) => Dict;
  resolveCapabilityMissingRedirectTarget: (input: {
    capabilityMissingCode: string;
    guardPayload: Dict;
    buildWorkbenchRouteTargetFn: (input: { query: Dict }) => unknown;
    resolveWorkbenchQueryFn: (reason: string, payload?: { public?: Dict; diag?: Dict }) => Dict;
  }) => unknown;
  isUrlAction: (meta: unknown, contract: unknown) => boolean;
  redirectUrlAction: (meta: unknown, contract: unknown) => Promise<boolean>;
  extractListOrderFromContract: (contract: ContractV2NormalizedStore) => string;
  resolveLoadPreflightSortValue: (input: Dict) => string;
  resolveLoadPreflightContractLimit: (input: Dict) => number;
  evaluateCapabilityPolicy: (input: { source: unknown; available: unknown; required?: string[] }) => { state?: unknown; missing?: unknown };
  resolveLoadCapabilityRedirectPayload: (input: Dict) => Dict;
  resolveModelFromContract: (contract: ContractV2NormalizedStore) => string;
  resolveActionViewResolvedModel: (input: Dict) => string;
  isClientAction: (meta: unknown) => boolean;
  isWindowAction: (meta: unknown) => boolean;
  getActionType: (meta: unknown) => string;
  resolveLoadMissingModelRedirectDecision: (input: Dict) => Dict;
  resolveMissingModelRedirectTarget: (input: {
    missingModelRedirect: Dict;
    buildWorkbenchRouteTargetFn: (input: { query: Dict }) => unknown;
    resolveWorkbenchQueryFn: (reason: string, payload?: { public?: Dict; diag?: Dict }) => Dict;
  }) => unknown;
  resolveLoadFormActionResId: (input: Dict) => number | null;
  resolveLoadMissingContractViewTypeErrorState: () => Dict;
  resolveLoadMissingViewTypeApplyState: (input: { missingViewTypeState: Dict; currentErrorMessage: string }) => {
    message: string;
    statusInput: string;
  };
  resolveLoadMissingResolvedModelErrorState: () => Dict;
  resolveLoadMissingResolvedModelApplyState: (input: { missingModelErrorState: Dict; currentErrorMessage: string }) => {
    message: string;
    statusInput: string;
  };
  capabilityMissingCode: string;
};

function normalizeRequiredCapabilities(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => String(item || '').trim()).filter(Boolean);
  }
  if (typeof value === 'string' && value.trim()) {
    return [value.trim()];
  }
  return [];
}

function resolveActionRequiredCapabilities(meta: Dict | null): string[] {
  if (!meta) {
    return [];
  }
  return [
    ...normalizeRequiredCapabilities(meta.required_capabilities),
    ...normalizeRequiredCapabilities(meta.requiredCapabilities),
  ];
}

export type ExecuteLoadPreflightResult =
  | { kind: 'blocked'; message: string; statusInput: string }
  | { kind: 'redirect'; target: unknown }
  | { kind: 'handled' }
  | {
      kind: 'continue';
      contract: ContractV2NormalizedStore;
      meta: Dict | null;
      contractViewType: string;
      preferredViewMode: string;
      activeContractFilterKey: string;
      activeSavedFilterKey: string;
      activeGroupByField: string;
      contractReadAllowed: boolean;
      contractWarningCount: number;
      contractDegraded: boolean;
      contractLimit: number;
      resolvedModel: string;
      setMetaModel: string;
      sortValue: string;
    };

function searchContract(contract: ContractV2NormalizedStore): Dict {
  return resolveContractV2SearchContract(contract);
}

function deriveSavedFilterChipsFromContract(contract: ContractV2NormalizedStore): SavedFilterChip[] {
  const rows = searchContract(contract).saved_filters;
  if (!Array.isArray(rows)) return [];
  return rows
    .map((row, idx) => {
      const raw = row && typeof row === 'object' ? row as Dict : {};
      const key = String(raw.key || raw.name || raw.xmlid || raw.xml_id || `saved_${idx + 1}`).trim();
      if (!key) return null;
      return {
        key,
        isDefault: raw.default === true || raw.is_default === true,
      };
    })
    .filter((row): row is SavedFilterChip => Boolean(row));
}

function deriveGroupByChipsFromContract(contract: ContractV2NormalizedStore): GroupByChip[] {
  const search = searchContract(contract);
  const custom = search.custom as Dict | undefined;
  const customGroup = custom?.group_by as Dict | undefined;
  const rows = [
    ...(Array.isArray(search.group_by) ? search.group_by : []),
    ...(Array.isArray(customGroup?.fields) ? customGroup.fields : []),
  ];
  if (!rows.length) return [];
  return rows
    .map((row) => {
      const raw = row && typeof row === 'object' ? row as Dict : {};
      const field = String(raw.field || raw.group_by || raw.groupBy || raw.group || raw.key || raw.name || '').trim();
      if (!field) return null;
      return {
        field,
        isDefault: raw.default === true || raw.is_default === true,
      };
    })
    .filter((row): row is GroupByChip => Boolean(row));
}

export function useActionViewLoadPreflightRuntime() {
  async function executeLoadPreflight(options: ExecuteLoadPreflightOptions): Promise<ExecuteLoadPreflightResult> {
    const { contract, meta } = await options.resolveAction(options.sessionMenuTree, options.actionId, options.actionMeta);
    if (options.isLoadCurrent && !options.isLoadCurrent()) {
      return { kind: 'handled' };
    }
    const nextMeta = (meta || null) as Dict | null;
    if (nextMeta) {
      options.setActionMeta(nextMeta);
    }

    const contractViewType = options.resolveContractViewMode(contract);
    if (!contractViewType) {
      const missingViewTypeState = options.resolveLoadMissingContractViewTypeErrorState();
      const missingViewTypeApplyState = options.resolveLoadMissingViewTypeApplyState({
        missingViewTypeState,
        currentErrorMessage: '',
      });
      return {
        kind: 'blocked',
        message: missingViewTypeApplyState.message,
        statusInput: missingViewTypeApplyState.statusInput,
      };
    }

    const preferredViewMode = options.resolvePreferredActionViewMode({
      contractViewTypeRaw: contractViewType,
      metaViewModesRaw: (nextMeta as { view_modes?: unknown } | null)?.view_modes,
      contract,
      routeViewModeRaw: options.routeViewModeRaw,
      currentPreferredViewModeRaw: options.currentPreferredViewModeRaw,
    });

    const contractSavedFilterChips = deriveSavedFilterChipsFromContract(contract);
    const contractGroupByChips = deriveGroupByChipsFromContract(contract);
    const routeSelection = options.resolveRouteSelectionState({
      routeFilterRaw: options.routeFilterRaw,
      routeSavedFilterRaw: options.routeSavedFilterRaw,
      routeGroupByRaw: options.routeGroupByRaw,
      routeGroupClearedRaw: options.routeGroupClearedRaw,
      routeGroupValueRaw: options.routeGroupValueRaw,
      activeContractFilterKey: options.activeContractFilterKey,
      activeSavedFilterKey: options.activeSavedFilterKey,
      activeGroupByField: options.activeGroupByField,
      contractFiltersRaw: searchContract(contract).filters,
      savedFilterChips: contractSavedFilterChips.length ? contractSavedFilterChips : options.contractSavedFilterChips,
      groupByChips: contractGroupByChips.length ? contractGroupByChips : options.contractGroupByChips,
    });
    const routeSelectionState = options.resolveRouteSelectionApplyState({ routeSelection });

    const accessPolicy = options.resolveContractAccessPolicy(contract);
    const contractFlags = options.resolveLoadPreflightContractFlags({
      contractReadAllowedRaw: options.resolveContractReadRight(contract),
      warningsRaw: contract.unsupported,
      degradedRaw: false,
    });
    const contractFlagState = options.resolveContractFlagApplyState({ contractFlags });

    const contractReadGuardPayload = options.resolveLoadContractReadRedirectPayload({
      contractReadAllowed: contractFlagState.contractReadAllowed,
      reasonCodeRaw: accessPolicy.reasonCode,
      accessModeRaw: accessPolicy.mode,
    });
    const contractReadGuardTarget = options.resolveCapabilityMissingRedirectTarget({
      capabilityMissingCode: options.capabilityMissingCode,
      guardPayload: contractReadGuardPayload,
      buildWorkbenchRouteTargetFn: options.buildWorkbenchRouteTarget,
      resolveWorkbenchQueryFn: options.resolveWorkbenchQuery,
    });
    if (contractReadGuardTarget) {
      return { kind: 'redirect', target: contractReadGuardTarget };
    }

    if (options.isUrlAction(nextMeta, contract)) {
      await options.redirectUrlAction(nextMeta, contract);
      return { kind: 'handled' };
    }

    const v2PrimarySource = resolveContractV2PrimaryDataSource(contract);
    const v2PrimaryParams = (v2PrimarySource.params && typeof v2PrimarySource.params === 'object' && !Array.isArray(v2PrimarySource.params))
      ? v2PrimarySource.params as Dict
      : {};
    const searchDefaults = searchContract(contract).defaults as Dict | undefined;
    const orderFields = collectContractOrderFields(contract);
    const fallbackSort = options.extractListOrderFromContract(contract) || '';
    const sortValue = sanitizeOrderValue(options.resolveLoadPreflightSortValue({
      currentSortRaw: sanitizeOrderValue(options.currentSortRaw, orderFields),
      sceneReadyDefaultSortRaw: sanitizeOrderValue(options.sceneReadyDefaultSortRaw, orderFields),
      sceneDefaultSortRaw: sanitizeOrderValue(options.sceneDefaultSortRaw, orderFields),
      searchDefaultOrderRaw: sanitizeOrderValue(v2PrimaryParams.order || searchDefaults?.order, orderFields),
      viewOrderRaw: '',
      metaOrderRaw: '',
      fallbackSortRaw: sanitizeOrderValue(fallbackSort, orderFields),
    }), orderFields);
    const contractLimit = options.resolveLoadPreflightContractLimit({ searchDefaultLimitRaw: v2PrimaryParams.limit || searchDefaults?.limit });

    const policy = options.evaluateCapabilityPolicy({
      source: nextMeta,
      available: options.sessionCapabilities,
      required: resolveActionRequiredCapabilities(nextMeta),
    });
    const capabilityGuardPayload = options.resolveLoadCapabilityRedirectPayload({
      stateRaw: policy.state,
      missingRaw: policy.missing,
    });
    const capabilityGuardTarget = options.resolveCapabilityMissingRedirectTarget({
      capabilityMissingCode: options.capabilityMissingCode,
      guardPayload: capabilityGuardPayload,
      buildWorkbenchRouteTargetFn: options.buildWorkbenchRouteTarget,
      resolveWorkbenchQueryFn: options.resolveWorkbenchQuery,
    });
    if (capabilityGuardTarget) {
      return { kind: 'redirect', target: capabilityGuardTarget };
    }

    const contractModel = options.resolveModelFromContract(contract);
    const resolvedModel = options.resolveActionViewResolvedModel({
      metaModelRaw: (nextMeta as Dict | null)?.model,
      routeModelRaw: '',
      contractModelRaw: contractModel,
    });
    const setMetaModel = !String((nextMeta as Dict | null)?.model || '').trim() && resolvedModel ? resolvedModel : '';

    const missingModelRedirect = options.resolveLoadMissingModelRedirectDecision({
      resolvedModel,
      isClientAction: options.isClientAction(nextMeta),
      isWindowAction: options.isWindowAction(nextMeta),
      actionTypeRaw: options.getActionType(nextMeta),
      contractDataTypeRaw: '',
      contractUrlRaw: '',
      metaUrlRaw: (nextMeta as Dict | null)?.url,
      noModelCode: 'ACT_NO_MODEL',
      unsupportedCode: 'ACT_UNSUPPORTED_TYPE',
    });
    const missingModelRedirectTarget = options.resolveMissingModelRedirectTarget({
      missingModelRedirect,
      buildWorkbenchRouteTargetFn: options.buildWorkbenchRouteTarget,
      resolveWorkbenchQueryFn: options.resolveWorkbenchQuery,
    });
    if (missingModelRedirectTarget) {
      return { kind: 'redirect', target: missingModelRedirectTarget };
    }
    if (!resolvedModel) {
      const missingModelErrorState = options.resolveLoadMissingResolvedModelErrorState();
      const missingResolvedModelApplyState = options.resolveLoadMissingResolvedModelApplyState({
        missingModelErrorState,
        currentErrorMessage: '',
      });
      return {
        kind: 'blocked',
        message: missingResolvedModelApplyState.message,
        statusInput: missingResolvedModelApplyState.statusInput,
      };
    }

    if (contractViewType === 'form') {
      const actionResId = options.resolveLoadFormActionResId({
        contractRaw: contract,
        routeQueryMapRaw: options.routeQueryMap,
        extractActionResIdFn: options.extractActionResId,
      });
      const target = options.buildModelFormRouteTarget({
        model: resolvedModel,
        id: actionResId ? String(actionResId) : 'new',
        query: options.resolveCarryQuery(),
      });
      return { kind: 'redirect', target };
    }

    return {
      kind: 'continue',
      contract,
      meta: nextMeta,
      contractViewType,
      preferredViewMode,
      activeContractFilterKey: routeSelectionState.activeContractFilterKey,
      activeSavedFilterKey: routeSelectionState.activeSavedFilterKey,
      activeGroupByField: routeSelectionState.activeGroupByField,
      contractReadAllowed: contractFlagState.contractReadAllowed,
      contractWarningCount: contractFlagState.contractWarningCount,
      contractDegraded: contractFlagState.contractDegraded,
      contractLimit,
      resolvedModel,
      setMetaModel,
      sortValue,
    };
  }

  return {
    executeLoadPreflight,
  };
}
