# P1 project evidence summary

## Boundary

- Branch: `fix/p1-project-evidence-summary-20261113`
- Baseline: `f70945256baf089bf26663b30ad50a55b9b04098`
- Formal Product Layer: P1 construction industry standard product
- Layer Target: project evidence summary for the formal project dashboard
- Module: `smart_construction_core`

The fix belongs in the industry module because actual payment, actual cost and
settlement rollups are construction business facts. Demo and frontend layers
must not synthesize them.

## Gap

`ProjectDashboardService` resolves `sc.evidence.summary.service`, but the model
is not registered. It falls back to an empty summary, so a posted
`payment.ledger=160000` appears as a zero payment execution total and zero
ledger count in the formal dashboard.

## Planned result

Register the missing model in `smart_construction_core`; aggregate only
caller-visible facts for the authorized project; expose source-model status and
bounded source references; and consume the result through the existing
dashboard contract.

## Implemented result

- Added `sc.evidence.summary.service` and registered it from the P1 services
  package.
- Aggregated company-currency facts under the caller environment:
  approved/done payment requests, posted payment ledgers, active financial or
  manual actual cost ledgers, and approved/done settlement orders.
- The dashboard's paid total now comes only from valid posted payment ledgers.
  Approved request amount remains a separate `payment_request_total` so an
  unpaid or partially paid request cannot be reported or warned as paid.
- Posted ledgers are included only for `normalized` or
  `legacy_observed_identity`; `legacy_unresolved_identity` is excluded from
  amount, count and references.
- Added explicit per-source status and bounded evidence references.
- Removed the dashboard's silent null-summary fallback and made it consume the
  registered service.
- Corrected stale dashboard guards to recognize the current multiline
  capability registry, additional runtime zones, projection-data builders and
  contract-snapshot/frontend architecture.
- Routed the new service/test/dashboard guard paths directly to
  `verify.project.dashboard.contract`. The generic test package initializer no
  longer drags an unrelated approval-contract ORM suite into this change.

## Verification

- `make verify.project.dashboard.contract`: PASS.
- `make verify.frontend.dev.incremental.unit`: PASS, 134 tests; all P1 and
  dashboard paths resolve to the dashboard contract gate.
- `make local.test.test MODULE=smart_construction_core
  TEST_TAGS=project_evidence_summary`: PASS, 4 ORM tests.
- The ORM fixture proves posted payment, unpaid approved request separation,
  unresolved legacy-ledger exclusion, nonzero formal dashboard fields,
  traceable refs and finance-source denial for a project member without finance
  groups.
- The mixed case uses request totals `165200`, valid posted paid `160050` and
  cost `162000`; the payment metric remains normal, proving request amount is
  not used for the payment-versus-cost warning.
- `local.dev.upgrade MODULE=smart_construction_core`: PASS; authority verify
  retained the demo company/currency/finance identity.
- Live DEMO-PJ-EXEC finance-manager readback through
  `project.dashboard.enter` returned `ok=true`,
  `payment_executed_total=160000.0`, payment evidence count 1, cost 4500000,
  settlement evidence count 1, and 8 evidence references.
- The live dashboard payload retained source authority for the summary service,
  Odoo ORM/read_group and business projection models.
- The block schema guard now resolves each actual `_envelope` return path. Its
  startup negative self-test changes an empty return to `data=dict()` and
  follows it with the real dynamic `ready/empty` helper path. State field sets
  are intersected across all returns, so a later complete branch cannot
  overwrite an earlier missing-field result.


## P4 CI preparation extension (owner request, 2026-11-13)

This candidate also introduces opt-in, same-run/same-attempt/same-shard pristine
industry dependency preparation. It does not reuse test results or change the
selected modules/tags. The backend workflow owns the ephemeral project and
volume lifecycle; local.test and persistent environments do not enable it.

The preparation process installs smart_construction_core without test-enable,
then verifies that the requested target remains uninstalled. Each target gets a
new PostgreSQL template clone and a separate copied filestore before the normal
`-i target --test-enable` invocation. Target pre/post installation hooks and
at_install/post_install tests remain on that invocation. Core itself and demo
retain clean installation; demo retains its separate environment authorization.

Identity binds full candidate SHA, CI run, attempt, shard and non-demo mode.
Existing target databases/filestores, unknown provenance, incomplete preparation,
and already-installed targets are refused. Preparation failure blocks the module;
no old test verdict is substituted. Existing workflow teardown removes the
per-run volume containing preparation data and provenance. The template is never
uploaded as an artifact or shared across runners, runs or candidates.

Validation at the dirty stage based on 537bd7251e4f1d46ebb6d10ccd2f0c82bdef1762:
- 8 focused pure tests pass, including one-install/two-clone behavior, independent
  attachment bytes, repeat-target refusal and missing-provenance refusal. PostgreSQL
  and the Odoo subprocess are mocked in those tests; this is not runtime evidence.
- Existing workflow dispatch contract: 17 tests pass.
- `make ci.local.iteration`: 8 affected targets pass; original output is
  `.runtime/ci-preparation-iteration.log` and the incremental execution receipt.
- Real PostgreSQL/Odoo clone execution, test-count comparison, installation count,
  preparation/test duration and end-to-end remote duration remain NOT_RUN.
  Compare the shared module subset against PR883's historical 13-module run;
  executor changes correctly require the wider CI scope as well.

The earlier unmapped-target/verification-lane failures were tooling-registration
failures, fixed by wiring the new unit target into the existing CI contract gate
and mapping its input paths. No coverage baseline was lowered.

Dependency propagation refinement and business-specific core selection are
explicit follow-up work, excluded from this first preparation-only change.
Rollback removes the workflow opt-in and the preparation wrapper; the normal
fresh-install test command remains available. Independent review and exact-head
remote required gates remain required before protected mainline integration.

Independent review found that explicit workflow test-tag overrides can select
dependency at_install tests. Preparation is now disabled for every nonempty
TEST_TAGS_INPUT; a regression executes the actual shell gate with default,
cross-module and unscoped selectors. Default target-scoped selection alone uses
the prepared baseline. The reviewer also reproduced the original real-builder
empty-branch negative case and confirmed the schema guard now rejects it.

### Dependency preparation affinity

The first real plan for 8287535a70192a733afdbdf57e4d28a7707fc20c exposed a
scheduling gap: historical per-module LPT put core+portal, norm+demo, and fixture
in separate shards. Only bundle+seed shared preparation, so the critical path
still paid repeated installation cost. The current refinement treats consumers
of the same manifest dependency as one scheduling group. Core and demo stay
independent units; no module/test is removed. Pure Python consumers may share
that shard but never receive an ORM database.

The planner retains manifest dependencies separately from test/import dependency
edges and computes affinity from the exact HEAD manifest graph. Explicit tag
overrides disable both preparation and affinity. Reuse-decision repartitioning
intersects the group with RUN modules, and workers verify frozen group identity.
Historical durations are conservatively summed without subtracting guessed
installation costs; these weights are not a forecast or measured speedup.

The observed 14-module full scope partitions into: shared consumers (norm,
fixture, bundle, portal, scene, seed); clean core; clean demo; and the six small
remaining modules. `backend_suite_plan` now passes 53 tests, including exact
union, one shared group, independent core/demo scheduling, override handling,
history repartition and frozen identity rejection. The new dirty candidate's
local iteration passes all 8 affected targets. The real execution comparison
remains pending the final exact-head CI; the initial runner validation is not
misrepresented as validation of the refined scheduler.
