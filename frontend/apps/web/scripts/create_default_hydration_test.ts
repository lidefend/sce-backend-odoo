import assert from 'node:assert/strict';
import {
  createRouteDefaultsFingerprint,
  resolveCreateDefaults,
  resolveCreateRouteRelationLabels,
  shouldHydrateCreateDefaults,
} from '../src/pages/contractForm/createDefaults';

const contract = {
  fields: {
    archived: { type: 'boolean' },
    category_id: { type: 'many2one' },
    owner_id: { type: 'many2one' },
    partner_id: { type: 'many2one' },
    priority: { type: 'integer' },
    title: { type: 'char' },
  },
  __unified_page_contract_v2: {
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

const defaults = resolveCreateDefaults({ contract, routeQuery, v2ContractStore: null });
assert.equal(defaults.owner_id, 17, 'a route default fills an empty contract value');
assert.equal(defaults.partner_id, 23, 'multiple route relation defaults are applied');
assert.equal(defaults.priority, 3, 'a scalar route default is hydrated without becoming a relation option');
assert.equal(defaults.category_id, 41, 'an explicit contract value wins over a route default');
assert.equal(defaults.title, 'Contract title', 'an explicit scalar contract value wins');
assert.equal(defaults.archived, false, 'an explicit boolean false remains authoritative');
assert.equal(defaults.department_id, 31, 'context fills a value absent from contract and route defaults');
assert.equal('owner_id_label' in defaults, false, 'display labels never become business fields');
assert.deepEqual(resolveCreateRouteRelationLabels(contract, routeQuery, defaults), {
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

console.log('[create-default-hydration] PASS cases=17');
