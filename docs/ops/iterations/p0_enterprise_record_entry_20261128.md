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
`entry_target.record_entry` for the native configuration action. The shared delivery
normalizer and scene shell compiler preserve that identity into `system.init`
navigation, route authority and the native delegate target, so the frontend can open
the exact authenticated company record instead of constructing `/new` from an absent
record identity.

## Validation

- `make verify.navigation.publication_consumers.unit`: PASS
- `make verify.backend.navigation_delivery.unit`: PASS
- `make verify.product.entry_publication.unit`: PASS
- `make verify.extension.hook_contracts.unit`: PASS
- `make verify.scene.company_route_scope_cache.orm`: PASS, 11 ORM tests
- `make ci.local.iteration`: PASS, 20 targets, 614 tests, 3 static checks, 0
  unmapped paths

Receipt:
`.runtime/frontend-dev-validation/executions/20261128T024119Z-2257973-304822757/receipt.json`

SHA256:
`8066bebd19f3858fd3dd91769ff08755cd87084f34d2e742f8bbbb2a92f53494`

PR integration, deployment and complete frontend user acceptance are not claimed.
