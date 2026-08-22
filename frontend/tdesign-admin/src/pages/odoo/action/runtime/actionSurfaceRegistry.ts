export type ActionSurfaceViewMode = 'list' | 'cards' | 'kanban' | 'pivot' | 'graph' | 'calendar' | 'gantt' | 'activity';

export type ActionSurfaceRendererStatus = 'ready' | 'fallback' | 'unsupported';

export interface ActionSurfaceRendererRegistration {
  semantic: string;
  mode: ActionSurfaceViewMode;
  label: string;
  requestedRendererKey: string;
  activeRendererKey: string;
  status: ActionSurfaceRendererStatus;
  reasonCode: string;
}

const registrations: ActionSurfaceRendererRegistration[] = [
  {
    semantic: 'tree',
    mode: 'list',
    label: '列表视图',
    requestedRendererKey: 'core.table',
    activeRendererKey: 'core.table',
    status: 'ready',
    reasonCode: '',
  },
  {
    semantic: 'list',
    mode: 'list',
    label: '列表视图',
    requestedRendererKey: 'core.table',
    activeRendererKey: 'core.table',
    status: 'ready',
    reasonCode: '',
  },
  {
    semantic: 'card',
    mode: 'cards',
    label: '卡片视图',
    requestedRendererKey: 'core.card',
    activeRendererKey: 'core.card',
    status: 'ready',
    reasonCode: '',
  },
  {
    semantic: 'cards',
    mode: 'cards',
    label: '卡片视图',
    requestedRendererKey: 'core.card',
    activeRendererKey: 'core.card',
    status: 'ready',
    reasonCode: '',
  },
  {
    semantic: 'kanban',
    mode: 'kanban',
    label: '看板视图',
    requestedRendererKey: 'core.workflow_board',
    activeRendererKey: 'core.workflow_board',
    status: 'ready',
    reasonCode: '',
  },
  {
    semantic: 'workflow_board',
    mode: 'kanban',
    label: '看板视图',
    requestedRendererKey: 'core.workflow_board',
    activeRendererKey: 'core.workflow_board',
    status: 'ready',
    reasonCode: '',
  },
  ...(['pivot', 'graph', 'calendar', 'gantt', 'activity'] as const).map(
    (semantic): ActionSurfaceRendererRegistration => ({
      semantic,
      mode: semantic,
      label: {
        pivot: '透视视图',
        graph: '图表视图',
        calendar: '日历视图',
        gantt: '甘特视图',
        activity: '活动视图',
      }[semantic],
      requestedRendererKey: `core.${semantic}`,
      activeRendererKey: `core.${semantic}`,
      status: 'ready',
      reasonCode: '',
    }),
  ),
];

const bySemantic = new Map(registrations.map((registration) => [registration.semantic, registration]));
const byMode = new Map(registrations.map((registration) => [registration.mode, registration]));
const nonCollectionSemantics = new Set(['form', 'dashboard', 'combine']);

export function actionSurfaceRegistration(mode: string, config: Record<string, unknown> = {}) {
  const registration = byMode.get(mode as ActionSurfaceViewMode);
  if (!registration) return null;
  if (!['pivot', 'graph', 'calendar', 'gantt', 'activity'].includes(registration.mode)) return registration;

  const explicitRenderer = String(config.renderer_key || config.rendererKey || '').trim();
  const dataSource = config.data_source || config.dataSource || config.data_contract || config.dataContract;
  const hasDeclaredDataSource = Boolean(dataSource && typeof dataSource === 'object');
  const hasStructuredConfig = Object.keys(config).some((key) =>
    [
      'dimensions',
      'dimension_fields',
      'group_by',
      'measures',
      'measure_fields',
      'date_field',
      'start_field',
      'end_field',
      'activity_type_field',
      'dependency_field',
    ].includes(key),
  );
  if (explicitRenderer && explicitRenderer !== registration.activeRendererKey) {
    return {
      ...registration,
      requestedRendererKey: explicitRenderer,
      status: 'fallback' as const,
      reasonCode: 'ACTION_SURFACE_RENDERER_CONTRACT_NOT_NEGOTIATED',
    };
  }
  if (!hasDeclaredDataSource && !hasStructuredConfig) {
    return {
      ...registration,
      status: 'fallback' as const,
      reasonCode: 'ACTION_SURFACE_DATA_CONTRACT_MISSING',
    };
  }
  return registration;
}

export function actionSurfaceViewOptions(declaredSemantics: string[]) {
  const available = new Map<ActionSurfaceViewMode, ActionSurfaceRendererRegistration>();

  declaredSemantics.forEach((value) => {
    const semantic = String(value || '')
      .trim()
      .toLowerCase();
    const registration = bySemantic.get(semantic);
    if (registration && registration.status !== 'unsupported') available.set(registration.mode, registration);
  });

  // A malformed or legacy action without a collection view still needs a usable surface.
  if (!available.size) {
    const fallback = byMode.get('list');
    if (fallback) available.set(fallback.mode, fallback);
  }

  return [...available.values()].map((registration) => ({
    content: registration.label,
    value: registration.mode,
    rendererKey: registration.activeRendererKey,
    status: registration.status,
    reasonCode: registration.reasonCode,
  }));
}

export function actionSurfaceDiagnostics(declaredSemantics: string[]) {
  const normalized = declaredSemantics
    .map((value) =>
      String(value || '')
        .trim()
        .toLowerCase(),
    )
    .filter(Boolean);
  const unsupported = [
    ...new Set(normalized.filter((semantic) => !bySemantic.has(semantic) && !nonCollectionSemantics.has(semantic))),
  ];
  return unsupported.map((semantic) => ({
    requestedRendererKey: `backend.${semantic}`,
    activeRendererKey: 'core.table',
    status: 'fallback' as const,
    reasonCode: 'ACTION_SURFACE_RENDERER_NOT_REGISTERED',
    message: `后端声明了 ${semantic} 视图，但当前前端没有对应运行时，已明确降级为列表视图。`,
  }));
}

export function actionSurfaceRendererRegistrations() {
  return registrations.map((registration) => ({ ...registration }));
}
