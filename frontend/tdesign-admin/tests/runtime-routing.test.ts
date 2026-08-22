import assert from 'node:assert/strict';

import test from 'node:test';

import {
  findRouteAuthority,
  normalizeRouteAuthorityContract,
  requiresRuntimeRouteValidation,
  routeAuthorityValidationParams,
} from '../src/utils/route/authority.ts';
import { resolveBusinessTarget } from '../src/utils/route/businessTarget.ts';
import {
  businessContextSnapshot,
  businessTabKey,
  restoreMissingRecordContext,
  sameBusinessContext,
} from '../src/utils/route/tabIdentity.ts';
import { actionSurfaceViewOptions } from '../src/pages/odoo/action/runtime/actionSurfaceRegistry.ts';

test('business target resolves shareable record routes with action context', () => {
  assert.deepEqual(resolveBusinessTarget({ model: 'sc.project', record_id: 42, action_id: 8, menu_id: 9 }), {
    name: 'OdooRecordDetail',
    params: { model: 'sc.project', id: '42' },
    query: { action_id: '8', menu_id: '9' },
  });
});

test('route authority enforces required query context', () => {
  const contract = normalizeRouteAuthorityContract({
    contract_version: 'route_authority.v1',
    principal_scope: { user_id: 1, company_id: 1, role_code: 'manager' },
    primary_actions: [
      { route_kind: 'PRIMARY_NAV', action_id: 8, menu_id: 9, context_requirements: { required_query: ['project_id'] } },
    ],
  });
  assert.equal(findRouteAuthority(contract, { actionId: 8, menuId: 9, query: {} }), null);
  assert.ok(findRouteAuthority(contract, { actionId: 8, menuId: 9, query: { project_id: '3' } }));
});

test('runtime authority validation forwards every declared context binding', () => {
  const authority = {
    route_kind: 'CONTEXTUAL_ROUTE' as const,
    action_id: 8,
    menu_id: 9,
    context_requirements: {
      required_query: ['project_id'],
      company_query: 'company_id',
      selected_record_query: 'selected_id',
      record_query: 'record_id',
    },
  };
  assert.deepEqual(
    routeAuthorityValidationParams(authority, {
      project_id: '3',
      company_id: '2',
      selected_id: '7',
      record_id: '11',
      ignored: 'value',
    }),
    { action_id: 8, project_id: '3', company_id: '2', selected_id: '7', record_id: '11' },
  );
  assert.equal(requiresRuntimeRouteValidation(authority), true);
  assert.equal(
    requiresRuntimeRouteValidation({
      route_kind: 'PRIMARY_NAV',
      action_id: 8,
      menu_id: 9,
      context_requirements: {},
    }),
    false,
  );
});

test('tab identity separates the same route by business context', () => {
  assert.notEqual(
    businessTabKey('/r/sc.project/42', { action_id: '8' }, { company_id: 1 }),
    businessTabKey('/r/sc.project/42', { action_id: '8' }, { company_id: 2 }),
  );
});

test('business tab snapshots only restorable scope and compares normalized values', () => {
  assert.deepEqual(
    businessContextSnapshot({ company_id: 2, current_project_id: 7, operation_strategy: 'self', ignored: true }),
    { company_id: 2, current_project_id: 7, operation_strategy: 'self' },
  );
  assert.equal(sameBusinessContext({ company_id: 2 }, { company_id: '2' }), true);
  assert.equal(sameBusinessContext({ company_id: 2 }, { company_id: 3 }), false);
});

test('record route restores action context removed by a stale persisted tab', () => {
  assert.deepEqual(
    restoreMissingRecordContext(
      { action_id: '8', menu_id: '9', source: 'work' },
      { source: 'work', section: 'collaboration' },
    ),
    { action_id: '8', menu_id: '9', source: 'work', section: 'collaboration' },
  );
  assert.equal(restoreMissingRecordContext({ action_id: '8', menu_id: '9' }, { action_id: '10', menu_id: '11' }), null);
});

test('action surface registry follows backend-declared views with a list fallback', () => {
  assert.deepEqual(
    actionSurfaceViewOptions(['tree', 'graph', 'calendar']).map((item) => item.value),
    ['list', 'graph', 'calendar'],
  );
  assert.deepEqual(
    actionSurfaceViewOptions(['card', 'kanban']).map((item) => item.value),
    ['cards', 'kanban'],
  );
  assert.deepEqual(
    actionSurfaceViewOptions(['unknown_view']).map((item) => item.value),
    ['list'],
  );
});
