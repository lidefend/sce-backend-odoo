# P0 Authoritative Navigation Route 2026-11-28

## Result

The clean enterprise initialization journey exposed two route carriers for the
same menu/action pair: final navigation used `/s/...`, while the scenario-surface
tree still used the pre-scene action route.

## Ownership

- Formal Product Layer: P0 platform contract projection.
- Layer Target: delivery navigation normalization and final scenario surface.
- Modules: `smart_core`, with construction contract assertions.
- Why Here: `smart_core` owns final route projection; frontend must not choose
  between contradictory declarations.
- Why Not Elsewhere: no frontend fallback, ACL change or second compiler is valid.
- Blast Radius: route-bearing navigation nodes and scenario-surface entries for
  the same authorized menu/action pairs.

## Required Gates

| Gate | State | Owner target |
| --- | --- | --- |
| Exact base/head identity | required | preflight and run binding |
| Focused normalizer regression | required | `verify.product.entry_publication.unit` |
| Cross-contract compiler regression | required | `verify.navigation_contract_compiler.unit` |
| Existing affected navigation family | required | `verify.backend.navigation_delivery.unit` |
| Real construction projection | required | `verify.changed_tests.orm` |
| Owning-module baseline | deferred_remote | exact-head PR CI |
| Remote required gates | required | exact-head PR CI |

## Evidence

The failing clean receipt is stored under:

`.runtime/agent-runs/FE-CONSUMPTION-CLOSEOUT-20261126/local-clean-finance-e2e/enterprise-setup/receipt.json`

It observed final route authority `/s/entry.smart_construction_core.menu_sc_enterprise_initialization`
with the company record entry, but the product quick entry navigated to `/a/966?menu_id=719`.
