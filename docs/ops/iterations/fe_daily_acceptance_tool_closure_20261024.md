# FE-DAILY-ACCEPTANCE-TOOL-CLOSURE-01

## Boundary

- Formal product layer: P4 ops delivery tool.
- Layer target: daily acceptance navigation expectations and multi-duty
  publication orchestration.
- Standard vs user-specific: operations validation mechanism; no product or
  tenant semantics.
- Why here: the observed failures are validation-tool assumptions, not deployed
  product behavior or contract declarations.
- Why not elsewhere: changing menus, product fields, permissions, module
  versions or runtime configuration to satisfy these tools would hide the
  defects.
- Blast radius: role-scoped navigation tests and the daily acceptance wrapper.
- Excluded: product source, module upgrade, frontend rebuild, deployment, push,
  PR, merge, production access and cleanup of other worktrees or evidence.

## Baseline

- Mainline and daily deployment identity:
  `96c860d0fb041c556b687afaad6dc689528785e5`.
- Daily duties: `demo` on `sc_demo`, `platform_control` on
  `sc_platform_control`.
- Frontend fingerprint reported by both duty faces:
  `33a88db417ed29b0b5e54a1becfa5e17cbe45ec14c9d246c0f11fab5ebd024bb`.
- Existing failure 1: the acceptance action-count unit pins stale finance and
  project-member counts.
- Existing failure 2: `release.daily_dev.acceptance.publish` reaches
  `release.dev.acceptance.publish`, which assumes the local `odoo` Compose
  service and reruns a local frontend build.

## Findings

- `menu_sc_historical_payment_fact` is explicitly inactive in the shipped
  finance menu wave and was removed from the finance locked navigation manifest.
  The current finance closure is 45 paths, not 46.
- The formal role manifest is internally consistent for the declared roles.
  Tests must derive role counts from that manifest rather than duplicate them.
- The deployed daily runtime has two duties with distinct compose projects,
  databases and services. The existing duty declaration and entry guard already
  own those identities; the acceptance wrapper must consume them instead of
  creating a second topology authority.

## Implementation

- The acceptance action-count unit now derives every locked role expectation
  from `config/frontend/authoritative_navigation.json` and verifies that the
  declared count equals the unique menu-identity list. It also records why the
  retired historical-payment menu is absent from the 45-entry finance closure.
- The daily publication target no longer depends on
  `release.dev.acceptance.publish`, `verify.frontend.build`,
  `check-compose-project`, or the local `odoo` service.
- Daily formal-surface audits execute inside the declared serving duty through
  `daily_runtime_duty_odoo_shell.py`; the duty and database are resolved from
  the existing daily entry and duty declarations.
- The payment-request formal list probe now follows the deployed contract:
  `legal_next_action_display` is interaction guidance and was intentionally
  retired from the fact-column list in commit `1b3d28728`.
- Data-presence audits for version acceptance remain outside the daily
  structural lane. The daily lane records empty business lists as data state;
  it does not convert them into a product-contract failure or silently seed
  data into the deployed demo database.
- The fixed daily readonly credential declaration now explicitly includes the
  relation-roundtrip tool. Its operation remains readonly and its database
  binding remains `sc_demo`; unlisted tools still fail closed.
- `daily.runtime.entry.verify` checks both declared duties' service face,
  database route, source revision and frontend fingerprint before publication
  acceptance can pass.
- The entry validator now rejects duplicate duty declarations. Existing
  negative cases continue to reject missing duties, unknown/wrong services and
  database-route mismatches.

## Verification

- `make verify.acceptance_action_count.unit`: PASS, 15 tests.
- `make verify.daily.runtime.entry`: PASS, 32 tests plus the entry guard.
- `make verify.daily_dev.acceptance.formal_surface.unit`: PASS, 10 tests.
- `make verify.frontend.acceptance.environment.guard`: PASS, 59 Python tests
  plus the two Node source tests.
- `make verify.daily.demo_credential.confirmation`: PASS, 6 tests.
- `make verify.environment.topology.guard`: PASS, 18 topology tests plus the
  nginx database-authority guard.
- `make verify.agent.ledger.unit`: PASS, 18 tests and the ledger guard.
- `make ci.local.iteration`: PASS, L1 only, `outside_scope=[]`.
- `make daily.runtime.entry.verify`: PASS, 66/66 live read-only checks against
  serving revision `96c860d0…`.
