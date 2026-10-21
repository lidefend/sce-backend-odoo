// Acceptance probes reuse the browser's entry-bound request, never storage-key
// conventions or physical database hints. Credentials remain in memory only.
export function successfulIntentData(status, body, label) {
  if (status < 200 || status >= 300 || !body || body.ok === false || body.error
      || Number(body.code || 0) >= 400) {
    throw new Error(`${label}: intent request rejected (HTTP ${status})`);
  }
  return body.result || body.data || body;
}

export async function bindAuthenticatedIntent(response, expectedUserId) {
  const body = await response.json();
  const data = successfulIntentData(response.status(), body, 'system.init');
  if (!(expectedUserId > 0) || Number(data.user?.id) !== expectedUserId) {
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
  return async (context, intent, params) => {
    let replay;
    try {
      replay = await context.request.post(url, {
        headers, data: { ...original, intent, params },
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
}
