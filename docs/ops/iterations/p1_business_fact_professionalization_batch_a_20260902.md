# P1 Business Fact Professionalization — Batch-A

## Batch Contract

- Current batch: `Batch-A`
- Single objective: restore an exact-head authoritative inventory and static standard for P1 business facts.
- Baseline: `refactor/p1-business-facts-professionalization-v1@394b2ffe20c48255d2c8c0788fbfc36456c7d007`
- Formal Product Layer: P1 construction industry standard product.
- Layer Target: `smart_construction_core` fact models and their architecture registries/audits.
- Standard vs User-Specific: reusable construction-industry standard.
- Why Here: contract, settlement, payment, cost, treasury, invoice, and project facts are industry product semantics.
- Why Not Elsewhere: P0 owns mechanisms, the frontend only consumes facts, P2 owns customer differences, and P4 owns delivery tooling.

## Scope

Allowed in Batch-A:

- `.agent/goals/P1-BUSINESS-FACT-PROFESSIONALIZATION.yaml`
- this iteration record
- `docs/architecture/backend_business_*_v1.*` registries that are direct inputs to the existing audit
- `scripts/verify/backend_business_fact_model_audit.py` only when required to make the audit reflect current source truth
- targeted static audit tests and generated reports

Not allowed in Batch-A:

- runtime business model, state, amount, approval, security, view, action, menu, manifest, or migration changes
- `frontend/`, `addons/smart_core/`, public intents, schema, or startup-chain changes
- runtime/container startup, database writes, module upgrade, fixture reset, or browser acceptance
- new Compose projects, databases, ports, volumes, credentials, fixtures, or handwritten runtime commands

## Exact-Head Entry Evidence

- initial tracked and untracked status: clean
- initial status digest: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- tracked index digest: `4f4f6af129cc8b166e340efd76b23b9b6bcad4327046f89827ef1e8c73d5b285`
- `make verify.backend_business_fact.model_standard`: FAIL on the exact baseline
- detected model classes: 370; previous audit document records 263
- unregistered formal facts: `sc.expense.contract.ledger`, `sc.income.contract.ledger`
- unregistered projections: 17
- unclassified models: 6
- stale registered projection/probe paths: 36
- undeclared standard gaps: 2
- `make verify.native.business_fact.static`: FAIL because the registered target references removed `scripts/migration/business_fact_upgrade_replay_flow.sh`

The second failure is a P4 verification-entry defect. It is recorded but excluded from this P1 batch; no local replacement entry will be invented.

## Product Roadmap Frozen From Read-Only Audit

### Batch-B — Contract Execution Position v1

Create one permission-correct and query-efficient native Odoo reconciliation fact for each contract. It must distinguish contract amount, approved/completed settlement, requested/reserved payment, net actual payment, reversals, and unallocated multi-contract payment facts. It must not infer a per-contract allocation when no authoritative allocation exists.

### Batch-C — Cost Fact Idempotency and Batch Write

Give cost-ledger source facts an enforceable idempotency key and replace per-line search/write amplification with grouped lookup and batch operations. Acceptance will use deterministic query budgets and replay/concurrency invariants.

## Runtime and Database Identity for Later Batches

- profile: `local.dev`
- Compose project: `sc-local-dev`
- database role: development demo-backed feature database
- tenant: platform internal demo tenant, no customer production data
- database: `sc_dev_demo`
- database filter: `^sc_dev_demo$`
- filestore/volumes: governed `sc_local_dev_*`
- native Odoo endpoint: governed backend port `8070`
- database mutations: serialized and only through exact `make local.dev.*` targets

## Validation Contract

Batch-A completes only when:

1. the backend business-fact model standard runs non-zero and passes on the frozen candidate;
2. all detected formal facts, projections, and model families have current explicit classification;
3. registry file/script/model references are either valid or explicitly retired by current policy;
4. generated reports bind the exact complete candidate fingerprint;
5. independent review confirms no runtime, database, frontend, P0 contract, or customer-specific change entered the batch.

## Risk and Rollback

- Risk: registering current source without reviewing ownership could legitimize accidental models. Mitigation: every new registry row must declare family, solution layer, authority, and projection/write status.
- Risk: stale legacy references may represent intentionally removed customer payload support. Mitigation: do not recreate removed migration scripts in P1; classify retirement explicitly.
- Rollback: revert the Batch-A registry/audit commit. No module upgrade or database rollback is required because Batch-A performs no runtime or database mutation.

## External Gate

The repository has no registered native `/web` write-journey Make target on this baseline. Creating that target is a separate P4 governance result. Later P1 batches may complete ORM, security, native XML, and governed runtime verification, but must report final browser write acceptance as `not_run` until that P4 capability exists.

## Batch-A Candidate Result

- inventory: 370 model classes, including 9 `AbstractModel` classes
- persistence classification: 131 native extensions, 110 custom models, 120 custom models with mixin/inheritance
- strict formal facts: 10 registered, 0 unregistered, 0 undeclared gaps
- projections: 34 registered, 0 unregistered, 0 shape/reference/implementation gaps
- projection modes: 25 SQL views, 2 physical refresh tables, 3 controlled generated ledgers, 2 runtime workbench facts, 1 computed runtime summary, 1 controlled writable snapshot
- model families: 19; ownership specs: 18; unclassified models: 0
- retired projection tooling: 10 model groups and 36 removed paths, all explicitly retired
- source enforcement: each projection mode must match both storage kind and class-derived behavior; wrong ORM mode registrations fail closed
- reports: JSON carries the complete entry manifest; Markdown binds its algorithm, branch, head, baseline, complete digest, scope manifest, entry count, exclusions, and companion JSON manifest

## Validation Evidence

- `python3 -m unittest scripts.verify.test_backend_business_fact_model_audit`: PASS, 11 non-zero tests
- `make verify.backend_business_fact.model_standard`: PASS
- `git diff --check`: PASS
- exact complete candidate identity: generated at `artifacts/backend/backend_business_fact_model_audit.json` and bound by `artifacts/backend/backend_business_fact_model_audit.md`
- `make verify.restricted ENV=dev ENV_FILE=/home/lidefend/workspace/sce-backend-odoo/.env.dev`: static contract guards, 20 + 85 + 5 tests, strict typecheck, development build, lint, production build all passed; final result FAIL at shared live scene readiness because `system.init` returned HTTP 500

The restricted failure is an external shared-runtime/startup-chain condition and is not evidence of a P1 code failure. It is not reported as PASS. Under the earliest-failing-gate rule, no full browser acceptance or shared-database mutation was attempted.

## Independent Review Status

The first frozen-candidate review returned `REQUEST_CHANGES` for three audit-authority defects: ORM modes could share the same storage-only proof, Markdown lacked fingerprint binding, and the companion findings document retained stale counts. The candidate now contains explicit fixes and negative tests for all three.

The second independent review returned `APPROVE` with no S1/S2. It additionally tested all 35 wrong-mode substitutions across the 7 ORM projections; every substitution produced an implementation gap. Batch-A is complete in its static, no-runtime scope. The shared `system.init` runtime failure and the missing native `/web` write-journey entry remain external gates and are not represented as passed.
