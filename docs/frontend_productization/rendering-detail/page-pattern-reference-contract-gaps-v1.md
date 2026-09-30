# Page Pattern Reference Contract Gaps v1

This ledger records reference details that cannot be implemented safely from the current authoritative payload. They are not permission to infer values in the frontend.

## P0 contract gaps

- Global search: the reference shell exposes a global search control, while the current payload only authorizes navigation filtering. A future capability must identify search domain, target route, result identity, and authority.
- Contextual detail drawer: the current record-entry contract expresses record intent and route disposition, but does not explicitly authorize `standalone_page | contextual_drawer`. Existing `/r` and `/f` semantics must not be reinterpreted by appearance.
- Record actions: copy, delete and their disabled reason are not consistently projected for every
  model/action pair. The explicit labelled detail action part of this bullet is closed; see the
  closed boundary decisions below. Do not re-open it by adding a second row-action field.
- Readonly section metadata: the reference displays section item counts. Contract V2 currently carries nodes and container structure but no authoritative displayed item-count presentation.
- Task slot coverage: the payment task form projects only a subset of the business facts shown by the reference detail. The form-structure producer must explicitly assign the remaining owned fields to task/core/condition/supplementary slots before the task renderer may show them.
- Task field geometry: the real payment task structure currently projects single-column containers whose widgets retain full-span metadata. `CanonicalFormNodeRenderer` correctly preserves those declared columns and spans. A future producer change must derive compact task geometry from the effective action/view structure; the frontend must not reinterpret `span=24` as half-width merely to imitate the reference readonly drawer.

## Closed boundary decisions (no longer gaps)

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

- Saved-search favorites need ownership and mutation capability before the favorite control can be universal.
- The Shell needs a formal user-facing release/version identity if the reference footer version is required.
- Authentication must declare credential-retention policy before a remember-account option stores any identifier.
- Authentication page authority must explicitly declare account-registration/help and alternate-login actions; the reference controls are not safe as hard-coded links.
- Authentication page authority must explicitly declare fullscreen if that reference control is required; the frontend must not render a non-functional icon.
- Collection view-switch and settings controls remain capability-bound; a single-view action must
  not acquire a decorative switch. Export is no longer part of this gap: the sampled list
  contracts now declare `batch_policy.available_actions=["export"]` together with
  `execution_intents.export = api.data` and `execution_operations.export = export_csv`, and the
  selection runtime executes that declared intent.
- Contextual readonly detail header, first-level collaboration tabs, compact relation tabs, description-grid skeleton, and close settlement require the formal contextual-drawer container authority above.

## Evidence gaps

- No authenticated 390px screenshot exists for the reference implementation. Candidate mobile safety can be proven, but mobile visual parity cannot be claimed until the reference evidence is captured.

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
