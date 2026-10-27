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
assert.deepEqual(child.buildCommandValue('lines', 'onchange'), [[0, draft.key,
  { state: 'draft', approved_by: false, quantity: 0, active: false }]],
  'new-row onchange preserves declared defaults but never serializes unprovided display placeholders');

assert.equal(child.effectiveColumn('lines', draft, columns[0]!).readonly, false);
child.setRowField('lines', draft.key, columns[0]!, 'Entered name');
assert.deepEqual(child.buildCommandValue('lines', 'write'), [[0, 0, { quantity: 0, active: false, name: 'Entered name' }]], 'readonly audit/state and untouched empty note are not writes');
child.setRowField('lines', draft.key, columns[5]!, '');
assert.equal((child.buildCommandValue('lines', 'write') as unknown as Array<[number, number, { note?: string }]>)[0][2].note, '', 'explicit empty user edit remains a write');
assert.equal((child.buildCommandValue('lines', 'onchange')[0]![2] as Record<string, unknown>).note, '', 'explicit empty user edit remains present in onchange');
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

const virtualChild = useOne2manyRuntime({ model: () => 'x.parent', recordId: () => 0,
  originalValues: () => ({}), parentValues: () => ({ '$native.fieldTypes': { lines: 'one2many' } }),
  onchangeLinePatches: () => [], resolveColumns: () => replayColumns, resolvePrimaryColumn: () => 'name',
  resolveRelationOptions: () => [], markFieldChanged: () => {}, loadDefaults: async () => ({ name: 'Same label', quantity: 1 }),
});
await virtualChild.addRow('lines'); await virtualChild.addRow('lines');
const [virtualA, virtualB] = virtualChild.visibleRows('lines');
const requestCommands = virtualChild.buildCommandValue('lines', 'onchange') as unknown[][];
assert.deepEqual(requestCommands.map(command => command[1]), [virtualA!.key, virtualB!.key]);
assert.notEqual(virtualA!.key, virtualB!.key);
virtualChild.prepareOnchangeRows('lines', [[1, virtualB!.key, { quantity: 8 }]])();
assert.equal(virtualChild.visibleRows('lines')[0]!.values.quantity, 1);
assert.equal(virtualChild.visibleRows('lines')[1]!.values.quantity, 8);
virtualChild.prepareOnchangeRows('lines', [[0, virtualB!.key, { name: 'Echo' }]])();
assert.equal(virtualChild.visibleRows('lines').length, 2, 'create echo must not duplicate an existing virtual identity');
assert.equal(virtualChild.visibleRows('lines')[1]!.values.quantity, 8);
assert.deepEqual((virtualChild.buildCommandValue('lines', 'write') as unknown[][]).map(command => command[1]), [0, 0]);
for (const commands of [[[1, 'unknown_ref', { name: 'Wrong' }]], [[2, 'unknown_ref']], [[4, virtualA!.key]], [[6, 0, [virtualA!.key]]]]) {
  const before = JSON.stringify(virtualChild.fieldRows('lines'));
  assert.throws(() => virtualChild.prepareOnchangeRows('lines', commands), { name: 'ContractGapError' });
  assert.equal(JSON.stringify(virtualChild.fieldRows('lines')), before);
}
virtualChild.prepareOnchangeRows('lines', [[2, virtualA!.key]])();
assert.equal(virtualChild.visibleRows('lines').length, 1);
assert.equal((virtualChild.buildCommandValue('lines', 'write') as unknown[][]).some(command => command[0] === 2), false);
virtualChild.prepareOnchangeRows('lines', [[0, 'server_ref', { name: 'Server', quantity: 3 }], [1, 'server_ref', { quantity: 4 }]])();
assert.equal(virtualChild.visibleRows('lines').find(row => row.key === 'server_ref')?.values.quantity, 4);
assert.deepEqual(virtualChild.projectModifierValues({ '$native.fieldTypes': { lines: 'one2many' } }).lines, []);
console.log('virtual relation identities roundtrip and write separation: passed');

