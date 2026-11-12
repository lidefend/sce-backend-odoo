# FE-02 Read Ownership And Collection Load Reduction

## Identity

- Repository: `sce-backend-odoo`
- Branch: `fix/fe-convergence-fe02-read-ownership-20261112`
- Baseline: `c4b07e17516490118a91f7cead655e15af94ef4d` (FE-01 candidate)
- Stage identity: baseline HEAD with this topic's explicit dirty scope

## Layer And Scope

- Formal Product Layer: P0 platform kernel product
- Layer Target: shared frontend collection loading and record-read ownership
- Module: `frontend/apps/web`
- Standard vs User-Specific: platform engineering standard
- Why here: stale completion and unnecessary reads are generic async/request ownership defects
- Why not elsewhere: the backend already declares the requested operation and data; no P1/P2 rule is missing
- Blast radius: formal list load success/catch publication, retained record reload denial handling, dead collection-scope modules and focused tests
- Excluded: retained `listAggregates`, FE-03/04, backend contracts, databases, deployment and write journeys

## Acceptance

1. Formal list loading makes no collection-scope totals or full-page metric calls.
2. A stale list success cannot publish records/status after its load lease is lost.
3. A stale form 403 cannot navigate after deactivation or record identity change.
4. Current loads continue to publish and navigate normally.
5. Focused tests, lint, strict typecheck, build and `ci.local.iteration` pass non-zero.

## Evidence

Results are recorded through `make agent.run.begin` and `make agent.run.record`. Original logs stay under `.runtime/agent-runs/FE-CONVERGENCE-FE02-20261112/`.

| Check | Result |
| --- | --- |
| `verify.frontend.action_view_route_lease_race.unit` | passed; route/generation ownership contract |
| `verify.frontend.professional_relation_lifecycle.unit` | passed; 58 checks including stale list success and scope-probe count 0 |
| `verify.frontend.record_form_return.unit` | passed; 20 checks including stale/current 403 navigation |
| `verify.action_view_runtime_smoke.behavior` | passed; 3 action-runtime smoke suites |
| `verify.frontend.lint.src` | passed; 0 errors, 4 pre-existing warnings |
| `verify.frontend.typecheck.strict` | passed |
| `verify.frontend.build` | passed; 5,382 modules transformed |
| `make ci.local.iteration` | passed; 13 affected targets |

Behavior evidence:

- Formal list success no longer defines or invokes collection-scope total scans or full-page metric scans; the two dedicated modules were removed.
- A stale list success leaves the newer records, status and trace untouched and performs zero scope probes.
- A late 403 after form deactivation performs no router navigation; the same 403 on the active record still follows the existing access-denied path.
- Retained `listAggregates` remain because the formal list renderer consumes them.
- Generated complexity/decision inventories refresh only source counts, line locations and the reduction from deleting the unused scope modules.

Not run:

- Deployed browser journeys for list A-to-B enumeration and retained-form A-to-B switching.
- Independent review and remote CI.

## Rollback

Revert the topic branch. No persistent data or service state is involved.
