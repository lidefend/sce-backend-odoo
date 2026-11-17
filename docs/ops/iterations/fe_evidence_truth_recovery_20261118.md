# Frontend evidence truth recovery (2026-11-18)

## Boundary

- Formal Product Layer: P4
- Layer Target: frontend generated evidence, audit classifiers and proof bindings
- Module: `scripts/audit`, `scripts/verify`, `docs/frontend_productization/rendering-detail`
- Standard vs User-Specific: platform engineering standard

The 2026-11-18 full audit found that several “green” frontend reports no longer
describe current source. The current rendering-detail generator reports 194
surfaces and 13 formal P0 gaps while the tracked report still declares 174
surfaces and zero gaps. Three further proof sources are stale: the accessibility
guard points at the retired CSS carrier, two visual-evidence markers no longer
exist, and the view-type probe emits an obsolete schema version.

Why here: these are measurement, routing and evidence-ownership defects. Product
rendering edits would compensate for the evidence layer and hide the real state.

Why not elsewhere:

- no backend contract, model, permission or business action change;
- no page-specific frontend fallback or CSS relaxation;
- the 13 residual component surfaces remain a separate P0 product batch.

Blast radius: frontend generated inventories, their offline checks, and completion
routing only. Runtime business behavior and deployed assets do not change.

## Scope

- route every current formal P0 gap to an explicit follow-up batch;
- repair source paths and browser assertion bindings without weakening checks;
- align the view-type render probe with the current Contract V2 schema;
- align domain surface classification with the action renderer registry;
- regenerate current inventories and review the resulting non-zero product gaps.

## Exclusions

- closing the 13 residual component ownership gaps in this P4 batch;
- removing TDesign internal selectors or editing rendering CSS;
- contract, permission, action, database, deployment or user-acceptance changes.

## Acceptance

- no current gap is left without a target batch;
- each formal visual proof points to an existing governed target and named assertion;
- accessibility checks follow the current owner source;
- the view-type and domain classifier checks pass for the current source;
- regenerated inventories are byte-reproducible under their governed `--check` commands.

## Rollback

Revert the P4 tooling and regenerated evidence commits together. No data or runtime
state requires restoration.

## Execution log

- Baseline: `main@200185560d5b745e1e7369694bfa9e9d7947f91f`, clean worktree.
- Results below are recorded in `.agent/runs/FE-EVIDENCE-TRUTH-RECOVERY-20261118/run.json`
  as checks execute; original logs remain under `.runtime/agent-runs/`.

### Evidence truth corrections

- Retargeted the global accessibility proof to the current owner,
  `frontend/apps/web/src/styles/accessibility.css`.
- Rebound the workspace-native-structure detail to the governed project-create
  native-structure probe and the workflow disabled-reason detail to the real
  workflow browser assertion source.
- Updated the view-type renderer probe from Contract V2 `2.2.0` to `2.5.0`.
- Aligned the domain rollout classifier with the current registry: pivot and graph
  are ready; calendar, gantt and dashboard remain explicit readable fallbacks.
- Fixed the Phase 0 CSS-variable scanner so BEM selectors such as `--action` are no
  longer reported as custom-property declarations.
- Classified the currently shipped design-token families in the token authority;
  all 201 real variable declarations now pass.

### P0 completion

- Closed the 13 residual formal P0 surfaces with parsed component bindings and
  governed state primitives.
- Replaced remaining custom state markup with `ScInlineState`, `ScErrorState` and
  governed list/card/field ownership where applicable.
- Removed all 11 internal TDesign selector overrides. Product styling now consumes
  public props/variables or project-owned semantic elements.
- Added explicit tab semantics and Delete-key focus return to activity page tabs;
  single-page visibility remains unchanged because it is the declared behavior.
- The current rendering-detail inventory reports 194 surfaces, P0/P1 `gap=0`,
  `unassignedGapSourceCount=0`, and zero official internal-selector gaps.

### Validation

| Check | Result |
| --- | --- |
| `make ci.local.iteration` | PASS; 31 affected targets executed |
| `verify.frontend.rendering_detail_state.unit` | PASS; 79 tests |
| `verify.frontend.view_type_render_coverage.guard` | PASS; 9 tests |
| `verify.frontend.project_domain_rollout.unit` | PASS; 10 tests |
| `verify.frontend.state_dashboard.browser` | PASS; state, tabs, focus and mobile overflow |
| `verify.frontend.rendering_detail_state.browser` | PASS; no mutation or browser errors |
| `verify.frontend.native_form_action_presentation.unit/browser` | PASS; desktop and 390px |
| `verify.frontend.navigation_shell.unit` | PASS; 6 shell components |
| `verify.frontend.professional_collaboration.unit` | PASS; backend-authoritative lifecycle |
| `verify.frontend.overlay_lifecycle.browser` | PASS; nested focus, return and body locks |
| `verify.frontend.component_driver_takeover.unit` | PASS; 33 required drivers |
| `verify.frontend.typecheck.strict` | PASS |
| `verify.frontend.lint.src` | PASS; zero errors, four pre-existing warnings |
| `verify.frontend.style_system.guard` | PASS; 201 classified Phase 0 variables |
| `verify.frontend.contract_basis.unit` | PASS; zero open contract defects |
| `verify.frontend.contract_v2_render_authority.unit` | PASS; 363 fields classified |

The earlier governed list-surface artifact at `cdaee13557...` remains reusable
because `ScTable` and its browser probe were unchanged by this batch. Its six
viewports report 352/352 gated checks, 30/30 records, 6/6 negative fixtures and
zero runtime errors.

## Boundary of the result

This batch establishes a truthful current source inventory and closes the exposed
P0 presentation ownership gaps. It does not deploy, merge, or prove the still
separate full-product accessibility, responsive, performance, role/user or
business-journey matrices.