replayChild.initRows('lines', [42, 43]);
replayChild.prepareOnchangeRows('lines', [[4, 99, { id: 99, name: 'Native linked', quantity: 7 }]])();
const linked = replayChild.fieldRows('lines').find(row => row.id === 99)!;
assert.equal(linked.values.name, 'Native linked');
assert.equal(linked.values.quantity, 7);
assert.equal(linked.values.id, 99);
assert.deepEqual(linked.dirtyFields, []);
assert.equal(linked.dirty, false);
assert.deepEqual(replayChild.buildCommandValue('lines', 'write'), [[4, 99]], 'hydration must not become a write');
replayChild.prepareOnchangeRows('lines', [[4, 99, { id: 99, name: 'Refreshed' }], [1, 99, { quantity: 8 }]])();
assert.equal(replayChild.fieldRows('lines').filter(row => row.id === 99).length, 1);
assert.deepEqual(replayChild.buildCommandValue('lines', 'write'), [[4, 99], [1, 99, { quantity: 8 }]]);
for (const commands of [
  [[4, 100, { id: 101, name: 'Wrong identity' }]],
  [[4, 100, { undeclared: 'Unknown field' }]],
  [[4, 100, null]], [[4, 'virtual', { name: 'Invalid target' }]],
  [[4, 100, { name: 'Staged' }], [4, 101, { id: 100 }]],
  [[2, 99], [4, 99, { id: 99, name: 'Resurrected' }]],
]) {
  const before = JSON.stringify(replayChild.fieldRows('lines'));
  assert.throws(() => replayChild.prepareOnchangeRows('lines', commands), { name: 'ContractGapError' });
  assert.equal(JSON.stringify(replayChild.fieldRows('lines')), before);
}
console.log('native LINK row data hydration, identity and atomic rejection: passed');

replayChild.prepareOnchangeRows('lines', [[4, 99, { id: 99, quantity: 7, name: 'Latest baseline' }]])();
assert.equal(replayChild.fieldRows('lines').find(row => row.id === 99)?.values.quantity, 8);
assert.equal(replayChild.fieldRows('lines').find(row => row.id === 99)?.values.name, 'Latest baseline');
assert.deepEqual(replayChild.buildCommandValue('lines', 'write'), [[4, 99], [1, 99, { quantity: 8 }]]);
replayChild.prepareOnchangeRows('lines', [[1, 99, { quantity: 9 }], [4, 99, { id: 99, quantity: 7 }]])();
assert.equal(replayChild.fieldRows('lines').find(row => row.id === 99)?.values.quantity, 9);
assert.deepEqual(replayChild.buildCommandValue('lines', 'write'), [[4, 99], [1, 99, { quantity: 9 }]]);
replayChild.setRowField('lines', linked.key, replayColumns[1]!, 10);
replayChild.prepareOnchangeRows('lines', [[4, 99, { id: 99, quantity: 7 }]])();
assert.equal(replayChild.fieldRows('lines').find(row => row.id === 99)?.values.quantity, 10);
console.log('native LINK hydration preserves local and prior UPDATE dirty values: passed');

const { one2manyColumnsFromSubview } = await import('../src/pages/contractForm/one2manyUtils');
const forceColumns = one2manyColumnsFromSubview({ tree: {
  columns: ['name', 'forced', 'computed'], column_occurrences: [
    { name: 'name', field_type: 'char' },
    { name: 'forced', field_type: 'char', attributes: { force_save: '1' }, modifiers: { readonly: true, invisible: true } },
    { name: 'computed', field_type: 'char', attributes: { force_save: '0' }, modifiers: { readonly: true, invisible: true } },
  ],
} }, () => null);
const forceChild = useOne2manyRuntime({
  model: () => 'x.parent', recordId: () => 9, originalValues: () => ({ lines: [42] }), parentValues: () => ({}),
  onchangeLinePatches: () => [], resolveColumns: () => forceColumns, resolvePrimaryColumn: () => 'name',
  resolveRelationOptions: () => [], markFieldChanged: () => {},
});
forceChild.initRows('lines', [[0, 0, { name: 'New', forced: 'Default force', computed: 'Default computed' }]]);
const forceNew = forceChild.visibleRows('lines')[0]!;
forceChild.setRowField('lines', forceNew.key, forceColumns[1]!, 'Forbidden edit');
assert.equal(forceNew.values.forced, 'Default force');
assert.deepEqual(forceChild.buildCommandValue('lines', 'write')[0], [0, 0, { name: 'New', forced: 'Default force' }]);
assert.equal((forceChild.buildCommandValue('lines', 'onchange')[0]![2] as Record<string, unknown>).computed, 'Default computed');
forceChild.initRows('lines', [42]);
forceChild.prepareOnchangeRows('lines', [[1, 42, { forced: 'Server force', computed: 'Server computed' }]])();
assert.deepEqual(forceChild.buildCommandValue('lines', 'write'), [[1, 42, { forced: 'Server force' }]]);
assert.deepEqual(forceChild.buildCommandValue('lines', 'onchange'), [[1, 42, { forced: 'Server force', computed: 'Server computed' }]]);
forceChild.initRows('lines', [42]);
forceChild.prepareOnchangeRows('lines', [[1, 42, { computed: 'No forced write' }]])();
assert.deepEqual(forceChild.buildCommandValue('lines', 'write'), []);
console.log('native hidden force_save write/onchange separation and edit refusal: passed');

