# CI schedule and baseline isolation (2026-11-18)

## Boundary

- Formal Product Layer: P4
- Layer Target: scheduled formal-release execution and offline baseline test isolation
- Module: GitHub Actions schedules and CI contract tests
- Standard vs User-Specific: platform engineering standard

The daily formal-release workflows move from `30 18 * * *` (02:30 Beijing)
to `0 18 * * *` (02:00 Beijing). Scheduled slot inference changes with them.

The corrected mainline full audit also exposed a test isolation defect:
`test_backend_impact_plan.py` inherited the job-level
`CANDIDATE_REQUESTED=true` while testing ordinary PR truth-table rows. The test
must set the candidate flag explicitly for every case so its result depends on
the assertion under test, not the ambient CI environment.

## Acceptance

- All five formal-release workflows use `0 18 * * *`.
- `scheduled_validation.py` infers an 18:00 UTC boundary.
- The truth-table test controls `CANDIDATE_REQUESTED` explicitly.
- CI contract, scheduled gates, guard registry and agent ledger pass non-zero.
- Ordinary PR required checks remain on risk-selected standard lanes.

## Rollback

Revert the cron/slot change and test isolation together. No runtime data requires
restoration.

## Execution log

- `verify.ci.workflow.contract`: PASS, 458 tests.
- `verify.ci.scheduled_gates`: PASS, 97 tests.
- `verify.guard.registry`: PASS, 24 tests plus the 1633-script audit.
- `verify.agent.ledger.unit`: PASS, 18 tests plus ledger consistency.
- `verify.agent.resume.unit`: PASS, 58 tests.
- `verify.frontend.dev.incremental.unit`: PASS, 174 tests.
- `verify.github_actions.security`: PASS, 18 tests plus the workflow policy audit.
- `CANDIDATE_REQUESTED=true make verify.test.baseline`: PASS, 339 cases in
  three independent orders with quarantine empty.

The failed full audit on `db37e290` is retained as the investigation anchor. Its
professional checks failed because the truth-table test inherited the candidate
job environment; the corrected baseline now runs under the same environment and
passes.
