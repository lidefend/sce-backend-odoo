# Scheduled CI Lint Recovery 2026-11-16

## Identity

- Branch: `fix/scheduled-ci-lint-20261116`
- Baseline: `ce41f14870531fda9a1a8f247761e142aff711a2`
- Formal Product Layer: P4
- Layer Target: scheduled frontend release lint
- Module: `frontend/apps/web/scripts`

## Purpose

Restore the nightly `frontend_release_gate` by removing the current mainline's
single reproducible frontend lint error. The fix is limited to test-script
hygiene: no product behavior, workflow trigger, lane selection, release
assertion, database, or runtime deployment changes.

## Failure Evidence

The 2026-11-15 scheduled run at `9c537187c05306663758c86f95e0e91d317381db`
produced four downstream failures:

- `frontend_release_gate` failed in its authoritative release command.
- `professional_quality_gate` failed because the managed ORM producer was the
  failed frontend gate.
- `merge_policy_gate` and `release_candidate_gate` rejected the failed sibling
  checks.

The frontend static audit recorded `delivery_hardening` and lint failures.
Current main already fixes the delivery-hardening guard. Re-running the remaining
failure locally at P4 baseline reproduced one lint error:

```text
frontend/apps/web/scripts/session_persistence_recovery_test.ts
  19:7  error  'waitForScheduledFlush' is assigned a value but never used
```

## Change

Remove the unused helper declaration. The recovery test already calls
`session.flushDurablePersist()` synchronously before asserting durable state, so
the timer-based scheduler helper is not part of this test's behavior.

## Verification

All local affected checks passed on the dirty candidate:

- `make verify.frontend.lint`: PASS, 0 errors. Four existing warnings remain and
  are non-blocking.
- `make verify.frontend.session_persistence.recovery.unit`: PASS with 135
  cases across snapshot (48), scheduler (25), failure (28), and recovery (34).
  The performance sub-check also passed its bounded metrics.
- `make verify.frontend.delivery_hardening.guard`: PASS, 17 tests.
- `VITE_ODOO_DB=sc_frontend_acceptance VITE_ODOO_DB_LOCKED=1
  VITE_APP_ENV=acceptance python3 scripts/verify/frontend_static_release_audit.py`:
  PASS for all ten checks, including lint, strict typecheck, production build,
  and frontend build fingerprint
  `412bed93f8ca3f867396bef781f8020a7337232b8595a2cea17d78b920da16c3`.
- `make verify.ci.scheduled_gates`: PASS.
- `make ci.local.iteration`: PASS; the frontend affected set executed all eight
  required targets and exited zero.

`verify.frontend.release.ci_guard` was also attempted as a supplemental command,
but it is not a registered Make target. This is a command-name error, not a
product or validation failure; the registered static release audit already ran
the release CI guard.

At local-batch validation time, no push, PR, merge, deployment, database write,
or service mutation had occurred.

## Integration and Post-Merge Verification

The exact reviewed candidate was published as PR #900 and merged through the
protected PR lane:

- Candidate head: `0a6224829f1e22454e0c0aeee21bd1ac6da30a15`
- Mainline merge: `44cfed924b44b690dbb9f833ca9fcb605e8196cc`
- Required `public_guard`, `merge_policy_gate`,
  `professional_quality_gate`, and `frontend_release_gate`: success on the
  candidate head.

A full-lane `frontend_release_gate` was then dispatched manually on merged main:

- Run: https://github.com/lidefend/sce-backend-odoo/actions/runs/43793607673
- Event/ref/head: `workflow_dispatch`, `main`, `44cfed924b44b690dbb9f833ca9fcb605e8196cc`
- Result: success in 23m27s
- Authoritative frontend release command: PASS
- Managed ORM regressions: PASS
- Static audit: PASS, all ten checks
- Navigation, role projection, delivery hardening, accessibility, performance,
  responsive, and error-recovery sections: PASS
- Evidence artifact digest:
  `sha256:95aa678b0bef7cc4dff33793a3607db70efff3c387215e9d97bdd030e111d7b4`

The manual full lane confirms the repaired workflow on the merged mainline. The
next natural cron `schedule` event remains an additional scheduled observation;
it is not required to reinterpret the already successful exact-main run.

## Ledger Closure

The recovery goal and run are marked `completed`. The merged topic branch was
removed from the active-run index. Offline ledger closure checks passed:

- `make verify.agent.ledger.unit`: PASS, 18 tests.
- `make verify.agent.resume.unit`: PASS, 58 tests.

The closeout branch is the only active-run binding for this bookkeeping update;
it carries no product, workflow, database, or runtime change.

## Rollback

Revert the single test-script change. No external state is mutated by this batch.
