# P0 enterprise record entry — 2026-11-28

## Scope

The enterprise-initialization scene must target the authenticated current company
record. The existing P0 `entry_target.record_entry` carrier remains the only route
and operation authority; no frontend domain evaluation is introduced.

## Exclusions

No ACL, record-rule, role, approval or payment semantics are changed. No runtime
deployment is performed by this batch.

## Result

The enterprise-initialization declaration now carries `record_id=env.company.id`.
A P0 extension-hook contract lets the construction scene layer publish a formal
scene `entry_target.record_entry` for the native configuration action. The existing
P0 navigation projection preserves that record entry into `system.init` navigation
and route authority, so the frontend can open the exact authenticated company record
instead of constructing `/new` from an absent record identity.

## Validation

- `make verify.navigation.publication_consumers.unit`: PASS
- `make verify.extension.hook_contracts.unit`: PASS
- `make verify.scene.company_route_scope_cache.orm`: PASS, 11 ORM tests
- `make ci.local.iteration`: PASS, 18 targets, 597 tests, 3 static checks

Receipt:
`.runtime/frontend-dev-validation/executions/20261128T020816Z-1986435-109178055/receipt.json`

SHA256:
`9ad0122f0cf2893c66ca059e74e050be8375dc9aceb8f58ed46e19e74efa7ac2`

PR integration, deployment and complete frontend user acceptance are not claimed.
