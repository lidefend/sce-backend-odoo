# Scheduled CI main lint recovery

Status: verification_pending

- Formal Product Layer: P4
- Layer Target: frontend logger runtime verification mock
- Baseline: `main@ddb008826174b8c387bdd0c6a70faf9022586c6b`
- Failure owner: validation tooling
- Excluded: logger product behavior, contracts, ACL, business data and deployment

## Failure

Full frontend release run
[`42752425393`](https://github.com/lidefend/sce-backend-odoo/actions/runs/42752425393)
stopped at the authoritative release audit on the exact main SHA.
`frontend_static_release_audit` reported one ESLint error in
`frontend/apps/web/scripts/logger_runtime_test.ts`:

```text
63:31 error '_key' is defined but never used @typescript-eslint/no-unused-vars
```

The same run passed strict type checking, the production build, frontend build
fingerprinting, authenticated probe boundaries, delivery hardening and all
other static release checks. Missing later evidence is a consequence of the
fail-fast release audit, not an independent product failure.

## Repair rule

Remove the unused parameter from the `localStorage.getItem` test mock. Do not
change logger behavior, assertions, lint policy or release evidence rules.

## Observed validation

- `make verify.frontend.console.guard`: passed, 7 tests plus the logger runtime
  policy execution.
- `make verify.frontend.lint.src`: passed with 0 errors and 4 existing warnings.
- `make verify.frontend.typecheck.strict`: passed.

Governed receipts, exact-head remote checks and the post-merge full lane remain
mandatory.
