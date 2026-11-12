import { ApiError } from '../api/client';

export function resolveAppInitFailureState(err: unknown) {
  const initError = err instanceof ApiError
    ? err.message
    : err instanceof Error
      ? err.message
      : String(err || 'init failed');
  return {
    initError,
    initTraceId: err instanceof ApiError ? err.traceId ?? null : null,
    initStatus: 'error' as const,
    isReady: false as const,
    routeAuthority: null,
    menuTree: [],
    navigationModel: null,
    scenarioSurface: null,
    currentAction: null,
    featureFlags: {},
    scenes: [],
    sceneVersion: null,
    sceneActionHints: {},
    capabilities: [],
    capabilityCatalog: {},
    capabilityGroups: [],
    sceneReadyContract: null,
    sceneGovernance: null,
    defaultRoute: null,
  };
}