const { one2manyDataColumnsFromSubview } = await import('../src/pages/contractForm/one2manyUtils');
const formOnlySubview = {
  tree: { columns: ['name'], column_occurrences: [{ name: 'name', field_type: 'char', modifiers: { readonly: true } }] },
  fields: { unrelated: { type: 'char' } },
  form: { layout: [{ type: 'group', children: [
    { type: 'field', name: 'name', fieldInfo: { type: 'char' } },
    { type: 'field', name: 'internal_note', fieldInfo: { type: 'char' }, attributes: { force_save: '1' }, modifiers: { readonly: true, invisible: true } },
    { type: 'field', name: 'token', fieldInfo: { type: 'char' }, children: [{ type: 'field', name: 'grandchild', fieldInfo: { type: 'char' } }] },
  ] }] },
};
const displayFields = one2manyColumnsFromSubview(formOnlySubview, () => null);
const dataFields = one2manyDataColumnsFromSubview(formOnlySubview, () => null);
assert.deepEqual(displayFields.map(field => field.name), ['name']);
assert.deepEqual(dataFields.map(field => field.name), ['name', 'internal_note', 'token']);
assert.equal(dataFields[0]!.readonly, true, 'form occurrence cannot loosen an inline declaration');
assert.throws(() => one2manyDataColumnsFromSubview({ form: { layout: [{ type: 'field', name: 'missing_type' }] } }, () => null), { name: 'ContractGapError' });
const formOnlyChild = useOne2manyRuntime({
  model: () => 'x.parent', recordId: () => 0, originalValues: () => ({}), parentValues: () => ({}),
  onchangeLinePatches: () => [], resolveColumns: () => displayFields, resolveDataColumns: () => dataFields,
  resolvePrimaryColumn: () => 'name', resolveRelationOptions: () => [], markFieldChanged: () => {},
  loadDefaults: async () => ({ internal_note: 'Authoritative default', token: 'Declared token' }),
});
await formOnlyChild.addRow('lines');
const formOnlyRow = formOnlyChild.visibleRows('lines')[0]!;
assert.equal(formOnlyRow.values.internal_note, 'Authoritative default');
formOnlyChild.setRowField('lines', formOnlyRow.key, dataFields[2]!, 'Unrendered edit');
assert.equal(formOnlyRow.values.token, 'Declared token');
formOnlyChild.prepareOnchangeRows('lines', [[1, formOnlyRow.key, { internal_note: 'Server note', token: 'Server token' }]])();
assert.deepEqual(formOnlyChild.buildCommandValue('lines', 'write'), [[0, 0, { internal_note: 'Server note', token: 'Server token' }]]);
assert.equal((formOnlyChild.buildCommandValue('lines', 'onchange')[0]![2] as Record<string, unknown>).internal_note, 'Server note');
const formOnlyBefore = JSON.stringify(formOnlyChild.fieldRows('lines'));
assert.throws(() => formOnlyChild.prepareOnchangeRows('lines', [[1, formOnlyRow.key, { unrelated: 'Not declared by a view' }]]), { name: 'ContractGapError' });
assert.equal(JSON.stringify(formOnlyChild.fieldRows('lines')), formOnlyBefore);
console.log('explicit child form data fields default/onchange/write with stable display scope: passed');

