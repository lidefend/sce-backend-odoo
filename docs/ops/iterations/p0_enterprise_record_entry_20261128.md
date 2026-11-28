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
- `make ci.local.iteration`: PASS, 15 targets, 535 tests, 3 static checks

Receipt:
`.runtime/frontend-dev-validation/executions/20261128T014323Z-1789915-255425642/receipt.json`

SHA256:
`d766ea3c8ec975165c85e04a9cab2a0a11e21d22c29e34b17b998ae74e1bc253`

PR integration, deployment and complete frontend user acceptance are not claimed.
