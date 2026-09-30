import assert from 'node:assert/strict';
import fs from 'node:fs';
import {
  createRouteDefaultsFingerprint,
  loadAuthoritativeCreateDefaults,
  mergeAuthoritativeCreateDefaults,
  resolveCreateDefaultGetRequest,
  resolveCreateDefaults,
  resolveCreateRouteRelationLabels,
  shouldHydrateCreateDefaults,
} from '../src/pages/contractForm/createDefaults';

const fieldTypes = {
  archived: 'boolean',
  category_id: 'many2one',
  owner_id: 'many2one',
  partner_id: 'many2one',
  priority: 'integer',
  title: 'char',
};
const v2ContractStore = {
  snapshot: {
    pageInfo: { contractVersion: '2.2.0', pageId: 'x.document.create', clientType: 'web' },
    layoutContract: { containerTree: [] },
    actionContract: { actionRuleList: [] },
    dataContract: {
      mainData: {
        owner_id: false,
        category_id: 41,
        archived: false,
        title: 'Contract title',
      },
      dataMeta: {
        sourceContext: { context: { default_department_id: 31 } },
      },
    },
  },
  widgetsByFieldCodeAll: new Map(Object.entries(fieldTypes).map(([name, type]) => [name, [{
    widgetId: `field.${name}`,
    widgetType: type,
    fieldCode: name,
    label: name,
    span: 6,
    componentKey: 'sc.input.text',
    capabilities: [],
    componentConfig: {},
    fieldDescriptor: { name, type },
  }]])),
} as never;
const routeQuery = {
  default_owner_id: '17',
  default_owner_id_label: 'Owner A',
  default_category_id: '99',
  default_category_id_label: 'Category from route',
  default_partner_id: '23',
  default_partner_id_label: 'Partner B',
  default_priority: '3',
  default_priority_label: 'High',
  default_title: 'Route title',
  default_archived: 'true',
};

const defaults = resolveCreateDefaults({ routeQuery, v2ContractStore });
assert.equal(defaults.owner_id, 17, 'a route default fills an empty contract value');
assert.equal(defaults.partner_id, 23, 'multiple route relation defaults are applied');
assert.equal(defaults.priority, 3, 'a scalar route default is hydrated without becoming a relation option');
assert.equal(defaults.category_id, 41, 'an explicit contract value wins over a route default');
assert.equal(defaults.title, 'Contract title', 'an explicit scalar contract value wins');
assert.equal(defaults.archived, false, 'an explicit boolean false remains authoritative');
assert.equal(defaults.department_id, 31, 'context fills a value absent from contract and route defaults');
assert.equal('owner_id_label' in defaults, false, 'display labels never become business fields');
assert.deepEqual(resolveCreateRouteRelationLabels(v2ContractStore, routeQuery, defaults), {
  owner_id: 'Owner A',
  partner_id: 'Partner B',
}, 'route labels hydrate only matching many2one defaults, never scalar fields');

const orderedA = createRouteDefaultsFingerprint(routeQuery);
const orderedB = createRouteDefaultsFingerprint(Object.fromEntries(Object.entries(routeQuery).reverse()));
assert.equal(orderedA, orderedB, 'route identity is independent of query insertion order');
assert.notEqual(
  orderedA,
  createRouteDefaultsFingerprint({ ...routeQuery, default_partner_id: '24' }),
  'a changed create default invalidates the retained route identity',
);

assert.equal(shouldHydrateCreateDefaults(null, 'create'), true);
assert.equal(shouldHydrateCreateDefaults(7, 'edit'), false);
assert.equal(shouldHydrateCreateDefaults(7, 'readonly'), false);
assert.equal(shouldHydrateCreateDefaults(null, 'readonly'), false);

const primaryDataSource = {
  query: 'api.data',
  intent: 'api.data',
  params: {
    op: 'default_get',
    model: 'x.document',
    fields: ['title', 'owner_id', 'computed_fact', 'not_on_form', 'title'],
    context: { default_owner_id: 17 },
  },
};
assert.deepEqual(resolveCreateDefaultGetRequest({
  primaryDataSource,
  model: 'x.document',
  fieldNames: ['title', 'owner_id', 'computed_fact'],
}), {
  model: 'x.document',
  fields: ['computed_fact', 'owner_id', 'title'],
  context: { default_owner_id: 17 },
}, 'the normalized data source is restricted to the current form model and fields');
assert.throws(() => resolveCreateDefaultGetRequest({
  primaryDataSource,
  model: 'x.other',
  fieldNames: ['title'],
}), /model mismatch/);
assert.throws(() => resolveCreateDefaultGetRequest({
  primaryDataSource: { ...primaryDataSource, params: { ...primaryDataSource.params, op: 'read' } },
  model: 'x.document',
  fieldNames: ['title'],
}), /api\.data\/default_get/);

