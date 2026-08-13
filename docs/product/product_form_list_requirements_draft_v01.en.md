# Product Form and List Requirements Draft v0.1

[中文](product_form_list_requirements_draft_v01.md)

## Decision

The original “construction management system visual form specification” is retained only as a business requirement pool. It is not an authority for menus, fields, lifecycle states, permissions, or frontend implementation. Its 71 items are now registered in a machine-readable matrix with four dispositions: `implemented`, `contract_gap`, `planned`, and `merge`.

The baseline is `9e2d2cb2e57d0465734cbc5900857a935fb88c51`. Authority is limited to mainline source, menus, Actions, models, native views, page contracts, and static permission declarations. Every item without authenticated runtime evidence remains `runtime_unverified`.

Machine assets:

- [71-item fact matrix](../../config/product_form_list_requirement_matrix_v01.json)
- [Six representative page contracts](../../config/representative_page_contracts_v01.json)
- [Industry benchmark page-quality baseline](../../config/industry_benchmark_page_quality_v01.json)

## Industry Benchmark Gate

Benchmarking is an input to page contracts, not a visual review postponed until release. Public official evidence is used only to extract capability patterns. It does not prove parity with a competitor and is not used to score a competitor without hands-on testing.

Repeated completeness patterns include contract-change-payment-settlement traceability, budget/contract/actual-cost comparison, project-finance-supply-chain-tax integration, source-document relations, operating metrics, and data-asset accumulation. Convenience patterns include source-data carry-over, downstream document generation, mobile approval, multi-role mobile work, workflow-driven handling, risk alerts, and configurable fields/processes. Official references: [Glodon construction cost management](https://www.glodon.com/product/375), [Glodon construction case](https://www.glodon.com/case/357.html), [Ming Yuan Cloud project management](https://www.mingyuanyun.com/solutions/urban-development/project-management), [Ming Yuan Cloud cost management](https://www.mingyuanyun.com/products/project-construction-management/cost-control), [Kingdee construction solution](https://www.kingdee.com/solutions/architecture0.html), and [Yonyou BIP Project Cloud](https://www.yonyou.com/subject/xmy?withYonyouMenu=&zixun=0).

Every representative page is assessed on two groups:

- Information completeness: identity, lifecycle, source-to-result trace, lines/totals, evidence, control baseline, permission scope, and report definition.
- Handling convenience: task-first screen, one-time entry, downstream generation, progressive disclosure, search/batch, mobile handling, exception recovery, and cross-document navigation.

The evidence scale is 0-3. Before rollout, every applicable dimension must reach at least level 2, “complete contract and operable main path.” Level 3 requires authenticated browser evidence with real runtime data.

## Architecture Boundary

- Formal Product Layer: primarily the P1 construction product, with declared P0 contract and renderer dependencies.
- Layer Target: product fact audit, native-view mapping, and semantic page-contract design.
- Module: `docs/product`, `config`, and read-only static verification.
- Standard vs User-Specific: standard-product candidates only; no P2 customer preference or P3 tenant runtime configuration.
- Why Here: page design must bind to menu, Action, model, native view, permission, and lifecycle facts first.
- Why Not Elsewhere: industry semantics do not enter `smart_core` or shared frontend code; unconfirmed fields do not enter low-code runtime state.
- Blast Radius: no model, menu, Action, runtime contract, database, dependency, or frontend component behavior changes.

## Source Inventory

| Source group | Count | Primary destination |
| --- | ---: | --- |
| Workbench | 4 | Workbench |
| Tendering | 5 | Project Center |
| Partners | 3 | Project Center |
| Project Management | 14 | Project Center; cost analysis splits into Cost Center |
| Contracts and Settlements | 7 | Contract Center |
| Finance | 17 | Finance Center; ledgers and reports move to Report Center |
| Accounting | 7 | separate accounting topic; reports move to Report Center |
| Administration | 5 | Administration Center |
| Tax | 9 | Tax Center; summary ledger moves to Report Center |

The source omits dedicated Cost Center, Report Center, and Product Configuration coverage. `Project Profitability Analysis` is therefore recorded as derived requirement `DERIVED-COST-001`; it does not replace any of the original 71 items.

## Four Dispositions

| Status | Meaning | Implementation rule |
| --- | --- | --- |
| `implemented` | mainline has a clear menu or capability carrier | optimize only after page-contract acceptance |
| `contract_gap` | a model or entry exists but page, lifecycle, permission, or source-type contracts are incomplete | close the contract first |
| `planned` | no formal product closure exists | do not start ordinary page development |
| `merge` | duplicates an existing handling surface, ledger, or report | merge into one fact object or read-only projection |

A menu proves an entry exists. It does not prove fields, required rules, approval, export, print, delete, or runtime role availability.

## Seven Page Recipes

| Recipe | Applies to | Required contract |
| --- | --- | --- |
| `dashboard` | workbench and cockpit | metric definition, period, filters, drill-down, refresh time |
| `master_data` | customer, supplier, employee, material master | identity, validity, references, archive permission |
| `business_document` | contract, payment, receipt, invoice | summary, parties, current task, lines, relations, evidence, workflow |
| `complex_workspace` | current accounts, refunds, reconciliation | multiple facts, differences, handling actions, trace chain |
| `ledger` | contract, fund, invoice ledger | read-only facts, source, balance, period, drill-down |
| `report` | project, cost, fund, tax report | metric definitions, dimensions, period, totals, refresh time |
| `configuration` | forms, fields, workflow, permissions | scope, version, publish, rollback, impact |

Complex documents use full pages. Dialogs are limited to low-risk short master data or auxiliary selection. A 390px viewport uses one column. Read-only detail uses business summaries rather than a page of disabled inputs.

## Six Representative Pages

| Page | Recipe | Current fact | Contract focus |
| --- | --- | --- | --- |
| Customer Master | master data | `res.partner` and customer Action | identity, contact, settlement/qualification, archive boundary |
| Income Contract | complex document | `construction.contract.income` | parties, tax and amount, performance, settlement, evidence |
| Material Receipt | line document | `sc.material.inbound` | source type, lines, acceptance, conditional contract requirement |
| Payment Request | approval/fund document | `payment.request` | settlement basis, payable amount, account, approval actions |
| Output Invoice | tax-linked document | `sc.invoice.registration` | source application, tax, invoice facts, reversal relation |
| Project Profitability | report | `project.profit.compare` | income, budget, actual cost, profit, definitions |

Each page must cover list/report, create/edit where applicable, read-only detail, empty state, forbidden state, and the 390px mobile state.

## Cost Source Contract

Labor, material, equipment, and subcontract cost documents must not all require a contract. Candidate source types are:

1. `contract_execution`: contract execution; contract required.
2. `spot_purchase`: spot purchase or casual labor.
3. `site_variation`: site variation.
4. `provisional_pending_contract`: provisional or pending contract.
5. `adjustment_reversal`: adjustment or reversal.

The frontend consumes backend-declared source type, required, and readonly outcomes; it does not infer them.

## Delivery Order with the Component Topic

1. Merge this fact matrix and representative contract topic first.
2. Create a fresh component-foundation branch from the then-current main.
3. Preserve `Sc*` business-semantic components; any third-party UI framework stays behind them.
4. Stack the six-page branch on the component branch and validate both together.
5. Merge component foundation first, then restack and merge the six pages.
6. Roll out center by center in small PRs; do not rewrite 71 pages at once.
7. Run accounting as a separate product topic.

The old `codex/tdesign-enterprise-ui-foundation-v1` branch is only a candidate code source. This topic neither selects nor adds a UI dependency.

## Entry Gates for the Next Stage

- the matrix static gate passes;
- Action, model, native-view, and permission anchors are complete for six pages;
- lifecycle and backend action contracts are explicit;
- the component inventory is derived from shared needs across the six pages;
- TDesign or another framework has an independent technical decision and does not alter the `Sc*` semantic API;
- later browser acceptance supplies runtime role, real-data, empty, forbidden, and mobile evidence.
- every applicable completeness and convenience dimension reaches at least level 2 on all six pages.
