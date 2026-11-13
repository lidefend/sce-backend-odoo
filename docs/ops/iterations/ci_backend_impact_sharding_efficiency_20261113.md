# CI backend impact and shard efficiency

## Boundary

- Branch: `codex/ci-backend-impact-sharding-efficiency-20261113`
- Baseline: `fa09c289374252420fbf6082b5ed794bc789292b`
- Formal product layer: P4 operations delivery tooling
- Layer target: backend impact selection and backend suite shard scheduling
- Module: governed CI planning tools

This batch changes only CI planning and its tests. Product modules, contracts,
permissions, business workflows, persistent databases and browser acceptance
are excluded.

## Target result

Acceptance database lifecycle files currently enter the broad backend-runtime
scope and therefore select every business module. Their real consumers are the
database-preparation tool suite and the isolated managed ORM acceptance chain.
The changed routing will select those owners without starting unrelated module
shards.

Backend shards currently use alphabetical round-robin assignment. The existing
remote plan already records prior actual module durations, so the planner can
apply deterministic longest-processing-time assignment to the same selected
module set. Unknown paths and generic shared runner changes continue to force
the full scope.

## Implemented routing

- `database_lifecycle_tooling` now owns `scripts/db/**` and
  `scripts/test/frontend_acceptance_db_ensure.sh` as high-risk control-plane
  inputs without marking them as Odoo backend runtime.
- Its ORM scope is `managed_acceptance`; the PR must still run
  `managed_orm_required=true`, while unrelated payment and module-suite ORM
  scopes are not selected.
- Generic `scripts/test/**` changes remain backend runtime and continue to
  force the complete conservative backend scope.
- `backend_suite_plan.partition()` uses deterministic longest-processing-time
  assignment. Historical `actual_duration_seconds` values from authenticated
  receipt candidates become weights; missing durations use unit weight.
- Equal loads prefer the shard with fewer assigned modules before using shard
  index. This seeds every opened shard even when several historical durations
  are exactly zero, so the generated plan remains acceptable to
  `validate_execution_plan()`.

## Recorded replays

Replaying the complete #881 path set from `70ad2e6a` to `6fe32a65` through the
new impact planner produced:

```text
mode=incremental
modules=[]
scope_status=NOT_APPLICABLE
tool_checks=8
```

The same path set classified as HIGH_RISK with `managed_orm_required=true`,
`orm_scopes=managed_acceptance`, and `payment_orm_required=false`.

Using the actual 14 module durations recorded in #881's frozen backend plan:

| Allocation | Shard estimate (seconds) | Slowest |
| --- | --- | ---: |
| Previous alphabetical round-robin | 1180 / 608 / 459 / 664 | 1180 |
| Duration-weighted LPT | 738 / 721 / 727 / 725 | 738 |

The selected 14 module identities are identical before and after allocation.
The 442 second reduction is a scheduling estimate from the recorded durations,
not a promise for the next runner.

## Verification

- `make ci.local.iteration`: PASS, three required targets executed, zero unmapped
  paths.
- `verify.ci.path_ownership.unit`: PASS, 20 tests.
- `verify.ci.workflow.contract`: PASS, 420 tests across its composed suites
  after the review fix.
- Original command logs:
  `.runtime/frontend-dev-validation/executions/20261113T080044Z-1782306-656175401/`.
- No database, runtime service, deployment target or product data was touched.

Remote CI remains the integration gate. This batch does not claim a new remote
timing result until the candidate runs on GitHub.

## Review follow-up

The independent review found that zero-duration weights could leave an empty
shard and make the consumer reject the execution plan. The scheduler now uses
module count as the second tie-break after load. Regression coverage generates
the plan through `apply_reuse_decision()` and then consumes it through the real
`validate_execution_plan()` for:

- `a=0, b=0`
- `a=10, b=0, c=0`
- four modules with all-zero durations

The rerun of `verify.ci.workflow.contract` reports 420 tests passed.
