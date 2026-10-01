import assert from 'node:assert/strict';
import fs from 'node:fs';
import { effectScope, reactive, ref } from 'vue';
import { useRelationRuntime } from '../src/pages/contractForm/useRelationRuntime';
import { useRecordRelationshipFields } from '../src/pages/contractForm/useRecordRelationshipFields';
import { useRecordPageLifecycle } from '../src/pages/contractForm/useRecordPageLifecycle';
import {
  buildProfessionalRelationCancelledMessage,
  buildProfessionalRelationCreatedMessage,
  resolveProfessionalRelationLifecycleEvent,
  settleProfessionalRelationLifecycle,
} from '../src/pages/contractForm/professionalRelationLifecycleModel';

const query = {
  relation_create_mode: 'dialog',
  relation_dialog_nonce: 'relation-nonce-1234',
  relation_return_field: 'partner_id',
  relation_return_model: 'sale.order',
};
const created = buildProfessionalRelationCreatedMessage({ query, createdId: 42, relationModel: 'res.partner', label: '伙伴 A' });
const cancelled = buildProfessionalRelationCancelledMessage({ query, relationModel: 'res.partner' });
assert.deepEqual(created, {
  type: 'sc.relation_record_created.v1', nonce: 'relation-nonce-1234', fieldName: 'partner_id',
  parentModel: 'sale.order', relationModel: 'res.partner', id: 42, label: '伙伴 A',
});
assert.equal(buildProfessionalRelationCreatedMessage({ query: {}, createdId: 42, relationModel: 'res.partner' }), null);
assert.ok(cancelled);
const context = { nonce: 'relation-nonce-1234', fieldName: 'partner_id', parentModel: 'sale.order', relationModel: 'res.partner' };
assert.equal(resolveProfessionalRelationLifecycleEvent({ active: true, context, eventOrigin: 'https://app.test', expectedOrigin: 'https://app.test', sourceMatches: true, payload: created })?.kind, 'created');
assert.equal(resolveProfessionalRelationLifecycleEvent({ active: true, context, eventOrigin: 'https://evil.test', expectedOrigin: 'https://app.test', sourceMatches: true, payload: created }), null);
assert.equal(resolveProfessionalRelationLifecycleEvent({ active: true, context, eventOrigin: 'https://app.test', expectedOrigin: 'https://app.test', sourceMatches: false, payload: created }), null);
assert.equal(resolveProfessionalRelationLifecycleEvent({ active: true, context, eventOrigin: 'https://app.test', expectedOrigin: 'https://app.test', sourceMatches: true, payload: { ...created, nonce: 'wrong-nonce' } }), null);
assert.equal(resolveProfessionalRelationLifecycleEvent({ active: true, context, eventOrigin: 'https://app.test', expectedOrigin: 'https://app.test', sourceMatches: true, payload: cancelled })?.kind, 'cancelled');

let active = true;
let createdCount = 0;
let closeSearchCount = 0;
assert.equal(settleProfessionalRelationLifecycle({
  active, closeLifecycle: () => { active = false; }, kind: 'created', restoreSearchOnCancel: true,
  restoreSearch: () => assert.fail('success must not restore search'),
  closeSearch: () => { closeSearchCount += 1; }, onCreated: () => { createdCount += 1; },
}), true);
assert.equal(settleProfessionalRelationLifecycle({
  active, closeLifecycle: () => {}, kind: 'created', restoreSearchOnCancel: true,
  restoreSearch: () => {}, closeSearch: () => { closeSearchCount += 1; }, onCreated: () => { createdCount += 1; },
}), false);
assert.equal(createdCount, 1);
assert.equal(closeSearchCount, 1);

active = true;
let restoreCount = 0;
assert.equal(settleProfessionalRelationLifecycle({
  active, closeLifecycle: () => { active = false; }, kind: 'cancelled', restoreSearchOnCancel: true,
  restoreSearch: () => { restoreCount += 1; }, closeSearch: () => assert.fail('cancel must preserve search'),
}), true);
assert.equal(restoreCount, 1);
console.log('[professional_relation_lifecycle_model_test] PASS cases=12 exact_once=1 dirty_preservation=1');

