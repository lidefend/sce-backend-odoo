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

- Owner decision53.19 requires approval consistency for ALL business documents, not only payment. Existing configuration selection, tier-runtime support and workflow profiles represent different implementation scopes; none is a whitelist that can silently redefine the required product coverage. Reuse the existing state machine/policy/tier mechanism and responsibility records; missing necessary configuration or execution support remains a product gap. Payment submission/decision/rejection implementation and pure tests are partial evidence only; module upgrade and real runtime validation remain pending.

- Native state-action projection remains a product gap (segment53.15), not an ops cleanup or an indefinite authority-side exception. `sc.general.contract.action_signed` now binds the existing workflow completion action in draft/confirmed, retaining the original business method and native authorization. Runtime proof remains pending. Plan start and document reset declarations are added in segment53.16, with runtime verification pending. Payment approval is unified in segment53.18 at the execution and native/contract entry levels; runtime verification remains pending. The remaining registered transition is payment reversal. The coverage guard currently unions method names across models and can undercount gaps; model-bound verification is required before claiming complete coverage. Track closure in existing `detail.action-state`; do not infer actions in the frontend.

- Saved-search control projection is closed in segment 53.2: the shared collection menu consumes explicit save/shared grants and execution intent; missing grants never enable writes. Successful save, refresh, failure feedback and product deletion/restoration subsequently passed in segment53.14; the earlier pending lifecycle is closed.
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


## Segment 53.14: saved-search product lifecycle closed

The53.10 gap is closed by product implementation and real operation, not cleanup tooling. P0 projects per-filter `search.favorite.delete` actions with explicit `filter_id`/model/action identity and enforces current ownership plus native ACL/rules without elevation. The shared official menu and dialog provide confirmation, cancellation, pending protection and failure feedback. Successful deletion is distinguished from subsequent refresh failure.

Runtime reports `tpl07-1790769636566/report.json` (25 assertions) and `tpl07-1790769758359/report.json` (24 assertions) bind their original successful save/readback reports. Private filters9 and10 were deleted through product UI, authoritative reads returned empty and reloads retained restoration. Deleting the selected favorite also cleared `saved_filter` route state. Narrow-screen confirmation was inspected. These are saved-search lifecycle results, not the older TPL05A49-case payment journey. The67 reference rows are again resolved; whole-goal completion still requires the original-scope audit and relevant mandatory gates.


## Segment 53.20: model-bound native action coverage

The coverage guard now matches `(model, method)`, preventing declarations on another model from masking product gaps. The existing native-action registry now explicitly records four unresolved state actions: payment execution reversal, contract-event rejection, expense approval and settlement approval. Registration is visibility, not completion or an exemption from the owner's all-business-document approval rule. The shared approval runtime integration and affected native/effective entries remain necessary P1 work; `detail.action-state` stays open.


## Segment 53.23: duplicate native approval entries retired in source

Expense (two forms) and settlement (one form) now retain only the same tier approval/rejection entries declared by their workflow profiles. The redundant post-review `action_approve` buttons are removed; compatibility methods remain instance-bound from53.22. Their native-action registrations are therefore retired. Two registered state-action gaps remain (contract-event rejection and payment-execution reversal). Module upgrade/runtime verification and all-document approval adoption remain open; this is not overall closure.

### Segment53.39 — Payment reversal projection aligned; runtime acceptance pending

The payment-execution workflow profile now follows the existing domain contract and native actions: draft permits submission/cancellation, confirmed permits payment/cancellation, and paid permits only the distinct `action_reverse_payment` command. The reversal action uses its own key/label/method; `cancel_record` describes the resulting cancelled record, not permission to call pre-payment `action_cancel`. The model still owns finance authorization, mandatory reversal reason, ledger reversal and `cancellation_kind=payment_reversed`. No approval or ledger execution is moved into the frontend.

The resolved undeclared-action registration is removed, leaving contract-event rejection as the single registered state-action gap. Offline projection/semantics tests pass; effective runtime/browser reversal verification remains pending. All-document approval adoption and `detail.action-state` remain open.

### Segment53.40 — Contract-event shared approval implemented; upgrade/runtime pending

