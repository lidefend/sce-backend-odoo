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
// The same child runtime serves every contract-declared collection.
const { useOne2manyRuntime } = await import('../src/pages/contractForm/useOne2manyRuntime');
const columns = [
  { name: 'name', label: 'Name', ttype: 'char', required: true, modifiers: { readonly: { kind: 'field_compare', field: 'state', operator: '!=', value: 'draft' } } },
  { name: 'state', label: 'State', ttype: 'selection', required: false, readonly: true },
  { name: 'approved_by', label: 'Approved by', ttype: 'many2one', required: false, readonly: true },
  { name: 'quantity', label: 'Quantity', ttype: 'float', required: false },
  { name: 'active', label: 'Active', ttype: 'boolean', required: false },
  { name: 'note', label: 'Note', ttype: 'char', required: false },
];
let resolveChild!: (values: Record<string, unknown>) => void;
let rejectChild!: (error: unknown) => void;
let requests = 0, changes = 0, errors = 0;
let owner: unknown = {};
const child = useOne2manyRuntime({
  model: () => 'x.parent', recordId: () => 10, originalValues: () => ({}), parentValues: () => ({}),
  onchangeLinePatches: () => [], resolveColumns: () => columns, resolvePrimaryColumn: () => 'name', resolveRelationOptions: () => [],
  markFieldChanged: () => { changes += 1; }, createScope: () => owner,
  loadDefaults: () => { requests += 1; return new Promise((resolve, reject) => { resolveChild = resolve; rejectChild = reject; }); },
  onCreateError: () => { errors += 1; },
});
const adding = child.addRow('lines');
assert.equal(child.defaultsPending.value, true);
assert.equal(child.visibleRows('lines').length, 0, 'no half-initialized row while defaults load');
await child.addRow('lines'); assert.equal(requests, 1, 'duplicate clicks cannot start parallel draft creation');
resolveChild({ state: 'draft', approved_by: false, quantity: 0, active: false }); await adding;
const draft = child.visibleRows('lines')[0]!;
assert.equal(draft.values.state, 'draft');
assert.equal(child.effectiveColumn('lines', draft, columns[0]!).readonly, false);
child.setRowField('lines', draft.key, columns[0]!, 'Entered name');
assert.deepEqual(child.buildCommandValue('lines', 'write'), [[0, 0, { quantity: 0, active: false, name: 'Entered name' }]], 'readonly audit/state and untouched empty note are not writes');
child.setRowField('lines', draft.key, columns[5]!, '');
assert.equal((child.buildCommandValue('lines', 'write') as unknown as Array<[number, number, { note?: string }]>)[0][2].note, '', 'explicit empty user edit remains a write');
assert.equal((child.buildCommandValue('lines', 'onchange') as unknown as Array<[number, number, { state?: string }]>)[0][2].state, 'draft', 'onchange sees full defaults including readonly state');
const failed = child.addRow('lines'); rejectChild(new Error('temporary failure')); await failed;
assert.equal(errors, 1); assert.equal(child.visibleRows('lines').length, 1, 'failure cannot append empty row');
assert.equal(child.defaultsPending.value, false);
const stale = child.addRow('lines'); child.clearRows(); owner = {}; resolveChild({ state: 'draft' }); await stale;
assert.equal(child.visibleRows('lines').length, 0, 'old response cannot append to another draft');
const old = child.addRow('lines'); const oldResolve = resolveChild; child.clearRows();
const newest = child.addRow('lines'); const newestResolve = resolveChild;
oldResolve({ state: 'approved' }); await old;
assert.equal(child.defaultsPending.value, true, 'old completion cannot clear new busy owner');
newestResolve({ state: 'draft' }); await newest;
assert.equal(child.visibleRows('lines').length, 1);
assert.equal(child.visibleRows('lines')[0]!.values.state, 'draft');
assert.equal(changes, 4, 'only accepted rows and explicit edits dirty the parent');
console.log('[create-default-hydration] PASS cases=55');

