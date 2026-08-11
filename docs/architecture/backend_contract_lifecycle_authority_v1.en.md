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
zero P0 findings. With the isolated-database 14/14 runtime probe, enterprise
maturity is assessed at **92/100, L4 (governed and production-ready)**.

This is not L5. Long-term contract SLO telemetry, automated N-1/N+1 consumer
compatibility drills, and signed supply-chain provenance remain separate work.

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
`artifacts/backend/backend_contract_lifecycle_runtime_probe.json`.

## Remaining L5 Work

- Contract-version SLO and degradation trend telemetry.
- Automated N-1/N+1 consumer compatibility and rollback rehearsals.
- Signed artifact provenance bound to the deployed runtime SHA.

Industry, customer and tenant layers may extend contract payloads through
approved extension points, but may not redefine this protocol or bypass its
publication authority.
