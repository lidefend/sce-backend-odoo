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

- `make verify.frontend.dev.incremental.unit`：102 tests PASS。
- 首次 clean HEAD `df87a428fb8167ff166c424956e8e63004c9ca68` 的
  `make ci.local.iteration`：planner 执行 3 个 target，全程 PASS。
- 后续仅文档/台账提交保持相同 runtime tree 时，planner 应继续复用首次回执；
  `reusedTargetCount=3`、`testsRun=false`、`verificationPassed=true`，不再次执行 3 个 target。
- 首次回执：
  `.runtime/frontend-dev-validation/executions/20261109T145927Z-2160635-236873218/receipt.json`

测试覆盖：dirty worktree 不复用、target log 被篡改不复用、runtime source 变化不复用、
bookkeeping-only 提交保持复用身份，以及 failed/blocked/interrupted/not-run 不作为通过。
缺失的 planner target 不再要求逐项复制到 `run.json`，但仍保留在 receipt 的
`registrationMissingTargets` 中。

可复用身份与日志校验位于 `scripts/ops/incremental_execution.py`，供其他增量 planner 复用相同原则。
