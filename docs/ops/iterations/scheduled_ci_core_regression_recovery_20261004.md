# Scheduled CI full-lane recovery — backend core regression + relation-read gate (2026-10-04)

Run: `.agent/runs/CI-SCHEDULED-FULL-LANE-RECOVERY-D/run.json`
Baseline: `814bbc2888bb5f70eca4fe013bdba79cb82fb483` (main, clean)

## Status boundary

Batch product review is **not** complete. Mainline integration, version release and product
delivery are untouched. This record is the living batch index; original logs are referenced,
not copied.

## Observed red lanes on main

| Lane | Trigger | Latest evidence | Signature |
| --- | --- | --- | --- |
| `backend_test_suite` | schedule (`cron 37 19 * * *`) | 37158252861 (10-03), 37076404721 (10-02), 36940538473 (10-01) | `smart_construction_core: 25 failed, 35 error(s) of 471` |
| `backend_test_suite` | dispatch | 37174945333 @4f55eed2 | same signature (full-lane); 37174639058 @4f55eed2 is single-module `sc_norm_engine` and is green |
| `frontend_release_gate` | dispatch | 37177685228 @814bbc28 | browser journey `verify.frontend.delivery_hardening.release.browser` times out; SPA lands on `/access-denied?reason=NAVIGATION_AUTHORITY_DENIED` |

Green reference: schedule 36789659135 @`fff226d7b` (core `0 failed of 470`).
Regression window `fff226d7b..f9d2f1d9f` contains exactly 3 commits; the only one touching
`addons/smart_construction_core` is **PR #525 `2d164a1f`**.
`backend_test_suite` is not a PR gate (schedule + dispatch only), which is why the drift merged.

## Local reproduction (governed)

```
ENV=dev ENV_FILE=.env.dev make test MODULE=smart_construction_core \
  TEST_TAGS="sc_smoke/smart_construction_core,sc_gate/smart_construction_core" \
  DB_NAME=sc_tmp_core_suite
```

Result: `25 failed, 35 error(s) of 471` — identical signature to CI.
Evidence: `/tmp/local_sc_core_test.log`, failure index `/tmp/fail_list.txt`, detail `/tmp/fail_detail.txt`.

## Triage

### (A) Intentional contract redesign, drifted guards — align the guard, keep it strict

