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
| Object and readout | `contracts/domain/payment-request.yaml`; runtime V2 field/status contract | `businessValuePresentation.ts`, `fieldSemantics.ts` | `listCellPresentation.ts`, `collectionKanbanPresentation.ts`, `FieldValue.vue`, `ProfessionalBusinessValueControl.vue` | 付款申请 list action 880 / menu 559; record detail/form routes | 24-case value matrix and 8 counterexamples PASS; current `FE-JOURNEY-APPROVAL-001` retains identity and `¥20.00` from the My Work card through the approval summary to the approved detail without divergence | already fulfilled for the selected record across My Work collection/action summary/detail; business-list and kanban renderer branches remain runtime-unverified |
| Form controls | action/page contract + native modifiers; `payment.request` domain state/capabilities | `canonicalFormRenderer.ts`, `formSection.mapper.ts` | `FormSection`, professional base/business/relation/detail controls | 付款申请 edit form action 881 / menu 560 | current `FE-DELIVERY-HARDENING-001` introduced two settlement lines, inline-edited 200→150, persisted/read back 150, then restored 0 rows / 20.00; 177 canonical presenter and save-recovery cases PASS | already fulfilled |
| Actions and feedback | `payment.request.available_actions` -> `payment.request.execute`; workflow contract status/action facts | `useRecordActionPresentation.ts`, `professionalWorkflowModel.ts` | `CanonicalActionBar.vue`, `ProductPageHeader.vue`, `ScPopover`, `ScDropdown` | form header/body/overflow and My Work 提交/批准 actions | current My Work J07 submitted `FE-JOURNEY-PAYMENT-001`; J08 reviewer approved `FE-JOURNEY-APPROVAL-001`; missing reject reason left data unchanged; 390/1440 responsive and project-member isolation PASS | already fulfilled |
| Pages and collections | action/page contract, collection/list profile, field roles | `listCellPresentation.ts`, `collectionViewRuntime` | `ListPage`, `CollectionPattern`, table/card/mobile-row components | 付款申请 list action 880 / menu 559 | current generic list matrix is 18/18 PASS at six viewports; current payment-specific browser begins at its declared record rather than traversing the list, while M7 payment-list observation is from earlier `f78a263` | runtime unverified for the current payment list-entry branch |
| Navigation and continuity | return identity/target declarations; route authority | `useCollectionViewContextRuntime.ts`, return query contract, action origins | `ActionView.vue` collection restoration; My Work detail return; relation return contract | My Work -> payment request -> My Work; relation field -> target -> source | current My Work J07 returns from payment detail and continues acting; current relation roundtrip restores path/title/status/tabs/actions with 0 denied/console errors; direct payment-list return remains in the unverified list-entry branch | already fulfilled for My Work and relation continuity; current payment-list return remains runtime unverified |
| Content and accessibility | field/help/rich-text declarations; dialog/overlay contract | `ScRichText`, shared overlay lifecycle, page identity and focus primitives | `ScRichText`, `ScDialog`, `ScDrawer`, shared focus/restore hooks | payment form help, rich content, dialogs and mobile keyboard path | rich-text and page-identity guards PASS; overlay runtime 27 checks PASS; current My Work confirmation focus and 390 keyboard/overflow checks PASS; the one guard failure was a stale validation marker, not product behavior | already fulfilled |

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

## Current-bound runtime evidence

The shared production frontend tree was built at
`7895f97569e1b9f74ecd2ee50eec9c386b647640`. The payment detail run served
that revision. After the My Work browser assertions changed in test-only commit
`60e6bbc749b6d3bd25bbc3af728d6f3e7dd5eb41`, the backend served the new commit
while the preview reported `preview_base_sha=7895f9756` and an unchanged entry
digest, proving that no production frontend source changed. All evidence used
database `sc_frontend_acceptance`.

