import assert from 'node:assert/strict';
import { evaluateRelativePerformanceBudget } from './frontend_performance_budget.mjs';

const budgets = {
  detail: { median_ms: 1200, p95_ms: 2500, max_ms: 2500 },
};
const baseline = {
  scenarios: {
    detail: { median_ms: 5000, slowest_ms: 5500 },
  },
};

const improved = evaluateRelativePerformanceBudget({
  scenarios: {
    detail: { median_ms: 2100, p95_ms: 2600, max_ms: 2600 },
  },
  budgets,
  baseline,
  maximumRegressionPercent: 10,
});
assert.equal(improved.relative_budget_pass, true);
assert.ok(improved.metric_regression_percent.detail.p95_ms < 0);
assert.ok(improved.metric_regression_percent.detail.max_ms < 0);

const regressed = evaluateRelativePerformanceBudget({
  scenarios: {
    detail: { median_ms: 5600, p95_ms: 6200, max_ms: 6200 },
  },
  budgets,
  baseline,
  maximumRegressionPercent: 10,
});
assert.equal(regressed.relative_budget_pass, false);

const missingBaseline = evaluateRelativePerformanceBudget({
  scenarios: {
    detail: { median_ms: 2100, p95_ms: 2600, max_ms: 2600 },
  },
  budgets,
  baseline: { scenarios: {} },
  maximumRegressionPercent: 10,
});
assert.equal(missingBaseline.relative_budget_pass, false);

console.log('[frontend_performance_budget.test] PASS relative p95/max baseline is fail-closed');
