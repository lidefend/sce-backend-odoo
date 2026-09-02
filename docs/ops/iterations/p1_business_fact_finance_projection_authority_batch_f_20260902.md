# P1 Canonical Finance Projection Authority — Batch-F

## Boundary

- Entry HEAD: `fe47096ed242863143ea6b61de5ab1adab92dfc9`
- Entry fingerprint: `170501c0e163066d51fa69e1b8cfb6c42648c499f4561855e45185303486b5a7`
- Formal Product Layer: P1 construction industry standard product
- Layer Target: `smart_construction_core` finance source identity, lifecycle and direct projections
- Standard vs User-Specific: construction-industry standard finance fact semantics
- Why Here: terminal business recognition, immutable company/currency identity and posted-cash evidence are industry finance facts
- Why Not Elsewhere: the frontend must not infer facts; P0 must not encode construction semantics; P2/P3 must not override authority; P4 may verify or replay but cannot own the model
- Blast Radius: receipt, deduction, tax, self-funding and tender-guarantee sources; canonical finance fact, contract execution/reconciliation and direct summaries/positions; versioned migration, native trace, focused tests and the source-derived projection audit carrier

## Single objective

Establish one canonical, lifecycle-correct and currency-safe finance projection. A projected row must preserve a stable source identity, belong to an eligible terminal lifecycle, carry an explicit company/currency identity and derive cash only from a matching posted treasury ledger.

## Model freeze

1. New finance source records snapshot company identity from their project; terminal identity and economic fields are immutable.
2. Existing rows are classified explicitly. Migration may preserve an observed historical identity, but it must not claim that an unproved identity was normalized.
3. Canonical eligibility is source-specific: expense `done`/`legacy_confirmed`, tax `deducted`/`legacy_confirmed`, self-funding `done`, receipt `received`/`legacy_confirmed`, and tender guarantee `confirmed`.
4. Draft, intermediate, cancelled, inactive or unresolved-identity rows never enter canonical totals.
5. Cash-in/cash-out is read from an exact matching posted `sc.treasury.ledger`; a business header amount is never relabelled as cash.
6. Received income is represented as `arrival_gross`; payment-request, project, company and currency identities must agree with its posted ledger.
7. Direct summaries group by project, company and currency. `MIN(company_id)`/`MIN(currency_id)` is forbidden for amount-bearing aggregates.
8. Drill-down domains preserve the same project/company/currency slice.
9. Historical records that cannot prove identity or cash evidence remain traceable outside canonical cash totals; no default company, project-company fallback or silent currency conversion is allowed.
10. Contract execution and reconciliation use the same identity-matched posted treasury evidence; a received document header is not cash proof.
11. Treasury rows are generated only through a module-private object authority token. Repeated writers must match the complete economic identity; a conflict is rejected rather than overwritten.
12. The projection registry and static audit must prove the current authority mechanism from the owning class; the retired forgeable `allow_ledger_auto` context is not an accepted authority.
13. A payment request persists its one terminal cash-source owner. Claim and final binding use a module-private object authority, cannot be forged through create/write context, and update the locked request row so cross-model concurrent claims cannot pass through a stale transaction snapshot.
14. Payment-ledger project, company, partner, currency and operation-strategy identities are immutable creation-time snapshots. Contract allocation project/company/currency identities are immutable child-fact snapshots; stored related fields are not accepted as historical fact identity.
15. Raw-SQL finance aggregation explicitly flushes every dependent ORM field, so posting and reversal are visible in the same transaction without stale fact positions.
16. A supplement contract cannot change its original-contract link after economic evidence exists when that link would indirectly replace direction, project, company, currency or partner identity.
17. Terminal deduction lines are immutable whether their parent is passed explicitly or through Odoo's standard `default_claim_id` context.
18. Snapshot and partial-index migrations are difference-write only. A clean replay preserves both table tuple identity and matching index relation identity; complete historical conflicts fail closed instead of being relabelled from current relations.
19. A legacy payment ledger or allocation with incomplete identity is an explicit unresolved historical fact. Its observed fields remain unchanged, missing project/company/partner/currency/strategy values are never synthesized from current request, project or contract relations, and unresolved rows are excluded from canonical actual-paid and funding positions.
20. Every paid, settlement, reconciliation and funding consumer requires a canonical ledger parent, canonical allocation child and exact frozen identity parity. A non-canonical parent also quarantines its funding children and removes their stored contributions through a difference-write migration.
21. Any posted unresolved or identity-mismatched ledger is ambiguous payment history. It contributes zero to authoritative totals and blocks request completion, new execution and new authoritative payment until governed repair resolves the evidence.
22. Historical rows without a company snapshot are ops-only: ordinary finance roles cannot see them through record rules. Native finance users receive a readonly same-company allocation evidence entry, while unresolved ledgers expose no allocation or correction action.
23. Ambiguous history is checked under the locked request authority row before both new and existing-ledger payment paths. A confirmed execution cannot transition to paid when its existing ledger has become unresolved or identity-conflicting.
24. Payment-execution readiness, ambiguous-history detection and request completion totals operate on recordsets. Batch creation keeps the expensive identity check constant across 1/10/50 records; only unavoidable per-document sequence and persistence work grows with the batch.

