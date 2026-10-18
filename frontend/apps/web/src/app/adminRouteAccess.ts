/**
 * Admin route access policy for the ADR-007 identity split.
 *
 * Platform control and tenant configuration are distinct authorities:
 * - `platformAdminOnly` routes require the backend-declared platform identity.
 * - the remaining `adminOnly` routes are tenant configuration surfaces and
 *   require the backend-declared tenant configuration identity.
 *
 * The flags are consumed from the runtime identity payload; no namespace
 * parsing happens here.
 */

export interface AdminRouteMeta {
  adminOnly?: unknown;
  platformAdminOnly?: unknown;
}

export interface AdminRouteUser {
  is_platform_admin?: boolean | null;
  is_tenant_config_admin?: boolean | null;
}

export type AdminRouteAccess = 'allow' | 'platform_required' | 'tenant_required';

export function resolveAdminRouteAccess(
  meta: AdminRouteMeta | null | undefined,
  user: AdminRouteUser | null | undefined,
): AdminRouteAccess {
  if (meta?.platformAdminOnly === true) {
    return user?.is_platform_admin === true ? 'allow' : 'platform_required';
  }
  if (meta?.adminOnly === true) {
    return user?.is_tenant_config_admin === true ? 'allow' : 'tenant_required';
  }
  return 'allow';
}

export function isAdminRouteAccessDenied(
  meta: AdminRouteMeta | null | undefined,
  user: AdminRouteUser | null | undefined,
): boolean {
  return resolveAdminRouteAccess(meta, user) !== 'allow';
}
