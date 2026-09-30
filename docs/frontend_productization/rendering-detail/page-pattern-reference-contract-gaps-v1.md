# Page Pattern Reference Contract Gaps v1

This ledger records reference details that cannot be implemented safely from the current authoritative payload. They are not permission to infer values in the frontend.

## P0 contract gaps


## Closed boundary decisions (no longer gaps)

- Readonly section metadata: the daily-snapshot reference printed an item count on the section
  heading line, and the earlier wording here asked Contract V2 to carry a displayed item-count
  presentation field. That wording is superseded and must not be re-opened. The authoritative detail
  composition is the official TDesign Starter (`detail/base`, `detail/advanced` at
  `aeed57076217f7777158b905f353d73585bad1c4`), whose section title is the card head only: the rendered
  `t-card__header` has `border-bottom: 0px`, and its `#actions` slot carries controls (quarter/month
  switch), never a count. An item count is a presentation derivation of the facts the section already
  renders, so it is neither a contract obligation nor something the frontend may fail a section for
  omitting. The dataset contract, the section nodes and the container structure stay exactly as they
  are; see `detail.section-heading` in
  `docs/frontend_productization/rendering-detail/page-pattern-reference-detail-ledger-v1.json`.

These were previously listed here. They are kept so the superseded wording is not reintroduced;
they are not producer-side gaps and must not be re-opened by adding the value to the contract.

- Collection row detail action: row activation is declared by the owning contract as
  `sourceWidgetId == "page.row"` on the action rule, carrying a non-empty label. Every sampled
  list contract declared it, so the earlier wording that collections declare "row activation"
  without an explicit labelled detail action is superseded. The frontend navigation runtime must
  resolve row activation from that declared placement only; `targetScope` is not a row signal,
  because `normalize_target_scope` collapses header/toolbar/smart/row placement into the closed V2
  target-scope vocabulary and therefore lets a header action masquerade as the row action.
  `scripts/verify/web_unified_page_contract_v2_guard.py` pins this rule and
  `frontend/apps/web/scripts/collection_row_action_identity_test.ts` proves the row click cannot
  inherit a header action's target.
- Collection export capability: `layoutContract.listProfile.batch_policy` and
  `actionContract.surfacePolicies.batch_policy` declare the export capability, its intent and its
  operation, so the collection toolbar is entitled to render the export control. Nothing about the
  capability may be inferred in the frontend when a contract omits it.
- Collection semantic tones: a status badge colour is a presentation decision, so it is owned by the
  frontend presentation layer and never by the business contract. No contract layer and no model
  profile declares a status-to-tone map, and the kernel does not supply one; the frontend resolves the
  tone from the authoritative status *value* (`frontend/apps/web/src/app/presentation/collectionStatusPresentation.ts`),
  so a localised label can never act as a colour authority. `scripts/verify/contract_governance_list_surface_split_guard.py`
  pins this in both directions (no tone in the list surface or profiles, and no frontend read of a contract tone).
  Which tone a declared state carries is therefore not a contract obligation at all.

## P1/P2 product gaps

- Saved-search control projection is closed in segment 53.2: the shared collection menu consumes explicit save/shared grants and execution intent; missing grants never enable writes. Successful save, refresh, failure feedback and recovery remain a separate interaction closure, not proven by opening and cancelling the form.
- Collection view-switch and settings controls remain capability-bound; a single-view action must
  not acquire a decorative switch. Export is no longer part of this gap: the sampled list
  contracts now declare `batch_policy.available_actions=["export"]` together with
  `execution_intents.export = api.data` and `execution_operations.export = export_csv`, and the
  selection runtime executes that declared intent.

## Official template baseline

The authoritative Web rendering and interaction baseline is the official TDesign Starter
(`Tencent/tdesign-vue-next-starter`), not the 2026-08-26 daily frontend snapshot that the original
reference screenshots were captured from. That snapshot stays a historical presentation reference
only: it is our own pre-adoption frontend (`referenceKind: daily-frontend-source-snapshot`, zero
`t-*` usages, `@sc/ui` as its only UI dependency), which is why some of its reference details have no
official counterpart.

Evidence: a local render of the official commit `aeed57076217f7777158b905f353d73585bad1c4`
(dev server against the shipped mock data, viewports 1440x900 and 390x844) held off-repo in
`sce-offrepo/artifacts/official-starter-reference/`. The official shell keeps a desktop minimum
width: at 390x844 it reports `scrollWidth - clientWidth = 434`, so the narrow-screen layout stays our
own adaptation and is not an official-sample debt.

## Evidence gaps

- The former missing-390px-reference claim is closed: official list/base, detail/base, detail/advanced and form/base screenshots already exist at both 1440x900 and 390x844 in `sce-offrepo/artifacts/official-starter-reference/`. The official sample preserves a desktop minimum width, so mobile pixel parity is not a requirement; candidate navigation, containment and action usability remain product responsibilities.
- Segment 52 verifies shared token resolution, typography and representative dual-viewport rendering. It does not close the capability gaps above or establish overall product delivery.