const runtime = useRelationRuntime();
Object.assign(runtime.relationSearchDialog, { open: true, fieldName: 'owner_id', rows: [{ id: 1, label: 'Old' }], selectedId: 1 });
const sanitizeError = () => 'Query failed';
await runtime.runRelationSearch({ fetchRows: async () => { throw new Error('offline'); }, sanitizeError });
assert.equal(runtime.relationSearchDialog.selectedId, null);
assert.deepEqual(runtime.relationSearchDialog.rows, []);
runtime.confirmRelationSearchSelection(() => assert.fail('a failed search cannot confirm an old row'), { id: 1, label: 'Old' } as never);
let completeOld!: (rows: never[]) => void;
const oldSearch = runtime.runRelationSearch({ fetchRows: () => new Promise((resolve) => { completeOld = resolve; }), sanitizeError });
await runtime.runRelationSearch({ fetchRows: async () => [{ id: 2, label: 'New', values: {} }], sanitizeError });
completeOld([{ id: 1, label: 'Old', values: {} }] as never[]);
await oldSearch;
assert.equal(runtime.relationSearchDialog.rows[0]?.id, 2);
let completeClosed!: (rows: never[]) => void;
const closedSearch = runtime.runRelationSearch({ fetchRows: () => new Promise((resolve) => { completeClosed = resolve; }), sanitizeError });
runtime.closeRelationSearchDialog();
completeClosed([{ id: 3, label: 'Closed', values: {} }] as never[]);
await closedSearch;
assert.equal(runtime.relationSearchDialog.open, false);
assert.deepEqual(runtime.relationSearchDialog.rows, []);
console.log('[professional_relation_lifecycle_model_test] PASS search-failure-order-cancel=3');

let completeColumns!: (columns: never[]) => void;
let staleSearches = 0;
const opening = runtime.openRelationSearch({ fieldName: 'old_id', descriptor: undefined, labels: {}, keyword: '', columns: [], createMode: 'none',
  loadColumns: () => new Promise((resolve) => { completeColumns = resolve; }), runSearch: async () => { staleSearches += 1; },
});
runtime.closeRelationSearchDialog();
await runtime.openRelationSearch({ fieldName: 'new_id', descriptor: undefined, labels: {}, keyword: '', columns: [], createMode: 'none',
  loadColumns: async () => [{ name: 'name', label: 'New name' }], runSearch: async () => {},
});
completeColumns([{ name: 'stale', label: 'Old name' }] as never[]);
await opening;
assert.equal(runtime.relationSearchDialog.fieldName, 'new_id');
assert.equal(runtime.relationSearchDialog.columns[0]?.name, 'name');
assert.equal(staleSearches, 0);
console.log('[professional_relation_lifecycle_model_test] PASS delayed-columns-cancel-reopen=1');

// Candidate search ordering: different keywords are independent requests now,
// so a late response for an earlier keyword must not repaint the panel.
{
  const guarded = useRelationRuntime();
  const pendingRows: Array<(rows: Array<{ id: number; label: string }>) => void> = [];
  const fetchOptions = () => new Promise<Array<{ id: number; label: string }>>((resolve) => { pendingRows.push(resolve); });
  const query = (keyword: string) => guarded.queryRelationOptions({
    fieldName: 'partner_id', keyword, relation: 'res.partner', canRead: true,
    hasDynamicFallback: false, currentValue: null, fetchOptions, isDeniedError: () => false,
  });
  const earlierKeyword = query('UM-P3');
  const laterKeyword = query('P1');
  assert.equal(pendingRows.length, 2, 'each keyword must reach the request layer');
  pendingRows[1]([{ id: 2, label: 'P1 record' }]);
  assert.deepEqual(await laterKeyword, [{ id: 2, label: 'P1 record' }]);
  assert.deepEqual(guarded.relationOptions.value.partner_id, [{ id: 2, label: 'P1 record' }], 'the newest keyword owns the panel');
  pendingRows[0]([{ id: 1, label: 'UM-P3 record' }]);
  assert.deepEqual(await earlierKeyword, [], 'a stale caller cannot publish returned rows elsewhere');
  assert.deepEqual(guarded.relationOptions.value.partner_id, [{ id: 2, label: 'P1 record' }], 'the late response must not repaint the panel');
  console.log('[professional_relation_lifecycle_model_test] PASS stale-candidate-search-guard=1');
}

