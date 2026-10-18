/**
 * Behavioural lock for the ADR-007 admin-route identity split.
 *
 * Tenant configuration surfaces (`/admin/scene-health`, `/admin/scene-packages`,
 * `/admin/usage-analytics`) must admit a demo tenant config admin, while the
 * platform control surface (`/admin/release-operator`) must reject that same
 * admin and admit a platform control admin.
 */
import assert from 'node:assert/strict';

import {
  isAdminRouteAccessDenied,
  resolveAdminRouteAccess,
  type AdminRouteUser,
} from '../src/app/adminRouteAccess';

let cases = 0;
const check = (actual: unknown, expected: unknown, label: string) => {
  assert.deepEqual(actual, expected, label);
  cases += 1;
};

const demoAdmin: AdminRouteUser = { is_platform_admin: false, is_tenant_config_admin: true };
const platformAdmin: AdminRouteUser = { is_platform_admin: true, is_tenant_config_admin: true };
const plainUser: AdminRouteUser = { is_platform_admin: false, is_tenant_config_admin: false };

const tenantRoute = { adminOnly: true };
const platformRoute = { adminOnly: true, platformAdminOnly: true };
const openRoute = { layout: 'shell' };

// 1. Demo admin: tenant configuration routes stay open.
check(resolveAdminRouteAccess(tenantRoute, demoAdmin), 'allow', 'demo admin passes tenant admin routes');
check(isAdminRouteAccessDenied(tenantRoute, demoAdmin), false, 'demo admin is not denied on tenant admin routes');

// 2. Demo admin: platform control route is denied.
check(resolveAdminRouteAccess(platformRoute, demoAdmin), 'platform_required', 'demo admin is denied release-operator');
check(isAdminRouteAccessDenied(platformRoute, demoAdmin), true, 'demo admin denied on platform control route');

// 3. Platform admin: both surfaces stay open.
check(resolveAdminRouteAccess(platformRoute, platformAdmin), 'allow', 'platform admin passes release-operator');
check(resolveAdminRouteAccess(tenantRoute, platformAdmin), 'allow', 'platform admin passes tenant admin routes');

// 4. Plain tenant user: no admin surface.
check(resolveAdminRouteAccess(tenantRoute, plainUser), 'tenant_required', 'plain user denied tenant admin routes');
check(resolveAdminRouteAccess(platformRoute, plainUser), 'platform_required', 'plain user denied platform control route');

// 5. Non-admin routes ignore the identity flags.
check(resolveAdminRouteAccess(openRoute, plainUser), 'allow', 'open routes ignore admin flags');

// 6. platformAdminOnly supersedes adminOnly when both are declared.
check(
  resolveAdminRouteAccess({ adminOnly: true, platformAdminOnly: true }, demoAdmin),
  'platform_required',
  'platformAdminOnly is evaluated before adminOnly',
);

console.log(`[admin_route_access_test] PASS cases=${cases}`);
