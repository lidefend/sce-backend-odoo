# FE-PEC-01A — ListPage Design-System Penetration

## Boundary

- Formal Product Layer: P0 platform kernel product.
- Layer Target: generic frontend `ListPage` cell presentation.
- Module: `frontend/apps/web`.
- Standard vs User-Specific: platform presentation mechanism; no customer-specific rule.
- Why Here: the list consumer already receives formal status and monetary semantics and can delegate their display to existing design-system primitives.
- Why Not Elsewhere: no backend fact, contract schema, business rule, model, role, field-specific branch, or runtime configuration changes are required.
- Blast Radius: desktop flat/grouped list status cells and explicitly monetary body/aggregate cells only. Selection, grouping, sorting, resize, paging, attachment, favorite, and row-open behavior remain unchanged.

## Result

- Raw `<button>` controls in `ListPage.vue`: 0 before, 0 after. Existing page actions already use `ScButton`; batch/group controls remain inside their governed product-list components.
- Migrated presentation paths: 2 — formal status to `ScStatusBadge`; formal monetary facts to `ScMoney` (body and aggregate rows share the same monetary predicate).
- Monetary detection is limited to formal `type`/`dataType=monetary` or `cellRole=money|monetary`; integer, float, and metric values are not inferred as money.
- `ListPage.css` removals: 0. The migration removed no `ListPage` class call sites, so no corresponding rule became unused.
- Behavior changed: NO.

## Evidence

- Initial fingerprint: `/tmp/fe-pec-01a-initial-fingerprint.json`; digest `7d93fecf456faaa1d58c990918910625797aa47cac260658e088570f3aa7caa2`; 7311 paths PASS.
- `make --no-print-directory verify.frontend.dev.incremental FRONTEND_DEV_CHANGED_PATHS='frontend/apps/web/src/pages/ListPage.vue'`: PASS.
- `make --no-print-directory verify.frontend.collection_row_cell.unit verify.frontend.style_system.guard verify.frontend.standard_list_scroll_contract.guard`: PASS; 8 focused tests executed.
- `pnpm run typecheck:strict`: PASS.
- `pnpm run build`: PASS (existing chunk-size advisory only).
