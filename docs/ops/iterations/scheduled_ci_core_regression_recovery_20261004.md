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

## Batch 2 — frontend full lane: released-surface binding + the #525 a11y regression

Branch `fix/scheduled-ci-frontend-settlement-release-targets`, baseline `2c3a9200` (main).

### Observed failure

`frontend_release_gate` dispatch run `37177685228` @`814bbc28`: the only failing check was
`verify.frontend.delivery_hardening.browser`. The released settlement deep link was refused and
the SPA landed on `/access-denied?reason=NAVIGATION_AUTHORITY_DENIED`. Every other check in the
same run passed. The 10-03 nightly failure was a different, earlier static guard that later
merges already repaired.

### Root cause (a) — probe bound a legacy menu outside the released contract (P4 verification tool)

The settlement journey was bound to `menu_sc_settlement_order` ("结算单", menu `357`). That
legacy entry is **not** in the 89-page released contract. The released settlement surfaces are
收入结算 `747/663`, 支出结算 `748/664`, 日常合同结算 `876/697`; both fixture records are
`settlement.expense`, so only `748` carries them. Role facts: finance renders no settlement leaf
in its released navigation; `pm` carries the settlement read group and can read both records.

Fix (owner-decided option B, no product/permission contract change):

- `scripts/verify/frontend_delivery_hardening_runtime_ids.py` now declares the menu/action pair
  for **every** target and fails closed when the resolved pair differs from the declaration:
  project -> `menu_sc_product_project_edit_v1`/`action_sc_product_project_edit_v1` (`861/680`),
  settlement -> `menu_sc_expense_contract_settlement`/`action_sc_settlement_order_expense`
  (`664/748`), contract, payment request and payment execution likewise.
- `scripts/verify/frontend_delivery_hardening_browser.mjs` runs the settlement surface and the
  settlement perf scenario as `pm`, and asserts the declared entry equals the acting role's
  *released* navigation entry (`assertReleasedSurfaceTarget`/`assertReleasedTargetForRole`,
  fail-closed). A legacy or foreign route now fails the probe instead of silently exercising a
  denied route.
- `addons/smart_construction_acceptance_fixture/tools/frontend_productization_fixture.py`
  reconciles the stored `company_id` on `payment.request` / `sc.payment.execution` rows in a
  **reused** acceptance database before the my-work scope assertion, with a regression test
  (`test_execution_freeze.py::test_reconcile_project_company_repairs_rows_from_a_reused_database`).

### Root cause (b) — genuine a11y regression introduced by #525 (P0 frontend rendering mechanism)

The a11y failures are **not** a pre-existing condition. The 09-18 full-lane run `35394617343`
succeeded with `PASS J09-J11 responsive=68 accessibility_blocking=0` (HEAD `26d254ade`), i.e.
after the 09-15 a11y gate landed. Every 10-04 failure until this batch stopped at an earlier
layer (style system / navigation policy / release audit / scene bridge / the 403 deep link) and
never reached the matrix, so the regression stayed unobserved. The matrix first ran on 10-04 and
reported 17 findings (16 serious `color-contrast`, 1 critical `aria-allowed-attr`).

All four points are in the #525 (`2d164a1f`) diff and are fixed in the owning renderer layer:

1. `frontend/packages/ui/src/kits/tdesign/theme.css`: `--td-text-color-placeholder` was moved
   from `--sc-semantic-text-secondary` to `--sc-semantic-text-muted`; restored (breadcrumb
   separators/prefixes, table headers, descriptions labels).
