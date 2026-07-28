export function evaluateRelativePerformanceBudget({
  scenarios,
  budgets,
  baseline,
  maximumRegressionPercent,
}) {
  const metricRegressionPercent = {};
  let pass = true;
  for (const [scenario, limits] of Object.entries(budgets)) {
    const current = scenarios[scenario] || {};
    const previous = baseline.scenarios?.[scenario] || {};
    const regressions = {};
    for (const [metric, limit] of Object.entries(limits)) {
      if (metric === 'description') continue;
      const baselineMetric = (
        metric === 'p95_ms' || metric === 'max_ms'
          ? previous[metric] ?? previous.slowest_ms
          : previous[metric]
      );
      const regression = baselineMetric > 0
        ? ((current[metric] - baselineMetric) / baselineMetric) * 100
        : null;
      regressions[metric] = regression;
      const absolutePass = Number.isFinite(current[metric]) && current[metric] <= Number(limit);
      const relativePass = typeof regression === 'number'
        && regression <= Number(maximumRegressionPercent);
      if (!absolutePass && !relativePass) pass = false;
    }
    metricRegressionPercent[scenario] = regressions;
  }
  const regressions = Object.values(metricRegressionPercent)
    .flatMap((row) => Object.values(row))
    .filter((value) => typeof value === 'number');
  return {
    metric_regression_percent: metricRegressionPercent,
    relative_regression_percent: Math.max(...regressions, 0),
    relative_budget_pass: pass,
  };
}
