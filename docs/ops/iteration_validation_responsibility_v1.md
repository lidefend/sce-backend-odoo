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
