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
- A transport exception waits 250 milliseconds and retries once.
- Repeated failure emits only a whitelisted transport code or error class.
- The incremental-worktree planner routes the shared probe and its behavior
  lock to `verify.frontend.delivery_hardening.guard`.
- Generated complexity and split-plan reports refresh only the line counts of
  the two changed incremental-routing files.

## Observed validation

- `make verify.frontend.delivery_hardening.guard`: passed, 17 tests.
- `make verify.frontend.dev.incremental.unit`: passed, 104 tests.

These observations still require governed receipts on an isolated clean
candidate, followed by exact-head PR checks and a fresh full-lane run.