// Exercise production lifecycle functions with deferred transport, including
// the actual reload entry. The dependency stubs supply contracts/data only.
let lifetimeChecks = 0;
const equal = (actual: unknown, expected: unknown, label: string) => {
  assert.deepEqual(actual, expected, label); lifetimeChecks += 1;
};
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
type Option = { id: number; label: string };
const scope = effectScope();
const guarded = scope.run(() => useRelationRuntime())!;
const issue = (pending: ReturnType<typeof deferred<Option[]>>, keyword = '') => guarded.queryRelationOptions({
  fieldName: 'owner_id', relation: 'x.owner', keyword, canRead: true,
  currentValue: null, hasDynamicFallback: false, fetchOptions: () => pending.promise,
  isDeniedError: () => true,
});
const oldRows = deferred<Option[]>();
const oldQuery = issue(oldRows);
const contractRead = deferred<never>();
const lifecycle = useRecordPageLifecycle({
  clearRelationRuntime: guarded.clearRelationRuntime,
  formRouteIdentity: () => 'record-b', renderErrorMessage: ref(''), loadError: {}, recordMissing: ref(false),
  applyPageStatusEvent: () => {}, validationErrors: ref([]), validationFieldErrors: ref({}), showOne2manyErrors: ref(false),
  contract: ref(null), v2ContractStore: ref(null), v2ContractDecodeError: ref(''), renderProfile: ref('edit'),
  model: ref('x.document'), actionId: ref(0), recordId: ref(2), menuId: ref(0),
  requestedSurface: ref(''), requestedSourceMode: ref(''), route: { query: {} },
  buildRouteContractContext: () => ({}), toPositiveInt: () => 0,
  loadModelContractV2: () => contractRead.promise, ApiError: class extends Error {}, ContractAccessPolicyError: class extends Error {},
});
const reload = lifecycle.reload();
oldRows.resolve([{ id: 1, label: 'Old record' }]);
equal(await oldQuery, [], 'actual reload invalidates pending query without a replacement query');
equal(guarded.relationOptions.value, {}, 'old success cannot refill reset options');
contractRead.reject(new Error('controlled load failure after invalidation'));
await reload;

const staleDenied = deferred<Option[]>();
const oldDeniedQuery = issue(staleDenied, 'old');
const currentRows = deferred<Option[]>();
const currentQuery = issue(currentRows, 'new');
currentRows.resolve([{ id: 2, label: 'Current' }]);
await currentQuery;
staleDenied.reject(new Error('old 403'));
await oldDeniedQuery;
equal(guarded.deniedRelationModels.has('x.owner'), false, 'stale 403 cannot deny current context');
guarded.invalidateRelationRequests();
equal(guarded.relationOptions.value.owner_id, [{ id: 2, label: 'Current' }], 'deactivation preserves settled labels');

