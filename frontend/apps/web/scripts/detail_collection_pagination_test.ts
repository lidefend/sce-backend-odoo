import assert from 'node:assert/strict';
import { isContractGapError } from '../src/app/contract/contractGap';
import {
  detailCollectionPageCount,
  paginateDetailCollectionRows,
  resolveDetailCollectionPageSize,
} from '../src/components/template/detailCollectionPagination';

function assertGap(label: string, run: () => unknown) {
  let stopped = false;
  try {
    run();
  } catch (error) {
    stopped = isContractGapError(error);
  }
  assert.equal(stopped, true, `${label}: expected a ContractGapError stop`);
}

const one2many = { name: 'line_ids', type: 'one2many' };

// T6: the declared page size is consumed as-is; a non-default value actually
// drives the visible record set.
assert.equal(resolveDetailCollectionPageSize(10, one2many), 10);
assert.equal(resolveDetailCollectionPageSize(50, one2many), 50);
assert.equal(resolveDetailCollectionPageSize(1, one2many), 1);

// T6: a missing or illegal declaration stops instead of falling back to a default.
assertGap('missing page size', () => resolveDetailCollectionPageSize(undefined, one2many));
assertGap('null page size', () => resolveDetailCollectionPageSize(null, one2many));
assertGap('string page size', () => resolveDetailCollectionPageSize('20', one2many));
assertGap('boolean page size', () => resolveDetailCollectionPageSize(true, one2many));
assertGap('zero page size', () => resolveDetailCollectionPageSize(0, one2many));
assertGap('negative page size', () => resolveDetailCollectionPageSize(-5, one2many));
assertGap('fractional page size', () => resolveDetailCollectionPageSize(1.5, one2many));

// T6: a non-one2many field does not paginate; the declaration is not applicable
// (null), which is not a fabricated default.
assert.equal(resolveDetailCollectionPageSize(undefined, { name: 'partner_id', type: 'many2one' }), null);
assert.equal(resolveDetailCollectionPageSize(20, { name: 'tag_ids', type: 'many2many' }), null);

const rows = Array.from({ length: 25 }, (_item, index) => index);

// T6: slicing is decided by the declared page size, not a hardcoded 20.
assert.deepEqual(paginateDetailCollectionRows(rows, 1, 10), rows.slice(0, 10));
assert.deepEqual(paginateDetailCollectionRows(rows, 2, 10), rows.slice(10, 20));
assert.deepEqual(paginateDetailCollectionRows(rows, 3, 10), rows.slice(20, 25));
assert.deepEqual(paginateDetailCollectionRows(rows, 2, 5), rows.slice(5, 10));
assert.deepEqual(paginateDetailCollectionRows(rows, 1, 50), rows);
assert.deepEqual(paginateDetailCollectionRows(rows, 1, null), rows);
assert.deepEqual(paginateDetailCollectionRows(rows, 99, 10), []);

// A would-be default of 20 must differ from the declared 10 slicing above.
assert.notDeepEqual(paginateDetailCollectionRows(rows, 2, 10), rows.slice(20, 40));

assert.equal(detailCollectionPageCount(0, 10), 1);
assert.equal(detailCollectionPageCount(25, 10), 3);
assert.equal(detailCollectionPageCount(20, 10), 2);
assert.equal(detailCollectionPageCount(21, 10), 3);
assert.equal(detailCollectionPageCount(40, 5), 8);
assert.equal(detailCollectionPageCount(40, null), 1);

console.log('[detail_collection_pagination_test] PASS cases=28');
