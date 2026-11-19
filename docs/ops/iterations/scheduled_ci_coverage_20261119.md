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

## PR 939 follow-up

The owner authorized PR publication; PR 939 was created as draft at bfb55ef958043139840a2d5bbeeca5f116cddbfd. Public guard run 44432090116 failed because `test_frontend_lane_commands_are_explicit` reads only the first `verify.frontend.pr.unit` declaration. Make itself merges prerequisites, so local execution passed, but adding a new first declaration broke the existing textual contract. This was introduced by this repair and missed by the original local validation selection. The correction merges the added prerequisites into the original first declaration without removing any checks. `verify.ci.scheduled_gates` is now explicitly registered for this run. Independent review remains pending.

## Full-chain navigation continuation

PR 939 merged at 0dc7778132a6814e3cb18eb7cecb3ba39ac5df71 with four required checks passed. Full dispatch 44432597937 subsequently failed at the form-open performance loop: after opening an unsaved payment create form, navigateSpa used history.pushState/popstate to force the list route. The retained form displayed its unsaved-leave confirmation while the harness waited for a list. The continuation owns P4 browser scenario transitions, not product dirty-state policy. Baseline is the merged main tree; previous worktree and evidence are preserved, with one replacement active repair worktree under the existing owner worktree authorization.

| Gate | State | Owner | Reason |
| --- | --- | --- | --- |
| Identity | required | exact main base and repair head | continuation |
| Owning module ORM | excluded | none | no model or product behavior change |
| Focused regressions | required | release.local_entry | clean/dirty/unrelated-dialog navigation |
| Product lint/type/build | excluded | none | product source unchanged |
| Full runtime browser | required, not_run | remote full release | observed integration failure |
| PR checks | required, not_run | exact-head checks | before merge |

Owner constraint: run the complete long chain locally before any push. No continuation changes have been pushed. The formal entry is `CONFIRM_FRONTEND_RELEASE_AUDIT=RUN_FROZEN_FRONTEND_RELEASE_AUDIT make verify.frontend.release.local SC_ACCEPTANCE_RUNTIME_PROFILE=local`. It binds isolated fixture tenant database `sc_frontend_acceptance`, exact filter `^sc_frontend_acceptance$`, project `sc-fe-r2-p1-01`, and separate declared DB/Redis/Odoo volumes. This is not the platform-control/industry catalog or a customer production database; customer business data is prohibited and isolated fixture data is allowed. Managed preflight verified those identities. Existing frontend PID 975157 is owned by another worktree, so a lifecycle handoff was requested rather than stopping it unilaterally.

The initial release-unit run exposed an existing structural test expecting two raw-history list navigations. Updated that assertion to preserve the settled-list requirement while requiring guarded form exits; all 38 hardening tests and 27 release-entry tests passed. Prior failure remains in its original log. Runtime/browser validation remains not_run until the environment is available.

### Disposable local full release (owner authorization)

Owner explicitly requested configuring a disposable environment on demand, replacing the
pending shared-environment handoff. P4 tooling owns the new
`verify.frontend.release.disposable` entry. It reuses carrier provision/discard and the
complete `verify.frontend.release.local` audit, followed by fixture ORM; no product
semantics or release assertions change.

Database role: isolated synthetic acceptance tenant; tenant/environment:
`sc-fe-local-release`. Not platform control, industry catalog, customer production, or
UAT. Customer business data forbidden; fixtures permitted. Database
`sc_frontend_acceptance` exists in its own PostgreSQL instance, exact filter
`^sc_frontend_acceptance$`. Dedicated database/session/filestore volumes:
`sc_fe_local_release_db`, `sc_fe_local_release_redis`, `sc_fe_local_release_odoo`.
Ports: 5185 frontend, 18092 acceptance backend, 19093 compose carrier. Credentials are
fresh private worktree-local ignored files, removed after verified cleanup. Existing
resources cause refusal before mutation; shared resources remain outside scope.

Required: lifecycle/profile tests (47 passed), iteration/freeze checks, full local audit
and fixture ORM, exact source and cleanup readback. Excluded: production and existing
acceptance carrier mutation. Not run yet: disposable full runtime audit. Publication
remains blocked until that complete local long chain passes.

Owner correction: retain failed disposable environments and private credentials for repair/retry; discard only after the complete release and fixture ORM pass with unchanged source. Reuse exact-head offline unit/static checkpoints only, checking static output hashes. Runtime assertions always rerun. Attempt 2 passed full units but failed because Docker created a root-owned evidence directory; attempt 3 provision is retained under an explicit controller handoff. No publication occurred.
