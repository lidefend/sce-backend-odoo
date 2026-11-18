import assert from 'node:assert/strict';
import {
  buildActionViewFieldFilter,
  parseActionViewFieldFilter,
  serializeActionViewFieldFilter,
} from '../src/app/runtime/actionViewFieldFilterRuntime';
import {
  buildActionViewListStatePatch,
  buildActionViewSyncedRouteQuery,
} from '../src/app/runtime/actionViewRouteRuntime';

const booleanFilter = buildActionViewFieldFilter({
  field: 'active',
  occurrenceKey: 'active@/search[1]/field[1]',
  label: '有效',
  type: 'boolean',
  operator: '=',
  value: false,
});
assert.equal(booleanFilter.domain[0][2], false);
assert.equal(parseActionViewFieldFilter(serializeActionViewFieldFilter(booleanFilter))?.value, false);

const zeroFilter = buildActionViewFieldFilter({
  field: 'sequence',
  occurrenceKey: 'sequence@/search[1]/field[2]',
  label: '顺序',
  type: 'integer',
  operator: '=',
  value: 0,
});
assert.equal(zeroFilter.domain[0][2], 0);
assert.equal(parseActionViewFieldFilter(serializeActionViewFieldFilter(zeroFilter))?.value, 0);

assert.throws(
  () => buildActionViewFieldFilter({
    field: 'partner_id',
    occurrenceKey: 'partner@/search[1]/field[3]',
    label: '客户',
    type: 'many2one',
    operator: '=',
    value: 7,
    domain: [],
    queryMode: 'filter_domain',
  }),
  (error: unknown) => Boolean(error && typeof error === 'object' && (error as { name?: string }).name === 'ContractGapError'),
);
assert.throws(
  () => buildActionViewFieldFilter({
    field: 'partner_id',
    occurrenceKey: 'partner@/search[1]/field[4]',
    label: '客户',
    type: 'many2one',
    operator: '=',
    value: Number.NaN,
  }),
  (error: unknown) => Boolean(error && typeof error === 'object' && (error as { name?: string }).name === 'ContractGapError'),
);
assert.equal(parseActionViewFieldFilter('{not-json'), null);

const queued = buildActionViewSyncedRouteQuery(
  {
    search: 'alpha',
    order: 'sequence asc, id asc',
    list_offset: '20',
    field_filter: serializeActionViewFieldFilter(zeroFilter),
  },
  {
    searchTerm: 'beta',
    sortValue: 'sequence asc, id asc',
    filterValue: 'all',
    groupSampleLimit: 3,
    groupSort: 'desc',
    collapsedGroupKeys: [],
    groupPageOffsets: {},
    groupWindowOffset: 0,
    groupQueryFingerprint: '',
    groupWindowId: '',
    groupWindowDigest: '',
    groupWindowIdentityKey: '',
    listOffset: 0,
    extra: { field_filter: serializeActionViewFieldFilter(zeroFilter) },
  },
);
assert.equal(queued.list_offset, undefined);
assert.equal(queued.field_filter, serializeActionViewFieldFilter(zeroFilter));
assert.equal(queued.search, 'beta');

const changed = buildActionViewListStatePatch({
  searchTerm: 'beta',
  sortValue: 'sequence asc, id asc',
  filterValue: 'all',
  groupSampleLimit: 3,
  groupSort: 'desc',
  collapsedGroupKeys: [],
  groupPage: '',
  activeGroupByField: '',
  groupWindowOffset: 0,
  groupQueryFingerprint: '',
  groupWindowId: '',
  groupWindowDigest: '',
  groupWindowIdentityKey: '',
  listOffset: 20,
});
assert.equal(changed.list_offset, '20');

console.log('[action_view_field_filter_runtime_test] PASS');
