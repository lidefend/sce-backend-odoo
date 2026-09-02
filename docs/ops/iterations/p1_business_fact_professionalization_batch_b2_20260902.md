# P1 Business Fact Professionalization — Batch-B2

## Batch Contract

- Formal Product Layer: P1 construction industry standard product.
- Layer Target: authoritative contract execution position in `smart_construction_core`.
- Standard vs User-Specific: standard construction contract execution semantics.
- Why Here: final price, settlement, invoice and cash execution are construction-industry facts shared by every deployment.
- Why Not Elsewhere: P0 owns generic mechanisms, P2 owns customer differences, P4 owns delivery tooling, and the frontend must not derive business facts.
- Blast Radius: canonical project contracts, their native read-only position surface, contract company containment, and directly affected tests/registries only.
- Entry HEAD: `d9ee00c8ebfa0584ade6a84b5d75836d0f212a31`.
- Entry complete fingerprint: `570922576a0359b7a57eab3afc8a081a00babbb2dd2e96dedde55d7a6ccc98ef` (7135 entries).

## Frozen Semantics

1. `construction.contract.amount_final` is the contract execution base after effective changes.
2. Settled amount uses only approved/done settlement-line attribution plus confirmed/legacy-confirmed signed adjustments.
3. Invoiced amount uses only registered/legacy-confirmed contract invoice registrations and retains signed reversals.
4. Income cash execution uses received/legacy-confirmed receipts; expense cash execution uses only posted immutable payment-ledger allocations.
5. Multi-contract documents follow explicit line/allocation attribution. Missing anchors are excluded, never guessed.
6. Every balance is a signed difference. Negative values expose over-settlement, over-invoicing, over-receipt or over-payment.
7. Ratios use one 0–100 percentage unit across canonical contracts and projections, may exceed 100% or be negative, and a zero contract base produces an explicit undefined ratio state rather than a fabricated zero percent.
8. Batch aggregation must have a fixed query ceiling independent of contract count.

## Scope

Allowed:

- canonical contract position fields and grouped aggregation helpers
- company-contained contract record rules
- native read-only tree/search/pivot/action and trace to canonical form
- `sc.contract.recon.summary` compatibility convergence only if it consumes the same position
- focused Odoo fact, permission, view and query-budget tests
- module version, manifest, registries and iteration evidence directly required by the batch

Excluded:

- `sc.general.contract` and full income/expense historical SQL-ledger rebuild
- cost attribution while `project.cost.ledger` has no contract anchor
- settlement, invoice, receipt, payment or contract-change workflow redesign
- manual historical anchoring or guessed allocation
- frontend, `smart_core`, public intents, startup chain or runtime profiles
- new database, port, volume, credential or fixture system

## Governed Runtime Identity

- profile/project/database: `local.dev` / `sc-local-dev` / `sc_dev_demo`
- exact dbfilter: `^sc_dev_demo$`
- filestore/volumes: governed `sc_local_dev_*`
- module upgrade: registered `make local.dev.upgrade` target only
- acceptance authority: Odoo ORM and native `/web` surfaces; custom frontend is not involved

## Acceptance

- non-zero focused tests cover state inclusion/exclusion, multi-contract attribution, signed overrun, zero-base ratios, reversal, permissions and source trace
- 1/10/50-contract aggregation stays within one fixed query budget
- native contract-read roles can search, group, pivot and open the canonical contract while writes remain governed by existing contract roles
- cross-company reads fail under allowed-company containment
- governed module upgrade and existing contract/payment regressions pass
- independent reviewers bind one frozen complete candidate fingerprint

## Implemented Result

- Added `sc.contract.execution.position`, a read-only SQL projection with one stable row per active canonical contract.
- Unified settlement, confirmed signed adjustment, direction-correct invoice, received income, and posted immutable payment-allocation facts behind one batch aggregation helper.
- Exposed final contract price, settled/invoiced/cash-executed amounts, signed balances, ratios, and an explicit zero-base ratio state on the canonical contract and native projection.
- Replaced per-contract reference counts with grouped queries and proved the execution helper remains at five queries for 1, 10, and 50 contracts.
- Converged `sc.contract.recon.summary` away from approved payment requests to the same received/posting authority; its current-position compute remains bounded at nine queries for 1, 10, and 50 summaries.
- Added contract-read ACLs, global allowed-company containment for canonical and wrapper contract models, and a native read-only tree/search/pivot/form entry with source-contract trace. Finance-only access is intentionally excluded because finance capability does not imply contract-center access and the trace target uses contract wrappers.
- Kept all public intents, frontend code, `smart_core`, runtime profiles, fixtures, databases, ports, volumes, and credentials unchanged.

## Candidate Evidence

- Governed incremental module upgrade on `sc-local-dev` / `sc_dev_demo` — PASS; post-upgrade demo authority check passed.
- `make local.dev.test MODULE=smart_construction_core TEST_TAGS=p1_contract_execution_position` — PASS, 11/11 tests, 0 failed, 0 errors; explicitly covers 50%, 100%, 120%, negative and zero-base ratios plus cross-company denial on the projection, canonical contract, income wrapper and expense wrapper.
- `make local.dev.test MODULE=smart_construction_core TEST_TAGS=p1_contract_payment_allocation` — PASS, 14/14 tests, 0 failed, 0 errors.
- `make local.dev.test MODULE=smart_construction_core TEST_TAGS=sc_gate` — PASS, 266/266 tests, 0 failed, 0 errors. The earlier nonexistent `p0_ledger_gate` tag produced zero tests and is explicitly rejected as evidence.
- `make local.dev.test MODULE=smart_construction_core TEST_TAGS=contract_execution_component_profile` — PASS, 5/5 tests, 0 failed, 0 errors.
- `make verify.backend_business_fact.model_standard` — PASS: 372 models, 36 projection/read models, 36 registered projections, zero unregistered projections, zero unclassified models.
- `make verify.role.acl.minimum_set.guard` — PASS.
- `make security.personal_data_scan` — PASS, confirmed matches 0.
- `make security.secrets.scan` — PASS, high-confidence confirmed matches 0.
- Python compilation and `git diff --check` — PASS.
- A registered native `/web` write-journey Make target is still absent and remains the declared P4 external gate; no in-topic browser/runtime workaround was introduced.
- The first frozen review correctly rejected a 0–100 versus 0–1 ratio-unit mismatch, incomplete direct coverage of global company rules, and a half-open finance-only projection ACL. The corrected candidate multiplies SQL ratios by 100, proves 50/100/120/negative/zero boundaries and canonical/projection parity, directly proves all four company boundaries, and removes finance-only projection access before refreeze.

## Review Freeze

- Independent review must bind the final complete worktree fingerprint generated after this tracked document is frozen.
- No tracked mutation is permitted after reviewers accept that fingerprint; any blocker fix requires a new fingerprint and repeat review.

## Rollback

- one Batch-B2 commit is the code rollback unit
- database schema changes use forward-fix/governed module-upgrade policy; no destructive cleanup is authorized
