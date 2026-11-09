# FE-ITERATION-EFFICIENCY-20261109

## Boundary

- Formal Product Layer: P4 ops delivery tool
- Layer Target: frontend incremental target registration and execution receipt reuse
- Module: `scripts/verify/frontend_dev_incremental.py`
- Product behavior, contracts, permissions, database, runtime and deployment: excluded

## Objective

Remove the requirement to mirror every planner-selected target into `run.json`, and reuse
a passed planner execution when the exact clean HEAD, changed path set and required target
set are unchanged.

## Acceptance

- Missing planner-owned run check copies do not block execution.
- Planner-owned targets and missing explicit run registrations remain visible in the receipt.
- Exact clean HEAD reuse is valid only when the execution identity and logs are unchanged.
- Dirty, changed, failed, blocked, interrupted or not-run results never reuse as pass.

## Validation

- `make verify.frontend.dev.incremental.unit`：100 tests PASS。
- 首次 clean HEAD `51fdccf3ad036d13e19a3921520e32325af42544` 的
  `make ci.local.iteration`：planner 执行 3 个 target，全程 PASS。
- 同一 clean HEAD 第二次执行：planner 直接复用首次回执，`reusedTargetCount=3`，
  `testsRun=false`，`verificationPassed=true`，未再次执行 3 个 target。
- 首次回执：
  `.runtime/frontend-dev-validation/executions/20261109T144940Z-2110155-665824890/receipt.json`
- 复用回执：
  `.runtime/frontend-dev-validation/executions/20261109T145009Z-2117315-569376311/receipt.json`

负例测试覆盖：dirty worktree 不复用、target log 被篡改不复用、failed/blocked/interrupted/not-run
不作为通过；缺失的 planner target 不再要求逐项复制到 `run.json`，但仍保留在 receipt 的
`registrationMissingTargets` 中。

可复用身份与日志校验位于 `scripts/ops/incremental_execution.py`，供其他增量 planner 复用相同原则。
