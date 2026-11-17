# FE collection numeric header alignment (2026-11-18)

## Boundary

- Formal Product Layer: P0
- Layer Target: public collection table presentation
- Module: frontend shared collection renderer
- Standard vs User-Specific: platform standard

Contract-driven listing already right-aligns numeric and monetary body cells.
The shared table header keeps the platform default alignment, so the column
label and its values can use different visual axes.

## Scope

This batch changes only the shared collection table presentation:

- numeric and monetary header cells consume the same right alignment as their
  body values;
- the real list-surface browser probe asserts header alignment alongside the
  existing body and aggregate checks;
- desktop and compact viewports must remain contained without page overflow.

No field, column set, ordering, width, sorting, permission, action or business
state changes.

## Static verification

| Check | Result |
| --- | --- |
| `verify.frontend.collection_view_semantics.unit` | PASS; collection model, relation and guard checks |
| `verify.frontend.list_surface_search_contract.unit` | PASS; 26 tests |
| `verify.frontend.typecheck.strict` | PASS |
| `verify.frontend.lint.src` | PASS; zero errors, four pre-existing warnings |
| `ci.local.iteration` | PASS; 5 affected targets with non-zero collection |

The real list-surface browser probe remains pending and must verify the new
header/value alignment at all governed viewports.

## Exclusions

- no backend or contract change;
- no model/page-specific branch;
- no change to row open method or view switching;
- no deployment or broad product acceptance claim.
