/**
 * Row activation identity must come from the contract's row placement.
 *
 * The backend `normalize_target_scope` collapses native placement (header /
 * toolbar / smart / row) into the closed V2 target-scope vocabulary, so header
 * actions also carry `targetScope: 'page'`.  A row-activation lookup that
 * accepts `targetScope === 'page'` therefore matches the first header action and
 * can navigate a row click to a header action's target.  These cases bind the
 * navigation runtime to the declared row placement instead.
 */
import assert from 'node:assert/strict';
import {
  ROW_PLACEMENT_WIDGET_ID,
  isRowPlacementAction,
  useActionViewNavigationRuntime,
} from '../src/app/action_runtime/useActionViewNavigationRuntime';

type Dict = Record<string, unknown>;

function rule(partial: Dict): Dict {
  return {
    actionId: 'action.placeholder',
    actionKey: 'placeholder',
    triggerType: 'click',
    sourceWidgetId: 'page.header',
    targetIds: [],
    dispatchMode: 'server',
    targetScope: 'page',
    refreshMode: 'partial',
    intent: 'execute',
    target: {},
    button: {},
    ...partial,
  };
}

const HEADER_HIJACK_TARGET = { route: '/f/other.model/999' };

const headerAction = rule({
  actionId: 'action.action_open_project_budgets',
  sourceWidgetId: 'page.header',
  target: HEADER_HIJACK_TARGET,
});

const rowAction = rule({
  actionId: 'action.open_form',
  actionKey: 'open_form',
  sourceWidgetId: ROW_PLACEMENT_WIDGET_ID,
  intent: 'open',
  target: { view_type: 'form' },
});

function makeStore(actionRuleList: Dict[], viewType = 'list') {
  return {
    snapshot: {
      pageInfo: { viewType, model: 'project.project' },
      actionContract: { actionRuleList, dependencyGraph: {} },
    },
    widgetsByFieldCode: new Map(),
  } as unknown as Parameters<typeof useActionViewNavigationRuntime>[0]['actionContract']['value'];
}

type Push = Dict;

function drive(actionRuleList: Dict[], row: Dict, options?: { viewType?: string; editable?: boolean }) {
  const pushes: Push[] = [];
  const runtime = useActionViewNavigationRuntime({
    routeQueryMap: { value: { view_mode: 'list' } } as never,
    showHud: { value: true } as never,
    menuId: { value: 501 } as never,
    actionId: { value: 348 } as never,
    actionContract: { value: makeStore(actionRuleList, options?.viewType || 'list') } as never,
    canEditRecord: { value: options?.editable === true } as never,
    resolvedModelRef: { value: 'project.project' } as never,
    modelRef: { value: 'project.project' } as never,
    routerPush: (target: unknown) => {
      pushes.push(target as Push);
      return Promise.resolve();
    },
  });
  runtime.handleRowClick(row);
  return pushes;
}

// 0. The placement predicate itself.
assert.equal(isRowPlacementAction(rowAction), true, 'row placement is a row action');
assert.equal(isRowPlacementAction(headerAction), false, 'header placement is not a row action');
assert.equal(isRowPlacementAction(null), false, 'missing action is not a row action');
assert.equal(isRowPlacementAction(undefined), false, 'undefined action is not a row action');
assert.equal(isRowPlacementAction({ sourceWidgetId: ' page.row ' }), true, 'placement id is trimmed');

// 1. A header action declared before the row action must never be chosen.
{
  const pushes = drive([headerAction, rowAction], { id: 10, model: 'project.project' });
  assert.equal(pushes.length, 1, 'a row click resolves exactly one target');
  const path = String(pushes[0].path || '');
  assert.ok(
    !path.includes('other.model'),
    `row activation must not inherit the header action target, got ${path}`,
  );
  assert.ok(
    path.endsWith('/project.project/10'),
    `row activation must open the clicked record, got ${path}`,
  );
}

// 2. The row action's own declared target is still honored and materialized.
{
  const explicitRow = rule({
    actionId: 'action.open_form',
    sourceWidgetId: ROW_PLACEMENT_WIDGET_ID,
    intent: 'open',
    target: { route: '/f/project.project/${id}' },
  });
  const pushes = drive([headerAction, explicitRow], { id: 10, model: 'project.project' });
  assert.equal(pushes.length, 1, 'declared row target resolves exactly one target');
  assert.equal(String(pushes[0].path || ''), '/f/project.project/10', 'row target materializes the row id');
  const targetQuery = (pushes[0].query || {}) as Dict;
  assert.equal(targetQuery.menu_id, 501, 'row target keeps the owning menu identity');
  assert.equal(targetQuery.action_id, 348, 'row target keeps the owning action identity');
}

// 3. Without a declared row placement the runtime must not invent row identity.
{
  const pushes = drive([headerAction], { id: 10, model: 'project.project' });
  assert.equal(pushes.length, 0, 'header-only contracts must not resolve a row action');
}

// 4. Row placement is only consumed on collection view types.
{
  const pushes = drive([headerAction, rowAction], { id: 10, model: 'project.project' }, { viewType: 'form' });
  assert.equal(pushes.length, 0, 'form contracts must not resolve a row action');
}

console.log('[OK] collection row action identity: 6 cases');
