# Scheduled CI authenticated probe transport recovery

Status: verification_pending

- Formal Product Layer: P4
- Layer Target: shared frontend authenticated intent probe
- Baseline: `main@ca032b92dd1131485313b9299b5e799c67f1d525`
- Excluded: product behavior, backend contracts, credentials and deployment

## Failure

The scheduled full frontend release gate reached the released-navigation
settlement assertion after a project-manager relogin, then failed while replaying
`system.init` through Playwright's API request context:

```text
system.init: authenticated probe transport failed
```

The same transport point failed in a previous manual full-lane run, while
HTTP/response, principal, entry-routing and database-routing checks are already
covered separately.

## Repair rule

Retry exactly once with a bounded timeout. A successful retry proceeds through
all existing assertions unchanged. Repeated transport failure remains
fail-closed and reports only a sanitized error code, never request headers or
credentials.

## Implementation

- The authenticated replay uses a fixed 30-second request timeout.
- A `system.init` transport exception waits 250 milliseconds and retries once.
- Every other intent remains single-attempt so the probe cannot replay a
  potential side effect.
- Repeated failure emits only a whitelisted transport code or error class.
- The incremental-worktree planner routes the shared probe and its behavior
  lock to both `verify.frontend.delivery_hardening.guard` and
  `verify.frontend.standard_preview.unit`.
- Generated complexity and split-plan reports refresh only the line counts of
  the two changed incremental-routing files.

## Observed validation

- `make verify.frontend.delivery_hardening.guard`: passed, 17 tests.
- `make verify.frontend.dev.incremental.unit`: passed, 104 tests.

The clean implementation commit
`06f74b2cea9ba6a0999824865586c4f05732974d` also produced governed receipts for:

- `verify.agent.ledger.unit`: passed, 18 tests.
- `verify.agent.resume.unit`: passed, 56 tests.
- `verify.frontend.standard_preview.unit`: passed, 131 Python tests and 42 Node
  assertions.
- `ci.local.iteration`: passed with all five registered targets, generated
  evidence preflight, page-contract bounds and trusted-scan scope resolution.

The original log paths are under
`.runtime/agent-runs/SCHEDULED-CI-AUTHENTICATED-PROBE-20261110/`.
Current exact-head PR checks and a fresh full-lane run remain mandatory.
