# PR 933 CI execution efficiency (2026-11-18)

## Boundary

- Formal Product Layer: P4
- Layer Target: backend CI execution selection, timeout, observability and receipt discovery
- Module: GitHub backend suite workflow and CI verification tools
- Standard vs User-Specific: platform engineering standard

The PR-specific business files remain owned by PR #933. This batch changes no
product contract, model, permission, action, frontend behavior or customer data.

## Root causes

- Workflow uploads `backend-execution-<run-id>-<shard>`, but receipt discovery
  and origin verification expected the legacy
  `backend-execution-<run-id>-<attempt>-<shard>` name. Discovery therefore
  returned zero locators even when successful mainline artifacts existed.
- Ordinary backend PRs selected the complete module baseline for every
  dependency-safe module. PR #933 selected 13 modules although its changed
  executable set contained 50 tests in two modules.
- Missing receipt discovery also discarded real module durations, so shard
  planning used unit weights of a few seconds instead of the measured
  269/24-second values visible on main.
- A module test had no independent timeout. Four shards could remain stuck in
  one step until the 240-minute job ceiling, with no live heartbeat.

## Correction

- Fix current and legacy artifact-name discovery and attempt-one verification.
- Add a focused PR plan that runs exact changed ORM selectors in impact-safe
  modules; fall back to complete modules when no changed tests exist.
- Keep full module baselines for schedule, explicit candidate and operator full
  audits.
- Execute every Odoo module through a hard-timeout wrapper with a 30-second
  heartbeat and preserved partial log.
- Use authenticated historical durations for shard balancing even when test
  reuse remains denied by the existing six-dimension closure policy.

## Acceptance

- Artifact discovery returns locators for real current artifact names.
- PR #933 plans only `smart_construction_core` and `smart_core`, with 50 exact
  selectors and measured 269/24-second shard weights.
- A module that emits no output still emits heartbeat lines.
- A hung module exits 124 within its lane timeout rather than waiting for the
  job ceiling.
- Scheduled and explicit formal-release runs retain complete module scope.
- CI workflow contract, scheduled gates and GitHub Actions security checks pass.

## Rollback

Revert the focused planner, wrapper, workflow routing and discovery correction
together. No database or runtime state requires restoration.

## Execution log

- `verify.ci.workflow.contract`: PASS, 462 tests.
- `verify.ci.scheduled_gates`: PASS, 97 tests.
- `verify.github_actions.security`: PASS, 18 tests plus workflow policy audit.
- `verify.guard.registry`: PASS, 24 tests plus 1636-script audit.
- `verify.test.coverage.registry`: PASS, 19 tests; generated snapshot refreshed.
- `verify.frontend.dev.incremental.unit`: PASS, 178 tests.
- `verify.agent.resume.unit`: PASS, 64 tests.
- Real focused planning for PR #933 selected two modules, 50 exact selectors,
  and authenticated durations of 269/24 seconds.
- A full local `ci.local.iteration` was intentionally stopped after fifteen
  targets because it would repeat already-passed PR business ORM work. It is
  not reported as a pass; the exact-head remote PR remains the integration
  authority.
