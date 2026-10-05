# Daily-dev user-level acceptance run retirement (2026-10-06)

Run: `.agent/runs/DAILY-DEV-ACCEPTANCE-RUN-RETIREMENT/run.json`
Branch: `codex/daily-dev-acceptance-run-retirement-20261006`
Baseline: `main` `48441a3bb6538da1f598090e0603335b023907d8` (after PR #586)

## Scope

Metadata only (P4 `ops_agent_run_index`). Retire the branchless `active` run
`DAILY-DEV-USER-LEVEL-ACCEPTANCE` as `superseded`. No product artifact, contract,
gate, fixture, database or runtime is changed.

## Context

`DAILY-DEV-USER-LEVEL-ACCEPTANCE` still declared `status: active` on `main` while
its closeout branch `codex/daily-dev-user-acceptance-closeout-20261005` no longer
existed. `ACTIVE-RUN-INDEX-DANGLING-CLOSEOUT`
(`docs/ops/iterations/active_run_index_dangling_closeout_20261006.md`) had removed
the dangling `.agent/active-runs.json` binding but deliberately left the run/goal
records untouched, so the run stayed `active` with no branch and no binding.

Per `.agent/README.md`, `completed` requires recorded acceptance/evidence/
documentation/rollback and must not be claimed merely because files were edited,
while `superseded` records that a newer decision replaces the record. The
historical record
(`docs/ops/iterations/daily_dev_user_level_acceptance_20261005.md`) explicitly left
**产品交付 未主张** and its parenthetical named unfinished template/viewport/theme
and relation round-trip verification. Claiming `completed` would therefore assert a
product delivery the record never claimed, so the run and goal are retired as
`superseded`.

## Evidence

- Branch absence: `git ls-remote --heads origin refs/heads/codex/daily-dev-user-acceptance-closeout-20261005`
  is empty and no local branch exists; `git ls-remote --heads origin 'refs/heads/codex/*'` is empty.
- Every path in the retired run's `scope` is present in `main`; the scope changes landed
  through PR #573 (`3f424993`) and PR #574 (`b6b8a0e6`).
- The dangling binding was already removed by `ACTIVE-RUN-INDEX-DANGLING-CLOSEOUT`; this
  batch only changes the run/goal status and adds this record.

## Changes

- `.agent/runs/DAILY-DEV-USER-LEVEL-ACCEPTANCE/run.json`: `status` `active` -> `superseded`;
  `next_exact_step` and a `completion` block record the four-layer outcome truthfully.
- `.agent/goals/DAILY-DEV-USER-LEVEL-ACCEPTANCE.yaml`: `goal.status` and the single batch are
  retired to `superseded`, with a `supersession` block naming the authority and the lanes that
  carried the remaining items.
- No single successor goal owns the whole objective; the remaining product-delivery items are
  recorded as carried by successor lanes, not as completed here.

## Outcome (2026-10-06)

- No branchless `active` run remains; `.agent/active-runs.json` holds only this batch's own
  binding until the final commit drops it.
- `make agent.run.resume` resolves this batch; `make verify.agent.resume.unit` and
  `make ci.local.iteration` are recorded in the run.
- Four-layer status: batch accepted (this metadata retirement); mainline integration pending
  the PR merge; version release not run; product delivery not claimed.
