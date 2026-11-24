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

## Responsibility separation

The scheduled backend planner now exposes three explicit suites:

- `product`: product-path modules, excluding explicit test-only carriers.
- `demo`: modules under `demo_addons`.
- `acceptance`: explicit forbidden implicit test carriers.

The sets must partition every runnable module without overlap. Product release
qualification runs only `product`. `.github/workflows/auxiliary_backend_suite.yml`
runs demo and acceptance independently on the same schedule, with separate
status and evidence. Demo or acceptance failure no longer blocks product
candidate-build eligibility.

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

## Suite-aware harness identity

The first exact-head three-suite dispatch exposed a P4 validation-tool defect:
the Compose project identity had been changed to
`sc-suite-<run>-<suite>-<shard>`, while dependency preparation and runner
cleanup still accepted only `sc-suite-<run>-<shard>`. Product and acceptance
tests therefore stopped before Odoo test execution with
`not an isolated backend suite project`; this is not a product-test verdict.

The harness now binds suite identity in dependency-template keys and accepts
only the following exact shard project shape:

```text
sc-suite-<run-id>-<product|demo|acceptance>-<0..3>
```

The focused negative cases reject the legacy shard shape, a missing or unknown
suite, a mismatched suite, an unbounded shard and a mismatched run identity.

Focused results:

- `scripts.test.test_dependency_baseline`: 11 PASS.
- `scripts.verify.test_github_actions_security_guard`: 18 PASS.
- `scripts.ci.test_ci_risk_workflow_contract`: 31 PASS.
- `scripts.ci.test_backend_suite_plan` plus dispatch contract: 96 PASS.
- `make ci.local.iteration`: PASS after the run scope was updated to the owned P4 files.
- `make verify.ci.scheduled_gates`: PASS.

The exact-head dispatch then exposed the next boundary in the same tool chain:
the workflow had the exact `SUITE_NAME`, `SC_ENVIRONMENT` and demo policy, but
`scripts/test/test.sh` forwarded only run/attempt/shard/head/project into the
isolated Odoo container. Preparation therefore rejected the missing suite
before any product test started. Runs `45341435662` (product) and
`45341434954` (acceptance) failed as `validation_tool_defect`, not as product
test verdicts.

The container preparation arguments now forward the same suite, environment
and demo policy as the workflow, and the focused test executes the real shell
fragment to assert all six exact identity fields. Updated focused result:
`scripts.test.test_dependency_baseline`: 12 PASS; `make ci.local.iteration`:
PASS.

Exact-head run `cf0a71a28eb6a47819cf8948503bd13249a2ec4c` then exercised the
three suites independently:

- Product `45342230427`: all four shards and coverage verification PASS.
- Demo `45342236804`: 28 tests executed; one stale test expectation still
  asserted the former generic payer label instead of the current realistic
  demo seed value. Classified as `baseline_evidence_defect`.
- Acceptance `45342251532`: 24 tests loaded, with two setup errors because the
  production fixture guard still required an `sc_test_` prefix while the
  isolated backend suite uses the exact attempt database
  `sc_suite_ci_<module>`. Classified as `validation_tool_defect`.

The demo assertion now matches the current declared seed fact,
`德阳建科建材有限公司基本户`. The acceptance guard now requires a non-empty
attempt database and exact equality with the active Odoo connection; it does
not admit arbitrary databases. `TestAcceptanceFixtureGuard` passed 5/5 in the
isolated `local.test` ORM lane. The subsequent `make ci.local.iteration`
passed with 19 acceptance-fixture tests plus all affected demo/tool guards.
