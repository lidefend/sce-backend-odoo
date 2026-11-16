import assert from 'node:assert/strict';
import test from 'node:test';
import { createExpectedHttpFailureBudget } from './platform_capability_explorer_browser_support.mjs';

const INTENT = 'platform.capability.explorer.list';

test('an expected HTTP failure can be consumed exactly once', () => {
  const budget = createExpectedHttpFailureBudget();
  budget.arm({ status: 409, intent: INTENT });
  assert.equal(budget.consume({ status: 409, intent: INTENT }), true);
  assert.equal(budget.consume({ status: 409, intent: INTENT }), false);
  assert.equal(budget.pending(), 0);
});

test('a non-matching response cannot consume the expected budget', () => {
  const budget = createExpectedHttpFailureBudget();
  budget.arm({ status: 409, intent: INTENT });
  assert.equal(budget.consume({ status: 409, intent: 'platform.capability.explorer.detail' }), false);
  assert.equal(budget.consume({ status: 500, intent: INTENT }), false);
  assert.equal(budget.pending(), 1);
  assert.equal(budget.consume({ status: 409, intent: INTENT }), true);
});

test('pending expected failures are visible when the injected response never arrives', () => {
  const budget = createExpectedHttpFailureBudget();
  budget.arm({ status: 409, intent: INTENT });
  assert.equal(budget.pending(), 1);
});

const { bindObservedDeniedIntent, authenticateDeniedProbe } = await import('./platform_capability_explorer_browser_support.mjs');
const { EventEmitter } = await import('node:events');
const ENTRY = 'https://example.test/t/registered-entry/login';
function startupResponse({ id = 7, namespace = 'registered-entry', headers = {}, context = { company_id: 3 } } = {}) {
  return {
    status: () => 200,
    json: async () => ({ data: { user: { id } } }),
    url: () => `https://example.test/t/${namespace}/api/v1/intent`,
    request: () => ({
      method: () => 'POST',
      url: () => `https://example.test/t/${namespace}/api/v1/intent`,
      allHeaders: async () => ({ authorization: 'Bearer test-only', 'content-length': '42', ...headers }),
      postData: () => JSON.stringify({ intent: 'system.init', context, params: {} }),
    }),
  };
}

test('observed authenticated transport preserves entry and context, and exposes exact denial', async () => {
  const probe = await bindObservedDeniedIntent(startupResponse(), 7, ENTRY);
  let sent;
  const context = { request: { post: async (url, options) => {
    sent = { url, ...options };
    return { status: () => 403, json: async () => ({ error: { reason_code: 'PERMISSION_DENIED' } }) };
  } } };
  assert.deepEqual(await probe(context), { status: 403, reasonCode: 'PERMISSION_DENIED', requestCount: 1 });
  assert.equal(sent.url, 'https://example.test/t/registered-entry/api/v1/intent');
  assert.equal(sent.headers.authorization, 'Bearer test-only');
  assert.equal(sent.headers['content-length'], undefined);
  assert.deepEqual(sent.data, { intent: INTENT, context: { company_id: 3 }, params: {} });
  context.request.post = async () => ({ status: () => 401, json: async () => ({ error: { code: 'AUTH_REQUIRED' } }) });
  assert.deepEqual(await probe(context), { status: 401, reasonCode: 'AUTH_REQUIRED', requestCount: 2 });
});

test('missing observation, wrong principal, wrong namespace and database hints are rejected', async () => {
  await assert.rejects(bindObservedDeniedIntent(undefined, 7, ENTRY), /request missing/);
  await assert.rejects(bindObservedDeniedIntent(startupResponse({ id: 8 }), 7, ENTRY), /principal mismatch/);
  await assert.rejects(bindObservedDeniedIntent(startupResponse({ namespace: 'other' }), 7, ENTRY), /namespace mismatch/);
  await assert.rejects(bindObservedDeniedIntent(startupResponse({ headers: { 'x-tenant': 'other' } }), 7, ENTRY), /namespace mismatch/);
  await assert.rejects(bindObservedDeniedIntent(startupResponse({ headers: { 'x-odoo-db': 'other' } }), 7, ENTRY), /database routing/);
  await assert.rejects(bindObservedDeniedIntent(startupResponse({ context: { db: 'other' } }), 7, ENTRY), /database routing/);
  await assert.rejects(bindObservedDeniedIntent(startupResponse({ headers: { authorization: '' } }), 7, ENTRY), /request missing/);
});

test('login observation must match the requested principal and listeners are released', async () => {
  for (const actualLogin of ['reader', 'other']) {
    const page = new EventEmitter();
    page.url = () => ENTRY;
    const submit = async () => {
      const response = startupResponse();
      page.emit('response', { ...response, request: () => ({
        ...response.request(), postData: () => JSON.stringify({ intent: 'login', params: { login: actualLogin } }),
      }) });
      page.emit('response', response);
    };
    const result = authenticateDeniedProbe(page, 'reader', submit);
    if (actualLogin === 'reader') assert.equal(typeof await result, 'function');
    else await assert.rejects(result, /requested login mismatch/);
    assert.equal(page.listenerCount('response'), 0);
  }
});
