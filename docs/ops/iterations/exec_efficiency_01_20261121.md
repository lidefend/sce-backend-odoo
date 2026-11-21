# EXEC-EFFICIENCY-01

## Objective

Make governed environment and evidence reuse the default execution strategy for
small local iterations. This batch is P4 execution-tool work only.

## Phase 1 evidence

The read-only diagnosis was performed on the merged acceptance worktree before
creating this branch:

- 101 ORM receipts and 27 template preparations in the preceding 12 hours;
- observed template preparations took 285-483 seconds;
- one `ci.local.iteration` took 546.8 seconds, of which 326.4 seconds was a
  template preparation;
- `smart_construction_bundle` does not include the reverse dependency
  `smart_construction_acceptance_fixture`;
- one wrong template choice spent a complete preparation and then ran zero
  tests;
- a single `sc_test_template` slot forces bundle and acceptance-fixture tests to
  evict each other;
- the fresh-install fingerprint currently includes upgrade-only migration files.

## P0 implementation boundary

1. Template coverage is validated from manifest dependencies before any database
   work. A template module must contain the requested test module.
2. Template databases are separated by template module so independent prepared
   scenarios no longer evict each other.
3. Fresh-install and upgrade schema identities are separate. Fresh install
   ignores migration-only files; upgrade identity retains them.
4. Incremental execution prefers the newest complete passed receipt with matching
   inputs instead of letting an interrupted attempt force unrelated targets to
   run again.

## Exclusions

- No business module changes.
- No frontend product behavior changes.
- No rebuild of `sc_dev_demo`, `sc_dev_sample`, `sc_clean`, or acceptance data.
- No production or deployment action.
- No migration of existing test databases without explicit confirmation.

## Validation

Implementation provides:

- manifest dependency coverage is checked before profile or Docker access;
- template database slots are derived from the template module;
- requested-module installation is read back after preparing a template;
- fresh-install and upgrade schema fingerprints are separate;
- every ORM test prints a machine-readable reuse/rebuild decision and exact
  rebuild cause before expensive preparation;
- a caller may select a validated superset template for incremental execution;
- complete passed receipts are preferred over newer interrupted receipts.

### Passed offline

- `verify.local.development_lifecycle.unit`: 67 tests.
- `verify.frontend.dev.incremental.unit`: 192 tests.
- `verify.agent.resume.unit`: 67 tests.
- `ci.local.iteration`: all static prerequisites passed; affected planner executed
  `verify.agent.ledger.unit` and `verify.baseline.iteration.execution.policy`.
- `make fe.install.cached`: 639 packages reused, 0 downloaded, 4 seconds.
- `make local.test.prepare`: registered `sc-local-test / sc_test` identity
  validated without runtime writes.

Original targeted logs:

```text
.runtime/agent-runs/EXEC-EFFICIENCY-01-20261121/local_test_runner.log
.runtime/agent-runs/EXEC-EFFICIENCY-01-20261121/incremental_planner.log
.runtime/agent-runs/EXEC-EFFICIENCY-01-20261121/agent_resume.log
```

### Runtime smoke pending explicit confirmation

The next check creates or refreshes only the disposable test resources:

```text
profile: sc-local-test
database: sc_test
templates:
  sc_test_template__smart_construction_bundle
  sc_test_template__smart_construction_acceptance_fixture
```

Expected writes: drop/recreate disposable `sc_test`, prepare the two template
databases as needed, run one focused ORM test per template, then remove transient
carriers. The readback must prove both template modules include their requested
test module and that a second identical run reports
`database_template_reused=true`. No persistent `sc_dev_demo`, sample, clean,
platform, or acceptance database is touched.

Recovery: these test databases are disposable and can be recreated through the
registered `local.test.*` targets. Execution remains blocked until the owner
confirms this exact target under the repository's fresh-install/template rule.

Remote integration is not run.