const inheritedState = { locked: true, hidden: true };
const inheritedSubview = { tree: { columns: ['name'] }, form: { layout: [
  { type: 'group', modifiers: { readonly: { kind: 'field_truthy', field: 'parent.locked' } }, children: [
    { type: 'group', modifiers: { invisible: { kind: 'field_truthy', field: 'parent.hidden' } }, children: [
      { type: 'field', name: 'companion', fieldInfo: { type: 'char' }, modifiers: { required: true } },
    ] },
  ] },
  { type: 'group', attributes: { readonly: '1' }, children: [
    { type: 'field', name: 'static_locked', fieldInfo: { type: 'char' } },
  ] },
] } };
const inheritedData = one2manyDataColumnsFromSubview(inheritedSubview, () => null);
const inheritedChild = useOne2manyRuntime({
  model: () => 'x.parent', recordId: () => 0, originalValues: () => ({}), parentValues: () => inheritedState,
  onchangeLinePatches: () => [], resolveColumns: () => inheritedData.slice(0, 1), resolveDataColumns: () => inheritedData,
  resolvePrimaryColumn: () => 'name', resolveRelationOptions: () => [], markFieldChanged: () => {},
});
inheritedChild.initRows('lines', [[0, 0, { name: 'Parent', companion: '', static_locked: 'No write' }]]);
const inheritedRow = inheritedChild.visibleRows('lines')[0]!;
assert.equal(inheritedChild.effectiveColumn('lines', inheritedRow, inheritedData[1]!).invisible, true);
assert.equal(inheritedChild.effectiveColumn('lines', inheritedRow, inheritedData[1]!).readonly, true);
assert.deepEqual(inheritedChild.buildCommandValue('lines', 'write'), [[0, 0, { name: 'Parent' }]]);
assert.equal(inheritedChild.collectValidation().issues.length, 0);
inheritedState.locked = false;
inheritedState.hidden = false;
assert.equal(inheritedChild.effectiveColumn('lines', inheritedRow, inheritedData[1]!).readonly, false);
assert.equal(inheritedChild.collectValidation().issues.length > 0, true);
assert.deepEqual(inheritedChild.buildCommandValue('lines', 'write'), [[0, 0, { name: 'Parent', companion: '' }]]);
console.log('form-only ancestor visibility and readonly preserve dynamic native conditions: passed');

for (const constraint of ['readonly', 'invisible']) {
  const invalidAncestorColumn = { ...inheritedData[1]!, readonly: true, modifiers: { readonly: true, invisible: true },
    ancestorModifiers: [{ [constraint]: { kind: 'unsupported_native_constraint' } }] };
  assert.throws(() => inheritedChild.effectiveColumn('lines', inheritedRow, invalidAncestorColumn), { name: 'ContractGapError' });
}
console.log('form-only ancestor defects cannot hide behind true local constraints: passed');

const parentFrame = { company_id: 1 };
let finishInitialization!: (value: Record<string, unknown>) => void;
const waitingChild = useOne2manyRuntime({ model: () => 'x.parent', recordId: () => 0,
  originalValues: () => ({}), parentValues: () => parentFrame,
  createDraftIdentity: () => ({ values: { lines: waitingChild.buildCommandValue('lines', 'onchange') }, context: parentFrame }),
  onchangeLinePatches: () => [], resolveColumns: () => columns, resolvePrimaryColumn: () => 'name',
  resolveRelationOptions: () => [], markFieldChanged: () => {},
  loadDefaults: () => new Promise(resolve => { finishInitialization = resolve; }),
});
const staleInitialization = waitingChild.addRow('lines');
assert.equal(waitingChild.defaultsPending.value, true);
parentFrame.company_id = 2;
finishInitialization({ state: 'draft', quantity: 1 });
await staleInitialization;
assert.equal(waitingChild.fieldRows('lines').length, 0, 'parent draft changes invalidate child initialization');
assert.equal(waitingChild.defaultsPending.value, false);
const currentInitialization = waitingChild.addRow('lines');
finishInitialization({ state: 'draft', quantity: 2 });
await currentInitialization;
assert.equal(waitingChild.fieldRows('lines')[0]!.values.quantity, 2, 'current parent initialization appends only after resolution');
console.log('child initialization waits and rejects parent draft drift: passed');