2. `ProductShellSidebarFooter.vue`: version line back to `--sc-semantic-text-secondary`.
3. `frontend/apps/web/src/layouts/AppShell.css` `.shell-content-footer` (added by #525): back to
   `--sc-semantic-text-secondary`.
4. `NavigationBreadcrumb.vue`: non-link context crumbs were declared `:disabled="!item.to"`,
   which TDesign paints with `--td-text-color-disabled`; the attribute is removed (pre-#525 these
   were readable text, and a non-link crumb does not navigate).
5. `ScSelect.vue`/`ScRelationField.vue`: `aria-required` was projected onto the TDesignSelect
   **wrapper** (`div.t-select__wrap`), which does not accept it; the native combobox input still
   receives it through `v-native-control-projection`. The wrapper binding is removed and locked
   by the primitive-adapter guard (same rule shape as the existing `ScDateField` assertion). The
   fix does **not** use `critical`, does not override ACL/field permissions, and adds no
   payment-model special case.

`scripts/verify/frontend_primitive_adapter_guard.py` (+ its unit fixture) is updated in step with
4 and 5; the visual marker for `--td-text-color-placeholder` is asserted as `secondary`.

### Evidence

- L1: `design_token_system.py`, `frontend_style_system_guard.py`, `frontend_navigation_shell_guard.py`,
  `frontend_primitive_adapter_guard.py` PASS; `make verify.frontend.primitive_adapter.unit` = 39 tests OK;
  `make verify.frontend.typecheck.strict` PASS.
- L2: `make frontend.acceptance.release.build` PASS.
- L4 matrix (SKIP_PERF, direct node, managed 5175/18082): the first attempts reached
  `accessibility blocking 0 / critical 0 / serious 0` and rendered 68 responsive pages, but the run
  still **FAILED** at the final `assertRuntimeClean` (`/tmp/dh_matrix6.log`, CI full lane
  `37209482547`). Only the accessibility half was green; "the L4 matrix passed" would have been a
  wrong reading of that run. After root cause (c) below: `report.pass=true`,
  `accessibility result=PASS blocking 0 (17 scans)`, responsive 68 pages / 4 viewports,
  J09/J10/J11 PASS, error-recovery PASS, log `/tmp/dh_matrix_f9f36b54.log`.
- L4 perf (PERF_ONLY): first attempt exceeded the `login_to_interactive` budget (median 3066 > 3000)
  while a stray 2-hour `grep -rln ... /` held 100% CPU; after the orphan was cleared the rerun PASSED
  on absolute and relative budgets (login 2642/p95 2765, my_work 388, payment_detail 245,
  settlement_detail 269, execution_detail 223, form_open 1068, company_switch 1941). Log
  `/tmp/dh_perf_only2.log`, report `artifacts/frontend-delivery-hardening/performance.json`.
- The authoritative full lane is the CI (`pnpm test:release`) run at the frozen head; the local
  matrix is iteration evidence for the same source set.

### Boundaries kept open

- The three-way declaration mismatch is a real, separate hazard and was **not** resolved by this
  batch: the 89-page released contract / `config/frontend/authoritative_navigation.json`
  (finance publishes 45 leaves, no settlement; pm publishes a settlement leaf) / backend
  `ROLE_SURFACE_OVERRIDES["finance"]` (still carries legacy settlement menus). Option B changed
  only the probe binding, so the finance settlement question needs its own P1/P2 topic.
- `rendering_detail_state` remains excluded per the earlier evidence and ruling.
- The environment DENY on the rebuild/snapshot lane stays a separate conclusion bound to the
  actual entry dependency and independent review; it is **not** generalized to "the environment
  passes". `acceptance.runtime.baseline_recovery.audit` PASS is recorded on its own.

### Root cause (c) — the matrix was still red at runtime: relation contracts fetched against the projection (P0 frontend contract consumption)

The final `assertRuntimeClean` of the matrix failed with eight 403s on
`ui.contract.v2 op=model res_id=0` — four `payment.request` and four
`payment.request.line`. One pair per viewport, on the `settlement-detail` surface rendered as the
project-manager fixture (`fixture_role_pm`).

- Locating it: a bounded read-only probe (`/tmp/surf_probe.mjs`, one route per role) reproduced the
  pair on `settlement-detail (pm)` only, and a role sweep against the managed backend
  (`/api/v1/intent`) showed the denial is the model ACL, not the route: `payment.request` /
  `payment.request.line` answer 200 for `finance`, `project_member` and `config_admin`, and 403
  `PERMISSION_DENIED 用户无权以 read 访问模型` for `pm`, `contract_operator` and `owner`.
- The declaration was already honest. The `sc.settlement.order` contract (action 748) projects both
  readonly one2many panels with `relation_entry.can_read=false`,
  `reason_code=RELATION_READ_FORBIDDEN`, `source=backend_contract` — and for `finance` the fields are
  not projected at all. So the ACL, the field permission and the projection are all correct.
- The defect was in the generic consumer:
  `ensureRelationFieldDescriptors` in
  `frontend/apps/web/src/pages/contractForm/useRecordRelationshipNavigation.ts` fetched a relation's
  model contract without consulting the declaration, so a page the actor *is* entitled to open
  issued a request the actor is *not* entitled to make. That is why the pair appeared on a surface
  whose journey, screenshots and axe scan all passed.
- Fix (P0, `f9f36b54`): fail closed on the declaration —
  `if (relationEntry(effectiveFieldDescriptor?.(name))?.canRead !== true) return;` — keeping the
  existing char-field fallback and mirroring `openRelationSearchDialog`. No ACL override, no
  payment-model special case and no relaxed assertion.
- Not disabled: on the same surface `sc.settlement.order.line` and `sc.settlement.adjustment` are
  still fetched and still answer 200 (`/tmp/surf_probe2.mjs`); for `finance`, whose contract does not
  project those two fields, behaviour is unchanged.
- Locked at L1: `frontend/apps/web/scripts/relation_column_descriptor_authority_test.ts` (declared
  readable / declared unreadable / entry absent, plus the PM settlement regression) is wired into
  `make verify.frontend.professional_relation_field.unit`. Negative control: removing the guard makes
  the test fail with exactly the observed defect (`declared unreadable: expected 0 ... got 1`).

### Follow-up: the first dispatched full lane exposed a stale guard literal

The first dispatched full lane at `6dce3a1d` (run `37208704607`) failed inside
`verify.frontend.release.unit`: `scripts/verify/test_frontend_delivery_hardening_guard.py::
ContractFormCacheOwnershipTest.test_browser_contract_target_uses_released_ten_center_entry`
asserted the *single-line spelling* of the runtime-ids contract binding, which the released-surface
change rewrote into the declared form. The assertion locked formatting, not the declaration, so it
is now parsed with `ast`: it requires `CONTRACT_MENU_XMLID == smart_construction_core.menu_sc_p1_daily_contract`,
`CONTRACT_ACTION_XMLID == smart_construction_core.action_sc_general_contract`, a `payload["contract"]`
binding that consumes those two constants, and the absence of the legacy
`menu_sc_construction_contract` menu. The released entry and the declared action pair are still
locked; the formatting is not. Local `make -k verify.frontend.release.unit` then passed.