// One authoritative frame feeds actual child rendering, edits, validation and writes.
const { bindNativeContext, bindNativeRowParentContext } = await import('../src/app/nativeModifierContext');
let parentDraft = false;
const contextualColumns = [{ name: 'note', label: 'Note', ttype: 'char', modifiers: {
  required: { kind: 'value_truthy', semantics: 'python', value_expr: { kind: 'context_get', key: 'required', default: false } },
  readonly: { kind: 'field_truthy', field: 'parent.locked' },
} }];
const contextual = useOne2manyRuntime({
  model: () => 'x.parent', recordId: () => 0, originalValues: () => ({}),
  parentValues: name => bindNativeRowParentContext(
    bindNativeContext({ locked: parentDraft, '$native.context': { required: false } }, { context: { required: false } }),
    { required: name === 'lines' },
  ),
  onchangeLinePatches: () => [], resolveColumns: () => contextualColumns,
  resolvePrimaryColumn: () => '', resolveRelationOptions: () => [], markFieldChanged: () => {},
});
await contextual.addRow('lines');
await contextual.addRow('other');
const contextualRow = contextual.visibleRows('lines')[0]!;
contextualRow.values['$native.context'] = { required: false };
assert.equal(contextual.effectiveColumn('lines', contextualRow, contextualColumns[0]!).required, true);
assert.equal(contextual.effectiveColumn('other', contextual.visibleRows('other')[0]!, contextualColumns[0]!).required, false);
assert.equal(contextual.collectValidation().issues.length, 1);
parentDraft = true;
contextual.setRowField('lines', contextualRow.key, contextualColumns[0]!, 'Denied');
assert.equal(contextualRow.values.note, '');
assert.equal(contextual.effectiveColumn('lines', contextualRow, contextualColumns[0]!).readonly, true);
parentDraft = false;
contextual.setRowField('lines', contextualRow.key, contextualColumns[0]!, 'Allowed');
assert.equal(contextual.collectValidation().issues.length, 0);
assert.deepEqual(contextual.buildCommandValue('lines', 'write'), [[0, 0, { note: 'Allowed' }]]);
parentDraft = true;
assert.deepEqual(contextual.buildCommandValue('lines', 'write'), [[0, 0, {}]]);
assert.throws(() => bindNativeRowParentContext({}, { required: true }));
assert.throws(() => bindNativeRowParentContext({ '$native.context': {} }, "{'required': True}"));
console.log('one2many authoritative row frame: passed');

const typedColumns = [
  { name: 'partner_id', label: 'Partner', ttype: 'many2one' },
  { name: 'note', label: 'Note', ttype: 'char', modifiers: {
    readonly: { kind: 'field_compare', semantics: 'python', field: 'partner_id', operator: '==', value: 7 },
    required: { kind: 'field_compare', semantics: 'python', field: 'partner_id', operator: '==', value: 8 },
  } },
];
const typedChild = useOne2manyRuntime({
  model: () => 'x.parent', recordId: () => 0, originalValues: () => ({}), parentValues: () => ({}),
  onchangeLinePatches: () => [], resolveColumns: () => typedColumns,
  resolvePrimaryColumn: () => '', resolveRelationOptions: () => [], markFieldChanged: () => {},
  loadDefaults: async () => ({ partner_id: [7, 'Initial'] }),
});
await typedChild.addRow('lines');
const typedRow = typedChild.visibleRows('lines')[0]!;
assert.equal(typedChild.effectiveColumn('lines', typedRow, typedColumns[1]!).readonly, true);
typedChild.setRowField('lines', typedRow.key, typedColumns[1]!, 'Denied');
assert.equal(typedRow.values.note, '');
typedChild.setRowField('lines', typedRow.key, typedColumns[0]!, 8);
assert.equal(typedChild.effectiveColumn('lines', typedRow, typedColumns[1]!).readonly, false);
assert.equal(typedChild.collectValidation().issues.length, 1);
typedChild.setRowField('lines', typedRow.key, typedColumns[1]!, 'Allowed');
assert.equal(typedChild.collectValidation().issues.length, 0);
assert.deepEqual(typedChild.buildCommandValue('lines', 'write'), [[0, 0, { partner_id: 8, note: 'Allowed' }]]);
typedChild.setRowField('lines', typedRow.key, typedColumns[0]!, 7);
assert.deepEqual(typedChild.buildCommandValue('lines', 'write'), [[0, 0, { partner_id: 7 }]]);
console.log('typed child relation draft runtime: passed');

