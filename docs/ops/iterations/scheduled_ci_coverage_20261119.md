# Scheduled CI coverage repair 2026-11-19

P4 / CI verification / standard platform tooling. Own test harnesses, scan ownership and check selection; no P0-P3 product semantics or database writes. User authorized an additional worktree; pre-existing work is excluded.

Baseline: `5e1cb935d31209cc9ece0f317d55a5064e3f7123`. Result index: `.agent/runs/SCHEDULED-CI-COVERAGE-20261119/run.json`.

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| Base/head | required | git identity | clean governed worktree |
| Module ORM baseline | excluded | none | no product model/service change |
| Existing/focused tests | required | localized_display, contract_reason_dialog, dev.incremental | observed failure and selection dependencies |
| Contract/schema | excluded | none | declarations unchanged |
| Frontend lint/type/build | excluded | none | product source unchanged |
| Component browser | required | contract_reason_dialog.browser | existing failing harness |
| Database/browser release | not_run | remote full lane | after cheap checks pass |
| Remote required gates | required | exact-head PR | before integration |

Observed schedule 44425118436 at 61d1b98d fails localized display registry on intakeAutosave.ts. Runs 44423363419, 44424786476 and 44425222656 fail downstream. Previous run 44213722972 fails dialog selector visibility. PR 937 passed standard lane, which omits localized display guard. No claim of recovered mainline yet.

## Root cause and containment

- The full release audit on `61d1b98d3c80e3e2c1f6e0f6947a9ce2221d7138` fails at the localized display scan because the new intake autosave file contains two date-shaped regular expressions. These validate storage wire shape and preserve the value; they do not parse dates or produce display text. Classification: validation-tool ownership registration defect. The registration is bounded to the two existing expressions and rejects date construction, parsing and locale formatting.
- [PR 937 standard check](https://github.com/lidefend/sce-backend-odoo/actions/runs/44416243615) explicitly skips the authoritative full release command. Standard checks include lint, typechecking, PR units, build and systemic static checks; neither standard PR units nor systemic static included localized display. Thus incremental success did not cover this already-existing release assertion. The new source also fell outside the narrow business-semantics selector. Putting the full-source guard in the existing systemic static entry covers new filenames without duplicating the path classifier or forcing full runtime acceptance in every iteration.
- [Scheduled frontend failure](https://github.com/lidefend/sce-backend-odoo/actions/runs/44425118436) then prevents managed ORM evidence production. [Professional quality](https://github.com/lidefend/sce-backend-odoo/actions/runs/44423363419) fails waiting for that producer, and merge/release gates propagate failure. Four red workflows are not four independent product failures.
- [Previous scheduled run](https://github.com/lidefend/sce-backend-odoo/actions/runs/44213722972) instead timed out waiting for the reason dialog. That component test passes 21 checks on the current baseline; no unsupported root cause or product patch is asserted. It is now required in the PR unit lane so future regressions can be detected before merging. Full-lane recovery remains unproven until remote execution.

## Changes and verification

Only P4 changes: bounded storage-validator registration, mandatory localized display scan in local systemic static and standard PR units, reason-dialog browser component test in PR units, and a gate-wiring regression test. No workflow trigger, required check, product source, database or environment authority changes.

Passed local `ci.local.iteration` (5 selected targets), 184 incremental planner tests, localized display scan (823 sources), 33 autosave cases and 21 reason-dialog assertions. Original logs and final states are indexed in the run. The first failed planner attempt was corrected by using the already-shared systemic static entry instead of broadening per-file selections; its failure log remains diagnostic only.

Rollback: revert this P4 repair commit through a protected PR. Rollback restores the coverage gap and the observed false failure; no database restoration is needed. Batch/mainline status remains verification_pending; deployment and user acceptance are outside this task.

The complete `verify.frontend.pr.unit` target passed with the new prerequisites. `ci.delivery.freeze.prepare` and generated-evidence preflight passed; generated diffs only update the regression test file line count. The same-head main push run 44418320636 also explicitly skipped the full release command, confirming that green push status did not prove full release readiness. Independent review and remote full release remain pending.
