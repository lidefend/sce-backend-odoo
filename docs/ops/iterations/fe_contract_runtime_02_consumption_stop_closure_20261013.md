# Frontend contract consumption stop-closure: T1–T9 (P0 runtime + P4 verification)

Run: `.agent/runs/FE-CONTRACT-RUNTIME-02/run.json`
Branch: `fix/fe-contract-runtime-02-consumption-stop-closure`
Baseline: `e4b8fd957e364a4d1749127d563398c8de80256d` (`main` == `origin/main`)
Date: 2026-10-13

## Purpose

Owner-directed read-only audit (bound `669902012f9d`, a child of `0f13a238`) concluded
that the official-component and page-composition main return is **done**, but
"rendering and interaction full closure" is **not** complete. Nine confirmed gaps remain;
this goal closes the six consumption gaps (T1–T6) with declaration-first stop semantics,
registers them in the contract-basis ledger/guard (T7), corrects the evidence reuse
identity (T8), and re-binds evidence through the single `evidence_scope` authority (T9).

The governing rule is unchanged and is the point of this batch: the frontend may only
render and interact; every missing or invalid declaration must **stop** the surface
through `ContractGapError` instead of being defaulted, guessed or silently dropped.

## Confirmed gaps (audit-verified at the audit binding)

| ID | Gap | Owner layer | Target |
|---|---|---|---|
| T1 | Create form hides fields whose name/label ends with 状态, overriding contract visibility (`pages/contractForm/nativeLayoutUtils.ts` `isCreateWorkflowStateField`) | P0 consumer | remove name/label inference; consume an explicit create-visibility declaration |
| T2 | Missing layout `span` decoded as `24` (`app/contracts/v2/schema.ts`); invalid span rendered full-width (`components/template/layoutSpan.ts`) | P0 declaration + consumer | declare which nodes must carry a span, fill producers, then remove the consumer fallback |
| T3 | Numeric stop primitive coerces `true`→`1` and truncates `1.9`→`1` (`app/contract/contractGap.ts` `requireDeclaredNumber`/`requireDeclaredNumberList`) | P0 mechanism | strict type/integer/range validation; never mutate the declared value |
| T4 | Collection capabilities default a missing `actions` to `[]`; items missing `action/scope` are dropped (`app/runtime/actionViewCollectionCapabilityRuntime.ts`) | P0 action consumer | distinguish a legal empty set from an illegal declaration; the latter stops |
| T5 | Record entry downgrades an illegal intent and a missing write authority to read-only; `auth=none/read/admin` merged (`app/runtime/recordEntryContract.ts`) | P0 contract semantics + consumer | explicit permission enum; separate "explicitly forbidden" from "declaration missing" |
| T6 | Master-detail relation pagination fixed at `20` by the frontend (`components/template/X2RelationRenderer.vue`) | P0 relation contract + consumer | consume the relation pagination declaration; remove the second parameter source |
| T7 | Contract-basis guard scans three pagination/limit regexes only; strings/tests do not prove visibility/action/permission correctness (`scripts/verify/frontend_contract_basis_guard.py`) | P4 tooling | register T1–T6 in the ledger, add consumption counter-examples, state the guard's coverage boundary |
| T8 | Evidence reuse identity lacks actual company/permission context readback and folds the whole bundle into every entry key (`scripts/verify/business_entry_matrix_model.mjs`) | P4 evidence | add the authoritative context readback; invalidate per unit's real dependency |
| T9 | Some template-ledger paths are shadowed by other reports; the latest 89-entry result is not aligned with the default reuse ledger; `.runtime/final-acceptance/list-surface-structure.json` is 12 create/edit checks with the list gated at 0, i.e. a mis-bound artifact | P4 acceptance | recover the original evidence, correct the index, reuse the approval binding, then patch only affected keys |

## Execution order (owner-set, not reordered)

1. **Fix mechanisms first (T1–T6)** in declaration → decode → consume order; each item runs
   only its owning layer's non-zero targeted test. T3 goes first because T2/T4/T5/T6 consume it.