- `make verify.daily_dev.product_menu_release_gate.guard`: PASS with
  `construction.standard` 91 pages and `construction.preview` 131 pages.
- The official complexity report and split-plan generators were run twice; the
  second generation was byte-identical. `ci.generated_evidence.preflight`
  passed every generated-report guard through the tracked-report checks, then
  stopped at `verify.frontend.component_driver_takeover.unit` because the clean
  local workspace has no `frontend/packages/ui/node_modules`. This is an
  environment precondition, not a report staleness failure; browser evidence
  below ran on the daily host where managed dependencies exist.

## Live deployment identity

- Repository and both duty `/api/runtime-version` endpoints:
  `96c860d0fb041c556b687afaad6dc689528785e5`.
- Shared frontend fingerprint:
  `33a88db417ed29b0b5e54a1becfa5e17cbe45ec14c9d246c0f11fab5ebd024bb`.
- Duties: `demo` / `sc_demo`, `platform_control` /
  `sc_platform_control`.
- `daily.runtime.entry.verify`: 66/66 checks PASS, including distinct service
  identities, database routing, source revision and frontend fingerprint.

## User journeys

| Journey | Result | Evidence |
| --- | --- | --- |
| Project workspace, ledger and mobile layout | PASS | Project form presentation: 1 target, 1 header/pattern, no overflow, no console/page/HTTP errors. Project ledger at 1440 and 390: 8/8 record checks, 108/108 gated checks, 5/5 negative fixtures, 0 runtime errors. Default landing and workspace routes loaded without errors. |
| Roles and permissions | PASS with a role-persona note | Real HTTP logins for `demo_role_finance`, `demo_role_pm`, `demo_role_owner`, `demo_role_project_a_member` returned role codes `finance`, `pm`, `owner`, `project_member`; `system.init` passed with zero missing authorities and no forbidden labels. Runtime ACL observation ran read-only for 21 permission groups and non-superuser witnesses. The demo role accounts expose live admitted-entry counts of 18/11/6/7 respectively; they are distinct demo role-group principals from the locked acceptance-fixture manifest, so this round does not relabel one surface as the other. |
| Feedback and draft state | PASS for frontend behavior | The deployed daily page and bundled frontend ran 9 scenarios: initial visible advice, partner-presence change, debounce collapse, old-success drop, old-failure drop, visible-to-hidden, hidden-to-visible recovery, record-switch invalidation and save-epoch invalidation. Evaluation responses were controlled by the browser harness so no demo business data was written. The live backend feedback path over an existing business record was not exercised because the demo database has no `sc.team.loan.deduction.workspace` record and the daily policy intentionally excludes the acceptance fixture. |
| Relation open and return | PASS | Live project `project.project/1`, action `588`, menu `382`, login `demo_full`. 13 relation controls were declared; 5 were readable/openable and all 5 opened. `user_id` completed the full return round trip with path, title, status bar, tabs and actions restored. Contract/render comparison covered 7/7 fields, with 5 recorded non-blocking differences and 0 blocking differences; no denied request or console/page error. This run used an explicit approved demo record identity and is diagnostic user acceptance, not a managed fixture-resolution receipt. |

## Recovery-point pairing

- Platform control: `/data/backups/daily-platform-control/sc_platform_control-20261024T092619Z-bb919137`, `database.dump`, 1,903,282 bytes, archive dbname `sc_platform_control`, created 2026-10-24 09:26:20 CST.
- Demo: `/data/backups/daily-demo-dev/sc_demo-20261024T092633Z-4344aa33`, `database.dump`, 34,680,369 bytes, archive dbname `sc_demo`, created 2026-10-24 09:26:33 CST.
- Both dumps are readable custom-format archives paired to the same deployment window that served `96c860d0…`; no restore was attempted in this acceptance batch.

## Product-defect finding

No additional product defect was proven by these journeys. The remaining
acceptance boundaries are the distinct demo-role versus fixture-role principal
populations and the unexercised live backend feedback path noted above.

## External state

The official fingerprint helper restored the missing ignored
`frontend/apps/web/dist-dev/.build-sha256` marker from the already-served
artifact; the computed value exactly matched both runtime instances
(`33a88d…`). No frontend build, service restart, module upgrade, database
restore, push, PR, merge, deployment or production operation was performed.
