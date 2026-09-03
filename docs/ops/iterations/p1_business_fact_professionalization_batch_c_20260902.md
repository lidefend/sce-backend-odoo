# P1 Business Fact Professionalization — Batch-C

Date: 2026-09-02

## Product boundary

- Formal Product Layer: P1 construction industry standard product.
- Layer Target: `smart_construction_core` cost domain models, source writers, native views, projections, tests and fact registry.
- Standard vs User-Specific: construction-industry standard.
- Why Here: project cost recognition, source provenance, period ownership and cost reporting are construction business facts.
- Why Not Elsewhere: no platform mechanism, frontend inference, customer preference or one-off ops repair owns these semantics.
- Blast Radius: `project.cost.ledger`, `project.cost.period`, purchase/stock/account/material/equipment producers, cost/profit/project projections and their native Odoo acceptance tests.

## Frozen entry

- Branch: `refactor/p1-business-facts-professionalization-v1`
- Entry HEAD: `de473e258d6c52dbb0172898aab30ac03b107a95`
- Baseline: `394b2ffe20c48255d2c8c0788fbfc36456c7d007`
- Governed runtime: `local.dev` / `sc-local-dev` / `sc_dev_demo` / `^sc_dev_demo$` / `sc_local_dev_*`
- Independent value: backend facts and the complete native Odoo journey are acceptable without the custom frontend.

## Problem statement

The current ledger stores purchase commitment, stock receipt, material consumption, supplier settlement, equipment usage and accounting recognition as indistinguishable `amount` rows. Existing projections then label an unfiltered sum as actual cost. Source identity is descriptive rather than enforced, generated rows are directly mutable, writer loops are query-amplifying, and project/period/WBS/currency consistency is not closed.

## Model v2 semantic freeze

1. `recognition_stage` is mandatory and records the economic stage: manual adjustment, commitment, receipt/accrual, consumption, settlement/accrual, accounting recognition or legacy unresolved evidence.
2. `reporting_treatment` is mandatory and records whether a row is an actual-cost fact or a memorandum/non-actual fact. Existing fields named “actual cost” may aggregate only `reporting_treatment = actual`.
3. Purchase confirmation is a commitment, not actual cost. Incoming stock is receipt/accrual evidence, not consumption. Material outbound and equipment usage are operational consumption. Material settlement is settlement/accrual evidence. Posted expense/account lines are accounting recognition. Manual source-free rows are explicit manual adjustments.
4. Generated facts require the complete immutable identity `(source_model, source_id, source_line_id)` and may be mutated or withdrawn only through the model service. Source-free rows remain role-maintained manual facts. Partial identities are invalid.
5. `amount` is normalized to the project company's currency. `source_amount` and `source_currency_id` preserve the source denomination; conversion uses the fact date and project company. No FX revaluation engine is introduced.
6. Period and WBS must belong to the same project; project company and reporting currency must agree. Violations fail closed.
7. Purchase/account/stock automatic ingestion is a single-choice company-owned product setting. The former global `ir.config_parameter` carrier is retired because it cannot represent different authorities per company; contradictory values fail closed at the company model.
8. Cost projections keep their existing public shape but consume only authoritative actual rows. Stage-specific investigation remains available in native Odoo views.
9. Historical rows with a partial or unsupported source identity are retained as `legacy_unresolved` memorandum evidence. They are never guessed, merged, deleted or admitted into actual cost during module upgrade.
10. Odoo `install_mode` may replay registered legacy XML evidence with an incomplete identity so installed demo/fixture modules remain upgradeable; that exception is unavailable to normal business calls and never promotes the row beyond `legacy_unresolved`.

## Delivery slices

### C1 — authoritative ledger model

- Add recognition, treatment and source-currency provenance.
- Add complete identity constraints, generated-fact immutability and a partial unique database index.
- Batch-resolve periods and validate project/WBS/period/company/currency containment.
- Establish batch upsert/withdraw services.

### C2 — producers and lifecycle

- Migrate purchase, stock, account, material outbound, material settlement and equipment writers to the service.
- Normalize source currency at the producer boundary.
- Remove stock-test fallback and prove retry idempotency.
- Make supported reversal/draft transitions withdraw only their own generated facts.

### C3 — projections and native acceptance

- Filter actual-cost projections by reporting treatment.
- Expose recognition/provenance in native tree, form, search, pivot and graph views.
- Prove manual/generated permissions, source traceability and stage-specific reporting.

## Validation and rollback

- Required gates: Quick/static guards, non-zero focused ORM tests, governed incremental module upgrade, fixture reset and release snapshot where registered, governed native Odoo user journey, independent exact-fingerprint review, generated reports and `make pr.push` only after all earlier gates pass.
- A zero-test result fails the batch.
- Rollback is by Batch-C commit boundary. No repair script, new database, runtime profile, port, volume, credential or frontend workaround is permitted.

## Implemented result

