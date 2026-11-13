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
  requires the guard to detect missing `fetch_intent`, copy and readonly fields.
