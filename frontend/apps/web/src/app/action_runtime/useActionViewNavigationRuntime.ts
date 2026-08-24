import type { Ref } from 'vue';
import { pickContractNavQuery } from '../navigationContext';
import { readWorkspaceContext } from '../workspaceContext';
import { buildEntryTargetRouteTarget } from '../routeQuery';
import { buildActionViewRowClickTarget, normalizeModelWriteAuthority, normalizeRecordOpenIntent, resolveRecordOpenTarget, shouldUseCanonicalCollectionDetail } from '../runtime/actionViewInteractionRuntime';
import { resolveRowClickPushState } from '../runtime/actionViewNavigationApplyRuntime';
import {
  resolveContractV2ActionRules,
} from '../contracts/v2/store';
import type { ContractV2NormalizedStore } from '../contracts/v2/types';

type Dict = Record<string, unknown>;

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
    const targetIntent = normalizeRecordOpenIntent(
      target.open_intent ?? target.openIntent ?? target.intent ?? target.entry_intent ?? target.entryIntent,
    );
    const targetAuthority = normalizeModelWriteAuthority(
      target.model_write_authority ?? target.modelWriteAuthority ?? target.model_write,
    );
    const targetModel = String(target.model || target.res_model || row.model || '').trim();
    const targetRecordId = target.record_id || target.recordId || row.id;
    if (targetModel && (targetIntent !== 'open' || targetAuthority !== null)) {
      const resolved = resolveRecordOpenTarget({
        model: targetModel,
        recordId: targetRecordId,
        actionId: options.actionId.value || undefined,
        menuId: options.menuId.value || undefined,
        requestedIntent: targetIntent,
        modelWriteAuthority: targetAuthority,
        carryQuery: query,
      });
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
    if (store) {
      const v2ViewType = String(store.snapshot.pageInfo.viewType || '').trim().toLowerCase();
      if (['list', 'tree', 'kanban'].includes(v2ViewType)) {
        const rows = resolveContractV2ActionRules(store);
        const rowAction = rows.find((action) => {
          if (!action || typeof action !== 'object') return false;
          const typed = action as unknown as Dict;
          return String(typed.triggerType || '').trim() === 'row_click'
            || String(typed.sourceWidgetId || '').trim() === 'page.row'
            || String(typed.targetScope || '').trim() === 'page';
        });
        if (rowAction) return rowAction as unknown as Dict;
      }
    }
    return undefined;
  }

  function handleRowClick(row: Dict) {
    const canonicalCollectionDetail = shouldUseCanonicalCollectionDetail({
      viewMode: options.routeQueryMap.value.view_mode,
      collectionSemantic: options.collectionSemantic?.value,
    });
    const rowAction = canonicalCollectionDetail ? undefined : resolveRowOpenAction();
    if (!rowAction && !canonicalCollectionDetail) return;
    if (rowAction) {
      const contractTarget = buildContractRowClickTarget(rowAction, row);
      if (contractTarget) {
        const rowClickState = resolveRowClickPushState({ routeTarget: contractTarget });
        if (rowClickState.shouldNavigate) void options.routerPush(rowClickState.target);
        return;
      }
      const payload = (rowAction.payload && typeof rowAction.payload === 'object' ? rowAction.payload : {}) as Dict;
      const viewMode = String(payload.view_mode || '').trim();
      if (viewMode && viewMode !== 'form') return;
    }
    const store = options.actionContract.value;
    const routeTarget = buildActionViewRowClickTarget({
      targetModel: options.resolvedModelRef.value || options.modelRef.value
        || String(store?.snapshot.pageInfo.model || ''),
      rawId: row.id,
      menuId: options.menuId.value,
      actionId: options.actionId.value,
      carryQuery: resolveCarryQuery(),
      editable: options.canEditRecord.value,
    });
    const rowClickState = resolveRowClickPushState({ routeTarget });
    if (!rowClickState.shouldNavigate) return;
    void options.routerPush(rowClickState.target);
  }

  return {
    resolveWorkspaceContextQuery,
    resolveCarryQuery,
    resolveWorkbenchQuery,
    handleRowClick,
  };
}