// Native default commands materialize real draft rows; virtual rows are not persisted IDs.
const defaultLines = [[0, 0, { name: 'Default line', quantity: 2 }]];
const identityColumns = [
  { name: 'name', label: 'Name', ttype: 'char' },
  { name: 'quantity', label: 'Quantity', ttype: 'float' },
  { name: 'note', label: 'Note', ttype: 'char', modifiers: { readonly: {
    kind: 'field_compare', semantics: 'python', field: 'parent.lines', operator: '!=', value: [],
  } } },
];
const identityChild = useOne2manyRuntime({
  model: () => 'x.parent', recordId: () => 0, originalValues: () => ({ lines: defaultLines }),
  parentValues: () => ({ lines: defaultLines, '$native.fieldTypes': { lines: 'one2many' } }),
  onchangeLinePatches: () => [], resolveColumns: () => identityColumns,
  resolvePrimaryColumn: () => 'name', resolveRelationOptions: () => [], markFieldChanged: () => {},
});
identityChild.initRows('lines', defaultLines);
const defaultRow = identityChild.visibleRows('lines')[0]!;
assert.equal(defaultRow.values.name, 'Default line');
assert.equal(defaultRow.values.quantity, 2);
assert.equal(defaultRow.values.id, false);
assert.equal(defaultRow.isNew, true);
assert.equal(identityChild.effectiveColumn('lines', defaultRow, identityColumns[2]!).readonly, false);
assert.deepEqual(identityChild.buildCommandValue('lines', 'write'), [[0, 0, { name: 'Default line', quantity: 2 }]]);
identityChild.initRows('lines', [[6, 0, [42]], ...defaultLines]);
const mixed = identityChild.visibleRows('lines');
assert.equal(mixed.length, 2);
assert.equal(identityChild.effectiveColumn('lines', mixed[1]!, identityColumns[2]!).readonly, true);
identityChild.setRowField('lines', mixed[1]!.key, identityColumns[2]!, 'Denied');
assert.equal(mixed[1]!.values.note, '');
identityChild.removeRow('lines', mixed[0]!.key);
assert.equal(identityChild.effectiveColumn('lines', mixed[1]!, identityColumns[2]!).readonly, false);
identityChild.setRowField('lines', mixed[1]!.key, identityColumns[2]!, 'Allowed');
assert.equal(mixed[1]!.values.note, 'Allowed');
identityChild.restoreRow('lines', mixed[0]!.key);
assert.equal(identityChild.effectiveColumn('lines', mixed[1]!, identityColumns[2]!).readonly, true);
identityChild.clearRows();
assert.equal(identityChild.visibleRows('lines').length, 0);
await identityChild.addRow('lines');
assert.equal(identityChild.visibleRows('lines').length, 2, 'add hydrates initial defaults before appending');
console.log('native default rows and parent collection identities: passed');

