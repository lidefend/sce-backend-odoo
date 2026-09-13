# Contract Collection and Work-item Reading Efficiency (2026-09-13)

## Objective and boundary

- Single product objective: expose the income-contract primary identity at the normal collection reading origin, and keep type, title, amount, and primary action readable in My Work at medium widths such as 1088px.
- P1 scope: existing field order in the `smart_construction_core` income-contract native tree.
- P0 scope: generic responsive layout of shared product work-item cards.
- Excluded: model facts, contract schema, permissions, routes, save and approval behavior, the general workbench, low-code features, and business data.

## Source configuration → contract → renderer map

| Page | Source configuration | Final contract | Renderer consumption | First divergence and owner |
| --- | --- | --- | --- | --- |
| Income-contract collection | `view_construction_contract_income_tree` places `subject` after status, date, archive, partner, and project; the action declares `tree_column=subject` and `presentation_mode=source_order` | `PageAssembler` emits `config.sheet.columns` in `columns_schema` order and retains the 220px subject width | `HierarchicalWorksheet` consumes `sheet.columns` directly; the title sits beyond the unscrolled 1088 viewport | The P1 source list order first diverges from identity-first reading; P0 does not reorder business columns |
| My Work | `PaymentRequestWorkItemService` explicitly emits `business_type`, `record.label`, a money fact, and contract-provided action tiers | `ProductMyWorkWorkspace` typing and `productMyWorkPresentation` preserve identity, amount, and action hierarchy | `MyWorkApprovalWorkspace` uses a four-column main area plus a separate action column above 640px; its one-item primary summary still uses a three-column grid, causing the type to collapse character by character at medium width | Generic P0 work-item layout is the first readability divergence; there is no P1 field or contract gap |

## Implementation steps

1. P1: move only income-contract `subject` to the first tree column and assert the final contract column order.
2. P0: move card actions to their own row at medium widths, prevent type-label character breaks, and give the single primary fact the full summary slot; extend the static guard.
3. L1: run `make ci.local.iteration`, the non-zero income-contract profile test, the My Work static guard, and strict frontend type checking.
4. L3/L4: after the governed P1 incremental upgrade, inspect only the affected 1088 surfaces in `local.dev`; freeze and run Quick once only after product acceptance.

## Baseline and prior evidence

- Baseline: `e9f78ff079817ebcd6154e77e872cefbaf62bf81`.
- Complete worktree fingerprint: `3aef44591a704d588fb9fb48f12a34d8d7fa5b37dcb3e2977281d64db931871c` (7424 paths).
- Existing 1088 dark evidence at `07758bd7…` shows the income-contract title after the project column and the My Work type label stacked vertically. From that evidence to this baseline, the My Work target source is unchanged; the income-contract chain only replaced a disclosure glyph with an icon, without changing column order or widths. This evidence is used for reproduction and impact analysis, not as current-candidate acceptance.

## Risk and rollback

- Risk: the P1 order affects all standard income-contract deployments; the P0 medium-width layout affects all formal My Work items.
- Control: no field, value, or action is removed or changed; P1 and P0 remain separate commits with focused shared-surface counterexamples.
- Rollback: revert the P0 layout commit first and the P1 view commit second; no database data rollback is required.

## Layered validation progress

| Layer | Entrypoint | Result |
| --- | --- | --- |
| L1 | `make ci.local.iteration` | PASS; 16 tests |
| L1 | `make verify.frontend.my_work_approval.guard`, `make verify.frontend.typecheck.strict` | PASS |
| L2 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS=my_work_backend` | PASS; 20 tests; three pre-existing audit-model skips are not batch failures |
| L2/L3 | The first contract-profile run identified that the installed view still contained the old XML; the explicitly declared `local.dev.upgrade` then performed the incremental upgrade | Upgrade PASS; authoritative `sc-local-dev/sc_dev_demo` identity PASS |
| L2 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS=contract_execution_component_profile` | PASS after upgrade; five test methods, seven Odoo test statistics, zero failures |
| L2 | `make verify.frontend.hierarchical_worksheet.unit`, `make verify.frontend.state_dashboard.unit` | PASS; respectively 18 Python tests + 15 interaction cases, and 24 Python tests + My Work presentation cases |
| L4 | Read-only 1088 product check | PASS; dark 1088×791 covered `/my-work` and income contracts at `/a/609?menu_id=660`, with `mutationCount=0`, empty errors/failures, and zero root-page horizontal overflow |

The initial contract-target failure was classified as a stale installed view before the required upgrade. The upgrade changed that environmental prerequisite, so the subsequent passing run was not a retry of an unchanged failure. Quick, fixture reset, release snapshot, and the browser matrix have not been run during development.

Before L4, `/tmp/sc-local-dev-candidate-frontend.pid` blocked startup because it remained bound to the deleted `/home/lidefend/workspace/sce-backend-odoo-batch2a-personnel-auth` worktree, old head `23225efbb8bf5bb8b0276af7ec016eb5e5614612`, and a still-running static service on port 5176. After separate authorization, cleanup verified the pidfile permissions, worktree path, head, command, process group, and port listener, then terminated only that old process and removed its pidfile. No governance tool, other frontend, database, worktree, or port configuration changed.

The governed candidate frontend then started successfully for the same product head, `4c806807028b3276c470d634df277f02ece90cb5`. The summary created at 2026-09-13 22:08:00 +08:00 is `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-work-reading-efficiency-4c806807-dark-1088/summary.json`; the desktop screenshots are `desktop-my-work.png` and `desktop-income-contract-workspace.png`. Manual review confirmed that the unscrolled income-contract table starts with Contract Title, while My Work keeps the type label horizontal and gives the title, amount, and Submit for approval action clear reading positions. The existing carrier also produced paired 390×844 samples, but this batch's product conclusion relies only on the required 1088×791 scenario.
