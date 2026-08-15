import assert from 'node:assert/strict';
import {
  actionResponseNavQuery,
  actionResponseRouteTarget,
} from '../src/pages/contractForm/actionContract';
import { buildContractActionRouteTarget } from '../src/app/runtime/actionViewContractActionRuntime';
import { useActionResponseNavigation } from '../src/pages/contractForm/useActionResponseNavigation';

const sourceQuery = {
  menu_id: '501',
  action_id: '502',
  view_id: '503',
  current_business_category_code: 'source.category',
  default_business_category_code: 'source.category',
  current_business_category_label: '来源业务',
  default_business_category_label: '来源业务',
  allowed_business_category_codes: 'source.category',
  search: 'source search',
  group_by: 'state',
  list_offset: '20',
  entry_context: JSON.stringify({ section: 'source', source: 'workspace' }),
  domain_raw: "[('source_id','=',7)]",
  context_raw: "{'source_model': True}",
  hud: '1',
};

const crossModelResult = {
  action_id: 626,
  context_raw: "{'default_source_id': 7, 'current_business_category_code': 'target.category'}",
  entry_target: {
    type: 'compatibility',
    route: '/f/x.target/new',
    compatibility_refs: {
      model: 'x.target',
      action_id: 626,
      menu_id: 627,
    },
  },
};

const crossModelQuery = actionResponseNavQuery(sourceQuery, crossModelResult, undefined, {
  currentModel: 'x.source',
});
assert.equal(crossModelQuery.hud, '1', 'shell diagnostics may cross a model boundary');
assert.equal(crossModelQuery.action_id, 626, 'backend target action replaces the source action');
assert.equal(crossModelQuery.menu_id, 627, 'backend target menu replaces the source menu');
assert.equal(crossModelQuery.context_raw, crossModelResult.context_raw, 'backend target context stays authoritative and opaque');
for (const key of [
  'current_business_category_code',
  'default_business_category_code',
  'current_business_category_label',
  'default_business_category_label',
  'allowed_business_category_codes',
  'search',
  'group_by',
  'list_offset',
  'domain_raw',
  'view_id',
  'entry_context',
]) {
  assert.equal(crossModelQuery[key], undefined, `cross-model navigation clears source-scoped ${key}`);
}

const sameModelQuery = actionResponseNavQuery(sourceQuery, {
  action_id: 700,
  entry_target: {
    type: 'compatibility',
    compatibility_refs: { model: 'x.source', action_id: 700 },
  },
}, undefined, { currentModel: 'x.source' });
assert.equal(sameModelQuery.current_business_category_code, 'source.category', 'same-model actions retain business context');
assert.equal(sameModelQuery.search, 'source search', 'same-model actions retain collection context');
assert.equal(sameModelQuery.entry_context, sourceQuery.entry_context, 'same-model actions retain validated workspace context');

const sameModelActionViewTarget = buildContractActionRouteTarget({
  nextActionId: 700,
  entryTarget: {
    type: 'compatibility',
    route: '/a/700',
    compatibility_refs: { model: 'x.source', action_id: 700, menu_id: 701 },
  },
  carryQuery: sourceQuery,
  responseQuery: null,
  currentModel: 'x.source',
  menuId: 501,
  keepSceneRoute: false,
  routePath: '/a/502',
});
assert.equal(sameModelActionViewTarget.query.menu_id, 701, 'an explicit backend target menu wins even within the same model');

const unknownModelQuery = actionResponseNavQuery(sourceQuery, { action_id: 701 }, undefined, {
  currentModel: 'x.source',
});
assert.equal(unknownModelQuery.current_business_category_code, 'source.category', 'an unknown target model does not guess a boundary');

const explicitRouteTarget = actionResponseRouteTarget(sourceQuery, {
  path: '/f/x.target/new',
  query: {
    context_raw: "{'target_query_wins': True}",
    current_business_category_code: 'target.category',
  },
}, crossModelResult, undefined, { currentModel: 'x.source' });
assert.equal(explicitRouteTarget.query.context_raw, "{'target_query_wins': True}", 'explicit target query wins over response and carry state');
assert.equal(explicitRouteTarget.query.current_business_category_code, 'target.category', 'target-declared business context is retained');
assert.equal(explicitRouteTarget.query.default_business_category_code, undefined, 'stale paired defaults are not reconstructed');

const actionViewTarget = buildContractActionRouteTarget({
  nextActionId: 626,
  entryTarget: crossModelResult.entry_target,
  carryQuery: sourceQuery,
  responseQuery: { context_raw: crossModelResult.context_raw },
  currentModel: 'x.source',
  menuId: 501,
  keepSceneRoute: false,
  routePath: '/a/502',
});
assert.equal(actionViewTarget.query.menu_id, 627, 'collection actions use the backend target menu across models');
assert.equal(actionViewTarget.query.action_id, 626, 'collection actions use the backend target action');
assert.equal(actionViewTarget.query.current_business_category_code, undefined, 'collection actions do not leak source business context');
assert.equal(actionViewTarget.query.search, undefined, 'collection actions do not leak source list state');
assert.equal(actionViewTarget.query.context_raw, crossModelResult.context_raw, 'collection actions preserve response context');

const pushedTargets: Array<Record<string, unknown>> = [];
const navigation = useActionResponseNavigation({
  router: {
    currentRoute: { value: { fullPath: '/r/x.source/7?action_id=502' } },
    resolve: () => ({ fullPath: '/f/x.target/new?action_id=626' }),
    push: async (target: unknown) => {
      pushedTargets.push(target as Record<string, unknown>);
    },
  } as never,
  currentQuery: () => sourceQuery,
  currentModel: () => 'x.source',
});
assert.equal(await navigation.navigateActionResponseResult(crossModelResult), true, 'the real form navigation runtime accepts the backend target');
assert.equal(pushedTargets.length, 1, 'the real form navigation runtime performs one navigation');
const pushed = pushedTargets[0];
assert.equal(pushed.path, '/f/x.target/new', 'the backend target route is preserved');
const pushedQuery = pushed.query as Record<string, unknown>;
assert.equal(pushedQuery.action_id, 626, 'the real navigation route uses the target action');
assert.equal(pushedQuery.menu_id, 627, 'the real navigation route uses the target menu');
assert.equal(pushedQuery.current_business_category_label, undefined, 'the real navigation route cannot inherit a source-model label');
assert.equal(pushedQuery.context_raw, crossModelResult.context_raw, 'the real navigation route preserves backend context');

const rawOnlyTargets: Array<Record<string, unknown>> = [];
const rawOnlyNavigation = useActionResponseNavigation({
  router: {
    currentRoute: { value: { fullPath: '/r/x.source/7?action_id=502' } },
    resolve: () => ({ fullPath: '/f/x.target/new?action_id=626' }),
    push: async (target: unknown) => { rawOnlyTargets.push(target as Record<string, unknown>); },
  } as never,
  currentQuery: () => sourceQuery,
  currentModel: () => 'x.source',
});
assert.equal(await rawOnlyNavigation.navigateActionResponseResult({
  raw_action: {
    id: 626,
    res_model: 'x.target',
    entry_target: crossModelResult.entry_target,
  },
}), true, 'a normalized raw action remains a backend navigation authority');
assert.equal((rawOnlyTargets[0].query as Record<string, unknown>).current_business_category_code, undefined, 'raw-action targets receive the same cross-model reset');

console.log('cross-model action navigation tests passed');