- Upgraded `project.cost.ledger` from an undifferentiated amount log to a stage-explicit cost-fact model with project-company currency normalization, original amount/currency evidence, complete generated-source identity, active/withdrawn lifecycle, and legacy-unresolved quarantine.
- Centralized all generated mutations in one batch upsert/withdraw service with deterministic period resolution, a shared 64-bit source-header advisory lock, stale-snapshot `FOR UPDATE` detection, bounded heterogeneous SQL correction writes, a shape-audited partial unique source index, retry idempotency, and user-level immutability. The lock order is fixed as source header, then project/period, then existing fact rows so withdrawal and replay cannot deadlock. The internal service authority is an in-process identity token and cannot be forged through RPC context.
- Migrated purchase, stock, accounting, material outbound, material settlement and equipment usage writers. Purchase cancellation and accounting draft transitions withdraw facts; supplier returns create negative receipt facts using the locked original receipt valuation and currency; customer/internal returns are excluded from that path; project material returns create negative operational-consumption facts.
- Kept manual source-free adjustments explicit and role-maintained. Existing actual-cost projections now include only active `financial_actual` and `manual_actual` facts; commitments, receipts, settlements and operational consumption remain independently inspectable and cannot be double-counted as financial actual.
- Enforced source/project company compatibility on purchase, accounting and stock carriers; retained accounting `amount_currency/currency_id` as source denomination while using the posted `balance` as authoritative company-currency amount; made period text and period record derive consistently from fact date; made the automatic-source authority company-scoped and added a one-time `17.0.0.139` migration from the retired global parameters.
- Upgraded project material returns to reference the exact issued line, lock that origin, conserve cumulative returned quantity, and inherit the original unit price. Supplier returns likewise require the active original receipt fact and never guess from purchase or standard price. Standard cost-code creation includes archived identities, reactivates a compatible code and fails before schema upgrade when legacy duplicates exist.
- Upgraded the return model again after concurrency review: the issued line now stores the authoritative cumulative returned quantity, all lines in one return document are aggregated by origin, and concurrent return transactions serialize on that origin. Submitted/confirmed outbound, settlement and equipment-usage facts are immutable at both header and line level so a terminal source cannot drift away from its generated ledger evidence.
- Period closure now participates in the same project-then-period lock order as fact writes. A period cannot become locked between validation and mutation, and a late writer that waited behind the lock observes the final locked state and fails closed.
- Added the schema-safe `17.0.0.141` post-migration and explicit `normalization_state`. Historical rows already denominated in the project-company currency are deterministically normalized; a historical foreign-currency amount keeps its exact old currency and amount as source evidence, receives zero company-currency amount, and is quarantined as `legacy_unresolved_currency` / `memorandum` until a separately governed conversion can prove the applicable rate. Projectless or companyless evidence is preserved as `legacy_unresolved_owner` and excluded by company record rules. The migration performs only idempotent difference writes and rebuilds the cumulative-return authority in one CTE update. Version `17.0.0.142` removes the schema-level currency default and non-null guess for quarantined history, while a model constraint and both normal/service creation boundaries still require every normalized new fact to use the project-company currency. Its idempotent post-migration clears stale company projection from unresolved-owner history without inventing ownership or currency.
- Exposed recognition stage, reporting treatment, fact state and source currency in native Odoo tree, form, search, pivot and graph views. Default native analysis uses a removable active filter instead of a hard action domain, and generated facts provide an ACL/record-rule-preserving source navigation action. The canonical report-center cost-ledger menu now includes `cost_read`; a real follower-based read-only user resolves the final manifest-loaded report-center parent chain, survives Odoo's native `load_menus`, opens action/tree/form, reads only record-rule-visible facts, and remains denied on source models without their native ACL. Reader/operator/manager behavior is verified against both ledger and source-model ACLs. No frontend, public intent, startup chain or `smart_core` contract changed.
- Updated the projection registry with the exact source set, mutation policy, lifecycle owner, idempotency key and focused acceptance probes.

## Verification evidence

