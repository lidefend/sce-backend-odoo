# Daily Dev — Typical Page to Full Product Acceptance (2026-10-13)

Goal: `DAILY-DEV-FULL-PRODUCT-ACCEPTANCE-20261013`
Run: `.agent/runs/DAILY-DEV-FULL-PRODUCT-ACCEPTANCE-20261013/run.json` (status `completed`)
Branch: `audit/daily-dev-full-product-acceptance-20261013` (merged); the batch's closure carrier `codex/daily-dev-acceptance-deployment-closeout` retires with this record
Baseline: `2e2951ea81cd3f9899f12e7d0bfb533882ee81ad` (after PR #649); the batch baseline advanced to `f0a549ea7969a0d58f764a96efc145c3242419e4` once PR #650 merged, and the closure delta is the bookkeeping change only

## Objective

1. Advance the daily development runtime (`sc-root:/opt/projects/repos/sce-product-odoo`,
   `ENV=dev`, DB `sc_demo`, custom frontend) from the stale detached head `7add8be3`
   to the exact current mainline `2e2951ea` through the governed candidate bundle-sync lane.
2. Rebuild the served frontend, align the served source revision, converge the published
   face and resolve the acceptance record identity.
3. Confirm acceptance from the affected typical page (payment-request chain, PR #649) and
   extend it to the full formal product entry set, verified by entry responsibility,
   permission boundary and key writes.

## Scope / exclusions

In scope: run/goal metadata; the daily runtime code face, served frontend, published face and
record identity; read-only user acceptance on `sc_demo`; the boundary defects the acceptance
exposes in the owning layer (see B1).

Explicitly excluded: relaxing any ACL/field permission/assertion; creating new environment or
credential authority; the pre-existing residual failures (`verify.contract.lint` 49 items, the
stale `res.users` assertion in `test_frontend_quality_safety_domain_rollout.py`, and the demo
seed vs #525 document state-guard conflict).

## Status

- [x] A: align the daily runtime to `2e2951ea` and confirm the payment-request typical page.
      Served identity read back as `2e2951ea` / `frontend_build_sha256=3730b10d…` on
      `http://1.95.85.92:18081`, DB `sc_demo`. Payment-request typical page PASS
      (`artifacts/frontend-business-entry-matrix/daily-2e2951ea-payment/`).
- [x] B1: first full formal 89-entry matrix at `2e2951ea`
      (`artifacts/frontend-business-entry-matrix/daily-2e2951ea-full/`, `completeness=complete`,
      `entries=89`) reported **4 failures** and 8 console errors, all in the formal 89 scope and all
      on the record-detail open of an otherwise healthy list.
- [x] B2: redeploy the boundary fixes and re-walk the matrix at the new served identity. The served
      identity is now `9b6a1128` / `frontend_build_sha256=00baf0f0…`. A targeted re-walk of the four
      entries PASS (`daily-9b6a1128-fix4`, `entries=4 problems=0 console_errors=0`) and the full
      matrix PASS (`daily-9b6a1128-full`, `completeness=complete entries=89 problems=0
      console_errors=0`, negative authority 10 fixture roles / 89 entries checked / 0 leaked).
- [x] B3: close the two gates the B2 fixes left behind (served assembled-contract cache re-pin and
      the unwired ops repair driver). PR **#650** merged (squash) so `main == origin/main ==
      f0a549ea7969a0d58f764a96efc145c3242419e4`.
- [x] C: deploy that exact mainline to the daily runtime through the governed lane and read it back.
      `daily.runtime.main.bundle_sync` normalized the detached candidate `9b6a1128` back onto `main`
      (`normalized_from_candidate=true`, `bundle_sha256=c02a2733…`), `source_revision.align` declared
      the served revision, `frontend.build` rebuilt the served bundle at the **identical**
      fingerprint `00baf0f0…` (entry asset `index-BHZ82tmH.js`), `published_face.converge`
      re-froze 90 released pages per product key (snapshot ids 93/94), and `record_identity.resolve`
      resolved the 10 acceptance carriers. Receipts: `.runtime/final-acceptance/daily-deployed/`.
      Read back from `http://1.95.85.92:18081/api/runtime-version`: `source_revision = git_sha =
      f0a549ea…`, `database=sc_demo`, `environment=dev`; the SPA entry serves
      `/assets/index-BHZ82tmH.js`.

### Evidence carried forward across `9b6a1128 -> f0a549ea`

The B2 matrix evidence is reused, not rerun, on a recorded deterministic impact analysis: the served
frontend fingerprint is byte-identical (`00baf0f0…`, so no rendering surface changed) and the only
backend delta between the two revisions is the assembled-contract cache identity plus test-only
wiring, which the B3 section records as behaviour-neutral. The cache bump strictly widens delivery
(warm clients stop serving the pre-facet assembly), so it cannot invalidate a page that already
passed at `9b6a1128`.

## B1 findings (all four entries are backend/contract-boundary defects)

| entry | model | action | observed |
|---|---|---|---|
| `smart_construction_core.menu_sc_p1_daily_contract` | `sc.general.contract` | 669 | 400 `native form projection requires a resolved native form layout` |
| `account.menu_action_move_journal_line_form` | `account.move` | 278 | 500 |
| `account.menu_action_account_form` | `account.account` | 291 | 500 |
| `smart_construction_core.menu_sc_account_journal_foundation` | `account.journal` | 1168 | 500 |

1. **Active view identity dropped (400).** The projection published `view_id` only when the
   action assembled exactly one canonical view type. A record-detail load declares
   `view_type=form` while the same action still assembles its tree/search family, so `view_id`
   was dropped and the published view-scoped orchestration contract (bound by `view_id`) stopped
   applying — the form lost its orchestration and its native layout. Fixed in the owning layer
   (`page_assembler._resolve_active_view_id`); the contract itself was already correct.
2. **Unbound structural low-code config over a bound native surface (400).** A low-code contract
   saved on 2026-10-11 without a view target
   (`view_orchestration:sc.general.contract:form:action:669:view:0`) declares a structural layout
   while the view-bound native semantic surface `daily_contract_form_native_v1` (view 1699) owns the
   same scope. The runtime view orchestrator must fail closed there (`CONFIG_TARGET_BINDING_REQUIRED`),
   the assembler then degrades the form view contract and the native form projection has no resolved
   layout. The edit is stale (`subcontract_mode` already reaches the page from view 1699's arch and
   from the scope's field policy), so it was retired through a narrow, dry-run-first ops script bound
   to the exact contract id.
3. **Native arch markup leaked into the presentation facet (500 ×3).** The container presentation
   projection derived the declared presentation facet (`styleToken`) from the native form arch's own
   CSS classes and failed the whole page closed on a class its closed vocabulary could not classify.
   Bootstrap/Odoo markup (`mx-3`, `col`, `oi`) is native rendering implementation, not product
   delivery semantics, so the vocabulary could never be complete — the earlier "add the missing
   token" fix was the same symptom. **Owner ruling: the presentation facet does not carry native arch
   class names.** The facet now publishes only product-declared presentation (pre-existing tokens,
   the declared layout vocabulary, the `sc-*` namespace); every other container class is dropped, so a
   native view can no longer fail a page through its own decoration and the facet stops growing with
   the arch vocabulary.

Fix commits: `8ad256ce` (1), `9b6a1128` (2), `f9df902a` (3).

## B3 findings (two gates the B2 fixes left behind)

The B2 fixes were correct at the product layer but left two verification gates
red, both caused by this batch's own inputs. They are closed here rather than
deferred, because a red gate on the batch's own input would otherwise be
inherited by every later candidate.

1. **Served assembled-contract cache no longer matched its pin (P0/P1 contract
   runtime).** `f9df902a` changed `ui_contract_v2_projection.py`, which is one of
   the pinned inputs of the assembled-contract response cache. The cache serves a
   whole assembled contract, so an unpinned change would keep serving the previous
   assembly and the presentation-facet correction would never reach a client with
   a warm cache. Fixed in the owning layer: `ASSEMBLED_CONTRACT_CACHE_VERSION`
   bumped to `ui-contract-v2-2026-10-13-drop-native-arch-class-from-presentation-facet`
   in the handler and in the guard, and `ASSEMBLED_CACHE_INPUTS_SHA256` re-pinned
   to `11385d19d89e04710b35be4adf286a38ff24f304ecdec95ed0ea20834acd7091`. No
   behaviour changed; only the cache identity did.
2. **The new ops repair driver was dead surface.** The verification-lane coverage
   audit correctly refused `scripts/ops/repair_unbound_structural_form_contract.py`
   as an unreferenced script under a frozen ratchet. The driver retires a live
   config on the demo-backed daily database, so it is wired instead of retired:
   `verify.contract.unbound_structural_form_contract.repair.unit` compiles it and
   runs a sandboxed behavioural test that drives the same source through the real
   fail-closed ladder, and the entry is a prerequisite of
   `verify.contract.architecture.suite` (reached by both `ci.local.quick.run` and
   the remote backend verify shard). The script count is back under the baseline
   and the target count is unchanged.

## Execution order correction

The B2 round pushed first and only then let the PR merge step trigger the
exact-head Quick, so the two gate fixes above invalidated an already-green
remote run and cost one wasted remote cycle. The governed order for the rest of
this batch is: fix -> `ci.local.iteration` -> risk-selected L2 ->
`ci.delivery.freeze.prepare` -> commit -> freeze the full fingerprint -> one
exact-head Quick **locally** -> push -> remote required checks -> merge. The
Quick result is produced before publication, never discovered by the merge step.

## Result index

Layer-level checks, exact commands, stage identity and receipts are recorded in the run record at
`.agent/runs/DAILY-DEV-FULL-PRODUCT-ACCEPTANCE-20261013/run.json`; the matrix artifacts are
under `artifacts/frontend-business-entry-matrix/`. Original logs are referenced, not copied here.

## Status boundary (reported separately)

- Batch acceptance: complete (A + B1 + B2 + B3).
- Mainline integration: complete — PR #650 merged; `main == origin/main == f0a549ea`.
- Version deployment to the daily development server: complete — the daily runtime serves
  `f0a549ea` / `frontend_build_sha256=00baf0f0…` on `sc_demo`, with the published face re-frozen at
  90 released pages per product key. This is the daily development runtime, not a formal release.
- Product delivery: **pending the owner's own login acceptance** as `wutao` on `sc_demo` at
  `http://1.95.85.92:18081`.

## Closure

This record closes the goal: the executor-side work (mainline alignment, full formal entry
acceptance, integration and deployment) is finished and the daily runtime serves `f0a549ea`. The
goal and its run are marked `completed` and the run is removed from `.agent/active-runs.json`;
the deployment carrier branch retires with this change. The owner's login acceptance is reported
separately as the product-delivery status and is not executor work — a defect found there starts a
new goal rather than reopening this one.
