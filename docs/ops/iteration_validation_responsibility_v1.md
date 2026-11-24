# Iteration Validation Responsibility v1

Status: active  
Authority: `AGENTS.md`
BASELINE_ITERATION_EXECUTION_POLICY=v1

Before the first mutation or validation run, every executor must declare three
separate lanes:

1. `local_targeted`: affected static, contract and non-zero targeted tests.
2. `remote_integration`: exact PR HEAD against the current target base.
3. `scheduled_release`: current remote main release qualification.

No lane substitutes for another.

New run records use schema v2. `make agent.run.resume` fail-closes before a
check starts when the three-lane declaration is absent, incomplete, includes
an unexplained exclusion, or omits an entrypoint for a required lane. Schema v1
records remain readable for historical branches only.

Small changes do not run the full `smart_construction_core` module suite locally.
Full module, full browser and Quick suites belong to explicit audit or remote CI.
The local planner records every affected `*.module_baseline` as
`deferredRemoteTargets`; it remains part of `completeAffectedTargets` and must
be executed by the exact-head remote integration lane.

Test-only module changes select the changed test classes through
`verify.changed_tests.orm`. An unchanged passed local.test receipt is reused
only when HEAD, complete source fingerprint, module, exact tag set and original
log bytes match. No receipt is reused across a source change.

`local.test` is worktree-scoped: the Compose project, volumes and non-blocking
lock are derived from the worktree root. The reusable module template is the
default, and each attempt clones a fresh database named
`sc_test_<worktree-key>_<attempt-key>`. A busy lock in the current worktree is an
`environment_defect`, not a PR blocker: do not wait or steal it, run unaffected
offline checks, commit, and create the PR. Exact-head remote CI is then the
integration authority.

A normal PR requires a clean committed HEAD, bounded diff, and accurate local
targeted evidence. Merge requires current exact-head required remote checks.
Scheduled CI separately determines whether the resulting mainline is eligible
for release.

## Lane authority matrix

| Lane | Trigger and entry | Exact identity | Required execution | It may establish | It must not establish |
| --- | --- | --- | --- | --- | --- |
| Local targeted | A developer change; `make ci.local.iteration`, backend/frontend lane entries | Current HEAD plus explicit dirty scope | Affected static, contract and non-zero targeted tests | `local_diff_confidence` | PR integration, full module baseline, release eligibility |
| Remote integration | Ordinary PR open/sync; the four required PR workflows | Exact PR HEAD against the current target base | Risk-selected affected surface; test-only backend changes use the owning changed tests, not unrelated dependency consumers | The merge gate when every current required check passes | Scheduled mainline release eligibility |
| Explicit candidate | PR `ci:candidate` label | Exact candidate HEAD/base | Full candidate professional/frontend/backend checks | Exact candidate-build eligibility | An ordinary PR shortcut, operator mainline audit or scheduled mainline result |
| Operator full release | `make release.main_full EXPECTED_MAIN=<sha>` | Exact main head/tree, five newly dispatched `workflow_dispatch` runs | Same full public/professional/nested-backend/frontend/merge/release-condition set as the scheduled lane | `operator_full_audit` candidate-build eligibility | A `scheduled_mainline` observation, PR merge acceptance or deployment authorization |
| Scheduled release | Cron `0 18 * * *` on `main` | One scheduled slot, exact current main head and tree | `public_guard`, `professional_quality_gate`, `frontend_release_gate`, `merge_policy_gate` and `release_candidate_gate`; professional nests the full `product` backend suite. Demo and acceptance responsibilities run in the independent `auxiliary_backend_suite` workflow | `candidate_build_eligible` for that exact current main head/tree | PR merge acceptance, deployment authorization, or a substitute for a PR's exact-head checks |

The scheduled five-workflow set is intentional. `release_candidate_gate` is
not a substitute for the four producer workflows: it waits for the exact-head,
same-scheduled-slot runs of `public_guard`, `professional_quality_gate`,
`frontend_release_gate` and `merge_policy_gate`, then materializes the
`sce.release_condition.v1` artifact. The nested backend suite is not a separate
schedule trigger; it is invoked by the full professional lane and enumerates
the complete product suite without a PR base.

Backend responsibility is release-carrier driven:

- `product`: modules under the product path, excluding explicit test-only
  carriers.
- `demo`: modules from `demo_addons`.
- `acceptance`: explicitly forbidden implicit test carriers such as the
  acceptance fixture.

The three sets must partition every runnable backend module without overlap.
Demo or acceptance failure blocks its own lane, not product candidate-build
eligibility. They still run on the same schedule to preserve full coverage and
publish independent evidence.

The scheduled condition is only `candidate_build_eligible`. It remains
`deployment_ready=false`; deployment approval and runtime readback are later,
separate authorities.

The release-condition assembler must re-read `refs/heads/main` and reject a
validated head that is no longer the current main. A main movement after the
producer runs begin makes their evidence stale for scheduled release
qualification even when each producer completed successfully.

An explicit candidate label is a PR candidate lane. Owner
`workflow_dispatch` on main is an operator full-release audit and is recorded
as `operator_full_audit`, never as `scheduled_mainline`.
Conversely, a scheduled run cannot replace the current PR HEAD checks because
its source is `main`, not the PR head.

Ordinary PR open/synchronize events do not start `release_candidate_gate`.
The gate starts only from the explicit `ci:candidate` label event, so unrelated
PR lifecycle events do not create a no-op candidate check. Apply the label to
the exact head being qualified; a later head requires a new explicit candidate
event.

## Impact-routed verification surface

Verification-tool checks follow their actual execution surface:

- `audit.verification.lane_coverage.check` is selected only when Make, workflow,
  guard-registry, verification-lane or planner inputs change.
- A passed `verify.verification.lane_coverage` receipt covers its internal audit
  subcheck for the same run and source identity. The plan records this through
  `reusedTargetCoverage`; covered targets are not executed twice.
- Planner changes route to `verify.frontend.dev.incremental.unit`. Run-context
  and generated-evidence-registry changes route to `verify.agent.resume.unit`;
  these are separate contracts.
- Local `make/ci.mk` changes run the lane policy and planner tests. The full CI
  workflow contract remains the exact-head remote control-plane responsibility.
- Unknown or invalid paths remain fail-closed. Shared-contract channel handoff
  and deferred remote module baselines are unchanged.

When target main advances, merge the current main into the PR branch, update the
active run baseline to that exact main SHA, and rerun the affected local set.
Previously recorded exact-head remote checks do not carry across the new base.

## Remote exact-set rules

- Frontend runtime and frontend tooling ownership are separate. Tooling-only
  changes still run their registered tool checks, but skip frontend
  lint/typecheck/test/build. Actual `frontend/**` runtime changes retain the
  standard or full frontend lane.
- A `make/ci.mk` edit may skip the remote frontend runtime lane only when an
  exact Git-tree proof shows every changed byte belongs to the three
  `ci.local.*iteration` target blocks or to the
  `verify.ci.scheduled_gates` recipe body. Any other Make change remains
  conservatively full.
- Backend focused planning uses exact changed-test selectors or exact changed
  pure-Python files only when every backend change is a direct `tests/test*.py`
  change and selector coverage is complete. Execution is narrowed to the
  modules that own those changed tests; unaffected dependency consumers are
  not rerun. Production code, test helpers, deleted tests, mixed changes and
  incomplete selectors retain full impacted-module coverage.
