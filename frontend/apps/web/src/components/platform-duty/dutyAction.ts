/**
 * Platform duty action resolution (PLATFORM-ADMIN-DUTY / ADR-007 D6).
 *
 * A declared duty carries a route, an action, or nothing.  The route is not
 * automatically a page: a bare ``/api/...`` endpoint must never enter the
 * router, because that would unmount the SPA and show raw JSON.  Platform
 * duties therefore declare an official window action or a declared frontend
 * route; an API-shaped route stays unresolved so the panel fails visibly
 * instead of inventing a product surface.
 */

export type DutyAction =
  | { kind: 'navigate'; route: string }
  | { kind: 'inline'; endpoint: string }
  | { kind: 'intent'; intent: string }
  | { kind: 'none' };

/** Routes served by the SPA shell. Anything else is not navigable. */
export const SPA_ROUTE_PREFIXES = ['/admin/', '/a/'] as const;
export const SPA_ROUTE_EXACT = ['/'] as const;

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
