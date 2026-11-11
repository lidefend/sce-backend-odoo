# 前端走查列表完整性与移动页签收口（2026-11-11）

## Boundary

- Formal Product Layer: P0 platform kernel product
- Layer Target: shared contract-driven collection rendering and responsive product-shell tabs
- Module: shared list cell, list column sizing, TDesign theme bridge and activity page tabs
- Baseline: `fe2f8ba175a685988a24c26dad08139d81018b30`
- Contract, ACL, backend business logic, customer modules, database writes and deployment are excluded

## Findings Bound To This Batch

- P1: project-ledger primary identity is clipped on both sides with no wrapper title.
- P2: list headers can break a two-character term into separate lines.
- P2: 390px activity tabs are clipped beside the TDesign arrow control and close targets are too small.
- P3: list cell containment must keep business identity to two lines so secondary facts do not expand rows without bound.
- Observation: collapsing the active navigation path is immediately undone by the active-path expansion effect.

## Decisions

- The collection cell owns two-line identity containment; the TDesign theme bridge may not force it back to one line.
- Primary identity keeps the complete value on the declared title and aria-label fallback.
- Header width includes the label plus the TDesign header-control reserve, and the label remains single-line.
- Mobile activity tabs use native horizontal scrolling and 44px controls; the vendor pager arrow is hidden in that viewport.
- Navigation expansion state remains persisted presentation state; active-path expansion runs only when the active path changes.
- P3 follows the two-line/secondary-collapse option: payment and other business identities are bounded at two lines and no
  separate compact-density switch is introduced in this batch.

## Runtime Diagnosis

Read-only observation used the existing daily runtime at `http://1.95.85.92:18081/t/demo`
(`sc_demo`, `wutao`, served `fe2f8ba17`). No write action was performed.

- Before the fix, the primary link occupied `192px`, while TDesign's internal `.t-button__text` remained `216px`
  wide and was centered. Its range started at `x=376` inside a link starting at `x=388`, so both ends were clipped.
- The collection theme bridge additionally forced `.collection-row-cell` to `white-space: nowrap`.
- Test-only injection of the candidate CSS moved the text range to the link's full `192px` content box
  (`x=388..580`) and retained the exact `title`/`aria-label` full value.
- With four activity tabs at 390px, test-only injection produced `clientWidth=390`, `scrollWidth=574`,
  `overflow-x:auto`, no vendor arrow, 44px tab controls and 44px close controls.

## Validation

- `make ci.local.iteration`: PASS, 13 required incremental targets, receipt
  `.runtime/frontend-dev-validation/executions/20261111T023002Z-3123216-258463872/receipt.json`.
- `make verify.frontend.lint.src`: PASS, 0 errors; the existing `StatusPanel.vue` warning remains.
- `make verify.frontend.typecheck.strict`: PASS.
- `make verify.frontend.build FRONTEND_DIST_DIR=frontend/apps/web/dist-dev`: PASS.
- `make verify.frontend.collection_row_cell.unit`: PASS, 9 tests.
- `make verify.frontend.navigation_shell.unit`: PASS, including the new narrow-tab and active-path collapse checks.
- `make verify.frontend.list_optional_columns.unit`: PASS, including the single-line header-width assertion.
- `make verify.frontend.list_surface_search_contract.unit`: PASS, 23 tests.
- `make verify.frontend.text_containment.guard`: PASS.
- `make verify.frontend.style_system.guard` / `verify.frontend.standard_list_scroll_contract.guard`: PASS.
- `make verify.frontend.contract_basis.unit verify.frontend.contract_basis.enforce`: PASS, open defects 0.

The browser structure probe was extended but was not run against the candidate deployment because this task did not
authorize a deployment. Its first/last-character detector is locked by
`verify.frontend.list_surface_search_contract.unit`; the affected runtime lane remains pending on the deployed candidate.

The browser suite correctly remains `affected` while its product inputs are uncommitted. That is expected until an
exact clean candidate is frozen; it does not invalidate the passing local incremental checks above.