const replayColumns = [
  { name: 'name', label: 'Name', ttype: 'char' },
  { name: 'quantity', label: 'Quantity', ttype: 'float' },
];
const replayChild = useOne2manyRuntime({
  model: () => 'x.parent', recordId: () => 9, originalValues: () => ({ lines: [42, 43] }),
  parentValues: () => ({ '$native.fieldTypes': { lines: 'one2many' } }),
  onchangeLinePatches: () => [], resolveColumns: () => replayColumns,
  resolvePrimaryColumn: () => 'name', resolveRelationOptions: () => [], markFieldChanged: () => {},
});
replayChild.initRows('lines', [42, 43]);
replayChild.mergeHydratedRecords('lines', [{ id: 42, name: 'Keep', quantity: 1 }, { id: 43, name: 'Other', quantity: 3 }]);
await replayChild.addRow('lines');
const localNewKey = replayChild.visibleRows('lines')[2]!.key;
replayChild.setRowField('lines', localNewKey, replayColumns[0]!, 'Local unsaved');
const beforeReplay = JSON.stringify(replayChild.fieldRows('lines'));
assert.throws(() => replayChild.prepareOnchangeRows('lines', [[1, 42, { quantity: 2 }], [1, 999, { quantity: 4 }]]), { name: 'ContractGapError' });
assert.equal(JSON.stringify(replayChild.fieldRows('lines')), beforeReplay, 'invalid later command cannot partially apply earlier command');
const commitReplay = replayChild.prepareOnchangeRows('lines', [[1, 42, { quantity: 2 }], [0, 0, { name: 'Server new', quantity: 4 }]]);
assert.equal(JSON.stringify(replayChild.fieldRows('lines')), beforeReplay, 'preparation is read-only');
commitReplay();
assert.equal(replayChild.fieldRows('lines')[0]!.values.name, 'Keep');
assert.equal(replayChild.fieldRows('lines')[0]!.values.quantity, 2);
assert.equal(replayChild.visibleRows('lines').some(row => row.key === localNewKey && row.values.name === 'Local unsaved'), true);
assert.equal(replayChild.visibleRows('lines').length, 4);
replayChild.prepareOnchangeRows('lines', [[2, 42], [3, 43], [4, 99]])();
assert.deepEqual(replayChild.buildCommandValue('lines', 'write'), [
  [2, 42], [3, 43], [0, 0, { name: 'Local unsaved' }], [0, 0, { name: 'Server new', quantity: 4 }], [4, 99],
]);
replayChild.prepareOnchangeRows('lines', [[6, 0, [99, 43]]])();
assert.deepEqual(replayChild.visibleRows('lines').map(row => row.id), [99, 43]);
replayChild.prepareOnchangeRows('lines', [[5, 0, 0]])();
assert.equal(replayChild.visibleRows('lines').length, 0);
const beforeInvalid = JSON.stringify(replayChild.fieldRows('lines'));
for (const commands of [[[1, 'virtual_1', { name: 'Unknown' }]], [[0, 0, { hidden: 1 }]], [[6, 0, [42, 42]]], [[4, -1]]]) {
  assert.throws(() => replayChild.prepareOnchangeRows('lines', commands), { name: 'ContractGapError' });
  assert.equal(JSON.stringify(replayChild.fieldRows('lines')), beforeInvalid);
}
console.log('one2many staged onchange replay and transport semantics: passed');
replayChild.initRows('lines', [42, 43]);
replayChild.prepareOnchangeRows('lines', [[2, 42], [5, 0, 0]])();
assert.deepEqual(replayChild.buildCommandValue('lines', 'write'), [[2, 42], [3, 43]], 'clear preserves earlier delete tombstone');
replayChild.initRows('lines', [42, 43]);
for (const tail of [[4, 42], [6, 0, [42]], [1, 42, { name: 'Revived' }]]) {
  const before = JSON.stringify(replayChild.fieldRows('lines'));
  assert.throws(() => replayChild.prepareOnchangeRows('lines', [[2, 42], tail]), { name: 'ContractGapError' });
  assert.equal(JSON.stringify(replayChild.fieldRows('lines')), before);
}
replayChild.prepareOnchangeRows('lines', [[3, 42], [4, 42]])();
assert.deepEqual(replayChild.visibleRows('lines').map(row => row.id), [42, 43], 'unlink followed by link is reversible');
