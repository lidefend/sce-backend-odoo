# Daily Dev — Typical Page to Full Product Acceptance (2026-10-13)

Goal: `DAILY-DEV-FULL-PRODUCT-ACCEPTANCE-20261013`
Run: `.agent/runs/DAILY-DEV-FULL-PRODUCT-ACCEPTANCE-20261013/run.json`
Branch: `audit/daily-dev-full-product-acceptance-20261013`
Baseline: clean `main` == `origin/main` == `2e2951ea81cd3f9899f12e7d0bfb533882ee81ad` (after PR #649)

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
- [~] B1: full formal 89-entry matrix. First full walk at `2e2951ea` is complete
      (`artifacts/frontend-business-entry-matrix/daily-2e2951ea-full/`, `completeness=complete`,
      `entries=89`) with **4 failures**, all in the formal 89 scope and all on the record-detail
      open of an otherwise healthy list.
- [ ] B2: redeploy the boundary fix, re-walk the full matrix at the new served identity and
      confirm zero problems.

## B1 findings (both root causes are backend/contract-boundary defects)

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
2. **Unclassified native class (500).** The container presentation projection fails closed on a
   declared class it cannot classify. Odoo's own accounting arches declare the native
   `alert-link` class, which the declared vocabulary did not carry. Fixed by adding the token to
   the projection vocabulary **and** implementing it in the renderer vocabulary, so the
   projection's accepted tokens stay equal to the renderer's implemented vocabulary.

Fix commit: `8ad256ce`.

## Result index

Layer-level checks, exact commands, stage identity and receipts are recorded in the run record at
`.agent/runs/DAILY-DEV-FULL-PRODUCT-ACCEPTANCE-20261013/run.json`; the matrix artifacts are
under `artifacts/frontend-business-entry-matrix/`. Original logs are referenced, not copied here.

## Status boundary (reported separately)

- Batch acceptance: A complete; B1 root-caused and fixed locally, B2 pending redeploy + re-walk
- Mainline integration: pending (fix not yet merged)
- Deployment: daily runtime currently serves `2e2951ea` (pre-fix)
- Product delivery: pending owner login confirmation