const reads: Array<ReturnType<typeof deferred<{ records: Array<Record<string, unknown>> }>>> = [];
const formData = reactive({ owner_id: [2] });
const rows = ref([{ id: 4, isNew: false }]);
const mergedChildren: unknown[] = [];
const store = ref({
  widgetsByFieldCode: new Map([
    ['owner_id', { fieldDescriptor: { type: 'many2one', relation: 'x.owner' } }],
    ['line_ids', { fieldDescriptor: { type: 'one2many', relation: 'x.line' } }],
  ]),
  snapshot: { dataContract: { dataMeta: { sourceContext: { context: { company_id: 8, allowed_company_ids: [8] } } } } },
});
class Denied extends Error { status = 403; reasonCode = 'PERMISSION_DENIED'; }
const fields = scope.run(() => useRecordRelationshipFields({
  ...guarded, ApiError: Denied, formData, v2ContractStore: store,
  fieldType: (descriptor: { type: string }) => descriptor.type,
  relationModel: () => 'x.owner', relationEntry: () => ({ canRead: true }),
  normalizeRelationIds: (value: unknown) => Array.isArray(value) ? value.map(Number) : [],
  relationReadFields: () => ['id', 'display_name'],
  readContractFormRecord: () => { const read = deferred<{ records: Array<Record<string, unknown>> }>(); reads.push(read); return read.promise; },
  relationOptionsFromRecords: (records: Array<{ id: number; display_name: string }>) => records.map(row => ({ id: row.id, label: row.display_name })),
  ensureOne2manyRows: () => rows.value, one2manyFieldRows: () => rows.value,
  mergeHydratedOne2manyRecords: (_name: string, records: unknown) => mergedChildren.push(records),
  nativeFormLayoutNodes: ref([]), findNativeFieldNodeInTree: () => null,
  nativeFieldSubviewFromTree: () => null, selectOne2manySubview: () => ({}),
  one2manyColumnsFromSubview: () => [{ name: 'name' }], isWritableFieldVisible: () => true,
}))!;
guarded.clearRelationRuntime();
const labelOld = fields.hydrateSelectedRelationOptions();
guarded.clearRelationRuntime();
reads.at(-1)!.resolve({ records: [{ id: 2, display_name: 'Stale label' }] });
await labelOld;
equal(guarded.relationOptions.value, {}, 'selected labels cannot merge across reload');
const changedSelection = fields.hydrateSelectedRelationOptions();
formData.owner_id = [3];
reads.at(-1)!.resolve({ records: [{ id: 2, display_name: 'Previous selection' }] });
await changedSelection;
equal(guarded.relationOptions.value, {}, 'selection changes invalidate label publication');
const changedContext = fields.hydrateSelectedRelationOptions();
store.value.snapshot.dataContract.dataMeta.sourceContext.context.company_id = 9;
reads.at(-1)!.reject(new Denied());
await changedContext;
equal(guarded.deniedRelationModels.has('x.owner'), false, 'hydration old-context 403 cannot poison deny cache');
const nestedContext = fields.hydrateSelectedRelationOptions();
store.value.snapshot.dataContract.dataMeta.sourceContext.context.allowed_company_ids.push(9);
reads.at(-1)!.resolve({ records: [{ id: 3, display_name: 'Old nested context' }] });
await nestedContext;
equal(guarded.relationOptions.value, {}, 'nested context mutation cannot change the captured identity');
const freshLabels = fields.hydrateSelectedRelationOptions();
reads.at(-1)!.resolve({ records: [{ id: 3, display_name: 'Current owner' }] });
await freshLabels;
equal(guarded.relationOptions.value.owner_id, [{ id: 3, label: 'Current owner' }], 'current selected labels publish');

const childrenOld = fields.hydrateVisibleOne2manyRows();
const childOldRead = reads.at(-1)!;
guarded.clearRelationRuntime();
equal(fields.isOne2manyHydrating('line_ids'), false, 'reset clears cancelled loading');
const childrenNew = fields.hydrateVisibleOne2manyRows();
const childNewRead = reads.at(-1)!;
childOldRead.resolve({ records: [{ id: 4, name: 'Old child' }] });
await childrenOld;
equal(mergedChildren.length, 0, 'old child data cannot merge');
equal(fields.isOne2manyHydrating('line_ids'), true, 'old finally cannot end new hydration');
childNewRead.resolve({ records: [{ id: 4, name: 'Current child' }] });
await childrenNew;
equal(mergedChildren, [[{ id: 4, name: 'Current child' }]], 'current child hydration merges once');
equal(fields.isOne2manyHydrating('line_ids'), false, 'current finally settles loading');
const changedRows = fields.hydrateOne2manyRows('line_ids');
rows.value = [{ id: 5, isNew: false }];
reads.at(-1)!.resolve({ records: [{ id: 4, name: 'Removed child' }] });
await changedRows;
equal(mergedChildren.length, 1, 'removed child identities cannot merge');