Contract events now participate in approval configuration, company-scoped shared submission, OCA reviews and outcome-bound callbacks. Native and workflow actions use the same real reviewer decisions; rejected events can resubmit and approved events can complete separately. The old direct approval/rejection UI path is removed. The final registered undeclared state-action entry is retired, leaving26 helper/navigation registrations. This is source-level closure of that registry only: module upgrade, real contract-event approval/rejection/resubmission and necessary document coverage beyond the old configuration/support lists remain product work. `detail.action-state` remains open.

### Segment53.41 — Contract-event ORM approval loop verified

Governed module upgrade and backend reload succeeded at b985a026b. The existing rollback-only approval smoke now passes17 checks, including five contract-event checks: no-configuration auto-approval without completion, real configured review creation, real approval plus explicit completion, rejection reason, and resubmission with a new review chain. Configuration restoration and absence of temporary records were verified. Final UI-contract/browser consumption, distinct reviewer roles and all necessary document coverage remain unproven; this does not close `detail.action-state`.

### Segment53.42 — Payment reversal page verified; event page lacks scoped record

Finance record186 (`paid`) passes16 browser assertions on the unchanged official preview: effective contract binds reversal to `action_reverse_payment`, the detail shows exactly one reversal entry and no pre-payment cancel/payment entries; both viewports remain usable, with no script errors or writes. This verifies presentation, not financial reversal execution. Contract-operator lookup returns no contract events in its authorized company8 scope, so event browser acceptance remains pending. Neither an empty authorized query nor the previous transaction-local ORM test proves that page accepted.

### Segment53.44 — Native reversal confirmation consumed by shared dialog

Native payment reversal now explicitly declares its ledger/request consequences. The existing parser publishes danger/requires_confirm; the unchanged official frontend opens the shared confirmation dialog with the exact contract message. Governed browser19 assertions pass on existing paid186, including cancelling with zero business requests. This closes the missing confirmation declaration/interaction, not financial reversal execution or all-document approval coverage.

### Segment53.45 — Plan state visibility corrected; approval adoption still required

The native plan form now permits completion only in `in_progress`, reset only in `cancel`, and cancellation only in `draft/confirmed/in_progress`, matching existing model methods and workflow projection. A focused test executes all five model transitions and compares native/profile availability across all five states plus an unknown state. XML runtime loading is pending the next consolidated upgrade. `sc.plan` still lacks configured shared approval and must be adopted; this visibility correction does not close that product gap.

### Segment53.46 — Plan approval adoption implemented; runtime pending

`sc.plan` now uses the existing shared policy and native review mechanism. Configured confirmation waits in draft with native approval status; no configuration confirms after schedule checks. Real validated callbacks confirm without starting execution. Start/completion remain separate, retain scheduling/node checks and require confirmed approval facts. Native/profile reviewer actions are aligned and rejection comments retained.52 approval,37 native and15 semantics tests pass. Module upgrade and real plan approval/rejection/resubmission remain pending; overall document coverage is not complete.

### Segment53.47 — Plan real approval loop verified

Governed module upgrade/backend reload at478215ca4 succeeded. The existing rollback approval smoke passes22 checks including five plan cases: automatic confirmation without execution, pending-review start denial, actual reviewer approval followed by explicit start/completion, rejection reason, and new-chain resubmission. Original configuration readback and temporary-record removal pass. Plan browser consumption and broader document coverage remain pending. The adjacent existing `sc.construction.diary` profile/model still has direct confirmation/completion without shared approval and remains necessary product work.

### Segment53.48 — Construction diary shared approval implemented

Construction diary now participates in company-scoped shared approval configuration and native review callbacks. Confirmation retains content validation; configured review waits in draft, no configuration confirms. Completion requires confirmed approval and remains independent. Native/profile actions align, including removing draft completion and the invalid done-state cancel entry.53 approval,38 native and15 semantics tests pass. Module upgrade and real diary runtime acceptance remain pending; overall approval coverage and `detail.action-state` remain open.

### Segment53.49 — Construction diary real approval loop verified

