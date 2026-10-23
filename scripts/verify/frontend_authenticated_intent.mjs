// Acceptance probes reuse the browser's entry-bound request, never storage-key
// conventions or physical database hints. Credentials remain in memory only.
export function successfulIntentData(status, body, label) {
  if (status < 200 || status >= 300 || !body || body.ok === false || body.error
      || Number(body.code || 0) >= 400) {
    throw new Error(`${label}: intent request rejected (HTTP ${status})`);
  }
  return body.result || body.data || body;
}

export function assertEntryRequest(url, headers, payload) {
  const parsed = new URL(url);
  const hasDatabase = value => value && typeof value === 'object'
    && ['db', 'database'].some(key => Object.hasOwn(value, key));
  if (parsed.username || parsed.password
      || ['db', 'database'].some(key => parsed.searchParams.has(key))
      || Object.keys(headers).some(key => ['x-odoo-db', 'x-db', 'x-odoo-database', 'x-odoo-db-locked'].includes(key.toLowerCase()))
      || hasDatabase(payload) || hasDatabase(payload?.context)
      || hasDatabase(payload?.params) || hasDatabase(payload?.params?.context)) {
    throw new Error('authenticated probe: client database routing is forbidden');
  }
}

export async function bindAuthenticatedIntent(response, expectedPrincipal) {
  const body = await response.json();
  const data = successfulIntentData(response.status(), body, 'system.init');
  const expectedUserId = typeof expectedPrincipal === 'number' ? expectedPrincipal : Number(data.user?.id);
  if (!(expectedUserId > 0)
      || Number(data.user?.id) !== expectedUserId) {
    throw new Error('system.init: authenticated principal mismatch');
  }
  const request = response.request();
  const url = request.url();
  const headers = { ...await request.allHeaders() };
  delete headers['content-length'];
  const original = JSON.parse(request.postData() || '{}');
  if (original.intent !== 'system.init' || !headers.authorization) {
    throw new Error('system.init: authenticated request missing');
  }
  assertEntryRequest(url, headers, original);
  const replayIntent = async (context, intent, params) => {
    const data = { ...original, intent, params };
    assertEntryRequest(url, headers, data);
    let replay;
    try {
      replay = await context.request.post(url, {
        headers, data,
      });
    } catch {
      // Playwright transport errors can include request headers in their log.
      throw new Error(`${intent}: authenticated probe transport failed`);
    }
    const result = await replay.json();
    const payload = successfulIntentData(replay.status(), result, intent);
    if (intent === 'system.init' && Number(payload.user?.id) !== expectedUserId) {
      throw new Error('system.init: authenticated principal mismatch');
    }
    return { status: replay.status(), body: result };
  };
  replayIntent.startupData = data;
  return replayIntent;
}

// Register before the login click so fast startup responses cannot be missed.
// Both waits settle even when the submit action fails; no detached rejection.
export async function authenticateBrowserProbe(page, expectedLogin, submit) {
  const wait = (intent) => page.waitForResponse((response) => {
    if (!response.url().includes('/api/v1/intent')) return false;
    try { return JSON.parse(response.request().postData() || '{}').intent === intent; }
    catch { return false; }
  }, { timeout: 45000 }).then(response => ({ response }), () => ({ failed: true }));
  const loginWait = wait('login');
  const startupWait = wait('system.init');
  await submit();
  const login = await loginWait;
  if (login.failed) throw new Error('login: response missing');
  let loginRequest = {};
  try {
    loginRequest = JSON.parse(login.response.request()?.postData() || '{}');
  } catch {
    throw new Error('login: request payload is invalid');
  }
  if (String(loginRequest?.params?.login || '') !== expectedLogin) {
    throw new Error('login: requested login mismatch');
  }
  successfulIntentData(login.response.status(), {}, 'login');
  const startup = await startupWait;
  if (startup.failed) throw new Error('system.init: response missing');
  return bindAuthenticatedIntent(startup.response);
}