const siblingInitialization = waitingChild.addRow('lines');
const sibling = waitingChild.fieldRows('lines')[0]!;
waitingChild.setRowField('lines', sibling.key, columns[3]!, 9);
finishInitialization({ state: 'draft', quantity: 3 });
await siblingInitialization;
assert.equal(waitingChild.fieldRows('lines').length, 1, 'sibling draft edits invalidate pending new-row initialization');
assert.equal(waitingChild.fieldRows('lines')[0]!.values.quantity, 9);
console.log('child initialization rejects sibling draft drift: passed');

// Server defaults and onchange keep labels for display; ORM writes require IDs.
const relationWriteColumns = [
  { name: 'name', label: 'Name', ttype: 'char' },
  { name: 'currency_id', label: 'Currency', ttype: 'many2one', forceSave: true, readonly: true },
];
const relationWrite = useOne2manyRuntime({
 model: () => 'x.parent', recordId: () => 0, originalValues: () => ({ lines: [42] }), parentValues: () => ({}),
 onchangeLinePatches: () => [], resolveColumns: () => relationWriteColumns, resolvePrimaryColumn: () => 'name',
 resolveRelationOptions: () => [], markFieldChanged: () => {}, loadDefaults: async () => ({ currency_id: [6, 'CNY'] }),
});
await relationWrite.addRow('lines');
const relationWriteRow=relationWrite.visibleRows('lines').find(row => row.isNew)!;
assert.deepEqual((relationWrite.buildCommandValue('lines','write')[0]![2] as Record<string,unknown>).currency_id,6);
assert.deepEqual(relationWriteRow.values.currency_id,[6,'CNY'],'serializing must not mutate the displayed relation');
assert.deepEqual((relationWrite.buildCommandValue('lines','onchange')[0]![2] as Record<string,unknown>).currency_id,[6,'CNY']);
relationWrite.initRows('lines',[42]);
relationWrite.prepareOnchangeRows('lines',[[1,42,{currency_id:[7,'USD']}]])();
assert.deepEqual(relationWrite.buildCommandValue('lines','write'),[[1,42,{currency_id:7}]]);
relationWrite.prepareOnchangeRows('lines',[[1,42,{currency_id:false}]])();
assert.deepEqual(relationWrite.buildCommandValue('lines','write'),[[1,42,{currency_id:false}]]);
for (const bad of [[6,'CNY','extra'],[0,'None'],[6,{label:'CNY'}],{},'invalid',1.2]) {
 relationWrite.fieldRows('lines')[0]!.values.currency_id=bad;
 assert.throws(()=>relationWrite.buildCommandValue('lines','write'),{name:'ContractGapError'});
}
console.log('child default/onchange many2one write identity and invalid-carrier refusal: passed');

