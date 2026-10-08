/**
 * Behavioural lock: the list page-size declarations are consumed through the real
 * runtime carrier, not through a guessed key path.
 *
 * Defect this covers (found on the daily server right after PR #621 was deployed):
 * `resolveActionViewPageSizeOptions/Range` read `searchContract.defaults` straight
 * off whatever object they were handed, while `ActionView.vue` hands them the
 * normalised contract store. That store exposes the snapshot under `.snapshot`
 * only, so the lookup always produced `{}` even though the backend declared
 * `page_size_options = [10, 20, 50]`; the list surface then stopped with
 * `ContractGapError search.defaults.page_size_options` and declared no
 * presentation surface at all.
 *
 * The assertions drive the production helpers with the production store factory,
 * so a regression cannot pass by matching declaration strings alone. The negative
 * case is asserted from a working baseline first: the same helper resolves the
 * declaration, then stops only once the declaration is actually removed.
 */
import assert from 'node:assert/strict';

import { createContractV2Store } from '../src/app/contracts/v2/store';
import type { ContractV2NormalizedStore, ContractV2Snapshot } from '../src/app/contracts/v2/types';
import {
  resolveActionViewPageSizeOptions,
  resolveActionViewPageSizeRange,
} from '../src/app/runtime/actionViewListPageSizeRuntime';
import { ContractGapError } from '../src/app/contract/contractGap';

let cases = 0;
const check = (actual: unknown, expected: unknown, label: string) => {
  assert.deepEqual(actual, expected, label);
  cases += 1;
};

// The minimal carrier the store factory actually walks (containers, data source,
// action rules, status rows). Only the search declaration varies per case.
function snapshotWithSearch(searchContract: Record<string, unknown> | undefined): ContractV2Snapshot {
  return {
    layoutContract: { containerTree: [] },
    dataContract: { dataSource: {} },
    actionContract: { actionRuleList: [] },
    statusContract: { widgetStatus: [], buttonStatus: [], containerStatus: [] },
    ...(searchContract === undefined ? {} : { searchContract }),
  } as unknown as ContractV2Snapshot;
}

const declaredDefaults = {
  limit: 20,
  order: 'id desc',
  page_size_options: [10, 20, 50],
  page_size_range: { min: 1, max: 200 },
};

const store = createContractV2Store(snapshotWithSearch({ defaults: declaredDefaults }));

// 1. Carrier shape: the store never re-exports the snapshot keys at top level.
check(
  Object.prototype.hasOwnProperty.call(store, 'searchContract'),
  false,
  'the normalised store must not expose searchContract at the top level',
);
check(
  Object.prototype.hasOwnProperty.call(store, 'snapshot'),
  true,
  'the normalised store carries the contract snapshot under .snapshot',
);

// 2. Baseline: the declared page-size surface resolves through the real carrier.
check(resolveActionViewPageSizeOptions(store), [10, 20, 50], 'declared page_size_options resolve');
check(resolveActionViewPageSizeRange(store), { min: 1, max: 200 }, 'declared page_size_range resolves');

// 3. Declaration-driven: a different declaration yields a different result, so the
//    helper cannot be passing because of a frontend constant.
const otherStore = createContractV2Store(snapshotWithSearch({
  defaults: { page_size_options: [25, 75], page_size_range: { min: 25, max: 75 } },
}));
check(resolveActionViewPageSizeOptions(otherStore), [25, 75], 'a second declaration is honoured verbatim');
check(resolveActionViewPageSizeRange(otherStore), { min: 25, max: 75 }, 'a second range is honoured verbatim');

// 4. Fail-closed: baseline was proven working above, so a throw here is the
//    removed declaration and not a broken harness.
const expectGap = (run: () => unknown, missing: string, label: string) => {
  try {
    run();
  } catch (error) {
    assert.ok(error instanceof ContractGapError, `${label}: expected ContractGapError`);
    assert.equal((error as ContractGapError).defect.missing, missing, `${label}: defect path`);
    cases += 1;
    return;
  }
  throw new Error(`${label}: expected a contract gap, got a value`);
};

expectGap(
  () => resolveActionViewPageSizeOptions(createContractV2Store(snapshotWithSearch({ defaults: { limit: 20 } }))),
  'search.defaults.page_size_options',
  'absent page_size_options stops',
);
expectGap(
  () => resolveActionViewPageSizeRange(createContractV2Store(snapshotWithSearch({ defaults: { page_size_options: [10] } }))),
  'search.defaults.page_size_range.min',
  'absent page_size_range stops',
);
expectGap(
  () => resolveActionViewPageSizeOptions(createContractV2Store(snapshotWithSearch(undefined))),
  'search.defaults.page_size_options',
  'absent searchContract stops instead of defaulting',
);
expectGap(
  () => resolveActionViewPageSizeOptions(null),
  'search.defaults.page_size_options',
  'an unresolved contract stops instead of defaulting',
);

// 5. Regression shape: a top-level `searchContract` is not the carrier. Reading it
//    is exactly how the deployed defect resolved a working declaration to nothing,
//    so this shape must stop rather than resolve.
const topLevelOnlyCarrier = {
  searchContract: { defaults: declaredDefaults },
  snapshot: {},
} as unknown as ContractV2NormalizedStore;
expectGap(
  () => resolveActionViewPageSizeOptions(topLevelOnlyCarrier),
  'search.defaults.page_size_options',
  'a top-level searchContract is not the carrier',
);

console.log(`[action_view_list_page_size_runtime_test] PASS cases=${cases}`);
