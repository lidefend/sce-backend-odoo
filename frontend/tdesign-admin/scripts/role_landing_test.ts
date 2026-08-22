import assert from 'node:assert/strict';

import type { RouteRecordRaw } from 'vue-router';

import { firstAvailableRoute, isNotFoundRoute, originalRequestedPath } from '../src/utils/route/roleLanding';

const notFoundRoute = { path: '/:w+', name: '404Page', redirect: '/result/404' } satisfies RouteRecordRaw;

assert.equal(
  originalRequestedPath({
    fullPath: '/result/404',
    redirectedFrom: { fullPath: '/menu-from-another-role', name: notFoundRoute.name },
  }),
  '/menu-from-another-role',
);

assert.equal(isNotFoundRoute({ name: notFoundRoute.name }), true);
assert.equal(isNotFoundRoute({ name: 'Result404', path: '/result/404' }), true);
assert.equal(isNotFoundRoute({ name: 'Result404', redirectedFrom: { name: notFoundRoute.name } }), true);
assert.equal(isNotFoundRoute({ name: 'OdooFinanceAction', path: '/finance/payment' }), false);

assert.equal(
  firstAvailableRoute([
    notFoundRoute,
    {
      path: '/finance',
      name: 'FinanceCenter',
      redirect: '/finance/payment',
    },
  ]),
  '/finance/payment',
);
assert.equal(
  firstAvailableRoute([
    notFoundRoute,
    {
      path: '/settlement',
      name: 'SettlementCenter',
      component: () => Promise.resolve({}),
      children: [{ path: 'orders', name: 'SettlementOrders', component: () => Promise.resolve({}) }],
    },
  ]),
  '/settlement/orders',
);
assert.equal(firstAvailableRoute([notFoundRoute]), '/dashboard/base');

console.log('role landing routing tests: PASS');
