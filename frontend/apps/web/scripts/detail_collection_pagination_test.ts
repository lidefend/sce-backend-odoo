import assert from 'node:assert/strict';
import { isContractGapError } from '../src/app/contract/contractGap';
import {
  detailCollectionPageCount,
  paginateDetailCollectionRows,
  resolveDetailCollectionPageSize,
} from '../src/components/template/detailCollectionPagination';
import {
  one2manyRowCollectionIdentity,
  visibleOne2manyRows,
} from '../src/pages/contractForm/one2manyUtils';

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

// 只读明细集合的声明可见性（回归锁）：可见集合的唯一依据是「该行是否已被声明移除」。
// 每列都为空值的行仍然是契约声明可见的记录：展示文本是否为空不是可见性依据，
// 否则一个合法空值行会从集合里消失，记录身份、数量与分页随之漂移。
type ProbeRow = {
  key: string;
  id: number | null;
  isNew: boolean;
  removed: boolean;
  dirty: boolean;
  dirtyFields: string[];
  values: Record<string, unknown>;
};

function probeRow(key: string, id: number | null, removed: boolean, values: Record<string, unknown>): ProbeRow {
  return { key, id, isNew: id === null, removed, dirty: false, dirtyFields: [], values };
}

const declaredRows: ProbeRow[] = [
  probeRow('new:1', null, false, { product_id: '', qty: '', price_unit: '' }),
  probeRow('id:7', 7, false, { product_id: null, qty: 0, price_unit: false }),
  probeRow('id:8', 8, true, { product_id: '', qty: '', price_unit: '' }),
];

const declaredVisible = visibleOne2manyRows({ line_ids: declaredRows }, 'line_ids');
// 声明可见行不因展示值为空而消失：只有被声明移除的行被排除。
assert.equal(declaredVisible.length, 2);
assert.deepEqual(declaredVisible.map(one2manyRowCollectionIdentity), ['key:new:1', 'id:7']);
// 两个保留行的每一列都是空值 —— 说明"显示文本非空"从未参与可见性裁决。
assert.equal(
  declaredVisible.filter(row => Object.values(row.values).every(value => ['', null, 0, false].includes(value as never))).length,
  2,
);
// 未声明的字段返回空集合，不构造第二套来源或默认行。
assert.deepEqual(visibleOne2manyRows({}, 'line_ids'), []);
assert.deepEqual(visibleOne2manyRows({ line_ids: declaredRows }, 'other_ids'), []);

// 数量与分页落在同一个可见集合上：计数、切片、跨页并集都不脱离该集合。
assert.equal(declaredVisible.length, detailCollectionPageCount(2, 2) * 2);
assert.deepEqual(paginateDetailCollectionRows(declaredVisible, 1, 1).map(one2manyRowCollectionIdentity), ['key:new:1']);
assert.deepEqual(paginateDetailCollectionRows(declaredVisible, 2, 1).map(one2manyRowCollectionIdentity), ['id:7']);
assert.deepEqual(
  [
    ...paginateDetailCollectionRows(declaredVisible, 1, 1),
    ...paginateDetailCollectionRows(declaredVisible, 2, 1),
  ].map(one2manyRowCollectionIdentity),
  ['key:new:1', 'id:7'],
);

console.log('[detail_collection_pagination_test] PASS cases=37');
