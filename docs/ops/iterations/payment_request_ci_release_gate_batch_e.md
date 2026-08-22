# Payment Request CI Release Gate — Batch E

## Boundary

- Formal Product Layer: P0 generic frontend contract consumption and product presentation guard compliance.
- Layer Target: normalized collection test fixtures, semantic design-token usage, and existing frontend complexity ratchets.
- Module: `frontend/apps/web`.
- Reason: the authoritative frontend release gate for the payment-request Floorplan branch failed before browser acceptance.
- Excluded: contract expansion, Native capability implementation, UI5 parity, Lite rollout, business-role inference, and database changes.

## Changes

- Removed a dead test-only import and assertions for an unimplemented Native column-occurrence helper instead of expanding the Native compatibility surface.
- Migrated collection presentation fixtures from the retired `head/views` shape to `ContractV2NormalizedStore` projections.
- Made the contract view-mode read null-safe without adding a parallel contract fallback.
- Replaced activity and mobile-action hard-coded colors with existing semantic design tokens.
- Restored `ListPage.vue` and `ActionView.vue` to their existing size ratchets without raising thresholds.

## Evidence

- `make verify.frontend.collection_view_semantics.unit` — PASS.
- `make verify.frontend.delivery_hardening.guard` — PASS (22 tests).
- `make verify.frontend.style_system.guard` — PASS, hard-coded color maximum remains 0.
- `make verify.frontend.typecheck.strict` — PASS.
- `make verify.frontend.release.unit` — PASS with non-zero unit coverage.
- `VITE_ODOO_DB=sc_frontend_acceptance VITE_ODOO_DB_LOCKED=1 VITE_APP_ENV=acceptance python3 scripts/verify/frontend_static_release_audit.py` — PASS.

The remaining `public_guard` personal-data registry and `professional_quality_gate` guard-registry failures are owned by the independently preserved P4 governance worktree and are not hidden by this batch.
