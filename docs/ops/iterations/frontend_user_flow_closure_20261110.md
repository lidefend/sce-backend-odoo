# Frontend user behavior closure

- Branch: `feature/fe-user-flow-closure-20261110`
- Baseline main: `ddb008826174b8c387bdd0c6a70faf9022586c6b`
- Plan: existing FE-01 through FE-05
- Formal product layer: P0 generic frontend contract consumption

## Baseline reconciliation

- PR #862 merged at `ca032b92dd1131485313b9299b5e799c67f1d525`.
- PR #863 closed the post-merge runtime logger S2 at
  `e56cd8d17fb5d08a62ff0dd2695f2aed06696a11`.
- The branch starts from current main
  `ddb008826174b8c387bdd0c6a70faf9022586c6b`; no old HEAD evidence is treated as
  current without checking its declared inputs.

## Scope order

1. Public capability coverage reconciliation.
2. Payment request representative journey.
3. FE-01/FE-02 state and readout consistency.
4. FE-03 hierarchy and action discoverability.
5. FE-04 handling and failure recovery.
6. FE-05 return and continuation.

## Coverage gap table

This table is populated from existing evidence and production consumers before
any frontend defect is fixed. Verdicts are limited to:

- already fulfilled
- justified variation
- frontend defect
- backend contract gap
- runtime unverified

| Capability | Contract declaration | Shared interpretation | Public consumer | Production entry | User behavior evidence | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Object and readout | `contracts/domain/payment-request.yaml`; runtime V2 field/status contract | `businessValuePresentation.ts`, `fieldSemantics.ts` | `listCellPresentation.ts`, `collectionKanbanPresentation.ts`, `FieldValue.vue`, `ProfessionalBusinessValueControl.vue` | 付款申请 list action 880 / menu 559; record detail/form routes | 24-case value matrix and 8 counterexamples PASS; current list runtime shows 20 rows at 1440/390; same record across list/detail/kanban not yet current-bound | already fulfilled for shared interpretation; runtime unverified for same-record cross-page comparison |
| Form controls | action/page contract + native modifiers; `payment.request` domain state/capabilities | `canonicalFormRenderer.ts`, `formSection.mapper.ts` | `FormSection`, professional base/business/relation/detail controls | 付款申请 create/edit form action 880 | 177 canonical presenter cases, save-failure recovery and relation authority tests PASS; current payment-request save/submit journey not yet current-bound | already fulfilled for shared control projection; runtime unverified for payment-request handling |
| Actions and feedback | `payment.request.available_actions` -> `payment.request.execute`; workflow contract status/action facts | `useRecordActionPresentation.ts`, `professionalWorkflowModel.ts` | `CanonicalActionBar.vue`, `ProductPageHeader.vue`, `ScPopover`, `ScDropdown` | form header, body actions and overflow; payment request observed `save_draft/submit/cancel` | native-action guard 15 tests, row-action identity 16 cases, disabled-reason browser evidence from prior merge; current payment request execution/failure recovery not current-bound | already fulfilled for shared action presentation; runtime unverified for complete handling loop |
| Pages and collections | action/page contract, collection/list profile, field roles | `listCellPresentation.ts`, `collectionViewRuntime` | `ListPage`, `CollectionPattern`, table/card/mobile-row components | 付款申请 list action 880 / menu 559 | 18-state list-surface matrix PASS for normal/batch/empty at six viewports; M7 observed payment list with 20 rows but is bound to earlier `f78a263` and has one separate authority-coverage problem | already fulfilled for shared collection behavior; payment-specific current runtime unverified |
| Navigation and continuity | return identity/target declarations; route authority | `useCollectionViewContextRuntime.ts`, `returnTo` query contract, action origins | `ActionView.vue` consumes collection page/scroll/anchor/focus restore; relation fields consume return contract | list row -> record/form; relation field -> related record; My Work -> payment request | collection semantics covers row identity and context; relation roundtrip restores path/title/status/tabs/actions with 0 errors; payment-list and My Work return chains not current-bound | already fulfilled for shared mechanisms; runtime unverified for the two payment continuation branches |
| Content and accessibility | field/help/rich-text declarations; dialog/overlay contract | `ScRichText`, shared overlay lifecycle, page identity and focus primitives | `ScRichText`, `ScDialog`, `ScDrawer`, shared focus/restore hooks | payment form help, rich content, dialogs and mobile keyboard path | rich-text and page-identity guards PASS; overlay runtime 27 checks PASS; current guard found one stale marker and was corrected without changing product behavior | already fulfilled; the one reconciliation finding was a validation-tool defect |

## Evidence identity decisions

- Current source baseline is main `ddb008826174b8c387bdd0c6a70faf9022586c6b`.
- `.runtime/acceptance-evolution/evidence.v1.json` binds
  `frontend_presentation`, `list_surface_structure` and `relation_roundtrip`
  to `0943095f1f443c50efde735fa8c3ec7c142a54a5`. The governed binding carried
  them to `b05a87d47` only because their declared suite inputs were unchanged.
  They are not a payment-request end-to-end journey by themselves.
- `.runtime/m7-matrix-1440-v3/summary.json` and its 390 counterpart are bound to
  `f78a26322cebea01147d778569480b51a76a44dc`; both have `ok=false` because one
  authority negative case lacks an eligible denied-role candidate. The payment
  request observations remain useful scoped facts, not a current overall PASS.
- Historical `artifacts/frontend-financial-workspace/report.json` and
  `artifacts/frontend-delivery-hardening/report.json` are not present in this
  worktree and are not reused as current evidence.

## Current static reconciliation

- `make verify.frontend.collection_view_semantics.unit` and
  `verify.frontend.professional_business_value.unit`: PASS.
- `make verify.frontend.canonical_form_presenter.unit` and
  `verify.frontend.contract_form_save_failure_recovery.unit`: PASS.
- `make verify.frontend.native_form_action_presentation.unit` and
  `verify.frontend.collection_row_action_identity.unit`: PASS.
- `make verify.frontend.page_identity`: PASS.
- `make verify.frontend.overlay_lifecycle.unit`: repaired validation drift then
  PASS, including the new `box-sizing: border-box` sabotage case.

## First reconciliation finding

`verify.frontend.overlay_lifecycle.unit` exposed a validation-tool drift rather
than a product regression:

- `ScDialog.vue` correctly retains the phone-safe width
  `calc(100vw - 2 * var(--sc-product-page-gutter))` and
  `box-sizing: border-box`;
- the guard still searched for the former inline-style spelling
  `boxSizing: 'border-box'`, so it rejected the shared CSS implementation.

The guard was aligned to the canonical CSS declaration and a focused
content-box sabotage test was added. No product component, width rule or
interaction behavior changed.

## Status

- Coverage reconciliation: completed.
- Current runtime gap: payment request end-to-end and return branches are
  explicitly unverified on the current main identity.
- First code change: overlay lifecycle validation drift only; no product UI
  change was required.
- Mainline integration: current main is the implementation baseline.
- Deployment: not performed.
- Product delivery: not claimed; representative journeys do not constitute all
  89 formal entries.
