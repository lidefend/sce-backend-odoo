/**
 * Batch C entry contract: one static build served under a namespace prefix.
 *
 * The same bundle is mounted at `/t/<alias>/` for a tenant and at
 * `/platform-admin/` for the platform entry. Every API call must stay inside
 * that prefix because the entry (nginx) refuses unknown namespaces and never
 * reads a client database hint.
 */

const TENANT_PREFIX = /^\/t\/([a-z0-9][a-z0-9-]{0,62})(?=\/|$)/;
const PLATFORM_PREFIX = /^\/platform-admin(?=\/|$)/;

export function resolveEntryBasePath(pathname?: string): string {
  const path = String(pathname ?? ((typeof window !== 'undefined' ? window.location.pathname : '') || ''));
  if (PLATFORM_PREFIX.test(path)) return '/platform-admin';
  const tenant = path.match(TENANT_PREFIX);
  return tenant ? `/t/${tenant[1]}` : '';
}

export function resolveEntryAudience(pathname?: string): 'platform-admin' | 'tenant' | '' {
  const path = String(pathname ?? ((typeof window !== 'undefined' ? window.location.pathname : '') || ''));
  if (PLATFORM_PREFIX.test(path)) return 'platform-admin';
  if (TENANT_PREFIX.test(path)) return 'tenant';
  return '';
}

export function entryScopedPath(path: string, basePath = resolveEntryBasePath()): string {
  const raw = String(path || '').trim();
  if (!raw || !basePath) return raw;
  if (!raw.startsWith('/')) return raw;
  if (raw === basePath || raw.startsWith(`${basePath}/`)) return raw;
  return `${basePath}${raw}`;
}
