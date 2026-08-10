#!/usr/bin/env node

import assert from 'node:assert/strict';
import {
  isActionViewLoadLeaseCurrent,
  shouldCaptureActionViewRouteLease,
} from '../../frontend/apps/web/src/app/actionViewRouteLeaseCore.js';

const versionActivity = 'action:846:menu:654';
const plannerActivity = 'action:584:menu:389';

assert.equal(shouldCaptureActionViewRouteLease(versionActivity, versionActivity), true);
assert.equal(
  shouldCaptureActionViewRouteLease(versionActivity, plannerActivity),
  false,
  'a kept-alive version page must not capture the planner route domain/context',
);

const base = {
  loadGeneration: 7,
  latestLoadGeneration: 7,
  isComponentActive: true,
  instanceActivityRouteKey: versionActivity,
  currentActivityRouteKey: versionActivity,
};
assert.equal(isActionViewLoadLeaseCurrent(base), true);
assert.equal(
  isActionViewLoadLeaseCurrent({ ...base, latestLoadGeneration: 8 }),
  false,
  'an earlier async response must not overwrite a newer load in the same page',
);
assert.equal(
  isActionViewLoadLeaseCurrent({ ...base, isComponentActive: false }),
  false,
  'a deactivated kept-alive page must not apply a response',
);
assert.equal(
  isActionViewLoadLeaseCurrent({ ...base, currentActivityRouteKey: plannerActivity }),
  false,
  'an async response must not cross action/menu activity identity',
);

console.log('[frontend_action_view_route_lease_race.test] PASS route snapshot and async response lease isolation');
