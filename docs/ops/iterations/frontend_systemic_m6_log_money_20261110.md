# FE-SYSTEMIC-CONVERGENCE M6：生产观测与金额表达统一

## Boundary

- Formal Product Layer: P0 platform kernel product
- Layer Target: shared frontend diagnostics and monetary presentation
- Module: API, session, action runtime, logger and one2many formatter
- Contract V2, ACL, backend semantics, database and deployment are excluded

## Baseline

- `console.*` calls in `frontend/apps/web/src`: 47
- Monetary display authority: `app/presentation/businessValuePresentation.ts`
- Remaining direct monetary branch: `contractForm/one2manyUtils.ts`

## Plan

Introduce one production-safe logger. Debug/info remain opt-in; warnings are
development diagnostics; errors remain explicit production reporting. Route the
one2many monetary branch through `formatMonetaryDisplayValue` while preserving
its existing six-decimal upper bound and empty-value behavior.

## Validation

- Scattered `console.*` calls: 47 → 0.
- Shared logger console sites: 0 (all output goes through an injectable sink).
- Logger policy tests: quiet development, explicitly verbose development and
  production builds passed.
- `Intl.NumberFormat` display points: 5 → 5 in the single
  `businessValuePresentation` module; `one2manyUtils.ts` no longer owns a
  separate monetary/number display implementation.
- `make verify.frontend.console.guard`: PASS, 4 tests.
- `make verify.frontend.dev.incremental.unit`: 103 passed.
- `make ci.local.iteration`: PASS, 19 targets.
- Receipt:
  `.runtime/frontend-dev-validation/executions/20261109T204128Z-72251-418469068/receipt.json`.

## Result

Pending commit, clean-HEAD iteration and affected 1440/390 page review.