2. **Add the regression lock with the fix (T7)**; T8 may run from an independent tool executor
   under one-worktree-one-writer.
3. **Bind evidence last (T9)**: derive the affected keys from the original ledger, approve the
   contract first, then verify the frontend executes the same contract. One consolidated
   closure review; unchanged evidence is reused, never a matrix per commit.

## Boundary

- Formal Product Layer: **P0** contract-runtime mechanism, with **P4** verification tooling as support.
- No business page layout rewrite; no new component unless a semantic has no renderer; no new
  environment/credential/fixture authority; no contract capability reduction; no guard relaxation;
  no state-machine DSL in this goal.
- Completion boundaries are reported separately: this goal proves batch/product-review evidence
  for the consumption gaps and guard/evidence bindings — not deployment, not target-user delivery.

## T8 — evidence reuse identity bound to the acting company/permission context

The matrix reuse identity previously had no authoritative company/role readback and folded the
whole bundle into every entry key, so an identity could be reused across a different acting
company (false reuse) while an unrelated change forced a full re-run (false invalidation).

Now the identity is derived from the captured authority, not from the request shape:

- `business_entry_matrix_model.mjs` reads the acting company and login from the closure snapshot
  (`acting_company_id` / acting login), fails closed when they are missing or mismatched, and
  binds per-unit permission context (`released_targets`, `capability_closure_sha256`, `company_id`)
  into the unit fingerprint. `environmentIdentity` now requires a positive-integer `actingCompanyId`
  and no longer folds `denied_role_candidates` into the environment identity.
- `business_entry_matrix_scope.mjs` resolves the acting company via `actingContext(closures, {login})`
  and re-verifies it against `summary.session_company_id` on `--emit-results`.
- `business_entry_negative_closures.mjs` requires `ACCEPTANCE_LOGIN`, records `acting`
  (`login`, `company_id`, `error`) in the snapshot, and rejects a missing/ mismatched acting company.
- `make/frontend.mk` forwards the required `ACCEPTANCE_LOGIN`.

Outcome: a company/permission context change invalidates only the affected keys; an unrelated
deployment no longer forces every key to re-run. The single `scripts/ops/evidence_scope.py` remains
the only scope authority.

## T9 — list-surface evidence re-binding (mis-bound artifact corrected, not re-run)

The audit chain reached the real defect first, without re-running the browser matrix.

**Confirmed mis-binding.** `docs/frontend_productization/rendering-detail/page-pattern-reference-detail-ledger-v1.json`
(`collection.header-actions`, `collection.toolbar-surface`) and `page-pattern-reference-contract-gaps-v1.md`
cited `.runtime/final-acceptance/list-surface-structure.json` as `316/316 gated`. That mutable path
had been overwritten by a payment.request create/edit run whose document records `records 12/12`,
`gated 0/0`, `negative_fixtures 0/0` — it gates no list surface at all. The ledger therefore asserted
list-surface coverage no artifact supported.

**Original evidence recovered (not regenerated).** `.runtime/final-acceptance/list-surface-all-7add8be3.json`
and its `-dark` twin (`list-surface-all-7a58470d.json` is the same value) are the real list-surface
observation: schema `frontend_list_surface_structure_browser.v1`, `gated 108/108`, `negative_fixtures 5/5`,
`runtime_errors 0`, `passed true`. The ledger text `316/316` was never self-consistent with any document
(the document states 108), so the reference — not the run — was corrected to `108/108 gated` over the
viewports/states the document actually observes (`1440/390 x normal/batch/empty`).