// The actual child runtime awaits native derived values before notifying the
// parent, and never accepts a stale/failed child result as saveable data.
const changeColumns = [
 {name:'amount',label:'Amount',ttype:'float'},
 {name:'derived',label:'Derived',ttype:'float',readonly:true,forceSave:true},
];
let changeParent = 1, changeNotifications = 0, dirtyNotifications = 0;
let changeScope = {};
const changeCalls: Array<{input: unknown; resolve: (value: Record<string,unknown>)=>void; reject:(error:Error)=>void}> = [];
const fieldChanges = useOne2manyRuntime({
 model:()=> 'x.parent', recordId:()=>0, originalValues:()=>({}), parentValues:()=>({company_id:changeParent}),
 createScope:()=>changeScope, onchangeLinePatches:()=>[], resolveColumns:()=>changeColumns, resolvePrimaryColumn:()=> 'amount', resolveRelationOptions:()=>[],
 markFieldChanged:()=>{ changeNotifications++; }, markDirty:()=>{ dirtyNotifications++; },
 loadDefaults:async()=>({amount:0,derived:0}),
 loadRowChange:async(_name,input)=>new Promise((resolve,reject)=>changeCalls.push({input,resolve,reject})),
});
await fieldChanges.addRow('lines');
let changeRow=fieldChanges.fieldRows('lines')[0]!;
const firstChange=fieldChanges.setRowField('lines',changeRow.key,changeColumns[0]!,5);
assert.equal(fieldChanges.defaultsPending.value,true);
assert.equal(changeNotifications,1,'parent onchange waits for child result');
assert.equal(dirtyNotifications,1,'unsaved protection starts before network');
assert(fieldChanges.collectValidation().issues.length>0,'pending computation must block save');
changeCalls.at(-1)!.resolve({derived:17}); await firstChange;
assert.equal(fieldChanges.defaultsPending.value,false);
assert.equal(changeNotifications,2);
assert.equal(fieldChanges.collectValidation().issues.length,0);
assert.equal((fieldChanges.buildCommandValue('lines','write')[0]![2] as Record<string,unknown>).derived,17);
const failedChange=fieldChanges.setRowField('lines',changeRow.key,changeColumns[0]!,6);
changeCalls.at(-1)!.reject(new Error('native refused')); await failedChange;
assert(fieldChanges.collectValidation().issues.includes('native refused'),'failed computation must block save');
const oldChange=fieldChanges.setRowField('lines',changeRow.key,changeColumns[0]!,7);
const oldCall=changeCalls.at(-1)!;
const latestChange=fieldChanges.setRowField('lines',changeRow.key,changeColumns[0]!,8);
oldCall.resolve({derived:999}); await oldChange;
assert.equal(fieldChanges.defaultsPending.value,true,'old completion cannot clear newer pending');
changeCalls.at(-1)!.resolve({derived:28}); await latestChange;
assert.equal((fieldChanges.buildCommandValue('lines','write')[0]![2] as Record<string,unknown>).derived,28);
const drifted=fieldChanges.setRowField('lines',changeRow.key,changeColumns[0]!,9);
changeParent=2; changeCalls.at(-1)!.resolve({derived:888}); await drifted;
assert(fieldChanges.collectValidation().issues.length>0,'changed parent refuses old derivation');
assert.equal((fieldChanges.buildCommandValue('lines','write')[0]![2] as Record<string,unknown>).derived,28);
const invalidPatch=fieldChanges.setRowField('lines',changeRow.key,changeColumns[0]!,10);
changeCalls.at(-1)!.resolve({unrelated:1}); await invalidPatch;
assert(fieldChanges.collectValidation().issues.length>0,'undeclared patch blocks save');
const departed=fieldChanges.setRowField('lines',changeRow.key,changeColumns[0]!,11);
fieldChanges.clearRows(); changeCalls.at(-1)!.resolve({derived:123}); await departed;
assert.equal(fieldChanges.fieldRows('lines').length,0);
assert.equal(fieldChanges.defaultsPending.value,false);
assert.equal(fieldChanges.collectValidation().issues.length,0,'departed failure cannot contaminate new page');
console.log('native child field onchange: pending/save, failure, latest, parent drift, invalid patch, departed page passed');

await fieldChanges.addRow('lines'); changeRow=fieldChanges.fieldRows('lines')[0]!;
const changedScope=fieldChanges.setRowField('lines',changeRow.key,changeColumns[0]!,3);
changeScope={}; changeCalls.at(-1)!.resolve({derived:31}); await changedScope;
assert(fieldChanges.collectValidation().issues.length>0,'same row under new contract must not become saveable');
fieldChanges.clearRows();
const multiColumns = [...changeColumns,{name:'second',label:'Second',ttype:'float'}];
const multiCalls: Array<{input:{id:number;values:Record<string,unknown>;changed:string[]};resolve:(value:Record<string,unknown>)=>void}> = [];
const multi=useOne2manyRuntime({model:()=> 'x.parent', recordId:()=>9, originalValues:()=>({lines:[42]}),parentValues:()=>({}),
 onchangeLinePatches:()=>[],resolveColumns:()=>multiColumns,resolvePrimaryColumn:()=> 'amount',resolveRelationOptions:()=>[],
 markFieldChanged:()=>{}, loadRowChange:async(_name,input)=>new Promise(resolve=>multiCalls.push({input,resolve})),
});
multi.initRows('lines',[42]);
multi.mergeHydratedRecords('lines',[{id:42,display_name:'UI label',amount:1,derived:0,second:0}]);
const hydrated=multi.fieldRows('lines')[0]!;
const eventA=multi.setRowField('lines',hydrated.key,multiColumns[0]!,10);
const eventB=multi.setRowField('lines',hydrated.key,multiColumns[2]!,20);
assert.deepEqual(multiCalls[1]!.input.changed,['amount','second'],'latest request includes all unacknowledged field onchanges');
assert.deepEqual(Object.keys(multiCalls[1]!.input.values).sort(),['amount','derived','second'],'loaded identity and display metadata are not business inputs');
assert.equal(multiCalls[1]!.input.id,42,'existing identity has its own channel');
multiCalls[1]!.resolve({derived:77}); await eventB;
multiCalls[0]!.resolve({derived:99}); await eventA;
assert.equal(multi.fieldRows('lines')[0]!.values.derived,77);
assert.equal(multi.collectValidation().issues.length,0);
const eventC=multi.setRowField('lines',hydrated.key,multiColumns[2]!,21);
assert.deepEqual(multiCalls[2]!.input.changed,['second'],'applied fieldChanges are acknowledged');
multiCalls[2]!.resolve({}); await eventC;
console.log('native child onchange: contract scope fail-closed, cross-field pending union and hydrated existing row passed');

