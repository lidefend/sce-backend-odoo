import assert from 'node:assert/strict';
import test from 'node:test';
import { createExpectedHttpFailureBudget } from './platform_capability_explorer_browser_support.mjs';

const INTENT = 'platform.capability.explorer.list';

test('an expected HTTP failure can be consumed exactly once', () => {
  const budget = createExpectedHttpFailureBudget();
  budget.arm({ status: 409, intent: INTENT });
  assert.equal(budget.consume({ status: 409, intent: INTENT }), true);
  assert.equal(budget.consume({ status: 409, intent: INTENT }), false);
  assert.equal(budget.pending(), 0);
});

test('a non-matching response cannot consume the expected budget', () => {
  const budget = createExpectedHttpFailureBudget();
  budget.arm({ status: 409, intent: INTENT });
  assert.equal(budget.consume({ status: 409, intent: 'platform.capability.explorer.detail' }), false);
  assert.equal(budget.consume({ status: 500, intent: INTENT }), false);
  assert.equal(budget.pending(), 1);
  assert.equal(budget.consume({ status: 409, intent: INTENT }), true);
});

test('pending expected failures are visible when the injected response never arrives', () => {
  const budget = createExpectedHttpFailureBudget();
  budget.arm({ status: 409, intent: INTENT });
  assert.equal(budget.pending(), 1);
});