**Regression lock.** New `scripts/verify/list_surface_evidence_binding_guard.py` mechanics: every
`X/Y gated`/`gates X/Y checks` claim must name at least one artifact that (a) exists, (b) declares the
list-surface schema, (c) gates the list surface (`summary.gated.total > 0`) and (d) records counts equal
to the claim. Any supported-by-nothing / non-list-surface / count-mismatch / path-less claim is DENY.
Unit-tested in `scripts/verify/test_list_surface_evidence_binding_guard.py` (supported passes; gates-nothing,
count mismatch, no-path, non-surface-schema, CLI-failure all rejected). The defect is recorded as
`CD-20261013-LIST-SURFACE-EVIDENCE-MISBINDING` in the contract-basis ledger; the guard runs in the quick
gate, PR/release unit lanes and `ci.delivery.freeze.prepare`.

## Independent review rework (REQUEST_CHANGES, 2026-10-13)

The frozen-candidate independent review returned REQUEST_CHANGES with four S1 blockers, one S2
and one pre-existing gap. All are fixed and lock-tested; the identified checks were invalidated
by their changed inputs and re-recorded (no full re-run).

| Finding | Fix | Lock |
|---|---|---|
| S1-1 status-bar suppression regressed to field-name level | `resolveStatusFieldSuppression` (`pages/contractForm/nativeLayoutUtils.ts`) now takes the node identity (`nodeIdentity` / `statusbarNodeIdentity`); `useRecordFormLayout` passes node identity, never the bare field name, so a same-name field at another occurrence stays visible | consumption cases cover "same field, different occurrence position" |
| S1-2 auth enum not wired to real consumption | `app/contract/contractAuthLevel.ts` adds `resolveOccurrenceAuthVerdict` (admin implies edit; missing/illegal → `ContractGapError` gap; unresolved → blocked); `useRecordFormLayout` consumes it and computes `readonly = gap || unresolved || (verdict && !edit)`, so admin is editable and a missing declaration stops | `contract_consumption_verdicts_test.ts` covers none/read/edit/admin plus missing-declaration |
| S1-3 acting principal's own permission change did not invalidate evidence | `business_entry_negative_closures.mjs` records and snapshots the acting principal's `role_xmlids` and rejects a missing closure; `actingContext` returns `role_closure_sha256`; `environmentIdentity` binds the acting company closure and fails closed without it | `business_entry_matrix_reuse_identity.test.mjs` + `test_business_entry_matrix_incremental.py` permission-change counter-examples |
| S1-4 required lanes depended on a git-ignored machine-local `.runtime` report | tracked archive `docs/frontend_productization/rendering-detail/evidence-archive/manifest.v1.json` + `scripts/ops/evidence_archive_fetch.py` (`--verify` / `--archive-root --apply`); the guard decides on archived identity (a present local copy must match its sha256; absence is still decidable), and `make/frontend.mk` adds `evidence.archive.verify`/`fetch` with `verify` as the guard's prerequisite | `test_list_surface_evidence_binding_guard.py` (machine-independent) |
| S2 unrelated deployment still invalidated everything | deployment source split out of the shared identity into `deploymentProvenance` (`served_revision` + `frontend_build_sha256`); each unit binds `surfaceInputs` (scope `declared_surfaces` / `whole_artifact` / `served_revision_degraded`) | `environmentIdentity` no longer folds bundle/deployment; per-unit invalidation cases in the reuse-identity test |
| pre-existing read-only master-detail filter | `components/template/X2ManyRelationRenderer.vue` returns `props.adapter.visibleOne2manyRows(...)` instead of filtering rows by non-empty display text | `detail_collection_pagination_test.ts` (declared-visible rows with legal empty values persist) |

The three offline counter-examples the review proved (bundle change alters the shared identity;
acting role change not in the identity; guard rejects when local evidence is missing) are now
locked by the rewritten tests. Ledger entry `CD-20261013-EVIDENCE-ARCHIVE-AND-ACTING-CLOSURE`
records the closure; `closedContractDefects` is now 10, `openContractDefects` remains 0.

## Verification index (living; receipts are the only verdict)

`.agent/runs/FE-CONTRACT-RUNTIME-02/run.json` is the result index (declared targets, inputs, receipts).
Current recorded checks:

