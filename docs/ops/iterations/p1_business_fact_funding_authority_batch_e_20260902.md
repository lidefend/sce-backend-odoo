# P1 Business Fact Professionalization — Batch-E

Date: 2026-09-02

## Product boundary

- Formal Product Layer: P1 construction industry standard product.
- Layer Target: `smart_construction_core` project funding baseline, payment-request funding snapshot, actual-payment allocation journal and native Odoo finance flow.
- Standard vs User-Specific: construction-industry standard.
- Why Here: versioned project funding authority, payment-period eligibility and actual-cash attribution are construction finance facts shared by every standard deployment.
- Why Not Elsewhere: `smart_core` owns generic mechanisms; P2 owns customer preferences; P3 is only a configuration carrier; P4 owns delivery/replay tooling; the frontend must render rather than derive these facts.
- Blast Radius: `project.funding.baseline`, its lines, `payment.request`, `payment.ledger`, `project.funding.actual.event.allocation`, the project funding-reservation concurrency version, payment-execution notification isolation, the historical contract-allocation backfill location, their native views/security, migrations `17.0.0.143` through `17.0.0.145` and focused tests. Cost recognition, general finance projections, public intent contracts, startup chain, custom frontend and runtime topology are excluded.

## Frozen entry and runtime identity

- Branch: `refactor/p1-business-facts-professionalization-v1`.
- Entry HEAD: `d1f695fb91310ee5c59da7427e01ec3654853616`.
- Repository baseline: `394b2ffe20c48255d2c8c0788fbfc36456c7d007`.
- Governed lifecycle: `local.dev` only; Compose project `sc-local-dev`; database `sc_dev_demo`; dbfilter `^sc_dev_demo$`; filestore and volumes `sc_local_dev_*`.
- Database role: persistent internal product/demo development database, not customer, sample, clean-install, acceptance or production authority.

## Model authority v1

1. A normalized funding baseline is created only as a draft with immutable company/currency economic-identity snapshots, control-period start/end, positive cap, stable project-scoped version number/key and positive plan lines whose total exactly equals the cap. Project ownership changes cannot rewrite baseline, line or allocation history, and cross-currency revision copying fails closed.
2. Creation and lifecycle operations acquire all involved project/baseline rows in one sorted global order. Activation and close also advance the same writable project reservation version used by payment submission, so a concurrent authority switch cannot leave a request bound from a stale repeatable-read snapshot. Activation is backed by a partial unique database index allowing one active baseline per project. A successor explicitly references the previous authority; activation atomically supersedes an active predecessor and records the inverse successor link when reopening authority from a closed predecessor.
3. Active, superseded, closed and cancelled authorities cannot be rewritten or deleted. Plan-line ownership is immutable and its identity is server-generated; only the in-process revision service can carry lineage into a successor. Close and revision require a persisted audit reason; revisions append a successor instead of modifying history.
4. A payment request snapshots the applicable normalized baseline during controlled submission. The baseline must match project, company, currency and request date. Submission locks requests first, reloads their project scope, locks projects, increments a shared writable reservation version and aggregates every request in the batch before enforcing the cap. Under PostgreSQL repeatable-read, competing same-project submissions therefore serialize by retry instead of evaluating the same stale snapshot. The binding cannot be forged, cleared or switched later.
5. Allocation is an append-only journal, created only by the payment-ledger service with an in-process authority token. Direct create/write/unlink is denied even to sudo callers.
6. Every allocation has a service-owned operation namespace, stable fact key, entry type, signed effective amount, effective date/time and normalization state. Allocation, correction and reversal namespaces cannot collide. Each operation key freezes the complete sorted line/original set, currency-rounded amounts and correction reason; exact replay is idempotent while subset, superset, amount, reason or ledger reuse fails closed before append.
7. The allocation transaction locks request, project, baseline, plan line and payment ledger in one global order and rechecks fresh state before writing.
8. Four conservation boundaries are enforced in the same transaction: plan lines equal baseline cap at activation; net line allocation cannot exceed planned amount; net event allocation cannot exceed posted payment; net baseline allocation cannot exceed the cap.
9. Payment reversal never deletes or edits allocation history. It appends one linked negative fact per unreversed allocation, inherits the original allocation's project/company/currency economic snapshot even after later project ownership changes, then records reverse navigation metadata and proves a zero net event allocation.
10. Aggregation uses grouped database queries rather than loading allocation histories into Python. Payment reservation SQL scopes posted-ledger aggregation to the target baseline and reuses one evaluation cache across a submit batch; 1/10/50 request regression proves bounded query growth. Covering indexes support line-, baseline- and event-based signed totals.