Governed upgrade/reload atcbd60bd63 succeeded. The existing rollback smoke passes27 checks including five diary cases: no-configuration confirmation without completion, pending approval blocks completion, real reviewer approval before explicit completion, rejection reason, and new-chain resubmission. Baseline policy/step readback and temporary-record absence were verified. PM-role end-to-end permissions, effective page/browser consumption and full document coverage remain open.

### Segment53.50 — New plan/diary page blockers confirmed

PM authorized-company8 queries for existing plans/diaries are empty, so record-detail acceptance remains pending. Separately opening unsaved create forms exposed real failures: plan receives a create-enabled contract but renders the official form in error with a network message; diary rejects its V2 snapshot because layout container children leak unsupported `field_info`. These are not passed browser checks and cannot be covered by27 ORM tests. Keep `detail.action-state` and affected form/contract delivery open; repair the producer for the diary and identify the failing plan request before downstream page acceptance. No business writes occurred.

### Segment53.51 — Plan create passes; diary postprocessor remains incompatible

Plan create failure was a P4 probe bug: read-only `default_get` was intercepted. Corrected probe passes12 create-form assertions with unchanged frontend/backend product inputs. Diary `field_info` leakage originated in P1 postprocessing, not the P0 assembler; the alias is fixed and39 focused tests pass. Runtime still rejects additional fields that the same postprocessor injects into runtime/meta and reports missing fields referenced by form structure. Retire/align the redundant diary layout rewrite with the native/configured contract; do not relax schema. Diary create remains failed, and existing-record acceptance remains pending scoped data.

### Segment53.52 — Diary duplicate layout retired; create page passes

Removed the diary-specific post-finalization layout rewrite and its wrapper/call. Native/configured layout and form structure now remain authoritative; no schema relaxation or frontend model exception.39 focused tests and the updated normalizer guard pass. Backend30ca72d76 renders the official diary create form successfully:12 browser assertions, both viewports, no errors/writes;31 field nodes retain name, periods, attachment, description and rejection fields previously lost. Diary create blockers from53.50/51 are closed. Existing-record handling/permissions and overall document coverage remain pending; do not close the entire action-state row.

### Segment53.53 — Tax deduction requires confirmation; approval adoption pending

Tax deduction model, native view and workflow profile now allow actual deduction only from `confirmed`; draft completion is removed. Finance access, amount/date preparation, readiness, responsibility checks, authoritative write and audit remain intact.40 focused tests pass; runtime loading awaits consolidated upgrade. Shared approval adoption remains required, including resolving amount preparation before threshold-based approval because current default deduction amounts are populated only at execution. This state-boundary fix is not approval completion.


### Segment53.60 — Shared approval reaches tax, tasks and project initiation; page and amount gaps remain

Subsequent53.54–53.60 work closes the tax approval adapter gap recorded above: invoice-derived amounts are prepared before matching tier thresholds; approval does not deduct. Tasks use sc_state and approval only reaches ready; starting remains explicit. Projects now use sc_approval_state independently from lifecycle_state; central lifecycle guards reject unapproved draft start/pause bypasses, while existing active-project lifecycle handling remains unchanged. Backend4a3e08ffa passes45 real rollback-scoped approval checks, including tax7, task5 and project6; configuration restoration and temporary-record absence are verified in the living batch record.

Project native forms separate submission, real reviewer decisions and start. Effective project action/state consumption and official-page behavior are not yet proven; the central workflow profile does not yet cover project.project, so existing native-profile guard success is not project coverage. Task create12 passes on frontendfed2dfcc2, but existing task detail/blocked execution journeys still lack an authorized record. The shared scene executor now consumes explicit blocked business outcomes rather than displaying completion; this is not a substitute for that missing journey.

**P1/P3 product gap:** project approval has no declared business amount authority. A contract total or budget must not be guessed as the approval amount. Shared policy compilation now rejects amount bounds on models without an amount mapping instead of silently ignoring them. A governed business amount declaration/configuration and its threshold/runtime proof are still required for those conditions. Ordinary unbounded project approvals are supported. Track all remaining work in existing `detail.action-state`; support registries and the45 checks do not bound or complete the all-business-document scope.