| Evidence | Result | Artifact |
| --- | --- | --- |
| Payment request detail collection | PASS: two settlement lines, inline edit 200→150, authoritative readback 150, restored to 0 rows / amount 20.00, 0 problems | `.runtime/final-acceptance/payment-request/7895f97569e1/report.json`, SHA-256 `101d8d4ecf82becd1b9b94c4f08d746c74f4755a3709234be9789f7c3baee3b0` |
| My Work payment handling | PASS: J07 submit and return, J08 approval, same `FE-JOURNEY-APPROVAL-001` identity and `¥20.00` readout on work card, approval summary and approved detail, role worklist update, reject-without-reason safety, company A/B/A isolation, project-member isolation; 1440/1280/390 PASS | `.runtime/final-acceptance/my-work-approval/report.json`, SHA-256 `3f53f7e59c2a512216bd97a20b73ccfead1f64725b3eb859543f17a7cb4a43c8` |
| Page presentation | PASS: one governed target, 0 mutations, 0 errors | `.runtime/final-acceptance/frontend-presentation/header.json`, SHA-256 `4fdc77be3e306d8c296e86a6858c016d8ce4a20dd19f6242d09dd141d5a54699` |
| List structure | PASS: full 18-state matrix, 0 failures | `.runtime/final-acceptance/list-surface-structure.json`, SHA-256 `196d712b6eb0ff6688744a5262abe0e273e4ef69eca9ce65da33884fb9e079b9` |
| Relation roundtrip | PASS: 13 declared entries, 3 opened, 0 blocking differences, 0 denied requests, 0 console errors | `.runtime/acceptance/local/7895f97569e1b9f74ecd2ee50eec9c386b647640/relation-roundtrip/20261110T043334859Z-2668058-15d8a8b1/summary.json`, SHA-256 `2d6d24dcb000a3bc0a0cb705b4b163d67d19ea0df3ca7221ece88f2f48f4d000` |

The acceptance-evolution manifest was re-recorded at the same head for
`frontend_presentation`, `list_surface_structure` and `relation_roundtrip`.

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

## FE-03 page hierarchy and action entry

| Surface | Result | Evidence |
| --- | --- | --- |
| Ordinary collection | fulfilled | Current list matrix 18/18 across 1440/1024/768/521/520/390; row identity and responsive components pass static locks |
| Readonly form | fulfilled | Current approved payment detail keeps identity/status/amount; page identity and financial workspace presentation pass |
| Edit form | fulfilled | Current payment detail collection edit/save/readback and My Work submit path pass |
| Action entry | fulfilled for represented pages | Header/body/My Work actions pass; native action guard has 15 cases and row action identity 16 cases |
| 390 action/accessibility | fulfilled | My Work keyboard path, confirmation focus, 390 wrap and no-overflow checks pass |
| Hierarchical worksheet | runtime unverified | 24 policy tests, 15 keyboard interaction cases and 10 load-stage cases PASS; full browser lane was blocked by a foreign process owning acceptance port 5175, not by a product assertion |

The full delivery-hardening lane was not claimed as a pass. Its login probe
returned 401 because the acceptance frontend port belongs to another worktree;
the process was preserved and the standard acceptance preview on 5180 remained
available. No product code was changed in response.

## FE-04 handling and failure recovery

| Scenario | Result | Evidence |
| --- | --- | --- |
| Edit and save | fulfilled | Current payment detail collection: 200→150, persisted, re-read and restored |
| Submit | fulfilled | Current My Work flow moved the draft to submit and reloaded authoritative state |
| Approve | fulfilled | Current reviewer action moved the item, refreshed count and exposed approved state |
| Invalid reject | fulfilled | Missing reason left business data unchanged |
| Request in progress / duplicate submit | static PASS | Save recovery/single-flight lifecycle tests pass; no second business mutation observed in current My Work run |
| Network / conflict / expired session | not currently run | Existing delivery-hardening J09 lane is complete but was blocked by another worktree owning port 5175; not a product failure |

No second frontend business state machine was introduced.

## FE-05 return and continuation

| Path | Result |
| --- | --- |
| My Work → payment detail → My Work | PASS: current browser returns to the worklist and continues approval/company actions |
| Relation field → target → source | PASS: path, title, statusbar, tabs and actions restored; no denied requests or console errors |
| Company/role context | PASS: A/B/A and project-member isolation |
| Direct payment business list → detail → list | runtime unverified |
| Same-record payment kanban → detail → kanban | runtime unverified |

## Status

- Coverage reconciliation: completed.
- Current runtime gap: the direct payment business-list entry/return and
  same-record kanban branches remain unverified. Payment detail
  edit/save/readback, My Work submission/approval, same-record amount readout,
  role isolation and My Work/relation return are current-bound and PASS.
- FE-03: ordinary/readonly/edit/action/mobile surfaces have current or static
  evidence; hierarchical runtime remains blocked by the external port owner.
- FE-04: normal handling, save/readback, submit/approval/reject safety are
  current-bound; network/409 recovery remains covered statically but not by the
  current full browser lane.
- FE-05: My Work and relation continuity are current-bound; direct business-list
  and kanban continuity remain explicitly unverified.
- Confirmed frontend product defects in this batch: 0.
- Fixed validation evidence defects: stale overlay geometry marker; missing
  same-record My Work/detail amount assertion.
- First code change: overlay lifecycle validation drift only; no product UI
  change was required.
- Mainline integration: current main is the implementation baseline.
- Deployment: not performed.
- Product delivery: not claimed; representative journeys do not constitute all
  89 formal entries.
