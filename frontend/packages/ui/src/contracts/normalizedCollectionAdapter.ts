import type { SceneCollectionContract, SceneWorkspaceIdentity } from './sceneCollection';
import type { SceneFact, SceneTableRow, SceneTone } from './sceneObjectPage';

type NormalizedWidget = {
  widgetId: string;
  fieldCode: string;
  label: string;
};

type NormalizedContainer = {
  children?: NormalizedContainer[];
  widgetList?: NormalizedWidget[];
};

type NormalizedListProfile = {
  columns: string[];
  column_labels: Record<string, string>;
  row_primary: string;
  status_field?: string;
  cross_device_critical_columns: string[];
  selection_policy: { enabled: boolean };
  sourceAuthority: {
    formal_projection: boolean;
    no_business_fact_authority: boolean;
    source_key: string;
  };
};

export interface ReadonlyNormalizedCollectionContract {
  pageInfo: {
    pageId: string;
    sceneKey: string;
    pageName: string;
    viewType: string;
    contractVersion: string;
  };
  layoutContract: {
    containerTree: NormalizedContainer[];
    listProfile: NormalizedListProfile;
  };
  statusContract: {
    globalStatus: { pageVisible: boolean; pageAuth: string };
    widgetStatus: Array<{ widgetId: string; visible: boolean }>;
    buttonStatus: Array<{ btnId: string; visible: boolean; disabled: boolean }>;
  };
  actionContract: {
    actionRuleList: Array<{ actionId: string }>;
  };
}

export interface ReadonlyNormalizedCollectionSnapshot {
  identity: SceneWorkspaceIdentity;
  contract: ReadonlyNormalizedCollectionContract;
  records: SceneTableRow[];
  runtime: {
    description: string;
    summaries: SceneFact[];
    filters: Array<{ id: string; label: string; value: string; active?: boolean }>;
    totalCount: number;
    rowToneByStatus?: Record<string, SceneTone>;
  };
}

export class NormalizedCollectionPilotError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NormalizedCollectionPilotError';
  }
}

function assertPilot(condition: unknown, message: string): asserts condition {
  if (!condition) throw new NormalizedCollectionPilotError(message);
}

function collectWidgets(containers: NormalizedContainer[]): NormalizedWidget[] {
  return containers.flatMap((container) => [
    ...(container.widgetList || []),
    ...collectWidgets(container.children || []),
  ]);
}

export function adaptReadonlyNormalizedCollection(
  snapshot: ReadonlyNormalizedCollectionSnapshot,
): SceneCollectionContract {
  const { contract, runtime } = snapshot;
  const { pageInfo, layoutContract, statusContract, actionContract } = contract;
  const profile = layoutContract.listProfile;
  const widgets = collectWidgets(layoutContract.containerTree);
  const widgetByField = new Map(widgets.map((widget) => [widget.fieldCode, widget]));
  const statusByWidget = new Map(statusContract.widgetStatus.map((status) => [status.widgetId, status]));
  const enabledActions = statusContract.buttonStatus.filter((status) => status.visible && !status.disabled);

  assertPilot(pageInfo.viewType === 'tree' || pageInfo.viewType === 'list', 'normalized page must declare a collection view type');
  assertPilot(pageInfo.pageId && pageInfo.sceneKey && pageInfo.contractVersion, 'normalized page identity is incomplete');
  assertPilot(statusContract.globalStatus.pageVisible, 'normalized page is not visible');
  assertPilot(['read', 'readonly'].includes(statusContract.globalStatus.pageAuth), 'pilot requires explicit read-only page authority');
  assertPilot(profile.sourceAuthority?.formal_projection, 'list profile lacks formal normalized source authority');
  assertPilot(profile.sourceAuthority?.no_business_fact_authority, 'list profile must remain a projection');
  assertPilot(profile.selection_policy?.enabled === false, 'read-only pilot forbids row selection');
  assertPilot(actionContract.actionRuleList.length === 0, 'read-only pilot forbids normalized actions');
  assertPilot(enabledActions.length === 0, 'read-only pilot forbids enabled button status');
  assertPilot(profile.columns.length > 0, 'normalized list profile has no columns');
  assertPilot(new Set(profile.columns).size === profile.columns.length, 'normalized list profile contains duplicate columns');
  assertPilot(profile.columns.includes(profile.row_primary), 'row primary field must be an authoritative list column');
  assertPilot(
    profile.cross_device_critical_columns.every((field) => profile.columns.includes(field)),
    'cross-device fields must be authoritative list columns',
  );

  const visibleColumns = profile.columns.filter((field) => {
    const widget = widgetByField.get(field);
    assertPilot(widget, `normalized list column is missing from containerTree: ${field}`);
    return statusByWidget.get(widget.widgetId)?.visible !== false;
  });
  assertPilot(visibleColumns.includes(profile.row_primary), 'row primary field is hidden by normalized status');

  const columns = visibleColumns.map((field) => {
    const widget = widgetByField.get(field)!;
    const label = String(profile.column_labels[field] || widget.label || '').trim();
    assertPilot(label, `normalized list column has no authoritative label: ${field}`);
    return { key: field, label };
  });
  const mobileFields = profile.cross_device_critical_columns.filter((field) => field !== profile.row_primary).slice(0, 4);
  const statusField = profile.status_field && visibleColumns.includes(profile.status_field)
    ? profile.status_field
    : undefined;
  const rows = snapshot.records.map((row) => {
    assertPilot(row.id, 'normalized record has no stable id');
    assertPilot(Object.prototype.hasOwnProperty.call(row.values, profile.row_primary), `normalized record lacks row primary: ${row.id}`);
    const statusValue = statusField ? row.values[statusField] : '';
    return {
      ...row,
      tone: statusValue ? runtime.rowToneByStatus?.[statusValue] : row.tone,
      values: Object.fromEntries(visibleColumns.map((field) => [field, String(row.values[field] ?? '')])),
    };
  });

  return {
    identity: snapshot.identity,
    title: pageInfo.pageName,
    description: runtime.description,
    eyebrow: `NORMALIZED · ${pageInfo.contractVersion}`,
    actions: [],
    summaries: runtime.summaries,
    filters: runtime.filters,
    table: {
      id: pageInfo.pageId,
      title: pageInfo.pageName,
      columns,
      rows,
      emptyText: '暂无可读取记录',
    },
    rowPresentation: {
      accessibilityLabel: `${pageInfo.pageName}记录`,
      titleField: profile.row_primary,
      statusField,
      mobileFields,
    },
    selectionMode: 'none',
    readonly: true,
    totalCount: runtime.totalCount,
    sourceTrace: {
      kind: 'normalized-collection',
      pageId: pageInfo.pageId,
      sceneKey: pageInfo.sceneKey,
      contractVersion: pageInfo.contractVersion,
    },
  };
}
