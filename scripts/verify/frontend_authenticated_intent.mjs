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

export function safeTransportCode(error) {
  for (const candidate of [error?.cause?.code, error?.code]) {
    const code = String(candidate || '').trim().toUpperCase();
    if (/^(?:E[A-Z0-9_]{2,63}|UND_ERR_[A-Z0-9_]+|ERR_[A-Z0-9_]+)$/.test(code)) {
      return code.slice(0, 64);
    }
  }
  for (const candidate of [error?.cause?.name, error?.name]) {
    const name = String(candidate || '').trim();
    if (/^(?:Error|TypeError|RangeError|AbortError|TimeoutError|APIError)$/.test(name)) {
      return name;
    }
  }
  return 'unknown';
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
    let transportCode = 'unknown';
    for (let attempt = 0; attempt < 2; attempt += 1) {
      try {
        replay = await context.request.post(url, {
          headers, data, timeout: 30000,
        });
        break;
      } catch (error) {
        transportCode = safeTransportCode(error);
        if (attempt === 0) await new Promise(resolve => setTimeout(resolve, 250));
      }
    }
    if (!replay) {
      throw new Error(`${intent}: authenticated probe transport failed (${transportCode})`);
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
  const cleanups = [];
  const waitForIntent = intent => new Promise(resolve => {
    const finish = result => {
      page.off('response', onResponse);
      clearTimeout(timer);
      resolve(result);
    };
    const onResponse = response => {
      try {
        if (!new URL(response.url()).pathname.endsWith('/api/v1/intent')) return;
        const request = response.request();
        if (request.method() !== 'POST') return;
        if (JSON.parse(request.postData() || '{}').intent !== intent) return;
      } catch { return; }
      finish({ response });
    };
    const timer = setTimeout(() => finish({ failed: true }), 45000);
    cleanups.push(() => finish({ failed: true }));
    page.on('response', onResponse);
  });
  const loginWait = waitForIntent('login');
  const startupWait = waitForIntent('system.init');
  try {
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
    return await bindAuthenticatedIntent(startup.response);
  } finally {
    for (const cleanup of cleanups) cleanup();
  }
}

// Hydration can remount the login form; verify both values after settling.
// Never include credentials or browser exception text in the failure message.
export async function fillLoginCredentials(page, login, password, timeout = 45000) {
  const deadline = Date.now() + timeout;
  const username = () => page.locator('#login-username, input[autocomplete="username"]').first();
  const secret = () => page.locator('#login-password, input[autocomplete="current-password"]').first();
  const remaining = () => Math.max(1, Math.min(1000, deadline - Date.now()));
  while (Date.now() < deadline) {
    try {
      await username().fill(login, { timeout: remaining() });
      await secret().fill(password, { timeout: remaining() });
      await page.waitForTimeout(Math.min(300, Math.max(0, deadline - Date.now())));
      const observedLogin = await username().inputValue({ timeout: remaining() });
      const observedPassword = await secret().inputValue({ timeout: remaining() });
      if (Date.now() <= deadline && observedLogin === login && observedPassword === password) return;
    } catch { /* Retry only within the bounded hydration deadline. */ }
    await page.waitForTimeout(Math.min(100, Math.max(0, deadline - Date.now())));
  }
  throw new Error('login form did not stabilize within timeout');
}
