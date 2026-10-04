# Active-run index closeout B (2026-10-05)

## Scope

Metadata only (P4 `engineering_context_run_index`): return
`.agent/active-runs.json` to the intentionally empty `branches` map.

## Context

The `CI-SCHEDULED-FULL-LANE-RECOVERY-D` round merged (PR #562..#565) and its five
merged candidate branches were retired through the governed
`scripts/ops/branch_cleanup_safe.sh` entry, each verified with
`squash_verified=1` (exact-head merged PR):

- `fix/scheduled-ci-core-regression-recovery` -> PR #561
- `fix/scheduled-ci-core-reset-and-reviewer-fixtures` -> PR #562
- `fix/scheduled-ci-frontend-settlement-release-targets` -> PR #563
- `fix/acceptance-fixture-company-reconcile` -> PR #564
- `fix/close-scheduled-lane-recovery-ledger` -> PR #565

Only the last one still had an active-run binding, which now points at a deleted
branch. This batch clears that binding, exactly as the earlier
`ACTIVE-RUN-INDEX-CLOSEOUT` round (PR #557 era) did.

## Changes

- `.agent/active-runs.json`: `branches` returned to an empty object.
- The completed `CI-SCHEDULED-FULL-LANE-RECOVERY-D` run and goal records are left
  untouched on `main`.

## Evidence

- `make verify.agent.resume.unit` (offline L1) -- see run record.
- No product artifact, contract, database, fixture or runtime is changed.

## Outcome (2026-10-05)

- `.agent/active-runs.json` `branches` is an empty object; no binding points at a
  retired branch.
- `make verify.agent.resume.unit` passed 30/30; `make ci.local.iteration` reported
  `PASS change_state=dirty coverage=L1_only` while the run was still bound.
- `make agent.run.resume` now reports `unregistered` on `main` and on this branch
  after the index was cleared, matching the earlier `ACTIVE-RUN-INDEX-CLOSEOUT`
  precedent.
- Four-layer status: batch accepted (this metadata change); mainline integration
  pending the ordinary PR lane; deployment `not_run`; product delivery `not_run`.
