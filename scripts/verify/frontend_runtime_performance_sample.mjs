// P4 measurement only. Never persist request parameters or response payloads.
const measuredIntents = new Set(['login', 'session.bootstrap', 'system.init']);
function numericMap(value) {
  return Object.fromEntries(Object.entries(value || {}).filter(([key, item]) =>
    /^[a-zA-Z0-9_.:-]{1,120}$/.test(key) && typeof item === 'number' && Number.isFinite(item) && item >= 0));
}
export function startupTiming(value) {
  if (!value || typeof value !== 'object') return null;
  const total = value.total_ms;
  return {
    total_ms: typeof total === 'number' && Number.isFinite(total) && total >= 0 ? total : null,
    timings_ms: numericMap(value.timings_ms),
    subtimings_ms: Object.fromEntries(Object.entries(value.subtimings_ms || {})
      .filter(([key, item]) => /^[a-zA-Z0-9_.:-]{1,120}$/.test(key) && item && typeof item === 'object' && !Array.isArray(item))
      .map(([key, item]) => [key, numericMap(item)])),
  };
}
export async function measureRuntimeSample(page, run, identity) {
  const requests = [];
  const started = performance.now();
  const capture = request => {
    if (!request.url().includes('/api/v1/intent')) return;
    let intent;
    try { intent = JSON.parse(request.postData() || '{}').intent; } catch { return; }
    if (measuredIntents.has(intent)) requests.push({ request, intent, started_ms: performance.now() - started });
  };
  page.on('request', capture);
  let total;
  try {
    await run();
    total = Math.round(performance.now() - started);
  } finally {
    page.off('request', capture);
  }
  // Read diagnostics after the original UI-ready measurement ends, so JSON
  // parsing/serialization does not become part of the product timing budget.
  const observations = await Promise.all(requests.map(async ({ request, intent, started_ms }) => {
    const row = { intent, started_ms: Math.round(started_ms), status: null,
      response_end_ms: null, request_duration_ms: null, startup_profile: null, diagnostic: 'unavailable' };
    try {
      const response = await request.response();
      if (!response) return row;
      const failure = await response.finished();
      const timing = request.timing();
      row.status = response.status();
      if (Number.isFinite(timing.responseEnd) && timing.responseEnd >= 0) {
        row.request_duration_ms = timing.responseEnd;
        row.response_end_ms = Math.round(started_ms + timing.responseEnd);
      }
      if (failure) return { ...row, diagnostic: 'request_failed' };
      if (intent === 'system.init') {
        const envelope = await response.json();
        row.startup_profile = startupTiming(envelope?.meta?.startup_profile);
      }
      row.diagnostic = intent === 'system.init' && !row.startup_profile ? 'startup_profile_missing' : 'captured';
    } catch { /* Missing diagnostics never fabricate zero server time. */ }
    return row;
  }));
  const ends = observations.map(row => row.response_end_ms).filter(value => value !== null);
  return { sample: identity, total_ms: total, requests: observations,
    first_request_ms: observations.length ? Math.min(...observations.map(row => row.started_ms)) : null,
    ui_after_last_response_ms: ends.length ? total - Math.max(...ends) : null };
}