let defaultGetCalls = 0;
const hydratedDefaults = await loadAuthoritativeCreateDefaults({
  primaryDataSource,
  model: 'x.document',
  fieldNames: ['title', 'owner_id', 'computed_fact'],
  baseDefaults: { title: 'Route title', owner_id: 17, computed_fact: '' },
  fetchDefaults: async (request) => {
    defaultGetCalls += 1;
    assert.equal(request.model, 'x.document');
    return { record: { title: 'Authoritative title', computed_fact: 'Derived fact', hidden_fact: 'blocked' } };
  },
});
assert.equal(defaultGetCalls, 1, 'a declared default_get source is consumed exactly once');
assert.deepEqual(hydratedDefaults, {
  title: 'Authoritative title',
  owner_id: 17,
  computed_fact: 'Derived fact',
}, 'authoritative model defaults override route fallbacks without injecting undeclared fields');
const legacyDefaults = await loadAuthoritativeCreateDefaults({
  primaryDataSource: {},
  model: 'x.document',
  fieldNames: ['title'],
  baseDefaults: { title: 'Legacy fallback' },
  fetchDefaults: async () => {
    defaultGetCalls += 1;
    return { record: {} };
  },
});
assert.deepEqual(legacyDefaults, { title: 'Legacy fallback' });
assert.equal(defaultGetCalls, 1, 'a legacy contract without a primary source performs no request');
await assert.rejects(() => loadAuthoritativeCreateDefaults({
  primaryDataSource,
  model: 'x.document',
  fieldNames: ['title'],
  baseDefaults: { title: 'Must not silently win' },
  fetchDefaults: async () => ({}),
}), /response record is required/, 'a malformed declared response fails closed instead of using static fallbacks');

const lifecycleSource = fs.readFileSync(
  'frontend/apps/web/src/pages/contractForm/useRecordPageLifecycle.ts',
  'utf8',
);
assert.match(lifecycleSource, /await loadAuthoritativeCreateDefaults\(/);
assert.match(lifecycleSource, /fetchDefaults:\s*defaultContractFormRecord/);
assert.ok(
  lifecycleSource.indexOf('shouldHydrateCreateDefaults') < lifecycleSource.indexOf('await loadAuthoritativeCreateDefaults('),
  'default_get consumption remains inside the create-only branch',
);

const relationBase = { owner_id: [17, 'Authorized owner'] };
const mergeRelation = (value: unknown, type = 'many2one') => mergeAuthoritativeCreateDefaults({
  baseDefaults: relationBase, authoritativeDefaults: { owner_id: value },
  fieldNames: ['owner_id'], fieldTypes: { owner_id: type },
}).owner_id;
assert.deepEqual(mergeRelation(17), [17, 'Authorized owner']);
assert.notEqual(mergeRelation(17), relationBase.owner_id, 'do not mutate shared mainData tuples');
for (const value of [18, false, null, 0, '', [17, 'Fresh label']]) {
  assert.deepEqual(mergeRelation(value), value, 'new authority or cleared identity must win');
}
assert.equal(mergeRelation(17, 'integer'), 17, 'tuple shape alone is not relation authority');
assert.equal(mergeAuthoritativeCreateDefaults({baseDefaults: relationBase,
  authoritativeDefaults: {owner_id: 17}, fieldNames: ['owner_id']}).owner_id, 17);
const relationLoaded = await loadAuthoritativeCreateDefaults({primaryDataSource,
  model: 'x.document', fieldNames: ['owner_id'], baseDefaults: relationBase,
  fieldTypes: {owner_id: 'many2one'}, fetchDefaults: async () => ({record: {owner_id: 17}})});
assert.deepEqual(relationLoaded.owner_id, [17, 'Authorized owner']);
console.log('[create-default-hydration] PASS cases=39');
