import type { Ref } from 'vue';
import { contractGapError } from '../contract/contractGap';
import { pickContractNavQuery } from '../navigationContext';
import { readWorkspaceContext } from '../workspaceContext';
import { buildEntryTargetRouteTarget } from '../routeQuery';
import { adaptLegacyRecordEntry, decodeFormalRecordEntry, resolveRecordOpenTarget } from '../runtime/recordEntryContract';
import { resolveRowClickPushState } from '../runtime/actionViewNavigationApplyRuntime';
import {
  resolveContractV2ActionRules,
} from '../contracts/v2/store';
import type { ContractV2NormalizedStore } from '../contracts/v2/types';

type Dict = Record<string, unknown>;

/**
 * Row-level placement is declared by the owning contract as
 * `sourceWidgetId === 'page.row'`; it is the only row-activation identity.
 *
 * Row identity must never be inferred from `targetScope`: the backend
 * `normalize_target_scope` intentionally collapses native placement
 * (header / toolbar / smart / row) into the closed V2 target-scope vocabulary,
 * so header actions also carry `targetScope: 'page'`.  The legacy `row_click`
 * trigger is likewise rewritten to `click` by `normalize_trigger_type` before
 * the contract is decoded, so it can never appear on a decoded action rule.
 */
export const ROW_PLACEMENT_WIDGET_ID = 'page.row';

export function isRowPlacementAction(action: unknown): boolean {
  if (!action || typeof action !== 'object') return false;
  return String((action as Dict).sourceWidgetId || '').trim() === ROW_PLACEMENT_WIDGET_ID;
}

type UseActionViewNavigationRuntimeOptions = {
  routeQueryMap: Ref<Record<string, unknown>>;
  showHud: Ref<boolean>;
  menuId: Ref<number | null>;
  actionId: Ref<number | null>;
  actionContract: Ref<ContractV2NormalizedStore | null>;
  canEditRecord: Ref<boolean>;
  collectionSemantic?: Ref<string>;
  resolvedModelRef: Ref<string>;
  modelRef: Ref<string>;
  routerPush: (target: unknown) => Promise<unknown>;
};

