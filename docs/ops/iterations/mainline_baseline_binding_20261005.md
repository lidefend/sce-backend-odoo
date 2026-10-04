# Mainline baseline binding (2026-10-05)

## Purpose

Bind the current clean mainline as the recorded baseline anchor for the next work
round, so the successor run registers `baseline_sha` against a known-good,
evidence-backed SHA instead of an inferred one.

## Bound baseline

- branch: `main`
- full SHA: `425c0118dbf82f07938ad26939270777f7623cdb`
- source: clean `main` after PR #566, with both scheduled lanes refreshed on the
  same SHA.

## Evidence at the bound SHA

- `backend_test_suite` run `37229452451` (`workflow_dispatch`, `main`,
  `425c0118dbf8`): success. 13/13 modules, 538 tests, `0 failed, 0 error(s)`.
- `frontend_release_gate` run `37229455315` (`workflow_dispatch`, `main`,
  `425c0118dbf8`): success. The single authoritative release command passed and the
  checkout/evidence identity checks passed.
- Offline baseline locks on `425c0118`: `verify.baseline.freeze_guard`
  (0 changed, 0 protected hits), `architecture.complexity_baseline_lock`
  (checked=11), `verify.contract.structure_lock` (domains=14, fingerprint=current).

## How the successor uses it

The next task registers one goal and one `run.json` and sets `baseline_sha` to the
bound SHA (or the then-current `main` if `main` has moved). No global baseline
registry file is introduced; the binding lives in the per-run `baseline_sha` and this
anchor record, consistent with existing repository practice.

## Exclusions

- No completed goal, run or manifest is modified.
- No guard, assertion or audit is relaxed.
- No product code, contract, runtime, database, fixture or deployment change.

## Outcome (2026-10-05)

- The anchor is recorded and the offline check passed 30/30.
- `.agent/active-runs.json` is intentionally empty at the frozen candidate; the
  successor registers one goal and one run and sets `baseline_sha` to the bound SHA
  (or the then-current `main`).
- Four-layer status: batch accepted (metadata binding); mainline integration pending
  the ordinary PR lane; deployment `not_run`; product delivery `not_run`.
