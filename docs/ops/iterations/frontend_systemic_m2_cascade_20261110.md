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
  `.runtime/frontend-dev-validation/executions/20261109T193951Z-3887329-362612180/receipt.json`.
- Browser candidate `9d616d608fa3630c9851128960ea304eefd55917`:
  WorkspaceHome, MyWork and PaymentRequestForm passed at 1440x960 and
  390x844. All six route/viewport checks report zero overflow, zero Console
  errors, zero HTTP errors and `mutationCount=0`; manual screenshot review found
  no M2 layout regression.
- Browser summary:
  `.runtime/m2-browser-9d616d608/summary.json`, SHA-256
  `9d98cfd24c2621227ffc65480df0429a9ed6ee3d0b110d7f50ed81af629b56f0`.

The guards that previously required `!important` in navigation, visually-hidden
and form-host rules now assert the same behavior without requiring cascade
priority hacks.
