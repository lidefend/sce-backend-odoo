# SCHEDULED-FULL-BASELINE-REMEDIATION-20261124

## Identity

- Base main: `5e436b2a6cb8816da94c0b3d3d831279628adf3d`
- Branch: `fix/scheduled-full-baseline-remediation-20261124`
- Source PR: #994, merged from `0d4ede7d18dd8f26e93ae508e041ec32892e21d3`

## Problem

The all-tests scheduled backend run
[`45329428029`](https://github.com/lidefend/sce-backend-odoo/actions/runs/45329428029)
correctly stopped on defects that the former gate-tag subset had omitted.

## Required closure

1. Pass the exact attempt database identity into isolated Odoo tests.
2. Make acceptance fixture tests seed only their own current test attempt.
3. Make demo ownership tests create or load their required scenario facts inside
   the test transaction.
4. Resolve the current smart_core field-settings contract assertion.
5. Resolve the settlement concurrency winner assertion.
6. Re-run every affected module's complete suite and then the exact-head full
   backend suite.

No skip, quarantine, wildcard suppression or production ACL change is accepted.

## Focused reproduction and fix

- Acceptance fixture: the harness now passes `SC_TEST_DB_NAME=<attempt database>`
  into the test container and the guard compares that exact database name
  instead of assuming a `sc_test_` prefix.
- Demo ownership: the test loads `s69_payment_ledger_surface` inside its class
  transaction when the contract XMLID is absent.
- Smart core field settings: the request declares the supported `web_pc`
  client type; the assertion now includes the failed envelope for diagnosis.
- Smart core isolated-order checks now synthesize their required reason-code
  metadata and select a leaf from either released navigation group instead of
  depending on industry module test order.
- Settlement concurrency: both serialization failure and PostgreSQL deadlock
  are retried in separate cursors, so neither worker can exit without an
  outcome.

Focused results:

- `smart_construction_acceptance_fixture`, acceptance scene tags: 28 PASS.
- `smart_core`, changed class: 78 PASS, including field settings and isolated
  order-sensitive registry/navigation cases.
- `smart_construction_core`, submit-versus-cancel concurrency method: 1 PASS.
- Shell/attempt identity tests: 11 PASS.
- Demo ORM reproduction is intentionally deferred to the governed remote full
  suite because `local.test` forbids the demo pre-init profile.
