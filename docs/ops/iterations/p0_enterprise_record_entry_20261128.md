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

The final consumer response also collapses duplicate carriers after checking equality:
navigation exposes only the node-level `entry_target`, and scene-ready rows expose only
the row-level `target`. Conflicting copies fail closed before reaching the frontend.

Sceneization ownership is now a separate stage. `DeliveryEngine` produces candidate
published entries and route authority; `PublishedSceneSurfaceService` compiles those
entries into the only scene navigation surface and scene shell rows; the release
snapshot freezes that result; effective delivery applies enterprise/user authorization
without recompiling it; `system.init` only serializes the resulting contract.

## Validation

- `make verify.navigation.publication_consumers.unit`: PASS
- `make verify.backend.navigation_delivery.unit`: PASS
- `make verify.product.entry_publication.unit`: PASS
- `make verify.extension.hook_contracts.unit`: PASS
- `make verify.scene.company_route_scope_cache.orm`: PASS, 11 ORM tests
- `make ci.local.iteration`: PASS, 36 targets, 975 tests, 5 static checks, 0
  unmapped paths

Receipt:
`.runtime/frontend-dev-validation/executions/20261128T044614Z-3281662-824149276/receipt.json`

SHA256:
`0f97c0e59c5f3d376db94c3106091ff2cf81cef1c692a710f48371348b3c8a0d`

PR integration, deployment and complete frontend user acceptance are not claimed.