| check | target | tests |
|---|---|---|
| contract_basis_guard | `verify.frontend.contract_basis.unit` | 15 |
| contract_gap_primitive | `verify.frontend.contract_gap_primitive.unit` | 40 |
| native_form_structure_responsibility | `verify.frontend.native_form_structure_responsibility.unit` | 18 |
| form_canvas_layout | `verify.frontend.form_canvas_layout.unit` | 60 |
| collection_view_semantics | `verify.frontend.collection_view_semantics.unit` | 54 |
| collection_action_capability | `verify.frontend.collection_action_capability.unit` | 59 |
| professional_detail_collection_guard | `verify.frontend.professional_detail_collection.unit` | 136 |
| agent_ledger | `verify.agent.ledger.unit` | 15 |
| business_entry_evidence_scope | `verify.frontend.business_entry.evidence_scope.unit` | 123 |
| list_surface_evidence_binding | `verify.frontend.list_surface_evidence_binding.unit` | 12 |
| contract_consumption_verdicts | `verify.frontend.contract_consumption_verdicts.unit` | 21 |
| verification_lane_coverage | `verify.verification.lane_coverage` | 66 |
| trusted_scan_scope_unit | `verify.trusted_scan.unit` | 68 |

Auxiliary (not a registered run check): `make verify.frontend.typecheck.strict` rc=0
(`.runtime/agent-runs/FE-CONTRACT-RUNTIME-02/logs/typecheck_strict.log`).

## Freeze-gate lane closure (2026-10-13)

The first exact-head Quick surfaced one remaining blocker: `audit.verification.lane_coverage --check`
DENY, because this batch added verification surface. Both halves were closed by wiring, not by
rewriting the frozen baseline (the ratchet may only shrink):

- `verify.frontend.contract_consumption_verdicts.unit` was defined but referenced nowhere
  (zero-reference `761 > 760`). It is now a prerequisite of `verify.frontend.pr.unit`,
  `verify.frontend.release.unit`, `verify.frontend.quick.gate` and `ci.delivery.freeze.prepare`, so
  the S1-1/S1-2 consumption locks run on the remote frontend lanes and at freeze instead of sitting
  as dead surface.
- `scripts/ops/evidence_archive_fetch.py` and `scripts/verify/list_surface_evidence_binding_guard.py`
  were reachable only from remote lanes (remote-only `85 > 83`). `verify.frontend.list_surface_evidence_binding.unit`
  is now a prerequisite of `verify.contract.architecture.suite` — the single source consumed by both
  `ci.local.quick.run` and `ci.professional.backend.shard-verify` — so the evidence-binding guard (and
  its `evidence.archive.verify` prerequisite) is enforced on the local exact-head lane and the remote
  gate at once. The suite wire carries no pnpm/esbuild token, so `static_suite_frontend_toolchain_guard`
  stays satisfied.

`python3 scripts/audit/verification_lane_coverage.py --check` → PASS at the frozen baseline
(zero-reference 760, remote-only 83, unregistered `0/0`; no baseline or exemption file changed).

Invalidation was limited to the changed inputs: `make/frontend.mk` invalidated
`contract_gap_primitive`, `business_entry_evidence_scope`, `list_surface_evidence_binding` and
`contract_consumption_verdicts`; the `run.json` check registration invalidated `agent_ledger`. All
five were re-run and re-recorded, and one new check (`verification_lane_coverage`, 44 tests) was
added. No unrelated check was re-run.

The consolidated product review / browser journeys for the affected list, form, read-only detail,
master-detail, action and permission surfaces are the final step after the mechanisms above are frozen.

## P4 verification-system governance closure (2026-10-13)

The owner-directed P4 governance task (9 items) landed in this same run and is verified separately
from the product gaps:

- `scripts/audit/verification_lane_coverage.py` now freezes item identities (a count-neutral
  replacement of a registered problem fails), replaces the blanket `review_by=2026-12-31` with
  per-class `review_triggers`, hard-checks owner/basis/expiry/unwired-gate-candidate, and prints the
  structural coverage separately from a functional verdict.