## Exclusions

- contract-cost attribution and the empty comprehensive cost summary
- native menu/access isolation owned by Batch-G
- custom frontend and P0 public contracts
- P2/P3 configuration and P4 runtime/environment or replay infrastructure

## Acceptance

- non-zero ORM tests prove lifecycle inclusion/exclusion, immutable terminal identity, unforgeable transitions, posted-ledger cash authority and currency separation
- migration is idempotent and classifies historical identity without guessing
- direct projections contain no cross-company or cross-currency aggregation
- governed incremental upgrade succeeds on `local.dev`
- native Odoo actions can open the exact source and exact project/company/currency detail slice
- query-count evidence remains bounded for 1/10/50 row projection reads
- full `sc_gate` and independent exact-fingerprint reviews pass

## Verification evidence

- `make verify.workspace.worktree.guard`: PASS, 17/17 checks.
- Governed `local.dev` incremental upgrade through `17.0.0.156`: PASS with post-upgrade authority verification. `.146` establishes source identity; `.147` quarantines inferred identities; `.148` quarantines duplicate terminal owners and creates canonical indexes; `.149` persists the one terminal cash-source owner; `.150` rebuilds only exact claims and preserves matching index identity on replay; `.151` converges request-backed expense cash facts and preserves matching index identity; `.152` materializes allocation identity while quarantining partial legacy rows; `.153` and `.154` classify payment-ledger and allocation identity from persisted evidence without filling missing values; `.155` quarantines funding children whose parent ledger is non-canonical and recomputes stored funding totals from canonical parent/child evidence; `.156` forward-fixes installations that already ran the earlier `.155` cutover. Payment snapshot and funding corrections are difference-write only, replay without rewriting unchanged tuples, and fail closed on canonical completeness/parity conflicts.
- `core_payment_amount_semantics`: PASS, 5 methods / 7 test stats. It proves that only posted, exact-identity allocation facts enter contract actual-paid, that ledger/allocation snapshots equal the owning contract slice, and that a controlled reversal is excluded in the same transaction after explicit ORM-to-SQL flushing.
- `p1_finance_projection_authority`: PASS, 32 methods / 34 test stats. The independent-transaction test asserts exactly one first-attempt PostgreSQL serialization failure and one committed terminal owner; private/immutable claims, terminal-source deletion protection, explicit and context-default child-line immutability, supplement-contract indirect identity freezing, historical mismatch quarantine, same-transaction receipt flushing, exact owned-ledger joins, payment-snapshot migration tuple stability, partial-index relation stability and bounded 1/10/50 ledger/execution batch query growth are covered. A genuine partial pre-cutover ledger/allocation/funding chain is replayed through `.152`-`.156` twice: missing identity remains missing, observed identity remains unchanged, tuple identities remain stable, child funding evidence is quarantined, all paid/funding/reconciliation/native totals and drill-downs remain empty, NULL-company history is hidden from both same-company and other-company finance managers, and the ambiguous history blocks request completion and new execution. A separate observed currency mismatch proves the same fail-closed behavior for complete but contradictory historical evidence. Existing ambiguous ledger reuse is rejected before a confirmed execution changes to paid. Receive-request completion now counts only exact posted canonical cash evidence: void, unresolved, cross-currency and otherwise contradictory history cannot complete the request, and ambiguous posted history fails closed. Receipt state, terminal ownership, treasury ledger and request completion are committed inside one savepoint, with a negative-path test proving the entire cash claim rolls back on insufficient evidence. A received receipt now accepts only note/attachment annotations; real finance-manager writes against classification, document, account, bill and amount fields are rejected, and native-view assertions prove the same terminal readonly boundary, finance-manager-only receive action and terminal cancel suppression. Real finance-read and finance-user principals are both denied direct receipt completion with zero change to receipt state, request state, terminal claim and ledger count; the same record then succeeds for a finance-manager principal and closes with an exact posted ledger. Payment-execution batches explicitly instrument ambiguity probes as exactly one call over recordsets of 1/10/50, batch all payment-basis relation reads, and enforce tightened total query budgets, so cold-cache persistence work cannot hide a singleton identity-check regression.
- `p1_contract_execution_position`: PASS, 13 methods / 15 test stats after the persistent-claim upgrade; a received header without matching posted treasury evidence is explicitly proved not to be cash, allocation drill-down is exact, and native aggregation separates currencies.
- `p0_state,rr_p1,team_loan_deduction_workspace`: PASS, 82 methods / 90 test stats, including state closure and contract/ledger record-rule isolation.
- `/smart_construction_core:TestP0LedgerGate`: PASS, 16 methods / 18 test stats; `rr_p1`: PASS, 2 methods / 6 test stats. These prove the existing P0 ledger behavior remains intact and finance visibility is tenant-contained after the stricter global company rules.
- Full `sc_gate`: PASS after the governed `.156` model upgrade, 339 methods / 435 Odoo test stats (424 core and 11 demo), 0 failed and 0 errors. Earlier attempts invalidated by the concurrently running frontend productization journey are environmental non-evidence; once that journey released `sc-local-dev`, the module was freshly upgraded, authority-verified and tested through the governed carrier. The prior business assertion failures were never waived and drove the snapshot redesign, explicit unresolved-history classification, fail-closed replay and reuse, exact parent/child funding authority, recordset-batched readiness/completion, exact receive-cash completion authority, atomic receipt rollback, strict received-fact immutability and real-role receipt completion authority.
- `python3 -m unittest scripts.verify.test_backend_business_fact_model_audit`: PASS, 15 tests, including mismatched guard/factory token rejection and retired boolean-marker rejection.
- `make verify.backend_business_fact.model_standard`: PASS, 372 models and 36 projections; zero unregistered projections, zero implementation gaps, zero undeclared standard gaps and zero unclassified models.
- Earlier exact-fingerprint reviews found cross-currency aggregation, missing source ACL checks, wrong deduction semantics, duplicate cash consumption, forgeable terminal creation, identity-guessing migration, incomplete drill-down dimensions, cross-model historical ownership bypass, receive-request direct completion, incomplete evidence views, migration-only indexes, missing concurrency proof, deletable terminal evidence, mutable deduction lines, non-exact receipt joins and linear payment-ledger creation queries. Later reviews found a `default_claim_id` child-line bypass, supplement-contract indirect identity drift, payment-snapshot history relabelling/no-op tuple rewrites, a missing receipt ORM flush, an omitted ledger-company SQL predicate and unconditional partial-index rebuilds. The latest review rounds found unresolved ledgers still entering settlement/request/native totals, non-canonical parents leaving funding allocations authoritative, reconciliation count/drill-down leakage, NULL-company finance visibility, unresolved-ledger funding buttons, missing native allocation audit, ambiguous history not blocking new execution or existing-ledger reuse, singleton ambiguity/completion queries inside batch loops, receive completion summing non-canonical linked ledgers, per-request payment-basis relation searches, mutable received receipt classifiers/accounts and native receipt buttons outside their server-authorized role/state. Every finding was repaired at the owning P1 model/security/native layer and covered by non-zero tests before the replacement candidate freeze.
- `verify.business.finance_document_tier_runtime_smoke` has no governed `local.dev.*` wrapper. The baseline hard lock forbids assembling its Compose/database environment manually, so this runtime evidence remains a declared P4 governance gap rather than in-topic evidence.
- Native Odoo `/web` write-journey acceptance remains `not_run`: this baseline has no registered native-web write Make target, as already recorded by the prior P1 batches. The available payment native-parity target is readonly and coupled to the custom frontend, so it cannot honestly satisfy the independent native write-flow requirement; creating the missing target remains P4 governance work rather than an in-topic workaround.
- `TEST_TAGS=p0_ledger_gate` collected zero tests and is recorded as non-evidence; the correct class selector `/smart_construction_core:TestP0LedgerGate` passed 16/16.
- Independent exact-fingerprint review: PASS on complete candidate `62d69ab617e6a6199064d820a50444527fe769f5c9740dbab949e0b4eeda27d9` (scope `99c449a01c6c8966981447ae51d148ff4f664c149a40d8b36956aa698453f2c6`, 7172 entries, HEAD `fe47096ed242863143ea6b61de5ab1adab92dfc9`). Business-fact, native-Odoo and ORM/SQL reviewers independently recomputed identical start/end fingerprints and each reported zero S0/S1/S2/S3 findings. The final role-boundary evidence proves finance-read and finance-user denial with zero side effects and finance-manager success on the same receipt chain.

## Rollback

- Batch-F lands as its own commit after the Batch-E commit.
- Schema evolution is forward-fixed through a later governed module upgrade; no destructive rollback or hand-built database command is permitted.
- The known missing P4 replay entry remains external and continues to block `make pr.push`.
