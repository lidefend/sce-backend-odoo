# FE collection scroll accessibility (2026-11-18)

## Boundary

- Formal Product Layer: P0
- Layer Target: shared collection table horizontal-scroll accessibility
- Module: frontend design-system table renderer
- Standard vs User-Specific: platform standard

`ScTable` currently exposes `tabindex`, `role="region"` and an instruction that
the table can be scrolled horizontally whenever a table width is configured.
That is true before layout measurement and remains true even when the columns
fit without overflow, creating a non-actionable focus stop and misleading assistive
technology output.

## Scope

- derive the scroll-region attributes from the measured overflow state;
- keep the existing arrow controls and keyboard instructions for overflowing
  tables;
- make the governed browser probe require scroll semantics and controls to agree
  at every viewport.

No contract, column, data, permission or business interaction changes.

## Static verification

| Check | Result |
| --- | --- |
| `verify.frontend.collection_view_semantics.unit` | PASS; collection, relation and guard checks |
| `verify.frontend.list_surface_search_contract.unit` | PASS; 26 tests |
| `verify.frontend.primitive_adapter.unit` | PASS; primitive contracts and guard |
| `verify.frontend.typecheck.strict` | PASS |
| `verify.frontend.lint.src` | PASS; zero errors, four pre-existing warnings |
| `ci.local.iteration` | PASS; 6 affected targets with non-zero collection |

The governed browser probe remains pending and must prove that the scroll
region count, arrow controls and measured overflow agree at every viewport.

## Exclusions

- no change to row opening, sorting, selection or pagination;
- no change to column widths or visibility;
- no model/page-specific branch;
- no deployment or broad product acceptance claim.