export function useActionViewNavigationRuntime(options: UseActionViewNavigationRuntimeOptions) {
  function resolveWorkspaceContextQuery() {
    return readWorkspaceContext(options.routeQueryMap.value);
  }

  function resolveCarryQuery(extra?: Record<string, unknown>) {
    return {
      ...pickContractNavQuery(options.routeQueryMap.value, extra),
      ...resolveWorkspaceContextQuery(),
    };
  }

  function resolveWorkbenchQuery(
    reason: string,
    payload?: { public?: Record<string, unknown>; diag?: Record<string, unknown> },
  ) {
    return {
      reason,
      ...resolveWorkspaceContextQuery(),
      ...(payload?.public || {}),
      ...(options.showHud.value
        ? {
            menu_id: options.menuId.value || undefined,
            action_id: options.actionId.value || undefined,
            ...(payload?.diag || {}),
          }
        : {}),
    };
  }

  function materializeRowTargetValue(value: unknown, row: Dict): unknown {
    if (typeof value === 'string') {
      return value.replace(/\$\{([A-Za-z_][A-Za-z0-9_]*)\}/g, (_match, key) => String(row[key] ?? ''));
    }
    if (Array.isArray(value)) {
      return value.map((item) => materializeRowTargetValue(item, row));
    }
    if (value && typeof value === 'object') {
      return Object.entries(value as Dict).reduce<Dict>((acc, [key, item]) => {
        acc[key] = materializeRowTargetValue(item, row);
        return acc;
      }, {});
    }
    return value;
  }

  function parseRouteTarget(rawRoute: unknown, query: Dict) {
    const raw = String(rawRoute || '').trim();
    if (!raw) return null;
    const [path, queryRaw] = raw.split('?', 2);
    const routeQuery: Dict = { ...query };
    if (queryRaw) {
      const params = new URLSearchParams(queryRaw);
      params.forEach((value, key) => {
        if (key) routeQuery[key] = value;
      });
    }
    return { path: path || raw, query: routeQuery };
  }

  function routeQueryValue(value: unknown): string | number | undefined {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    const text = String(value ?? '').trim();
    return text || undefined;
  }

  function buildContractRowClickTarget(rowAction: Dict, row: Dict) {
    const rawTarget = rowAction.target && typeof rowAction.target === 'object' ? rowAction.target as Dict : {};
    const target = materializeRowTargetValue(rawTarget, row) as Dict;
    const carryQuery = resolveCarryQuery();
    const targetQuery = target.query && typeof target.query === 'object' && !Array.isArray(target.query)
      ? materializeRowTargetValue(target.query as Dict, row) as Dict
      : {};
    const query = {
      ...carryQuery,
      ...targetQuery,
      menu_id: options.menuId.value || undefined,
      action_id: options.actionId.value || undefined,
      entry_intent: routeQueryValue(target.entry_intent || target.entryIntent),
      record_id: routeQueryValue(target.record_id || target.recordId),
    };
    const formalEntry = decodeFormalRecordEntry(target.record_entry);
    const explicitSceneTarget = (
      (target.entry_target && typeof target.entry_target === 'object'
        && String((target.entry_target as Dict).type || '').trim() === 'scene')
      || String(target.scene_key || target.sceneKey || '').trim()
    );
    const hasLegacyRecordCarrier = !explicitSceneTarget && [
      target.open_intent, target.openIntent, target.intent, target.entry_intent, target.entryIntent,
      target.model_write_authority, target.modelWriteAuthority, target.model_write,
    ].some((value) => value !== undefined && value !== null && String(value).trim() !== '');
    const recordEntry = formalEntry
      ? {
          ...formalEntry,
          actionId: formalEntry.actionId || options.actionId.value || undefined,
          menuId: formalEntry.menuId || options.menuId.value || undefined,
          carryQuery: query,
        }
      : hasLegacyRecordCarrier ? adaptLegacyRecordEntry(target, {
          fallbackModel: row.model,
          fallbackRecordId: row.id,
          fallbackActionId: options.actionId.value || undefined,
          fallbackMenuId: options.menuId.value || undefined,
          carryQuery: query,
        }) : null;
    if (recordEntry) {
      const resolved = resolveRecordOpenTarget(recordEntry);
      if (resolved) return resolved;
    }
    const entryTarget = target.entry_target && typeof target.entry_target === 'object'
      ? target.entry_target as Dict
      : (String(target.scene_key || target.sceneKey || '').trim()
        ? {
            type: 'scene',
            scene_key: target.scene_key || target.sceneKey,
            route: target.route,
            scene_label: target.scene_label || target.sceneLabel,
          }
        : null);
    if (entryTarget) {
      return buildEntryTargetRouteTarget(entryTarget, {
        query,
        menuId: options.menuId.value,
        actionId: options.actionId.value,
        keepSceneRoute: false,
      });
    }
    if (target.route) {
      return parseRouteTarget(target.route, query);
    }
    return null;
  }

  function resolveRowOpenAction() {
    const store = options.actionContract.value;
    if (!store) return undefined;
    const v2ViewType = String(store.snapshot.pageInfo.viewType || '').trim().toLowerCase();
    if (!['list', 'tree', 'kanban'].includes(v2ViewType)) return undefined;
    const rows = resolveContractV2ActionRules(store);
    const rowAction = rows.find((action) => isRowPlacementAction(action));
    return rowAction ? (rowAction as unknown as Dict) : undefined;
  }

  function handleRowClick(row: Dict) {
    const rowAction = resolveRowOpenAction();
    if (!rowAction) {
      throw contractGapError({
        kind: 'contract_defect',
        missing: 'actionContract.actionRuleList.page.row',
        requiredDeclarationLayer: 'P0:smart_core:unified_page_contract_v2_assembler',
      }, '原生集合行点击缺少 page.row 动作声明');
    }
    const contractTarget = buildContractRowClickTarget(rowAction, row);
    if (contractTarget) {
      const rowClickState = resolveRowClickPushState({ routeTarget: contractTarget });
      if (rowClickState.shouldNavigate) void options.routerPush(rowClickState.target);
      return;
    }
    const payload = (rowAction.payload && typeof rowAction.payload === 'object' ? rowAction.payload : {}) as Dict;
    const viewMode = String(payload.view_mode || '').trim();
    if (viewMode && viewMode !== 'form') return;
    throw contractGapError({
      kind: 'contract_defect',
      missing: `actionContract.actionRuleList.${String(rowAction.actionId || 'page.row')}.target.record_entry`,
      requiredDeclarationLayer: 'P0:smart_core:unified_page_contract_v2_assembler',
    }, '原生集合行打开动作缺少完整记录入口声明');
  }

  return {
    resolveWorkspaceContextQuery,
    resolveCarryQuery,
    resolveWorkbenchQuery,
    handleRowClick,
  };
}