- The three ledgers moved only what the facts required (3 `gate_candidate` reclassifications to
  `release_runbook` / `ops_runbook`); nothing was deleted to make a gate pass. The ratchet counts
  may only shrink.
- `scripts/ci/trusted_scan_scope.py` bounds transient `git` spawn failures (EAGAIN/ENOMEM/EFAULT)
  with a bounded retry instead of failing the Quick gate on a flake.

## Declared-visible detail collection: regression lock (2026-10-13)

The independently reviewed T6/pre-existing read-only filter removal had no behavioural lock; the
source-grep guard only asserted "the amount total is not narrowed to the current page". The
declared-visible rule is now single-sourced and locked:

- `pages/contractForm/one2manyUtils.ts` owns `visibleOne2manyRows(rowsByField, fieldName)`: the only
  exclusion is a declared removal (`!row.removed`). A blank display value is not a visibility fact.
- `pages/contractForm/useOne2manyRuntime.ts` delegates `visibleRows` to that helper, so the runtime
  cannot carry a second visibility rule.
- `frontend/apps/web/scripts/detail_collection_pagination_test.ts` (run by
  `verify.frontend.collection_action_capability.unit`, the ledger binding `[5]` regression guard)
  asserts that every-blank rows stay in the set, that record identity/count/pagination all read the
  same set, and that an undeclared field yields an empty set rather than a fabricated default.
- `scripts/verify/frontend_professional_detail_collection_guard.py` fails if the helper filters by
  display text, if the runtime stops delegating, or if the renderer adds a second visibility rule;
  two negative fixtures prove those branches fire.

## Contract producer → consumer chain re-verified (2026-10-13)

Every declaration the strict consumers now require is produced by the real backend and bound in
`docs/architecture/frontend_contract_basis_ledger.json` (`frontend_contract_basis_guard` asserts the
declaration symbol still exists at the producer and the consumption symbol at the consumer):

| declaration | producer | consumer |
|---|---|---|
| `surfacePolicies.collection_capabilities.actions[]` (action/scope/intent/available) | `addons/smart_core/utils/collection_action_capability.py` `build_collection_capabilities` | `app/runtime/actionViewCollectionCapabilityRuntime.ts` |
| `relation_entry.page_size` | `app_config_engine/services/assemblers/page_assembler.py` `_build_relation_entry_for_field` | `components/template/detailCollectionPagination.ts` |
| containerTree `span` (1..24) | `handlers/ui_contract_v2_projection.py` | `components/template/layoutSpan.ts` |
| `entry_target.record_entry` (`entry_intent`, `model_write_authority`) | `core/navigation_entry_target.py` `_build_record_entry` | `app/runtime/recordEntryContract.ts` |
| permission auth level `none\|read\|edit\|admin` | `core/unified_page_contract_v2_permissions.py` `permission_auth_level` | `app/contract/contractAuthLevel.ts` |

Lane evidence at this candidate: `verify.frontend.contract_basis.enforce` PASS (`open_defects=0`),
`verify.frontend.canonical_form_presenter.unit` PASS, `verify.frontend.page_pattern_reference_parity.unit`
PASS (`owned_gaps=0`), `verify.frontend.product_page_pattern.unit` PASS. `make ci.local.iteration` PASS
(L1 only; `unmappedPathCount=17` by design).

Invalidation was limited to the changed inputs: the new/changed frontend sources invalidated
`contract_basis_guard` (its input is the `frontend/apps/web/src` tree), `run.json` invalidated
`agent_ledger`, and the changed `scripts/verify` sources invalidated `verification_lane_coverage`.
All three were re-run and re-recorded; `collection_action_capability` and the new
`professional_detail_collection_guard` were recorded against their corrected input lists. No
unrelated check was re-run.

Still open (not part of this step): the consolidated affected-surface product review with real
representative roles/companies, and the target-environment upgrade/user acceptance.
