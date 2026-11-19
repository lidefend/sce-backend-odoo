import { authenticateBrowserProbe, assertEntryRequest, successfulIntentData } from '../../../../scripts/verify/frontend_authenticated_intent.mjs';

// Keep observed credentials in this closure only; never expose them in reports.
export async function bindObservedDeniedIntent(response, expectedUserId, entryUrl, expectedTenant = '') {
  if (!response) throw new Error('denied probe: authenticated startup request missing');
  const startup = successfulIntentData(response.status(), await response.json(), 'system.init');
  if (!(expectedUserId > 0) || Number(startup.user?.id) !== expectedUserId) {
    throw new Error('denied probe: authenticated principal mismatch');
  }
  const request = response.request();
  const url = request.url();
  const headers = { ...await request.allHeaders() };
  delete headers['content-length'];
  const original = JSON.parse(request.postData() || '{}');
  const entry = new URL(entryUrl);
  const observed = new URL(url);
  const namespace = entry.pathname.match(/^\/t\/([^/]+)(?:\/|$)/)?.[1];
  const tenantHint = String(expectedTenant || namespace);
  if (!namespace || observed.origin !== entry.origin
      || observed.pathname !== `/t/${namespace}/api/v1/intent`
      || (headers['x-tenant'] && tenantHint && headers['x-tenant'] !== tenantHint)) {
    throw new Error(`denied probe: entry namespace mismatch entry=${entryUrl} observed=${url} namespace=${namespace} tenant=${headers['x-tenant'] || ''}`);
  }
  if (request.method() !== 'POST' || original.intent !== 'system.init' || !headers.authorization) {
    throw new Error('denied probe: authenticated startup request missing');
  }
  assertEntryRequest(url, headers, original);
  let requestCount = 0;
  return async context => {
    const data = { ...original, intent: 'platform.capability.explorer.list', params: {} };
    assertEntryRequest(url, headers, data);
    requestCount += 1;
    const result = await context.request.post(url, { headers, data, timeout: 30000 });
    let body = {};
    try { body = await result.json(); } catch { /* Caller still checks the status and reason. */ }
    return { status: result.status(), reasonCode: String(body?.error?.reason_code || body?.error?.code || ''), requestCount };
  };
}

export async function authenticateDeniedProbe(page, expectedLogin, submit, declaredEntryUrl = '', expectedTenant = '') {
  const entryUrl = String(declaredEntryUrl || page.url());
  let startupResponse;
  const observe = response => {
    try {
      if (!startupResponse && JSON.parse(response.request().postData() || '{}').intent === 'system.init') {
        startupResponse = response;
      }
    } catch { /* Ignore unrelated browser requests. */ }
  };
  page.on('response', observe);
  try {
    const authenticated = await authenticateBrowserProbe(page, expectedLogin, submit);
    return await bindObservedDeniedIntent(
      startupResponse,
      Number(authenticated.startupData.user?.id),
      entryUrl,
      expectedTenant,
    );
  } finally {
    page.off('response', observe);
  }
}

export function createExpectedHttpFailureBudget() {
  const expectations = [];

  return {
    arm({ status, intent, count = 1 }) {
      if (!Number.isInteger(status) || status < 400 || status > 599) {
        throw new Error('expected HTTP failure status must be a 4xx or 5xx integer');
      }
      if (!Number.isInteger(count) || count < 1) {
        throw new Error('expected HTTP failure count must be a positive integer');
      }
      expectations.push({
        status,
        intent: String(intent || ''),
        remaining: count,
      });
    },
    consume({ status, intent }) {
      const requestIntent = String(intent || '');
      const expectation = expectations.find((item) => (
        item.remaining > 0
        && item.status === status
        && (!item.intent || item.intent === requestIntent)
      ));
      if (!expectation) return false;
      expectation.remaining -= 1;
      return true;
    },
    pending() {
      return expectations.reduce((total, item) => total + item.remaining, 0);
    },
  };
}
