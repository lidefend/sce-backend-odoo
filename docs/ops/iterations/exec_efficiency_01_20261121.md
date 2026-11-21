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

## Bundle coverage finding

The independent productization check reports one P1 engineering-report gap and
confirms the current `smart_construction_bundle` manifest is not an empty shell.
However, `bundle_registry.list_bundle_scenes()` still contains five legacy scene
summaries while the current product organization declares 46 scenarios and 132
unique pages.

This is a separate product catalog debt. Bundle installation dependencies still
cover the core/scene/portal modules used by local ORM targets, so the bundle can
be used as an installation template for this P4 batch. The bundle registry must
not be treated as the authoritative current product scenario catalog.

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
  `verify.agent.ledger.unit`, `verify.baseline.iteration.execution.policy` and
  `verify.verification.lane.coverage`.
- `make fe.install.cached`: 639 packages reused, 0 downloaded, 4 seconds.
- `make local.test.prepare`: registered `sc-local-test / sc_test` identity
  validated without runtime writes.

Original targeted logs:

```text
.runtime/agent-runs/EXEC-EFFICIENCY-01-20261121/local_test_runner.log
.runtime/agent-runs/EXEC-EFFICIENCY-01-20261121/incremental_planner.log
.runtime/agent-runs/EXEC-EFFICIENCY-01-20261121/agent_resume.log
```

### Runtime template smoke

The next check creates or refreshes only the disposable test resources:

```text
profile: sc-local-test
database: sc_test
templates:
  sc_test_template__smart_construction_bundle
  sc_test_template__smart_construction_acceptance_fixture
```

Governed runtime entries:

```text
make verify.local.test.template.bundle.orm
make verify.local.test.template.fixture.orm
```

Expected writes: drop/recreate disposable `sc_test`, prepare the two template
databases as needed, run one focused ORM test per template, then remove transient
carriers. The readback must prove both template modules include their requested
test module and that a second identical run reports
`database_template_reused=true`. No persistent `sc_dev_demo`, sample, clean,
platform, or acceptance database is touched.

Owner confirmed the exact disposable target. Runtime results:

| Template module | First run | Second run | Tests |
| --- | --- | --- | --- |
| `smart_construction_bundle` | 287s, `rebuild:template_missing` | 12s, `reuse` | 17 + 17 |
| `smart_construction_acceptance_fixture` | 287s, `rebuild:template_missing` | 16s, `reuse` | 1 + 1 |

Readback confirmed:

- both template databases exist with distinct database comments;
- each requested module is `installed` in its template;
- bundle/core/scene coexist in both templates;
- acceptance fixture and bundle template slots coexist;
- the legacy `sc_test_template` was not deleted or migrated;
- every transient test carrier was removed.

The runtime targets are registered as `local_diagnostic` and the verification
lane baseline was deliberately refreshed: one target moved out of the
zero-reference set and the two new runtime diagnostics moved in.

Authoritative readbacks:

```text
.runtime/agent-runs/EXEC-EFFICIENCY-01-20261121/bundle_template_readback.json
.runtime/agent-runs/EXEC-EFFICIENCY-01-20261121/fixture_template_readback.json
```

The new runtime entries are registered as `local_diagnostic` in the verification
lane disposition registry. The reviewed baseline update:

- registers `verify.local.test.template.bundle.orm`;
- registers `verify.local.test.template.fixture.orm`;
- removes registration for `verify.local.dev.enterprise_configuration.consumer`,
  which is no longer zero-reference;
- changes the zero-reference ceiling from 672 to 673, exactly the net addition
  of one identity.

The exact-head Quick also exposed an unused duplicate test tag,
`fixture_scenario_identity`. The test is already selected by the managed
`acceptance_business_scene_lifecycle` tag, so the duplicate tag was retired
instead of registering a second coverage consumer.

Remote integration is not run yet.