const auxiliaryReads: Array<ReturnType<typeof deferred<void>>> = [];
const retainedActive = ref(true);
let auxiliaryChildren = 0;
const retainedLifecycle = useRecordPageLifecycle({
  captureRelationRequest: guarded.captureRelationRequest,
  isComponentActive: retainedActive, renderProfile: ref('edit'), status: ref('ok'),
  formRouteIdentity: () => 'retained', retainedRouteIdentity: ref('retained'),
  hydrateSelectedRelationOptions: () => { const read = deferred<void>(); auxiliaryReads.push(read); return read.promise; },
  hydrateVisibleOne2manyRows: async () => { auxiliaryChildren += 1; },
});
const oldAuxiliary = retainedLifecycle.preloadFormAuxiliaryData(0);
retainedActive.value = false;
guarded.invalidateRelationRequests();
retainedActive.value = true;
retainedLifecycle.ensureFormInitialReload();
equal(auxiliaryReads.length, 2, 'retained activation resumes auxiliary reads without resetting its draft');
auxiliaryReads[0].resolve();
await oldAuxiliary;
equal(auxiliaryChildren, 0, 'old auxiliary chain cannot start child work after reactivation');
auxiliaryReads[1].resolve();
await Promise.resolve();
equal(auxiliaryChildren, 1, 'only current resumed chain starts child hydration');

guarded.clearRelationRuntime();
const deniedCurrent = deferred<Option[]>();
const deniedCurrentQuery = issue(deniedCurrent);
deniedCurrent.reject(new Error('current 403'));
await deniedCurrentQuery;
equal(guarded.deniedRelationModels.has('x.owner'), true, 'current authority denial is retained');
guarded.clearRelationRuntime();
const disposeRows = deferred<Option[]>();
const disposeQuery = issue(disposeRows);
const disposeLabels = fields.hydrateSelectedRelationOptions();
const disposeRead = reads.at(-1)!;
let timerCalls = 0;
guarded.relationQueryTimers.owner_id = setTimeout(() => { timerCalls += 1; }, 0);
scope.stop();
disposeRows.resolve([{ id: 9, label: 'Disposed' }]);
disposeRead.reject(new Denied());
equal(await disposeQuery, [], 'disposed query returns no publishable result');
await disposeLabels;
await new Promise(resolve => setTimeout(resolve, 5));
equal([timerCalls, guarded.deniedRelationModels.size, guarded.relationOptions.value], [0, 0, {}], 'dispose cancels timers and suppresses hydration errors');
const pageSource = fs.readFileSync('frontend/apps/web/src/pages/ContractFormPage.vue', 'utf8');
assert.match(pageSource, /isComponentActive\.value\], invalidateRelationRequests, \{ flush: 'sync' \}/);
lifetimeChecks += 1;
console.log(`[professional_relation_lifecycle_model_test] PASS shared-record-lifetime=${lifetimeChecks}`);

// A superseded search must not fall back to the unfiltered query either.
{
  const superseded = useRelationRuntime();
  const keywords: string[] = [];
  const pendingRows: Array<(rows: Array<{ id: number; label: string }>) => void> = [];
  const query = (keyword: string, hasDynamicFallback: boolean) => superseded.queryRelationOptions({
    fieldName: 'partner_id', keyword, relation: 'res.partner', canRead: true,
    hasDynamicFallback, currentValue: null,
    fetchOptions: (search: string) => {
      keywords.push(search);
      return new Promise<Array<{ id: number; label: string }>>((resolve) => { pendingRows.push(resolve); });
    },
    isDeniedError: () => false,
  });
  const noMatch = query('zzz-no-match', true);
  const emptyKeyword = query('', false);
  assert.deepEqual(keywords, ['zzz-no-match', '']);
  pendingRows[1]([{ id: 5, label: 'Unfiltered record' }]);
  await emptyKeyword;
  pendingRows[0]([]);
  await noMatch;
  assert.deepEqual(keywords, ['zzz-no-match', ''], 'a superseded search must not issue the dynamic fallback query');
  assert.deepEqual(superseded.relationOptions.value.partner_id, [{ id: 5, label: 'Unfiltered record' }]);
  console.log('[professional_relation_lifecycle_model_test] PASS superseded-dynamic-fallback=1');
}
