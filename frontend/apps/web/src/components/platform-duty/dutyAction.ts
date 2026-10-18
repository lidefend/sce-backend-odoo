/**
 * Platform duty action resolution (PLATFORM-ADMIN-DUTY / ADR-007 D6).
 *
 * A declared duty carries a route, an intent, or nothing.  The route is not
 * automatically a page: ``/api/ops/tenants`` is an API endpoint, and pushing it
 * into the router would unmount the SPA and show raw JSON.  Only a declared
 * frontend route may navigate; every ``/api/`` duty is consumed inside the
 * platform page so the duty is usable where it is listed.
 */

export type DutyAction =
  | { kind: 'navigate'; route: string }
  | { kind: 'inline'; endpoint: string }
  | { kind: 'intent'; intent: string }
  | { kind: 'none' };

/** Routes served by the SPA shell. Anything else is not navigable. */
export const SPA_ROUTE_PREFIXES = ['/admin/', '/a/'] as const;
export const SPA_ROUTE_EXACT = ['/'] as const;

/** Exact platform-control routes declared by the backend duty contract. */
export const DECLARED_PLATFORM_API_ENDPOINTS = {
  tenantRegistry: '/api/ops/tenants',
  maintenanceAccess: '/api/ops/maintenance/access',
  jobStatus: '/api/ops/job/status',
  subscriptionSet: '/api/ops/subscription/set',
} as const;

/** Endpoints that mutate state and therefore must not be auto-fetched. */
export const WRITE_ENDPOINTS = [DECLARED_PLATFORM_API_ENDPOINTS.subscriptionSet] as const;

export function isApiEndpoint(route: string): boolean {
  return String(route ?? '').trim().startsWith('/api/');
}

export function isSpaRoute(route: string): boolean {
  const value = String(route ?? '').trim();
  if (!value.startsWith('/')) return false;
  if (value.startsWith('/api/')) return false;
  if ((SPA_ROUTE_EXACT as readonly string[]).includes(value)) return true;
  return SPA_ROUTE_PREFIXES.some((prefix) => value.startsWith(prefix));
}

export function isWriteEndpoint(endpoint: string): boolean {
  return (WRITE_ENDPOINTS as readonly string[]).includes(String(endpoint ?? '').trim());
}

export function resolveDutyAction(
  duty?: { route?: string | null; intent?: string | null } | null,
): DutyAction {
  const route = String(duty?.route ?? '').trim();
  if (route) {
    if (isApiEndpoint(route)) return { kind: 'inline', endpoint: route };
    if (isSpaRoute(route)) return { kind: 'navigate', route };
    return { kind: 'none' };
  }
  const intent = String(duty?.intent ?? '').trim();
  if (intent) return { kind: 'intent', intent };
  return { kind: 'none' };
}
