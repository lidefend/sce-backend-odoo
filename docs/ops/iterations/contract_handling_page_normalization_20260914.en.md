# Contract-handling Page Information Closure (2026-09-14)

中文：[contract_handling_page_normalization_20260914.md](contract_handling_page_normalization_20260914.md)

## Objective and boundary

- Single product result: the formal income- and expense-contract entries clearly identify the contract, expose core facts and editable lines, and separate notes, attachments, execution, and trace information.
- Baseline: `origin/main@731c7e6d43f64e4f8e764c67880be6943afcee15`; branch: `codex/contract-handling-page-normalization-v1`.
- P1: `smart_construction_core` owns explicit wrapper bindings, industry form sections, field order, and labels.
- P0: `smart_core` only resolves explicit bindings and preserves native constraints; the frontend only preserves explicit sections and omits navigation for sections with no presentable content.
- P4: focused tests, browser evidence, delivery documents, and final gates.
- Excluded: contract lists, changes, settlement, payment, save, approval, permissions, amount computation, attachment-authorization expansion, fixtures, business-data edits, the general workbench, and low-code features.

## Source view → final contract → page result → first divergence

| Formal entry | Source declaration and identity | Final contract | Page result | First divergence and owner |
| --- | --- | --- | --- | --- |
| Income contract | menu `660`, action `609`, wrapper `construction.contract.income`; P1 explicitly maps `contract.income` to policy model `construction.contract`; the native form declares anchored business sections | `PageAssembler` keeps direct-model lookup first, then consumes only an exact `entry_model + category_code + policy_target_model` binding and applies it only when unique. V2 preserves create-hidden and other-profile readonly policy | Identity/basic facts → scope → lines/amounts → notes/attachments; readonly additionally exposes collapsed execution and source trace | Wrapper lookup was a P0 resolver gap whose authoritative alias belongs to P1; task floorplan reclassification of explicit sections was a P0 consumer divergence; income field grouping and order belong to P1 |
| Expense contract | menu `661`, action `610`, wrapper `construction.contract.expense`; P1 explicitly maps `contract.expense`, independent from income | The same generic resolver selects the expense policy and fails closed for missing or ambiguous mappings. Section identity, profile visibility, readonly, and subordinate roles survive | Basic facts lead with supplier/subcontractor, project, date, and owner; expense-specific scope is separate; lines/amounts precede notes; execution and trace are collapsed; historical payment remains accessible but outside primary navigation | Expense grouping, labels, line order, and historical-payment role are P1; a dead link for a profile-empty section was a generic P0 content-detection gap |
| Direct-model counterexample | Action model directly matches `sc.business.category.target_model` | Direct lookup remains first and does not invoke alias inference | Existing behavior is unchanged | P0 regression protection |
| Missing/ambiguous counterexample | P1 provides no binding or more than one target | No policy is selected; no parent traversal, suffix inference, or first-match selection | Income and expense policies cannot silently leak into one another | P0 fail-closed behavior |

## Page result

- The header retains existing mode, status, and action authority. Create hides platform state; readonly/edit profiles retain the declared readonly constraints without changing state values or transitions.
- Both entries use identity/basic facts → scope → lines/amounts → notes/attachments. Execution and trace remain separate from contract maintenance.
- Line identity, unit, quantity, price, and amount precede tender-source and auxiliary codes; empty names are never fabricated.
- Unanchored layout groups remain untitled. Only explicit business sections enter primary navigation. A profile-empty section is omitted, while a partially visible or default-collapsed section with content remains reachable.
- Historical payment stays readonly, collapsed, and accessible, while a P1 subordinate declaration keeps it outside the primary workflow navigation.

## Amount and attachment decision boundaries

| Fact | Current authoritative definition and consumers | This batch |
| --- | --- | --- |
| `amount_untaxed` | The base contract derives it from `line_amount_total`; percentage tax produces `amount_tax`, and `amount_total` is tax-inclusive. Forms, final price, and downstream execution continue to consume it | Preserve field, label, and computation; do not nominate a new primary amount |
| `visible_contract_amount` | `contract_business.py` defines a stored compute/inverse projection of `amount_untaxed` with “standard product contract amount” help; receivable and formal expense projections consume it | Keep it with `amount_untaxed`; do not merge or visually promote either one |
| `attachment_text` | Historical/platform text carrier; income keeps one “historical attachment text”, expense one “platform attachment text” | No migration or substitution with file relations |
| `attachment_ids` | The base model has an `ir.attachment` many-to-many. The expense native form already authorizes the field/widget; equivalent income-form authorization has not been proven | Expense consumes its existing entry; income gains no upload surface; unified authorization is a separate decision |

## Verification and evidence

| Layer | Entrypoint or evidence | Result |
| --- | --- | --- |
| L1 | `make ci.local.iteration` | PASS, 16 tests |
| L1/L2 | `make verify.frontend.native_section_navigation.unit` | PASS, including fully hidden, partially hidden, collapsed-with-content, and subordinate counterexamples |
| L2 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS=contract_handling_page_policy` | PASS, 7 methods / 9 Odoo statistics; covers isolated income/expense selection, cross/missing cases, sections, labels, and state |
| L3 | `make local.dev.upgrade MODULE=smart_construction_core`; `make local.dev.health` | PASS using registered `sc-local-dev` / `sc_dev_demo` / 18081 only |
| L4 light | `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-handling-expense-candidate-359c1ff9/` | Income and expense create/read, existing expense draft edit, 1440/1088×791/390; summaries pass with zero mutations |
| L4 sections | `section-probe/report.json` in the same directory | 1088/390 click, manual scroll, keyboard disclosure, focus retention, and natural expansion pass |
| L4 dark | `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-handling-final-preflight-359c1ff9/dark-structure-1088-390-v2/summary.json` | Expense create/read at 1088×791 and 390×844 pass section navigation, middle/bottom, and responsive-boundary checks; zero mutations and errors |
| L5 | `make ci.delivery.freeze.prepare`, one final `make ci.local.quick`, independent review | Recorded after freeze in off-repository exact-head receipts; this tracked document will not be changed afterwards |

One optional dark manual-scroll parameter timed out inside the runner’s supplemental wait and was classified as a `validation_tool_defect`. Removing that redundant parameter left the governed runner’s built-in section-click and stable-state journey, which passed. The failed input was not retried unchanged, and neither product nor verification tooling was modified.

## Known boundaries, risk, and rollback

- Both source lines in the readonly sample have empty BOQ name and unit values. No name or record was fabricated; non-empty business identity remains uncovered.
- No income draft was available and an effective record’s `/f` route was not counted as edit coverage. Expense edit used one existing draft and did not save.
- Real save, approval, all roles, changes, settlement, payment, formal attachment authorization, and amount-definition decisions were not tested.
- P0 risk is limited to explicit category mapping, native hidden constraints, and section navigation. Tests prove isolation, fail-closed ambiguity, preservation of valid sections, and no contract-model special case in production P0.
- Rollback order: P0 frontend section consumption, P0 mapping/constraint propagation, then P1 expense and income view/policy commits. No business-data rollback is required.

## Next step

- After freeze, run Quick once, perform exact-head independent review, and use governed remote delivery. Stop on head drift, conflict, or a new blocker.
- Primary amount definition, formal income attachment entry, and a non-empty line sample remain separate decisions/data prerequisites.
