/**
 * Executable proof for PAYMENT-REQUEST-CHAIN-ALIGNMENT F2.
 *
 * Defect this covers (found while confirming the payment-request chain): the
 * list-profile projection built its `batch_policy` object eagerly, so a
 * fail-closed declaration assertion ran before the "no declaration -> no
 * projection" short circuit.  On a real page the first evaluation happens
 * before `ui.contract.v2` resolves, so the call threw `ContractGapError`, the
 * consuming computed stayed cached as `undefined`, and the later contract-ready
 * read crashed with `Cannot read properties of undefined (reading 'map')`.
 *
 * The two directions that must both hold:
 *   - no contract yet, or a contract that declares no list-profile batch
 *     policy, projects nothing and does not throw;
 *   - a declared but incomplete batch policy still fails closed.
 */
import assert from 'node:assert/strict';
import { ref } from 'vue';

import { useActionViewContractShapeRuntime } from '../src/app/action_runtime/useActionViewContractShapeRuntime';
import type { ContractV2NormalizedStore } from '../src/app/contracts/v2/types';

let cases = 0;
const check = (actual: unknown, expected: unknown, label: string) => {
  assert.equal(actual, expected, label);
  cases += 1;
};

const runtime = useActionViewContractShapeRuntime({
  pageText: (_key: string, fallback: string) => fallback,
  actionContract: ref<ContractV2NormalizedStore | null>(null),
  advancedFields: ref<string[]>([]),
  activeGroupByField: ref(''),
});

const storeWithListProfile = (listProfile: Record<string, unknown>) => ({
  snapshot: {
    layoutContract: { listProfile },
    actionContract: { surfacePolicies: {} },
  },
}) as unknown as ContractV2NormalizedStore;

// 1) Readiness: the contract has not arrived yet, so there is nothing to
//    project.  This used to throw and poison the consuming computed.
check(runtime.extractListProfile(null), null, 'a missing contract must not project a list profile');
check(runtime.extractListProfile(undefined), null, 'an undefined contract must not project a list profile');

// 2) A loaded contract that declares columns but no list-profile batch policy is
//    not a declaration gap: behaviour comes from surface_policies.
const declared = runtime.extractListProfile(storeWithListProfile({
  columns: ['name', 'amount'],
  column_labels: { name: '申请单号' },
}));
check(declared?.columns.join(','), 'name,amount', 'declared columns must project');
check(declared?.batch_policy, undefined, 'an undeclared batch policy must stay undeclared');

// 3) A declared-but-incomplete batch policy is a real gap and must still stop.
assert.throws(
  () => runtime.extractListProfile(storeWithListProfile({
    columns: ['name'],
    batch_policy: { available_actions: ['export'] },
  })),
  /list_profile\.batch_policy\.enabled/,
  'a declared batch policy without enabled must still fail closed',
);
cases += 1;

console.log(`[frontend.contract.shape.projection] PASS cases=${cases}`);
