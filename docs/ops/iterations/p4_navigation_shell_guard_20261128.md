# P4 Navigation Shell Guard 2026-11-28

## Objective

Repair the stale navigation compilation delegation guard that blocks current
main and PR 1034 even though the product already has one navigation compiler.

## Boundary

- Formal Product Layer: P4 operations and delivery verification.
- Layer Target: frontend navigation shell guard.
- Module: `scripts/verify`.
- Standard vs user-specific: platform delivery verification.
- Why Here: the product implementation already delegates correctly; the guard
  still asserts the compiler at its pre-refactor call site.
- Why Not Elsewhere: no platform, frontend, industry, customer or low-code
  product behavior requires change.
- Blast Radius: navigation shell guard and its negative tests.
- Exclusions: system.init, delivery services, navigation compiler, page
  rendering, business data and PR 1034.

## Root Cause

The current authority chain is:

`system.init -> EffectiveDeliveryService -> PublishedSceneSurfaceService ->
NavigationContractCompiler.compile()`

`system.init` consumes `delivery_payload["navigation"]`. The guard instead
requires `NavigationContractCompiler` and `.compile()` to appear directly in
`system_init.py`, so correct delegation is rejected.

The same failure reproduces on the baseline worktree and is not caused by PR
1034.

## Acceptance

- PublishedSceneSurfaceService must construct and invoke the one compiler.
- system.init must consume the sealed `delivery_payload["navigation"]`.
- system.init must not import or construct the compiler.
- system.init must not rebuild a local `data["navigation"]` payload.
- Navigation shell and backend delivery tests pass non-zero.

## Evidence

- `make verify.frontend.navigation_shell.unit`: passed.
- Navigation shell guard: `PASS components=6`.
- Guard unit suite: 31 tests.
- Negative coverage now rejects:
  - direct `system.init` compiler construction;
  - local navigation payload reconstruction in `system.init`;
  - removal of the compiler from `PublishedSceneSurfaceService`.
- `make ci.local.iteration`: passed with 2 executed targets and no unmapped
  paths.
- Receipt:
  `.runtime/frontend-dev-validation/executions/20261128T075355Z-706962-68211060/receipt.json`.

Exact-head remote checks remain pending until the candidate is committed and
published.
