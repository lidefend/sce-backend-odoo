import assert from 'node:assert/strict';
import {
  resolveCollectionPageJump,
  resolveCollectionPageLimit,
  resolveCollectionPageOffset,
  resolveCollectionPaginationMode,
} from '../src/app/presentation/collectionPaginationPresentation';

assert.equal(resolveCollectionPaginationMode({ groupedWindow: true, paged: true }), 'grouped');
assert.equal(resolveCollectionPaginationMode({ groupedWindow: false, paged: true }), 'paged');
assert.equal(resolveCollectionPaginationMode({ groupedWindow: false, paged: false }), 'count');
assert.equal(resolveCollectionPageOffset({ requestedOffset: -40, total: 95, limit: 20 }), 0);
assert.equal(resolveCollectionPageOffset({ requestedOffset: 1000, total: 95, limit: 20 }), 80);
assert.equal(resolveCollectionPageOffset({ requestedOffset: 20, total: 95, limit: 20 }), 20);
assert.deepEqual(resolveCollectionPageJump({ requestedPage: 4, currentPage: 1, totalPages: 5, limit: 20, total: 95 }), { page: 4, offset: 60 });
assert.deepEqual(resolveCollectionPageJump({ requestedPage: 'bad', currentPage: 2, totalPages: 5, limit: 20, total: 95 }), { page: 2, offset: 20 });
assert.deepEqual(resolveCollectionPageJump({ requestedPage: 99, currentPage: 2, totalPages: 5, limit: 20, total: 95 }), { page: 5, offset: 80 });
// 合法范围必须来自契约声明：同一入参在不同声明范围下结果不同，证明前端没有夹取字面量。
assert.equal(resolveCollectionPageLimit(0, 40, { min: 10, max: 200 }), 10);
assert.equal(resolveCollectionPageLimit(999, 40, { min: 10, max: 200 }), 200);
assert.equal(resolveCollectionPageLimit('bad', 40, { min: 10, max: 200 }), 40);
assert.equal(resolveCollectionPageLimit(999, 40, { min: 25, max: 50 }), 50);
assert.equal(resolveCollectionPageLimit(0, 40, { min: 25, max: 50 }), 25);
assert.equal(resolveCollectionPageLimit('bad', 5, { min: 25, max: 50 }), 25);
console.log('[collection_pagination_presentation_test] PASS cases=15');
