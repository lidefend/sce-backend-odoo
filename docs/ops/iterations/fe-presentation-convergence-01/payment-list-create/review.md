# Payment list create: implementation review

User decision: creation starts at the formal payment application list's New button. This supersedes the earlier keep-create-false product decision, not ACL or record rules. No new menu or direct-URL acceptance substitute.

Baseline: `4853b1b441837aa814049b2b9e31e9bdaa827767`, branch `fix/payment-list-create`, uncommitted scope recorded in current run. Previous PAYMENT-NEW-02 work is preserved separately; it is not part of this candidate.

Ownership: P1 / smart_construction_core / native formal payment list declaration. This is a standard business entry choice; P0 capability combination and generic frontend consumption remain authoritative. Blast radius: formal payment list only; no global create policy, ACL, menu restoration, list editing or deletion change.

Validation plan: existing native declaration tests first (L1/L2), then iteration guards. Database-backed contract and actual button acceptance are not replaced by source tests. No module upgrade, fixture, business writes, deployment, merge or PR publication in this local implementation. Current environment is unchanged; runtime results remain not_run until an authorized candidate environment is available.

Rollback: revert the single list capability declaration and its scoped regression test.

## Local result

Only product delta: `view_payment_request_formal_payment_apply_tree` sets `create="true"`; `edit="false"` and `delete="false"` are unchanged. The existing formal action still selects `view_payment_request_pay_form` and supplies `default_type=pay`, `default_business_category_code=finance.payment.apply.pay`. No new action, menu, frontend branch, ACL or record rule. P0 continues intersecting model rights, action context and tree/form restrictions; this declaration grants no model permission.

Existing test `test_payment_list_declarations_respect_native_field_usage` now guards the list create/edit/delete policy, exact form binding and default business context. Existing generic deny-create contract test remains unchanged. No extra test entrypoint.

- `make verify.native_form.declarations.unit`: 3 tests, initial expected failure on create=false (`.runtime/payment-list-create-before.log`).
- First post-change attempt exposed a test bug reading text rather than the XML eval attribute (`.runtime/payment-list-create-after.log`); fixed in the test only.
- Final same command: 3/3 passed (`.runtime/payment-list-create-after-fixed.log`).
- `make ci.local.iteration`: passed (`.runtime/payment-list-create-iteration.log`); its recommendations do not replace the explicitly executed tests. The final test-only eval-read fix was covered by the targeted rerun.
- `git diff --check`: passed.
- DB-backed contract, role-negative runtime, actual list-button opening and save validation: not_run. No module upgrade or isolated database write was performed. This is a local implementation candidate, not runtime acceptance.

PAYMENT-NEW-02's independent-entry requirement is superseded by the new product choice. Its uncommitted patch remains preserved, not applied to this main-based candidate. Existing main browser tests already use the formal list button; no independent target is introduced. Before carrying over any probe changes, remove that superseded requirement while retaining contract/DOM checks and generic denied-create tests. #768 status and gates are unchanged. No push, merge or deployment.

## PAYMENT-LIST-CREATE-02 diff review

Full product diff is exactly one XML attribute, create=false to create=true. Edit/delete remain false; action/context, ACL/record rules, frontend, model save/submit logic are unchanged. `ActionView.vue` still consumes effective create capability and invokes its existing `openCreateRecord` path; source inspection is not browser acceptance.

The original test's substring assertion for eval was insufficient. It now parses the actual eval AST, resolves only literal `ref(string)` calls to symbolic XMLIDs, and uses `ast.literal_eval` to compare the complete ordered `views` and `view_ids` structures. Unknown function calls are rejected, never evaluated. The test continues checking pay/category defaults and no context create denial.

`make verify.native_form.declarations.unit`: 3/3 passed after this test refinement (`.runtime/payment-list-create-02-tests.log`). `make ci.local.iteration`: passed (`.runtime/payment-list-create-02-iteration.log`). Prior failing old-declaration test is retained. Scope: L1/L2 source declaration regression; runtime ACL/contract and real button evidence remain pending. Saving a payment requires separate authorization and is not performed.

Candidate publication is authorized by the latest request after required checks. Quick/finalization results are kept under the current run's referenced runtime evidence; no prior candidate success is inherited. This review is author self-check, not independent final approval.
