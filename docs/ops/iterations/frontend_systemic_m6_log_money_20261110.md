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

Pending.

## Result

Planned.
