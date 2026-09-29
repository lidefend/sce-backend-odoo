/**
 * Executable proof for FE-TPL-06A: the list's ordering allowlist and the list
 * header read the same contract declaration.
 *
 * Defect this covers (found while adopting the payment-request list): a column
 * declared `sort_field: "amount"` in the contract was offered as sortable by
 * the header, but the request sanitiser did not know that declaration, dropped
 * the clause, and sent the previous order. The click looked applied while the
 * server kept its old order — a silent no-op, not a refusal.
 *
 * Two directions are asserted, because both matter:
 *   - a declared sort field survives (the contract's own statement is honoured);
 *   - an undeclared field is still dropped (the allowlist stays fail-closed).
 */
import assert from 'node:assert/strict';

import {
  collectContractOrderFields,
  sanitizeOrderValue,
} from '../src/app/action_runtime/useActionViewLoadPreflightRuntime';
import type { ContractV2NormalizedStore } from '../src/app/contracts/v2/types';

let cases = 0;
const check = (actual: unknown, expected: unknown, label: string) => {
  assert.equal(actual, expected, label);
  cases += 1;
};

const widget = (fieldCode: string, componentConfig: Record<string, unknown> = {}) => ({
  widgetId: `w_${fieldCode}`,
  widgetType: 'display',
  fieldCode,
  label: fieldCode,
  span: 12,
  componentKey: 'display.text',
  capabilities: [],
  componentConfig,
  ownerContainerId: 'c1',
});

// Shaped like the real list contract: a display column that orders by another
// field (`request_amount_display` -> `amount`), plus a plain column.
function fakeContract(): ContractV2NormalizedStore {
  const widgets = [
    widget('name'),
    widget('state'),
    widget('request_amount_display', { value_field: 'amount', sort_field: 'amount' }),
    widget('payee_account_completeness'),
  ];
  return {
    widgetsByFieldCode: new Map(widgets.map((row) => [row.fieldCode, row])),
    primaryDataSource: {},
    snapshot: { searchContract: {} },
  } as unknown as ContractV2NormalizedStore;
}

const contract = fakeContract();
const allowed = collectContractOrderFields(contract);

// The contract's own ordering declarations.
check(allowed.has('id'), true, 'the identity field is always orderable');
check(allowed.has('name'), true, 'the record display field is always orderable');
check(allowed.has('display_name'), true, 'the Odoo display name is always orderable');
check(allowed.has('state'), true, 'a list column field code is orderable');
check(allowed.has('amount'), true, 'a column-declared sort_field is orderable, not only the column name');
check(allowed.has('request_amount_display'), true, 'the declared column itself stays orderable');

// Direction: the contract's declared sort survives sanitisation.
check(
  sanitizeOrderValue('amount asc', allowed),
  'amount asc',
  'the declared sort field reaches the request instead of being dropped',
);
check(
  sanitizeOrderValue('amount desc', allowed),
  'amount desc',
  'the direction is preserved',
);
check(
  sanitizeOrderValue('state asc, amount desc', allowed),
  'state asc, amount desc',
  'multi-clause orders keep their order',
);

// Fail-closed: nothing outside the contract becomes orderable.
check(sanitizeOrderValue('create_uid asc', allowed), '', 'an undeclared field is still dropped');
check(sanitizeOrderValue('amount; DROP TABLE x', allowed), '', 'a non-identifier is dropped');
check(sanitizeOrderValue('amount sideways', allowed), '', 'an unknown direction is dropped');
check(sanitizeOrderValue('', allowed), '', 'an empty order stays empty');
check(sanitizeOrderValue(undefined, allowed), '', 'an absent order stays empty');

console.log(`[list_order_field_contract_test] PASS cases=${cases}`);