## Historical migration policy

- Version `17.0.0.143` adds schema carriers before registry load and indexes after history classification.
- Version `17.0.0.144` replaces the old unconditional amount/successor constraints with normalized-only amount enforcement and live-successor uniqueness, preserving already-correct constraint/index OIDs on replay.
- Version `17.0.0.145` freezes baseline/allocation company and currency identities, adds the project reservation concurrency version, and quarantines missing or mismatched historical economic identity instead of inventing it. Global record rules exclude unresolved baseline, line and allocation evidence from every user-facing company scope, including multi-company finance managers; it remains available only to governed migration/repair code.
- Historical baseline periods and authoritative version order are never guessed. Legacy rows receive only a trace key and explicit unresolved-period/authority classification; duplicate active authorities are quarantined.
- Historical line keys derive from immutable row identity. Allocation rows with valid relations retain their original amount and become unresolved-period evidence; missing or inconsistent relations become `legacy_unresolved_relation`.
- Conservation violations become `legacy_unresolved_conservation`. No unresolved history enters normalized enforcement or reporting silently.
- The pre-migrations perform difference writes and are replay-safe. Post-migrations verify exact named-index uniqueness, keys, includes and predicate shape, replacing only stale same-name indexes. Historical contract-allocation totals are backfilled after registry schema creation instead of racing new stored fields from a model `init()` hook.

## Native Odoo journey

- Finance readers, users and managers can traverse the final active funding-summary, payment-ledger and allocation-journal menu ancestry, survive native `load_menus`, and open their tree/form views. The final finance overlay keeps `payment.ledger` under the active finance center instead of the unpublished legacy analysis group.
- Finance users and managers can open an allocation wizard from a posted payment ledger bound to a normalized baseline. The wizard submits only line IDs and positive amounts to the same authoritative service; it cannot write the journal directly. Correction mode includes every baseline line, including a currently full line whose capacity is restored atomically by the selected reversals.
- Only finance managers can activate, cancel, close or revise a baseline. Close/revision use a modal wizard with a mandatory audit reason and return the created revision as a normal native form.
- Real role execution proves reader denial, finance-user allocation, manager correction and manager `sc.payment.execution.action_reverse_payment()`. Each chatter delivery runs in its own database savepoint, so even a PostgreSQL failure inside notification delivery cannot abort an otherwise valid paid/reversal fact transition.
- The allocation journal is visible in both its finance menu and the source payment-ledger form, including reversals and net effect.

## Verification evidence

- Python compilation, XML registry loading, static boundary tests and `git diff --check` — PASS.
- Governed `local.dev` incremental upgrade through `17.0.0.145` — PASS, including replay after external runtime interruption; demo authority verification reports installed module, authoritative finance membership and CNY company currency.
- Focused `p1_funding_authority` suite — PASS, 18 post-test methods / 20 Odoo statistics, 0 failures, 0 errors. In addition to lifecycle, conservation, idempotency, native-role and activation-concurrency coverage, it proves immutable baseline/line/allocation/reversal company-currency snapshots across project ownership changes, direct and replay-safe `17.0.0.145` anomaly quarantine with user invisibility, a real same-project concurrent submit race, and an activate-versus-submit race. Both authority races observe `SerializationFailure`; fresh-transaction retry binds the current baseline and preserves the cap.
- Registered legacy `smart_core` allocation ORM suite — PASS, 38 post-test executions / 21 `smart_core` Odoo statistics, 0 failures, 0 errors after moving all writes to the authoritative service and preserving hidden/missing identifier equivalence.
- Final post-slice `sc_gate` — PASS, 307 post-test methods, 390 `smart_construction_core` and 11 demo Odoo statistics, 0 failures, 0 errors.
- Business-model audit/standard — PASS: 372 models, 36 projections, zero unregistered projections, registry shape/path gaps, unclassified models or undeclared standard gaps.
- Minimum ACL guard — PASS. Personal-data scan — PASS with zero confirmed matches; high-confidence secret scan — PASS with zero confirmed matches.
- `make verify.native.business_fact.static` remains blocked by the pre-existing P4 validation-tool defect: the registered target references missing `scripts/migration/business_fact_upgrade_replay_flow.sh`. Batch-E does not create an in-topic substitute; `make pr.push` remains prohibited.

## Rollback and release status

- Batch-E is one independently acceptable commit and rollback unit. Schema rollback is not destructive; database evolution follows forward-fix plus governed incremental upgrade.
- No frontend, contract, runtime-profile, database, port, volume, fixture or credential authority was created or changed.
- Browser/release acceptance and PR push are intentionally not claimed while the known P4 replay-tool gap remains unresolved.