const hiddenTreeSubview = { fields: {computed_token: {type: 'char', readonly: true}}, tree: {
  columns: [{name: 'name', type: 'char'}],
  columns_schema: [{name: 'name', type: 'char'}, {name: 'row_kind', type: 'selection'}, {name: 'computed_token', type: 'char'}],
  column_occurrences: [
    {name: 'name', field_type: 'char'},
    {name: 'row_kind', field_type: 'selection', native_locator: '/tree/field[2]', attributes: {force_save: '1'}, modifiers: {readonly: true, column_invisible: true}},
    {name: 'row_kind', field_type: 'selection', native_locator: '/tree/field[3]', modifiers: {readonly: true, column_invisible: true}},
    {name: 'computed_token', field_type: 'char', modifiers: {column_invisible: true}},
  ],
} };
const hiddenDisplay = one2manyColumnsFromSubview(hiddenTreeSubview, () => null);
const hiddenData = one2manyDataColumnsFromSubview(hiddenTreeSubview, () => null);
assert.deepEqual(hiddenDisplay.map(column => column.name), ['name']);
assert.deepEqual(hiddenData.map(column => column.name), ['name', 'row_kind', 'row_kind', 'computed_token']);
assert.equal(hiddenData[1]!.forceSave, true);
assert.equal(hiddenData[2]!.forceSave, undefined);
assert.equal(hiddenData[3]!.readonly, true);
assert.equal(one2manyDataColumnsFromSubview(hiddenTreeSubview, () => ({type:'char',readonly:false}))[3]!.readonly, true);
assert.notEqual(hiddenData[1]!.key, hiddenData[2]!.key);
const hiddenRuntime = useOne2manyRuntime({
  model: () => 'x.parent', recordId: () => 0, originalValues: () => ({}), parentValues: () => ({}),
  onchangeLinePatches: () => [], resolveColumns: () => hiddenDisplay, resolveDataColumns: () => hiddenData,
  resolvePrimaryColumn: () => 'name', resolveRelationOptions: () => [], markFieldChanged: () => {},
  loadDefaults: async () => ({row_kind: 'item', computed_token: 'default'}),
});
await hiddenRuntime.addRow('lines');
const hiddenRow = hiddenRuntime.visibleRows('lines')[0]!;
assert.equal(hiddenRow.values.row_kind, 'item');
hiddenRuntime.setRowField('lines', hiddenRow.key, hiddenData[1]!, 'forged');
assert.equal(hiddenRow.values.row_kind, 'item');
hiddenRuntime.prepareOnchangeRows('lines', [[1, hiddenRow.key, {row_kind: 'server', computed_token: 'server'}]])();
const hiddenCommands = hiddenRuntime.buildCommandValue('lines', 'write') as unknown[][];
assert.equal((hiddenCommands[0]![2] as Record<string, unknown>).row_kind, 'server');
assert.equal(Object.hasOwn(hiddenCommands[0]![2] as object, 'computed_token'), false);
assert.throws(() => one2manyDataColumnsFromSubview({tree: {...hiddenTreeSubview.tree, column_occurrences: []}}, () => null), {name: 'ContractGapError'});
console.log('hidden tree dependency defaults/onchange, occurrence, force_save and edit boundary: passed');
