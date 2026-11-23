# BASELINE-EVIDENCE-01

## Identity

- Investigation base: `b0c08392679b9f305c9b6e6819c86e254b9e7d61`
- Formal stable baseline anchor: `5b58d6a1b2ac759c2f1c1cac26e820236fd74f9f`
- Branch: `audit/BASELINE-EVIDENCE-01-20261123`
- Product source modification: none
- Candidate P0-B worktree modification: none

## Baseline definition correction

The formal stable baseline is the declaration in
`scripts/verify/test_baseline_manifest.json` plus its two declared ORM groups.
That manifest explicitly states it is not all repository tests.

The failure below comes from the broader
`verify.smart_construction_core.module_baseline` suite. Its failure does not
mean the PR735 stable baseline was overwritten, and it is not itself a
platform contract baseline.

The product baseline relevant to Contract V2 is the fact-to-contract chain:
Odoo facts -> declared Contract V2 producer output -> strict consumer decode ->
affected page behavior. Odoo framework behavior remains covered by Odoo-owned
tests; it is not redefined as SCE's contract authority.

## Root cause

The candidate full-module log contains exactly 80 failures. All 80 return
`CONTRACT_VERSION_UNSUPPORTED` because the test caller declared
`client_contract_capabilities` while omitting `client_type`.

Timeline:

- `594309dee` (2026-11-22, PR #953 lineage) added capability declarations to
  many native-lowcode test callers.
- `122129513` (2026-11-23, PR #974 P0-A merge) introduced strict negotiation:
  once versions or capabilities are declared, a missing/unknown `client_type`
  fails closed.
- The affected test callers were not updated in that same change.

This is mixed evidence debt after a formal contract-entry rule change:

- direct contract test callers omitted the explicit client identity;
- the change-set preview/publish/rollback path forwarded declared
  capabilities but dropped the declared `client_type` before invoking the
  unified Contract V2 handler.

It is not evidence that the P0-B attachment producer is incorrect.

## Evidence

- Candidate failure log:
  `.runtime/test-baseline/1795418028785810533/odoo.log`
  (SHA-256 recorded in the inventory JSON).
- Clean-base representative reproduction:
  `/home/lidefend/workspace/sce-backend-odoo-task-model-03-20261123-industry-business-model-02-20261123/.runtime/test-baseline/1795419027831832794/receipt.json`
  at clean HEAD `b0c08392679b9f305c9b6e6819c86e254b9e7d61`.
- Representative test:
  `TestCompanyProjectRefundFeedback.test_create_ui_contract_uses_request_local_feedback_proof`.
- Representative clean-base result: one test fails with the same
  `CONTRACT_VERSION_UNSUPPORTED` response.
- Full inventory:
  `docs/audit/baseline_evidence_01/failure_inventory.json`.

The attempted full clean-base rerun was rejected before database mutation by
the shared `local-test.lock` (`BlockingIOError`). That full rerun is
`not_run`; it is not claimed as a pass or failure.

## Failure grouping

| Test file | Failures |
| --- | ---: |
| `test_ledger_summary_guarantee_native_lowcode.py` | 12 |
| `test_context_workspace_native_lowcode.py` | 11 |
| `test_tax_deduction_native_lowcode.py` | 11 |
| `test_expense_claim_native_lowcode.py` | 9 |
| `test_daily_contract_settlement_native_lowcode.py` | 7 |
| `test_hr_payroll_native_lowcode.py` | 5 |
| `test_payment_execution_native_lowcode.py` | 5 |
| `test_usage_performance_native_lowcode.py` | 5 |
| `test_invoice_native_lowcode.py` | 4 |
| `test_policy_document_capability.py` | 3 |
| `test_receipt_income_native_lowcode.py` | 3 |
| `test_system_permission_accounting.py` | 3 |
| `test_company_project_refund_feedback.py` | 1 |
| `test_user_feedback_business_views.py` | 1 |

There are 34 literal request-construction sites missing `client_type`. Two
additional same-pattern sites are currently outside the selected failing tag
set and should be corrected in the same test-only cleanup to avoid a second
wave:

- `test_feedback_evaluation_rt_http.py`
- `test_native_advisory_draft.py`

## Implemented remediation

This branch implements the bounded remediation:

1. For each affected request that declares contract capabilities and represents
   a Web PC contract consumer, add explicit `client_type: "web_pc"`.
2. Cover the two adjacent same-pattern files.
3. Keep strict negotiation unchanged.
4. Add or retain regression tests proving missing/unknown `client_type` still
   fails with `CONTRACT_VERSION_UNSUPPORTED`.
5. Forward the caller's declared `client_type` through change-set
   preview/publish/rollback into the unified Contract V2 handler.
6. Keep strict negotiation unchanged.
7. Replace the shared local-test identity with a worktree-scoped Compose
   project, volume set and lock. Database name inside each isolated carrier
   remains the governed `sc_test`.

The local-test runner now derives `sc-local-test-<worktree-key>` and unique
volumes from the absolute worktree root. Different worktrees no longer contend
for one database lock.

This is not "fabricating" a client identity: these tests directly model Web
contract requests and must declare the caller identity required by the current
contract-entry rule. The values are explicit test facts, not product defaults.

## Validation

- `scripts.verify.test_local_test_runner`: PASS, 23 tests.
- `make local.test.prepare`: PASS with the worktree-scoped identity.
- Representative formerly failing browser-independent ORM case
  `TestContextWorkspaceNativeLowcode.test_one_workbench_closes_the_authorized_form_configuration_loop`:
  PASS, 1 test, independent project
  `sc-local-test-16e96c2dcade/sc_test`.
- Full affected-class collection is intentionally delegated to exact-head
  remote CI instead of rebuilding the whole local module template again.

## Impact boundary

- The only product change is forwarding an already-declared client identity
  through the existing change-set handler. ACL, Record Rules, workflows,
  database schema and file-service authorization are unchanged.
- No change to Contract V2 negotiation semantics.
- No change to P0-B attachment facts or FCF-02-2.
- Independent PR required because this reconciles broader test evidence, not
  the P0-B product result.

## Conclusion

The 80 failures are broader-suite stale caller/entry-forwarding debt, not a
failure of the formal PR735 baseline and not a P0-B product regression. The
bounded fix preserves strict negotiation and adds explicit caller identity at
the test and change-set entry boundary.
