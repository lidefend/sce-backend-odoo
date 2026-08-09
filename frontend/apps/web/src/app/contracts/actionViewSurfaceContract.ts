import { resolveUnifiedPageContractV2 } from './unifiedPageContractV2';
import { resolveUnifiedPageContractV2ListProfile } from './unifiedPageContractV2';

type Dict = Record<string, unknown>;

export type FocusNavAction = {
  label: string;
  to: string;
  query?: Record<string, string>;
};

export type SurfaceIntent = {
  title: string;
  summary: string;
  actions: FocusNavAction[];
  emptyTitle: string;
  emptyHint: string;
  primaryAction: FocusNavAction;
  secondaryAction?: FocusNavAction;
};

export type SurfaceIntentContract = {
  title?: string;
  summary?: string;
  actions?: FocusNavAction[];
  empty_title?: string;
  empty_hint?: string;
  primary_action?: FocusNavAction;
  secondary_action?: FocusNavAction;
};

function asDict(value: unknown): Dict {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  return value as Dict;
}

function parseViewModes(raw: unknown): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  const push = (value: unknown) => {
    const mode = normalizeActionViewMode(value);
    if (!mode || seen.has(mode)) return;
    seen.add(mode);
    out.push(mode);
  };
  if (Array.isArray(raw)) {
    raw.forEach(push);
    return out;
  }
  String(raw || '').split(',').forEach(push);
  return out;
}

function collectContractViewModes(contract: Dict | null): string[] {
  if (!contract) return [];
  const out: string[] = [];
  const seen = new Set<string>();
  const addMode = (raw: unknown) => {
    const mode = normalizeActionViewMode(raw);
    if (!mode || seen.has(mode)) return;
    seen.add(mode);
    out.push(mode);
  };
  const addModes = (raw: unknown) => {
    parseViewModes(raw).forEach((mode) => addMode(mode));
  };

  const v2 = resolveUnifiedPageContractV2(contract);
  addModes(v2?.pageInfo?.viewType);

  const head = asDict(contract.head);
  addModes(head.view_type);
  addModes(contract.view_type);

  const views = asDict(contract.views);
  if (views.tree || views.list) addMode('tree');
  if (views.kanban) addMode('kanban');
  if (views.pivot) addMode('pivot');
  if (views.graph) addMode('graph');
  if (views.calendar) addMode('calendar');
  if (views.gantt) addMode('gantt');
  if (views.activity) addMode('activity');
  if (views.dashboard) addMode('dashboard');
  return out;
}

export function normalizeActionViewMode(raw: unknown): string {
  const mode = String(raw || '').trim().toLowerCase();
  if (!mode) return '';
  if (mode === 'list') return 'tree';
  return mode;
}

export type ActionCollectionPresentation = {
  semantic: 'table' | 'card' | 'workflow_board' | 'hierarchy_browser' | 'pivot' | 'graph' | 'calendar' | 'gantt' | 'activity' | 'dashboard';
  label: string;
  groupField: string;
  groupedLanes: boolean;
  config: Dict;
};

export function resolveActionCollectionPresentation(
  contract: Dict | null,
  modeRaw: unknown,
): ActionCollectionPresentation {
  const mode = normalizeActionViewMode(modeRaw);
  if (mode === 'tree') {
    const listProfile = resolveUnifiedPageContractV2ListProfile(contract);
    const formalPresentation = asDict(listProfile.collection_presentation);
    if (String(formalPresentation.semantic || '').trim() === 'hierarchy_browser'
      && formalPresentation.enabled === true) {
      return {
        semantic: 'hierarchy_browser',
        label: String(formalPresentation.label || '').trim() || '层级',
        groupField: '',
        groupedLanes: false,
        config: asDict(formalPresentation.config),
      };
    }
    return { semantic: 'table', label: '表格', groupField: '', groupedLanes: false, config: {} };
  }
  if (['pivot', 'graph', 'calendar', 'gantt', 'activity', 'dashboard'].includes(mode)) {
    const views = asDict(contract?.views);
    return {
      semantic: mode as ActionCollectionPresentation['semantic'],
      label: String(modeRaw || ''),
      groupField: '',
      groupedLanes: false,
      config: asDict(views[mode]),
    };
  }
  if (mode !== 'kanban') {
    return { semantic: 'card', label: String(modeRaw || ''), groupField: '', groupedLanes: false, config: {} };
  }
  const views = asDict(contract?.views);
  const kanban = asDict(views.kanban);
  const presentation = asDict(kanban.collection_presentation);
  const capabilities = asDict(presentation.capabilities);
  const semantic = String(presentation.semantic || '').trim().toLowerCase();
  const groupField = String(presentation.group_field || '').trim();
  const groupedLanes = capabilities.grouped_lanes === true;
  if (semantic === 'workflow_board' && groupField && groupedLanes) {
    return {
      semantic: 'workflow_board',
      label: String(presentation.label || '').trim() || '流程看板',
      groupField,
      groupedLanes: true,
      config: {},
    };
  }
  return {
    semantic: 'card',
    label: semantic === 'card' ? String(presentation.label || '').trim() || '卡片' : '卡片',
    groupField: '',
    groupedLanes: false,
    config: {},
  };
}

