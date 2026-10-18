import assert from 'node:assert/strict';
import test from 'node:test';

import {
  isApiEndpoint,
  isSpaRoute,
  resolveDutyAction,
} from './dutyAction.ts';

test('an API duty is consumed inline and never navigated', () => {
  const endpoint = '/api/ops/maintenance/access';
  const action = resolveDutyAction({ route: endpoint });
  assert.deepEqual(action, { kind: 'inline', endpoint });
  assert.equal(isApiEndpoint(endpoint), true);
  assert.equal(isSpaRoute(endpoint), false);
});

test('declared frontend routes may navigate', () => {
  assert.deepEqual(resolveDutyAction({ route: '/admin/release-operator' }), {
    kind: 'navigate',
    route: '/admin/release-operator',
  });
  assert.deepEqual(resolveDutyAction({ route: '/a/92' }), {
    kind: 'navigate',
    route: '/a/92',
  });
  assert.deepEqual(resolveDutyAction({ route: '/' }), { kind: 'navigate', route: '/' });
  assert.equal(isSpaRoute('/admin/scene-health'), true);
  assert.equal(isSpaRoute('/a/92'), true);
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
