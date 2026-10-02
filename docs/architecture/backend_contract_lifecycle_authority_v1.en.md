# Backend Contract Lifecycle Authority v1

Date: 2026-08-11
Formal Product Layer: P0
Architecture Layer: L0-L1
Runtime Owner: `smart_core`

## Decision

The backend contract system now has one fail-closed lifecycle from versioned
schema definition through authoritative projection, deterministic generation,
append-only publication, runtime trimming, final resealing, traceability and
typed consumer compatibility.

Machine control coverage is **100/100** across eight lifecycle dimensions with
zero P0 findings. The isolated-database fourteen-assertion runtime probe is
re-read offline by `scripts/verify/backend_contract_lifecycle_runtime_schema_guard.py`,
which locks its declared set, bound database, module version and source revision,
so the runtime half is offline-verifiable like the machine half. Enterprise
maturity is assessed at **92/100, L4 (governed and production-ready)**.

This is not L5. Contract-version SLO telemetry and trend (success, degradation
and integrity-failure rates aggregated per contract version, with a durable store,
a retention horizon and a trend read model) is delivered and runtime-verified on
the isolated `sc-contract-lifecycle-v1` profile by the
`fix/contract-slo-telemetry` workstream, so it is no longer a gap. Signed
supply-chain provenance and automated N-1/N+1 consumer compatibility drills
remain separate work, so the L4 assessment is deliberately unchanged.

## Authority Rules

- Unified Page Contract v2.2 Schema and enum registry are identified by SHA-256.
- Assemblers bind generator, source type and source SHA-256.
- Published configuration contracts retain payload and definition digests plus
  source authority.
- Publication is row-locked and idempotent.
- Rollback appends a new version; it never rewrites or reuses historical version
  numbers.
- Version rows reject external creation, mutation and deletion.
- Full runtime contracts are resealed after extensions and client trimming.
- `meta.lifecycle` binds request ID, trace ID, schema/source/contract digests and
  runtime stage.
- Typed frontend consumers preserve lifecycle evidence.
- The product release gate invokes the lifecycle authority guard.

## Runtime Evidence

The isolated `sc_contract_lifecycle` database, exact
`^sc_contract_lifecycle$` dbfilter, independent volumes and no demo/customer
data passed all fourteen publication, definition-binding, idempotency, append-only rollback,
immutability and recomputed population-integrity assertions on `smart_core
17.0.1.1.9`. The rehearsal also repaired deliberately drifted 17.0.1.1.8
evidence through the standard module-upgrade path.

Machine evidence is written to
`artifacts/backend/backend_contract_lifecycle_runtime_probe.json` by
`scripts/verify/backend_contract_lifecycle_runtime_probe.py`.

The artifact is re-validated offline by
`scripts/verify/backend_contract_lifecycle_runtime_schema_guard.py`: the assertion
set must be exactly the declared fourteen (`declaredChecks` must equal the
`checks` keys, no gap, no extra, no duplicate, every entry `true`), all counters
must be 14/14 with an empty `errors` and `versionDigestMismatchSample`, the
identity must bind `probe=backend_contract_lifecycle_runtime_probe`,
`schemaVersion=1.0.0`, `database=sc_contract_lifecycle` and
`moduleVersion=17.0.1.1.9`, and `sourceRevision` must be a full commit SHA equal
to the expected revision when one is supplied. Producer and guard share one
declared set and fail closed on drift, so a truncated, renamed or hand-edited
artifact cannot be reported as a pass. The negative-first unit proof is
`scripts/verify/test_backend_contract_lifecycle_runtime_schema_guard.py`, run as
part of `verify.backend.contract_lifecycle.authority` and the runtime lane.

## Remaining L5 Work

- Contract-version SLO and degradation trend telemetry — delivered by the
  `BACKEND-CONTRACT-SLO-TELEMETRY` workstream (durable store, retention horizon,
  trend read intent, runtime-verified); no longer a gap.
- Automated N-1/N+1 consumer compatibility and rollback rehearsals — delivered
  by the same workstream as a declaration-level offline drill (the production
  key surface is projected, the rollback rule is bound to the publication
  authority's `max(cur, latest)+1` append, and each injected break is proven to
  fail the drill only after the un-injected baseline passes); no longer a gap.
- Signed artifact provenance bound to the deployed runtime SHA — the unified,
  digest-linked attestation (schema + contract + artifact + source revision +
  deployment runtime SHA) and its independent host-side re-verification are
  delivered. The signature is a process-local ephemeral Ed25519 self-signature,
  so it proves consistency and tamper-evidence but **not** who built the
  artifact; the external trust root remains open.

Industry, customer and tenant layers may extend contract payloads through
approved extension points, but may not redefine this protocol or bypass its
publication authority.
