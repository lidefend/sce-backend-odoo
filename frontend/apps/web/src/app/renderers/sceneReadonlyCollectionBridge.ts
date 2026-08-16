import {
  adaptReadonlyNormalizedCollection,
  type ReadonlyNormalizedCollectionContract,
  type SceneCollectionContract,
  type SceneTableRow,
  type SceneWorkspaceIdentity,
} from '@sc/ui/bridge';
import { resolveUnifiedPageContractV2 } from '../contracts/unifiedPageContractV2';

type Dict = Record<string, unknown>;

export type SceneReadonlyCollectionBridgeInput = {
  actionContract: unknown;
  records: Dict[];
  columnLabels: Record<string, string>;
  totalCount: number;
  identity: SceneWorkspaceIdentity;
  description?: string;
};

export type SceneReadonlyCollectionBridgeResult = {
  ok: boolean;
  reasonCode: string;
  contract: SceneCollectionContract | null;
  pageAuth: string;
  sceneKey: string;
  model: string;
  selectionEnabled: boolean;
  hasMutationActions: boolean;
};

function asDict(value: unknown): Dict {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Dict : {};
}

function asList(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function failed(
  reasonCode: string,
  detail: Partial<Pick<SceneReadonlyCollectionBridgeResult, 'pageAuth' | 'sceneKey' | 'model' | 'selectionEnabled' | 'hasMutationActions'>> = {},
): SceneReadonlyCollectionBridgeResult {
  return {
    ok: false,
    reasonCode,
    contract: null,
    pageAuth: '',
    sceneKey: '',
    model: '',
    selectionEnabled: true,
    hasMutationActions: true,
    ...detail,
  };
}

export function sceneCollectionRowToRecord(row: SceneTableRow): Dict {
  return { id: row.id, ...row.values };
}

export function resolveSceneReadonlyCollectionBridge(
  input: SceneReadonlyCollectionBridgeInput,
): SceneReadonlyCollectionBridgeResult {
  const v2 = resolveUnifiedPageContractV2(input.actionContract);
  if (!v2) return failed('SCENE_DRIVER_NORMALIZED_V2_MISSING');
  const status = asDict(v2.statusContract);
  const globalStatus = asDict(status.globalStatus || status.global_status);
  const widgetStatus = asList(status.widgetStatus || status.widget_status).map((item) => {
    const row = asDict(item);
    return {
      widgetId: String(row.widgetId || row.widget_id || ''),
      visible: row.visible !== false,
    };
  });
  const buttonStatus = asList(status.buttonStatus || status.button_status).map((item) => {
    const row = asDict(item);
    return {
      btnId: String(row.btnId || row.btn_id || ''),
      visible: row.visible === true,
      disabled: row.disabled !== false,
    };
  });
  const listProfile = asDict(v2.layoutContract.listProfile);
  const selectionPolicy = asDict(listProfile.selection_policy || listProfile.selectionPolicy);
  const sourceAuthority = asDict(listProfile.sourceAuthority || listProfile.source_authority);
  const columns = asList(listProfile.columns).map((item) => String(item || '').trim()).filter(Boolean);
  const normalizedListProfile: ReadonlyNormalizedCollectionContract['layoutContract']['listProfile'] = {
    columns,
    column_labels: {
      ...input.columnLabels,
      ...asDict(listProfile.column_labels || listProfile.columnLabels),
    } as Record<string, string>,
    row_primary: String(listProfile.row_primary || listProfile.rowPrimary || ''),
    status_field: String(listProfile.status_field || listProfile.statusField || '') || undefined,
    cross_device_critical_columns: asList(
      listProfile.cross_device_critical_columns || listProfile.crossDeviceCriticalColumns,
    ).map((item) => String(item || '').trim()).filter(Boolean),
    selection_policy: { enabled: selectionPolicy.enabled === true },
    sourceAuthority: {
      formal_projection: sourceAuthority.formal_projection === true || sourceAuthority.formalProjection === true,
      no_business_fact_authority: sourceAuthority.no_business_fact_authority === true
        || sourceAuthority.noBusinessFactAuthority === true,
      source_key: String(sourceAuthority.source_key || sourceAuthority.sourceKey || ''),
    },
  };
  const pageAuth = String(globalStatus.pageAuth || globalStatus.page_auth || '').trim().toLowerCase();
  const hasMutationActions = v2.actionContract.actionRuleList.length > 0
    || buttonStatus.some((item) => item.visible === true && item.disabled !== true);
  const selectionEnabled = selectionPolicy.enabled !== false;
  const failureDetail = {
    pageAuth,
    sceneKey: String(v2.pageInfo.sceneKey || ''),
    model: String(v2.pageInfo.model || ''),
    selectionEnabled,
    hasMutationActions,
  };
  if (!['read', 'readonly'].includes(pageAuth)) {
    return failed('SCENE_DRIVER_PAGE_NOT_READONLY', failureDetail);
  }
  if (hasMutationActions) {
    return failed('SCENE_DRIVER_MUTATION_ACTION_PRESENT', failureDetail);
  }
  if (selectionEnabled) {
    return failed('SCENE_DRIVER_SELECTION_PRESENT', failureDetail);
  }
  const normalizedContract: ReadonlyNormalizedCollectionContract = {
    pageInfo: v2.pageInfo,
    layoutContract: {
      containerTree: v2.layoutContract.containerTree,
      listProfile: normalizedListProfile,
    },
    statusContract: {
      globalStatus: {
        pageVisible: globalStatus.pageVisible === true || globalStatus.page_visible === true,
        pageAuth,
      },
      widgetStatus,
      buttonStatus,
    },
    actionContract: {
      actionRuleList: v2.actionContract.actionRuleList,
    },
  };
  const rows: SceneTableRow[] = input.records.map((record, index) => ({
    id: String(record.id || `row-${index + 1}`),
    values: Object.fromEntries(columns.map((field) => [field, String(record[field] ?? '')])),
  }));
  try {
    const contract = adaptReadonlyNormalizedCollection({
      identity: input.identity,
      contract: normalizedContract,
      records: rows,
      runtime: {
        description: String(input.description || '').trim(),
        summaries: [],
        filters: [],
        totalCount: Math.max(0, Number(input.totalCount || rows.length)),
      },
    });
    return {
      ok: true,
      reasonCode: '',
      contract,
      pageAuth,
      sceneKey: String(v2.pageInfo.sceneKey || ''),
      model: String(v2.pageInfo.model || ''),
      selectionEnabled,
      hasMutationActions,
    };
  } catch {
    return failed('SCENE_DRIVER_NORMALIZED_ADAPTER_REJECTED', failureDetail);
  }
}
