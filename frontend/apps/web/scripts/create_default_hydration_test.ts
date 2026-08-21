import assert from 'node:assert/strict';
import fs from 'node:fs';
import {
  createRouteDefaultsFingerprint,
  loadAuthoritativeCreateDefaults,
  resolveCreateDefaultGetRequest,
  resolveCreateDefaults,
  resolveCreateRouteRelationLabels,
  shouldHydrateCreateDefaults,
} from '../src/pages/contractForm/createDefaults';
import { createContractV2Store } from '../src/app/contracts/v2/store';

const v2ContractStore = createContractV2Store({
    pageInfo: { contractVersion: '2.2.0', pageId: 'x.document.create', clientType: 'web' },
    layoutContract: {
      pageId: 'x.document.create', layoutType: 'form', adaptMode: 'desktop', layoutHints: {}, componentRegistry: {},
      containerTree: [{
        containerId: 'form.root', containerType: 'form', title: 'Document', span: 24, children: [],
        widgetList: [
          ['archived', 'boolean'], ['category_id', 'many2one'], ['owner_id', 'many2one'],
          ['partner_id', 'many2one'], ['priority', 'integer'], ['title', 'char'],
        ].map(([fieldCode, fieldType]) => ({
          widgetId: `field.${fieldCode}`, widgetType: fieldType, fieldCode, label: fieldCode,
          span: 24, componentKey: 'sc.form.field', capabilities: [], componentConfig: { fieldType }, fieldType,
        })),
      }],
    },
    actionContract: { actionRuleList: [] },
    statusContract: { globalStatus: {}, widgetStatus: [], containerStatus: [], buttonStatus: [], selectorStatus: [] },
    dataContract: {
      dataSource: { primary: {} },
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
    runtimeContract: {},
    formStructureContract: {},
    meta: {},
} as never);
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

console.log('[create-default-hydration] PASS cases=28');
