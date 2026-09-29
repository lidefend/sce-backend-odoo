// Authentication establishes only the fixture session; all remaining calls read.
const reads = new Set(['login', 'system.init', 'ui.contract', 'ui.contract.v2', 'my.work.summary', 'workspace.home', 'user.view.preference.get', 'ui.business_config.surface.get', 'ui.business_config.coverage.scan', 'global.message.conversations', 'global.message.thread']);
export function permitsInventoryRequest(method, pathname, body, allowNavigationTelemetry = false) {
  if (method !== 'POST' || pathname !== '/api/v1/intent') return false;
  const request = body?.params?.intent ? body.params : body;
  if (request?.intent === 'usage.track') return allowNavigationTelemetry;
  if (request?.intent === 'api.data') return ['list', 'read', 'default_get'].includes(request.params?.op);
  return reads.has(request?.intent);
}
