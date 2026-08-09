import type { ActionCollectionPresentation } from '../contracts/actionViewSurfaceContract';

export type ActionSurfaceRendererStatus = 'ready' | 'fallback' | 'unsupported';
export type ActionSurfaceRendererOutlet = 'standard' | 'component';

export type ActionSurfaceRendererDescriptor = {
  requestedRendererKey: string;
  activeRendererKey: string;
  semantic: string;
  viewMode: string;
  status: ActionSurfaceRendererStatus;
  outlet: ActionSurfaceRendererOutlet;
  config: Record<string, unknown>;
  reasonCode: string;
};

type ActionSurfaceRendererRegistration = {
  semantic: string;
  requestedRendererKey: string;
  activeRendererKey: string;
  status: Exclude<ActionSurfaceRendererStatus, 'unsupported'>;
  outlet: ActionSurfaceRendererOutlet;
  reasonCode: string;
};

const registrations: readonly ActionSurfaceRendererRegistration[] = [
  { semantic: 'table', requestedRendererKey: 'core.table', activeRendererKey: 'core.standard_collection', status: 'ready', outlet: 'standard', reasonCode: '' },
  { semantic: 'card', requestedRendererKey: 'core.card', activeRendererKey: 'core.standard_collection', status: 'ready', outlet: 'standard', reasonCode: '' },
  { semantic: 'workflow_board', requestedRendererKey: 'core.workflow_board', activeRendererKey: 'core.standard_collection', status: 'ready', outlet: 'standard', reasonCode: '' },
  { semantic: 'hierarchy_browser', requestedRendererKey: 'core.hierarchy_browser', activeRendererKey: 'core.hierarchy_browser', status: 'ready', outlet: 'component', reasonCode: '' },
  { semantic: 'hierarchy_planner', requestedRendererKey: 'core.hierarchy_planner', activeRendererKey: 'core.hierarchy_planner', status: 'ready', outlet: 'component', reasonCode: '' },
  { semantic: 'hierarchical_worksheet', requestedRendererKey: 'core.hierarchical_worksheet', activeRendererKey: 'core.hierarchical_worksheet', status: 'ready', outlet: 'component', reasonCode: '' },
  { semantic: 'pivot', requestedRendererKey: 'core.pivot', activeRendererKey: 'core.readable_records', status: 'fallback', outlet: 'standard', reasonCode: 'RENDERER_PIVOT_PLANNED' },
  { semantic: 'graph', requestedRendererKey: 'core.graph', activeRendererKey: 'core.readable_records', status: 'fallback', outlet: 'standard', reasonCode: 'RENDERER_GRAPH_PLANNED' },
  { semantic: 'calendar', requestedRendererKey: 'core.calendar', activeRendererKey: 'core.readable_records', status: 'fallback', outlet: 'standard', reasonCode: 'RENDERER_CALENDAR_PLANNED' },
  { semantic: 'gantt', requestedRendererKey: 'core.gantt', activeRendererKey: 'core.readable_records', status: 'fallback', outlet: 'standard', reasonCode: 'RENDERER_GANTT_PLANNED' },
  { semantic: 'activity', requestedRendererKey: 'core.activity', activeRendererKey: 'core.readable_records', status: 'fallback', outlet: 'standard', reasonCode: 'RENDERER_ACTIVITY_PLANNED' },
  { semantic: 'dashboard', requestedRendererKey: 'core.dashboard', activeRendererKey: 'core.readable_records', status: 'fallback', outlet: 'standard', reasonCode: 'RENDERER_DASHBOARD_PLANNED' },
];

export const ACTION_SURFACE_RENDERER_REGISTRY = Object.freeze(
  Object.fromEntries(registrations.map((registration) => [registration.semantic, Object.freeze({ ...registration })])),
) as Readonly<Record<string, Readonly<ActionSurfaceRendererRegistration>>>;

export function resolveActionSurfaceRenderer(
  presentation: ActionCollectionPresentation,
  viewModeRaw: unknown,
): ActionSurfaceRendererDescriptor {
  const semantic = String(presentation.semantic || '').trim().toLowerCase();
  const viewMode = String(viewModeRaw || '').trim().toLowerCase();
  const registration = ACTION_SURFACE_RENDERER_REGISTRY[semantic];
  if (!registration) {
    return {
      requestedRendererKey: semantic ? `unknown.${semantic}` : 'unknown.empty',
      activeRendererKey: 'core.unsupported',
      semantic,
      viewMode,
      status: 'unsupported',
      outlet: 'component',
      config: {},
      reasonCode: 'ACTION_SURFACE_RENDERER_NOT_REGISTERED',
    };
  }
  return {
    requestedRendererKey: registration.requestedRendererKey,
    activeRendererKey: registration.activeRendererKey,
    semantic,
    viewMode,
    status: registration.status,
    outlet: registration.outlet,
    config: presentation.config,
    reasonCode: registration.reasonCode,
  };
}

export function registeredActionSurfaceSemantics(): string[] {
  return Object.keys(ACTION_SURFACE_RENDERER_REGISTRY);
}
