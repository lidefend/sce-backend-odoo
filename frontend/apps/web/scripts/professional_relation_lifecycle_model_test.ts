import assert from 'node:assert/strict';
import { useRelationRuntime } from '../src/pages/contractForm/useRelationRuntime';
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
  assert.deepEqual(await earlierKeyword, [{ id: 1, label: 'UM-P3 record' }], 'the late caller still receives its own rows');
  assert.deepEqual(guarded.relationOptions.value.partner_id, [{ id: 2, label: 'P1 record' }], 'the late response must not repaint the panel');
  console.log('[professional_relation_lifecycle_model_test] PASS stale-candidate-search-guard=1');
}

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