## Ownership enforcement

Every contract gap also carries an authoritative `owner` and the `followUp` target that closes it in
`page-pattern-reference-detail-ledger-v1.json`. That pairing is not advisory: `make
verify.frontend.page_pattern_reference_parity.unit` runs
`scripts/verify/page_pattern_reference_ledger_guard.py`, which fails when a contract gap names no
P0-P4 or evidence owner, states no follow-up, drops its authority, or when a `needs_work` item
survives in a ledger declared complete.

## Fail-closed rules

- Missing capability hides or disables the control; query parameters never create authority.
- No model, action, menu, field label, or Chinese-text special case may substitute for a missing contract field.
- A legacy route cannot silently become drawer authority.
- Visual similarity cannot override readonly/edit, action, mutation, or record-level permission decisions.


## Segment 53.5: readonly-detail reference correction

The superseded contextual-drawer dependencies came from the historical daily frontend
snapshot. They are superseded by the pinned official `detail/base/index.vue` and
`detail/advanced/index.vue`, which use standalone Card/Descriptions pages. A drawer contract,
forced first/second-level tabs and drawer skeleton geometry are therefore not prerequisites
for official takeover. The existing shared readonly composition and contract-declared fields,
notebooks, relations, collaboration and return context remain authoritative. This correction
does not close `detail.action-state`: declared denial feedback and executable record actions
are tracked separately. Existing segment52 runtime evidence is reused; no new business
capability is inferred from either reference.


## Segment 53.6: public authentication and shell disposition

Runtime version was already produced by `system.init`; the missing shared-footer consumer is
implemented. Public activation/recovery actions likewise already exist and are consumed;
they are not producer gaps. Current live checks bind the visible heading, actions and product
version to those authorities.

The pinned official login Header has no fullscreen action. Its remember checkbox has no
bound persistence behavior, and its shell Search component only controls focus/text without
querying results. These demo/reference details do not authorize new credential retention,
SMS/QR/third-party authentication or cross-model business search. They are marked not
applicable for this rendering takeover; any separately confirmed feature must declare its
own security/query/execution contract before controls are offered. Existing login, activation,
recovery and authorized menu-search responsibilities remain required and covered by their
existing evidence. No backend or account writes were performed in this batch.

## Segment 53.7: live task authority replaces stale slot assumptions

The existing payment action775/view2145 now returns `container_tree_authority`, an effective native field tree and intentionally empty retired `slots`. Its published configuration and native semantic anchors already provide the business structure. The 1440/390 browser probe verifies actual project/partner field positions: two columns on desktop, one column on narrow screens. No contract/layout rewrite is needed for `task.field-grid`.

`task.slot-coverage` remains open as a responsibility-level coverage check, not a request to revive slots. Compare required facts and their native/display aliases, conditional visibility, notebook and relation responsibilities before claiming closure. The scoped report `tpl07-1790768273395/report.json` proves the current authority and geometry, not all business coverage.

## Segment 53.9: remaining reference responsibilities resolved

Task coverage now follows the existing P1 matrix and effective native tree, not obsolete slots. Report `tpl07-1790768656354/report.json` has43 passing assertions: required inputs, contract/settlement conditional fields, attachment, payment-record relation, historical readonly fact, return, and responsive layout. Earlier business-write journeys remain their own unchanged evidence; this closes the reference projection gap without promoting the formal business matrix.

Record-copy disposition: `effectiveRecordCapabilities.duplicate` is derived from access rights. Current payment `actionRuleList` declares save, workflow and relation actions but no copy execution; the P1 matrix and pinned official detail compositions do not require a copy journey. Do not invent that business feature from a capability boolean. Declared edit/delete denial feedback was verified in53.5. This resolves the former open scope decision; it is not a claim that copying records has been implemented.

The67-entry reference ledger has no open items. Overall completion remains unproven: planned saved-search success/refresh/restoration, outstanding required gates and the full goal completion audit retain their own obligations.


## Segment 53.10: owner-confirmed saved-search product gap

The saved-search product currently exposes save but lacks a deletion/management entry. This is a P0 product gap, not merely an acceptance cleanup problem. Reopen `collection.favorite` in the existing67-entry ledger. Prior save-control, failure-feedback and cache-refresh results remain scoped evidence.

Required closure: explicit per-filter deletion authority and executable binding, backend ownership/ACL enforcement, shared official-menu consumption, confirmation and success/failure feedback, followed by actual save→refresh→delete→authoritative refresh verification. An operational cleanup cannot satisfy those responsibilities. The proposed temporary P4 restore tool was withdrawn before any lifecycle configuration write or database operation.
