# FE-SYSTEMIC-CONVERGENCE M2：层叠与 !important 清理

## Boundary

- Formal Product Layer: P0 platform kernel product
- Layer Target: generic frontend cascade and accessibility style split
- Module: styles, shell, hierarchy, form and collection surfaces
- Contract V2, ACL, backend semantics, database and deployment are excluded

## Baseline and Target

- Baseline `!important`: 41 declarations across 13 files
- Target: 0 declarations
- `product-patterns.css`: keep product patterns, move global accessibility and
  reduced-motion foundations to `styles/accessibility.css`
- The skip link consumes `pattern.overlay.skip_link_z_index`; the application
  stylesheet no longer embeds a raw stacking value.

## Validation

- `!important`: 41 → 0.
- `product-patterns.css`: 512 lines → 455 lines.
- Global accessibility/focus/reduced-motion rules moved to `styles/accessibility.css`
  (53 lines) and imported before product patterns.
- `make verify.frontend.style_system.guard`: PASS.
- Design Token package build: PASS.
- Design Token verify: PASS.
- Design Token unit tests: 5 passed.
- `make verify.frontend.navigation_shell.unit`: PASS.
- `make verify.frontend.professional_business_value.unit`: PASS.
- `make verify.frontend.scene_component_bridge.guard`: PASS.
- lint: 0 errors, 3 existing component warnings.
- strict typecheck: PASS.
- `make ci.local.iteration`: PASS, 23 affected targets, receipt
  `.runtime/frontend-dev-validation/executions/20261109T193111Z-3822641-522047199/receipt.json`.

The guards that previously required `!important` in navigation, visually-hidden
and form-host rules now assert the same behavior without requiring cascade
priority hacks.
