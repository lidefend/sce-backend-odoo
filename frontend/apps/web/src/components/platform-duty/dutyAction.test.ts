import assert from 'node:assert/strict';
import test from 'node:test';

import { isApiEndpoint, isSpaRoute, isWriteEndpoint, resolveDutyAction } from './dutyAction.ts';

test('an API duty is consumed inline and never navigated', () => {
  const action = resolveDutyAction({ route: '/api/ops/tenants' });
  assert.deepEqual(action, { kind: 'inline', endpoint: '/api/ops/tenants' });
  assert.equal(isApiEndpoint('/api/ops/tenants'), true);
  assert.equal(isSpaRoute('/api/ops/tenants'), false);
});

test('declared frontend routes may navigate', () => {
  assert.deepEqual(resolveDutyAction({ route: '/admin/release-operator' }), {
    kind: 'navigate',
    route: '/admin/release-operator',
  });
  assert.deepEqual(resolveDutyAction({ route: '/' }), { kind: 'navigate', route: '/' });
  assert.equal(isSpaRoute('/admin/scene-health'), true);
});

test('an undeclared route never navigates', () => {
  assert.deepEqual(resolveDutyAction({ route: '/ops/tenants' }), { kind: 'none' });
  assert.deepEqual(resolveDutyAction({ route: 'https://example.invalid/x' }), { kind: 'none' });
  assert.equal(isSpaRoute('/platform'), false);
});

test('an intent duty stays an intent and an empty duty has no action', () => {
  assert.deepEqual(resolveDutyAction({ intent: 'release.operator.surface' }), {
    kind: 'intent',
    intent: 'release.operator.surface',
  });
  assert.deepEqual(resolveDutyAction({}), { kind: 'none' });
  assert.deepEqual(resolveDutyAction(null), { kind: 'none' });
});

test('write endpoints are declared so they are never auto-fetched', () => {
  assert.equal(isWriteEndpoint('/api/ops/subscription/set'), true);
  assert.equal(isWriteEndpoint('/api/ops/tenants'), false);
  assert.equal(isWriteEndpoint('/api/ops/job/status'), false);
});

test('every declared platform API duty resolves to an inline action', () => {
  const apiDuties = ['/api/ops/tenants', '/api/ops/maintenance/access', '/api/ops/job/status'];
  for (const route of apiDuties) {
    assert.equal(resolveDutyAction({ route }).kind, 'inline', route);
  }
});