- Python compilation, JSON parsing and `git diff --check` — PASS.
- `make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_core` — PASS through `17.0.0.142` on `sc-local-dev` / `sc_dev_demo`; the nullable historical-currency schema transition, post-migration, and post-upgrade authority check passed with installed module and CNY company currency.
- `make local.dev.test MODULE=smart_construction_core TEST_TAGS=/smart_construction_core:TestCostFactModelV2,/smart_construction_core:TestCostFactConcurrencyV2` — PASS, 19 methods / 23 Odoo test statistics, 0 failed, 0 errors. Coverage includes the full fact semantics and role matrix, unforgeable normalization state, terminal source/state immutability, schema-safe and idempotent foreign-currency quarantine using the real migration script, native return onchange/view behavior for historical sources without a material catalog, grouped return conservation, bounded insert/correction/withdraw/reactivate query growth, withdrawal/replay serialization, receipt-correction/supplier-return origin consistency, period-lock versus late-write serialization, and concurrent project-return conservation. The concurrency probes deliberately exercise stale-snapshot serialization failures and prove the final authoritative state after the governed outer retry boundary.
- `make local.dev.test MODULE=smart_construction_core TEST_TAGS=cost_fact_stock_writer,product_system_settings` — PASS, 3 methods / 7 Odoo test statistics, 0 failed, 0 errors. Covers real supplier receipt, exact locked supplier-return valuation, customer-return exclusion and independent company source authorities.
- `make local.dev.test MODULE=smart_construction_core TEST_TAGS=equipment_usage_product` — PASS, 1 method / 3 Odoo test statistics, 0 failed, 0 errors.
- `make local.dev.test MODULE=smart_construction_core TEST_TAGS=cost_fact_projection_v2` — PASS, 4 methods / 8 Odoo test statistics, 0 failed, 0 errors.
- `make local.dev.test MODULE=smart_construction_core TEST_TAGS=/smart_construction_core:TestP0StateClosure` — PASS, 78 methods / 80 Odoo test statistics, 0 failed, 0 errors after upgrading its shared project fixture to explicit company ownership.
- Latest focused `cost_fact_v2` regression — PASS, 17 methods / 19 Odoo test statistics, 0 failed, 0 errors. The real migration scripts preserve owner-unresolved and currency-unresolved evidence without guessing; repeat replay also preserves the PostgreSQL tuple identity (`ctid`), proving physical as well as semantic idempotence.
- Combined owned regression (`cost_fact_v2,cost_fact_concurrency_v2,cost_fact_stock_writer,product_system_settings,equipment_usage_product,cost_fact_projection_v2`) — PASS, 31 methods / 45 Odoo test statistics, 0 failed, 0 errors. A known-owner, unknown-source-currency row receives only the standard reporting currency and remains quarantined: replay never backfills that reporting currency as an invented source denomination.
- `make local.dev.test MODULE=smart_construction_core TEST_TAGS=sc_gate` — PASS, 289 methods, 0 failed, 0 errors (370 core + 11 demo Odoo test statistics). The earlier Batch-C run correctly failed four legacy fixture paths that used companyless projects; the model remained strict and the fixtures were upgraded.
- `make verify.backend_business_fact.model_audit` and `make verify.backend_business_fact.model_standard` — PASS: 372 models, 36 projections, zero unregistered projection models, zero registry shape/path gaps, zero unclassified models and zero undeclared standard gaps.
- `make verify.role.acl.minimum_set.guard`, `make security.personal_data_scan`, and `make security.secrets.scan` — PASS; zero confirmed personal-data or high-confidence secret matches.
- First through sixth exact-fingerprint independent reviews — REQUEST_CHANGES. The candidate was governably thawed after each review. The fifth review found that schema-level required/default currency could still guess or block unresolved-owner history, and that `cost_read` lacked a complete native menu path. The withdrawn v6 candidate then exposed a deeper replay concern: a second run could reinterpret an assigned reporting currency as historical source evidence and could issue no-op tuple rewrites. The v7 fact-domain and ORM reviews approved those repairs, while the v7 native review found that a later taxonomy XML reparented the cost ledger below a subsequently deactivated menu, making the leaf-only visibility assertion a false positive. Final manifest ownership now keeps the ledger under the active report center, and the acceptance test validates the entire active/visible ancestor chain plus Odoo's real `load_menus` result. The governed upgrade, focused 17/19, owned 31/45 and full 289-method gates all pass after this repair.
- v8 exact-fingerprint fact-domain, native-journey and ORM/performance reviews — APPROVE with zero S0-S3 findings. All reviewers independently bound digest `7201b1ae2f6a7d8e88f937cedd54440a94f7da33793191d00785ca5985e359cb`, scope `9f6415a689d869b18a24ce0a9ac370e9b0b205874cf573ba3b512f301e75057f`, 7146 paths, baseline `394b2ffe20c48255d2c8c0788fbfc36456c7d007` and HEAD `de473e258d6c52dbb0172898aab30ac03b107a95`; pre/post review recomputation was stable.
- `make verify.native.business_fact.static` — FAIL, classified `validation_tool_defect` owned by P4: registered target references absent `scripts/migration/business_fact_upgrade_replay_flow.sh`. The same pre-existing gap was already declared before Batch-C and no P1 workaround was introduced; therefore `make pr.push` remains prohibited.
- The broad `TEST_TAGS=cost` run is not acceptance evidence: it selected unrelated BoQ tests and exposed an existing `project.cost.plan.node` versus `project.cost.plan.line` assertion. The two owned projections were rerun through the unique `cost_fact_projection_v2` tag and passed.

## Review freeze and rollback

- Independent reviewers must bind the final complete tracked/staged/untracked fingerprint produced after this document and the delivery-context log are frozen.
- Any product mutation after review invalidates the fingerprint and requires focused revalidation plus repeat review.
- Batch-C is one commit rollback unit. Database schema changes follow forward-fix plus governed module-upgrade policy; destructive data cleanup is not authorized.
