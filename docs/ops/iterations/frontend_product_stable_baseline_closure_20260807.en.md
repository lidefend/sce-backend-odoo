# Custom Frontend Product Stable Baseline Closure (2026-08-07)

Chinese version: [frontend_product_stable_baseline_closure_20260807.md](frontend_product_stable_baseline_closure_20260807.md)

## Objective

This initiative replaces page-by-page visual patching with a durable product baseline. It freezes layer ownership, shared page contracts, responsive behavior, lifecycle geometry, environment profiles, and browser evidence so collection, form, workbench, dialog, and state surfaces cannot drift by model, route, device, or loading phase.

Baseline SHA: `074938d2bf9096b2258cbbdc8137c22c2dc979ca`. Implementation branch: `feature/frontend-product-stable-baseline`.

## Architecture ownership

- Formal Product Layer: P0 platform kernel product.
- Layer Target: generic frontend contract consumption, application shell, page orchestration boundary, and shared renderers.
- Modules: `frontend/apps/web`, `scripts/verify`, and `config/frontend`; `smart_core` is changed only when a generic semantic contract is missing.
- This is a platform mechanism. It must not contain construction, tenant, role, model, menu, scene, or route-specific preferences.
- Industry XML, tenant modules, runtime low-code data, and migration scripts must not mask shared renderer defects.

## Fixed runtime chain

`native view → normalized/semantic backend contract → page orchestration → shared renderer → design-system component`

`AppShell` owns navigation, tabs, route hosting, and the single main vertical scroll owner. Page orchestration chooses templates and capability slots only. The custom frontend has no industry awareness. Any industry or tenant expression must first be normalized by the backend into generic zone/block/field/action/capability contracts; the frontend renders those nodes without knowing whether they represent projects, contracts, construction, finance, or any other domain.

## Stable page contract

- At a given viewport, collection, loading, empty, error, readonly, create, and edit routes share one outer canvas geometry.
- Page types may change only internal layout. They must not resize the routed root, change shell height, or create another main scroll owner.
- Page-level horizontal overflow is forbidden. Wide tables may scroll only inside their local table container.
- Table, explicit card, and responsive mobile card are presentations of one collection contract.
- Readonly/create/edit share one form command, workflow, section, field, relation, x2many, attachment, and collaboration system.
- Loading, empty, error, forbidden, saving, success, and failure are first-class states with stable geometry and recovery behavior.

## Zero-debt definition

Zero debt means every exception is either removed or explicitly governed. Model/action/menu/scene/route/role/label-driven shared layout branches, production frontend industry dictionaries, business-field inference, industry model mappings, industry-specific page components, duplicate width or scroll authorities, unexplained `!important` declarations, masking overflow, fixed component caps, frontend business guesses, lifecycle geometry changes, hard-coded audit environments, and weak existence-only assertions are unresolved by default. Test fixtures may name representative business domains but production code must never import them.

Any retained exception requires an identifier, owner component, rationale, scope, exit condition, enforcing gate, and browser evidence. Unregistered exceptions must be zero.

## Milestones

1. M0 — discover routes, templates, contract sources, renderers, scroll owners, environment entries, and classify every exception.
2. M1 — stabilize shell geometry and loading/ready/empty/error lifecycle ownership.
3. M2 — converge collection/search, table/card presentation, selection, bulk actions, columns, pagination, export, and local scrolling.
4. M3 — converge readonly/create/edit forms and complex fields; remove all business-page exceptions and move every missing semantic back to backend contracts.
5. M4 — converge tokens, spacing, density, color, border, radius, shadow, icons, and interactive states.
6. M5 — make one audit implementation run through governed development, test, daily-development, and release-candidate profiles.
7. M6 — deploy an exact candidate SHA to daily development, complete independent visual review, then prepare mainline integration.

## Acceptance

- Primary acceptance principal: `wutao`, defined as the full-product account. Any inaccessible formal menu, action, page, read, or export capability is a backend role mapping, menu-group, model-access, record-rule, or contract-projection defect; it must not be hidden by frontend logic or dismissed as insufficient account permission.
- Viewports: 1920×1080, 1440×900, 1280×800, 1024×768, 768×1024, and 390×844; all routes smoke at 1440 and 390.
- Templates: home, table, card, readonly, create/edit, relation dialog, one2many, collaboration, designer, loading, empty, and error/forbidden.
- Representative domains: home/my work, project ledger, general contract, construction contract, construction diary, plan progress, partners, payment/receipt, and materials.
- Chromium automation is the gate. Windows Chromium and HarmonyOS browsers verify the same account, contract, preference, default presentation, and visible columns.
- Route, template, and representative-domain coverage must be 100%; P0/P1 defects and unregistered exceptions must be zero.
- Production frontend industry knowledge, technical labels, hidden-field leaks, mojibake, missing icons, console errors, unexpected request failures, page-level horizontal overflow, lifecycle canvas drift, and cross-browser default-view drift must all be zero.
- All type, unit, design-system, workspace-canvas, production-build, and browser gates must pass on one full SHA.

Human input is required only for a new dependency, permission/API/business-semantic change, irreversible data operation, conflicting product decision, or the same non-converging blocker for three consecutive iterations.
