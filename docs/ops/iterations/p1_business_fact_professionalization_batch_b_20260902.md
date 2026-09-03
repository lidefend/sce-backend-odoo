# P1 Business Fact Professionalization — Batch-B

## Batch Contract

- Current batch: `Batch-B`
- Single objective: persist one immutable, auditable contract-allocation snapshot for every actual `payment.ledger` fact.
- Entry HEAD: `3d6d3382c18b288fc0142afc71c862d5ea2a6b4a`
- Entry complete fingerprint: `55bb7f7918f6705564866dec9b1edcbb5b89a38099d57efead548de7b2a00065`
- Formal Product Layer: P1 construction industry standard product.
- Layer Target: payment fact authority in `smart_construction_core`.
- Standard vs User-Specific: reusable construction-industry settlement/payment accounting semantics.
- Why Here: actual-payment attribution to construction contracts is an industry fact, not a generic platform mechanism.
- Why Not Elsewhere: P0 owns mechanisms, P2 owns customer differences, P4 owns delivery tooling, and the frontend must not infer allocation.

## Frozen Semantics

1. `payment.ledger` remains the only new-system actual-payment authority.
2. Allocation is captured in the same transaction as ledger creation and never recalculated from later request-line edits.
3. All active request lines are the first allocation basis; any non-positive basis makes the ledger explicitly unresolved. A unique direct request contract is the fallback only when no active line basis exists.
4. Resolved lines must agree on contract/project/company/currency anchors and their basis total must equal the approved request amount within currency precision.
5. Partial payment is allocated by snapshotted basis ratio with deterministic currency rounding; allocated rows must sum exactly to the ledger amount.
6. Missing, conflicting, or incomplete authority produces explicit `review_required` rows. It must never be evenly split, assigned to the first contract, or hidden.
7. Reversal preserves allocation evidence; net actual-paid aggregation includes only parent ledgers in `posted` state.
8. Once a request has left draft/rejected/cancel, allocation-bearing request-line fields are immutable.

## Scope

Allowed:

- `payment.ledger.allocation` model and its registration
- controlled allocation construction from `payment.ledger.create()`
- ledger allocation totals/status fields
- payment-request-line immutability for allocation basis fields
- contract actual-paid aggregation consuming posted allocation facts
- least-privilege ACL and company/project record rules
- module version/data registration needed for the new P1 model
- focused Odoo tests, goal/iteration evidence, and directly affected fact registries

Excluded:

- contract execution position native views, actions, or menus
- settlement-line fact freezing and adjustment convergence
- cost-ledger idempotency or batching
- frontend, `smart_core`, public intents, `system.init`, or `ui.contract`
- new runtime profile, database, port, volume, fixture, credential, or handwritten DB/Compose command

## Database and Upgrade Identity

- target role: development demo-backed feature database
- tenant: platform internal demo tenant; not customer production data
- environment/profile: `local.dev`
- Compose project: `sc-local-dev`
- database: `sc_dev_demo`
- exact dbfilter: `^sc_dev_demo$`
- filestore/volumes: governed `sc_local_dev_*`
- module: `smart_construction_core`
- upgrade: required through the registered `make local.dev.upgrade` entry only
- shared database mutations: serialized; no upgrade runs while the existing shared runtime gate is known unhealthy

## Validation Contract

- non-zero focused Odoo tests cover direct, multi-contract, partial, rounding, unresolved, reversal, immutability, idempotency, and company/project visibility
- model/fact registry guard passes with the new model classified
- module upgrade succeeds on the governed `local.dev` identity before runtime acceptance
- existing ledger reversal and payment semantics regressions remain green
- independent review binds the complete frozen candidate fingerprint

## Candidate Evidence

- Governed incremental upgrade: `make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_core` — PASS on `sc-local-dev` / `sc_dev_demo`; post-upgrade authority verification passed.
- Allocation fact journey: `make local.dev.test MODULE=smart_construction_core TEST_TAGS=p1_contract_payment_allocation` — PASS, 14/14 tests, 0 failed, 0 errors.
- Existing ledger gate: `make local.dev.test MODULE=smart_construction_core TEST_TAGS=/smart_construction_core:TestP0LedgerGate` — PASS, 16/16 tests, 0 failed, 0 errors.
- Existing payment semantics: `make local.dev.test MODULE=smart_construction_core TEST_TAGS=/smart_construction_core:TestCorePaymentAmountSemantics` — PASS, 5/5 tests, 0 failed, 0 errors.
- Model/fact audit unit suite — PASS, 11/11 tests; exact model standard guard — PASS.
- `make verify.role.acl.minimum_set.guard` — PASS.
- `make security.personal_data_scan` — PASS, confirmed matches 0; the changed synthetic ledger fixture is registered only for `PD003`, its exact path, and immutable blob `487ac377c8a9a689fef795881d9a228c8cc91ee2`.
- `make security.secrets.scan` — PASS, high-confidence confirmed matches 0.
- The broader backend guard reached its live contract-schema check after all static guards passed, then received the pre-existing shared-runtime `401 AUTH_REQUIRED`; no startup, identity, or P4 credential mutation is in Batch-B scope.
- `make verify.native.business_fact.static` currently references the absent governed script `scripts/migration/business_fact_upgrade_replay_flow.sh`; this repository entrypoint gap is P4-owned and was not bypassed inside the P1 topic.
- Independent review is required against the final complete candidate fingerprint recorded outside this tracked document; no tracked mutation is permitted after review begins.

## Implemented Result

- `payment.ledger.allocation` stores immutable request-line/direct-contract attribution, source anchors, basis amount, allocated amount, resolution state, reason, and deterministic key.
- Allocation creation is same-transaction, row-locked, batched, idempotent, currency-exact, and rejects guessing from execution headers.
- Request-line basis mutations lock all source and destination request rows in deterministic order, re-read workflow state, and reject either direction of a reparent across a frozen request.
- Historical backfill repairs allocation scope and parent ledger totals/status idempotently; ambiguous history and all history with active request lines remain explicit `review_required`.
- Repeated backfill updates parent ledger summaries only when a stored value is distinct; the focused test compares PostgreSQL `ctid` before and after an unchanged second init to prove that the parent tuple was not rewritten.
- Ordinary ledger and allocation mutation is rejected; controlled reversal retains allocation evidence while posted-only aggregation removes the reversed amount from net actual paid.
- Finance roles receive read-only access constrained by company and project membership/followership, with manager scope limited by the global company rule.
- Contract actual-paid metrics aggregate posted allocation facts in one grouped ORM query instead of inferring from payment execution headers.

## Risk and Rollback

- Existing ledgers require a governed backfill path; ambiguous history remains unresolved rather than guessed.
- Contract paid totals may decrease where the old execution-header shortcut overstated authority; this is a fact correction and must be evidenced.
- Rollback is the Batch-B commit plus governed module downgrade/forward-fix policy; no destructive database cleanup is authorized.