`docs/phase_p0/state_machine.md` (updated inside #525) declares the new routing:

- *No configured approval: submission advances through `submit` to `approved` in one
  transaction, with an automatic-submission audit; it does not fabricate tier reviews or
  validation status.*
- `action_approve` / `action_set_approved` are compatibility delegates, not separate transitions.
- Documents must enter through `draft` and reach business states only through formal actions.

The models enforce this with real guards (`单据必须从草稿…`, `请先提交单据并完成审批…`,
`状态必须通过办理动作产生。`) introduced by #525. The pre-#525 guard tests
(`test_p0_state_closure.py`, `test_p0_ledger_gate.py`, `test_p1_finance_projection_authority.py`,
`test_p1_funding_authority.py`, `test_project_state_transition_validation.py`,
`test_team_loan_deduction_workspace.py`, `test_tax_filing.py`, `test_product_reports.py`,
`test_project_special_tax_deduction.py`, `test_cost_fact_concurrency_v2.py`,
`test_labor_product_capability.py`, `test_tender_document_advisory.py`,
`test_material_supplier_return.py`, parts of `test_p1_payment_request_capability.py`) still
assert the old contract (`submitted` after submit, manual `action_approve`, non-draft
`create()`, business action without submission) and therefore fail.

Resolution: realign the drifted assertions to the declared contract **without weakening
them** — assert the terminal state, the absence of fabricated review instances, and the
preserved audit, rather than deleting the check. No payment/finance model receives a special
case and no ACL/field-permission rule is overridden.

### (B) Genuine defects surfaced by the same run — fix the product/test tool

1. **Tier server actions missing `groups_id`** → `TestInstallGate.test_actions_have_groups_at_install`,
   `TestActionGroupsGate.test_actions_have_groups`. ~30 `server_action_*_on_approved/_on_rejected`
   records in `data/finance_document_tier_actions.xml` (and sibling core data) declare no group,
   while `data/material_outbound_tier_actions.xml` declares groups on all of its actions.
   Fix at the owning layer: declare the same capability groups already used by
   `security/action_groups_patch.xml`.
2. **Plan validation guard gap** → `TestP0StateClosure.test_material_plan_blocks_invalid_anchor_or_state_jump`
   (`UserError not raised`). Verify whether the plan `action_on_tier_approved` path is missing its
   `validation_status` precondition when no approval instance exists; fix the model if so.
3. **Stale test patch target** → `TestMyWorkBackend` patches
   `…handlers.my_work_summary.PaymentRequestWorkItemService`, which moved to
   `services/payment_request_work_item_service.py`. Fix the patch target.
4. **Stub gap** → `TestPaymentRequestWorkItemService` `Record` stub lacks `review_ids`
   (`AttributeError`). Fix the stub to mirror the real record contract.
5. **`sc.approval.policy` AccessError** in `TestP1PaymentRequestCapability.test_available_actions_use_model_capabilities_not_role_names`
   — determine whether the test user is missing a governed read rule for the approval-policy
   authority model (product) or the test needs the documented authority context (test tool).

### (C) Not yet triaged

`TestPaymentRequestApprovalIntentBackend`, remaining `TestPaymentRequestWorkItemService`
cases, remaining `TestP1PaymentRequestCapability` cases, `TestP0StateClosure` state-jump
errors, `TestProjectStateTransitionValidation`, `TestP1FinanceProjectionAuthority` receipt
rollback case. Each will be classified (A) or (B) before any edit.

## Frontend relation-read gate (batch 2, after batch 1)

- Chain: `frontend/apps/web/src/router/index.ts` → `findRouteAuthority` → fallback
  `frontend/apps/web/src/app/relationReadRouteAuthority.ts` (added by #525) requires every
  `return_*` value to be non-zero, so a bare deep link with no `return_*` is denied.
- The settlement order is declared in the finance `primary_menu_xmlids` / `leaf_keys` (45) but
  not in `browser_leaf_keys` (15); `browser_expected_count` asserts exact equality, so it
  cannot simply be added there.
- Ownership to be decided with evidence: backend route-authority declaration cannot satisfy a
  bare deep link, versus the frontend fallback treating a released record deep link as a
  relation read. No assertion or audit will be relaxed.

## Next exact step

Batch 1: converge `smart_construction_core` to 0 failing on `sc_tmp_core_suite`, then freeze
and deliver via the governed PR flow. Batch 2: fix the relation-read authority, then dispatch
both schedule lanes on the merged main.

## Batch 1 follow-up (PR #561 merged, nightly still red)

PR #561 merged as `a61615b8`. The dispatched `backend_test_suite` on the merged main
(run `37194316962`) still failed with `2 failed, 1 error(s) of 471`, so Batch 1 was **not**
closed and the nightly lane had been red for three consecutive days.

### Invalidated evidence

The PR's local L2 evidence (`sc_tmp_core_suite`, log `/tmp/local_sc_core_test7.log`) reported
`0 failed, 0 error(s)`. That database already had `smart_construction_core` installed, so
`--without-demo=all -i` never re-installed it and the run never exercised the fresh-install
path the CI lane uses. Reproduction on a fresh database (`sc_ci_repro_core1`) reproduced the
exact CI failures. That evidence is superseded; the replacement is a fresh-database run.

### Root causes (all in the payment-request approval area touched by #525/#561)

1. `sc.approval.policy._start_submission_review` (product). A rejected payment request keeps
   its sibling `tier.review` rows `pending/waiting`; only the reviewer's own row becomes
   `rejected`, so `validation_status` is `rejected` while three steps are still live. The
   "clear only finished reviews" branch therefore deleted one row and then raised
   `旧审批实例未能重置`. Resubmission must clear the whole finished instance.
   `_state_from` for `payment.request` is `["draft"]` while submissions enter `submit`, so
   OCA's `restart_validation()` never clears the instance for this model.
2. `TestPaymentRequestWorkItemService` fixture. The submitted record's reviewers were bound to
   the executive only, so the finance actor the assertions exercise could not review.
3. `TestP1PaymentRequestCapability.test_available_actions_use_model_capabilities_not_role_names`
   fixture. The capability-holder under test was never bound as the live instance's reviewer.

Root causes 2 and 3 are fixture bindings, not relaxed assertions: the projection legitimately
requires `can_review` for a live instance (R10-v2), and the fixtures now express a record whose
current step the actor under test actually owns.

### Fix and evidence

- `models/support/approval_policy.py`: clear the whole finished instance, fail closed for
  anything that is neither `rejected` nor `validated`.
- `tests/test_payment_request_work_item_service.py`,
  `tests/test_p1_payment_request_capability.py`: bind the actors under test as current reviewers.
- Fresh-install L2 (`sc_ci_repro_core2`): `0 failed, 0 error(s) of 471` (`/tmp/repro_core2.log`).
- Focused L2 (4 tests): `0 failed, 0 error(s)` (`/tmp/repro_core2_focused.log`).
- `verify.ci.scheduled_gates`: PASS, 29 tests (`/tmp/ci_scheduled_gates_batch2.log`).
- `scripts/ci/personal_data_scan.py`: PASS, `confirmed_matches=0` (`/tmp/personal_data_scan_batch2.log`).
- Generated evidence: the added lines bump the complexity metric for
  `approval_policy.py` and `test_p1_payment_request_capability.py`, so
  `docs/engineering_convergence/complexity_budget_report.md` was refreshed with
  `python3 scripts/ci/generate_complexity_budget_report.py --write` and committed with this batch.

## Corrected next exact step

Publish this branch, confirm the four required checks on the PR head, then re-dispatch
`backend_test_suite` on the merged main and require `0 failed, 0 error(s) of 471` from a fresh
per-module database. Only then is the nightly lane closed. Batch 2 (frontend relation-read 403)
follows.