export function resolveGroupedCollectionPresentation(
  presentation: ActionCollectionPresentation,
  activeGroupFieldRaw: unknown,
): ActionCollectionPresentation {
  const groupField = String(activeGroupFieldRaw || '').trim();
  if (presentation.semantic !== 'card' || !/^[A-Za-z_][A-Za-z0-9_]*$/.test(groupField)) return presentation;
  return { semantic: 'workflow_board', label: '流程看板', groupField, groupedLanes: true, config: {} };
}

export function resolveActionViewAvailableModes(options: {
  contractViewTypeRaw: unknown;
  metaViewModesRaw: unknown;
  metaViewsRaw?: unknown;
  contract: Dict | null;
}): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  const addMode = (raw: unknown) => {
    const mode = normalizeActionViewMode(raw);
    if (!mode || mode === 'form' || seen.has(mode)) return;
    seen.add(mode);
    out.push(mode);
  };
  const addModes = (raw: unknown) => {
    parseViewModes(raw).forEach((mode) => addMode(mode));
  };
  addModes(options.contractViewTypeRaw);
  addModes(options.metaViewModesRaw);
  addModes(options.metaViewsRaw);
  collectContractViewModes(options.contract).forEach((mode) => addMode(mode));
  return out;
}

export function resolveRenderableActionViewMode(preferredRaw: unknown, modes: string[], fallback: string): string {
  const mode = normalizeActionViewMode(preferredRaw) || modes[0] || fallback;
  if (mode === 'list' || mode === 'tree') return 'tree';
  if (['kanban', 'pivot', 'graph', 'calendar', 'gantt', 'activity', 'dashboard'].includes(mode)) return mode;
  return '';
}

export function resolveActionViewModeLabel(options: {
  mode: string;
  strictContractMode: boolean;
  strictLabelMap: Record<string, string>;
  pageText: (key: string, fallback: string) => string;
  contract?: Dict | null;
}): string {
  const normalized = normalizeActionViewMode(options.mode);
  if (normalized === 'tree' || normalized === 'kanban') {
    return resolveActionCollectionPresentation(options.contract || null, normalized).label;
  }
  const strictLabel = options.strictLabelMap[normalized];
  if (options.strictContractMode && strictLabel) return strictLabel;
  if (normalized === 'pivot') return options.pageText('view_mode_pivot', '透视');
  if (normalized === 'graph') return options.pageText('view_mode_graph', '图表');
  if (normalized === 'calendar') return options.pageText('view_mode_calendar', '日历');
  if (normalized === 'gantt') return options.pageText('view_mode_gantt', '甘特');
  if (normalized === 'activity') return options.pageText('view_mode_activity', '活动');
  if (normalized === 'dashboard') return options.pageText('view_mode_dashboard', '仪表板');
  return options.mode;
}

export function resolveActionViewSurfaceIntent(options: {
  strictContractMode: boolean;
  strictSurfaceContract: Dict;
  contractSurfaceIntent: SurfaceIntentContract;
  pageText: (key: string, fallback: string) => string;
}): SurfaceIntent {
  const intentSource = options.strictContractMode
    ? asDict(options.strictSurfaceContract.intent)
    : asDict(options.contractSurfaceIntent);
  const primaryAction = asDict(intentSource.primary_action);
  const secondaryAction = asDict(intentSource.secondary_action);
  const actions = Array.isArray(intentSource.actions) ? (intentSource.actions as FocusNavAction[]) : [];
  const secondaryTarget = String(secondaryAction.target || '').trim();

  return {
    title: String(intentSource.title || '').trim() || options.pageText('intent_title_default', '业务列表'),
    summary: String(intentSource.summary || '').trim() || options.pageText('intent_summary_default', '请通过页面动作继续处理。'),
    actions,
    emptyTitle: String(intentSource.empty_title || '').trim() || options.pageText('empty_title_default', '暂无可展示内容'),
    emptyHint: String(intentSource.empty_hint || '').trim() || options.pageText('empty_hint_default', ''),
    primaryAction: {
      label: String(primaryAction.label || '').trim() || options.pageText('primary_action_default', '去我的工作'),
      to: String(primaryAction.target || '/my-work'),
    },
    secondaryAction: Object.keys(secondaryAction).length && secondaryTarget
      ? {
          label: String(secondaryAction.label || '').trim() || options.pageText('secondary_action_default', '进入场景'),
          to: secondaryTarget,
        }
      : undefined,
  };
}
