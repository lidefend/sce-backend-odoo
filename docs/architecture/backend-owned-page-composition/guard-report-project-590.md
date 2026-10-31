# Page Composition Integrity Guard 1.1.0

- overall: FAIL
- executed_at: 2026-10-31T13:47:17.903329+00:00
- repository_sha: a9cd2fd5879d8a5358c2ad737602e0ae72644555
- page_classification: formal

## Status counts

| status | count |
| --- | --- |
| PASS | 5 |
| FAIL | 1 |
| WARNING | 0 |
| NOT_VERIFIED | 5 |
| NOT_APPLICABLE | 0 |

## NOT_VERIFIED

- PC-005: projection semantics incomplete
- PC-008: verified permission evidence missing; declaration alone is not proof
- PC-009: old-consumer regression evidence missing
- PC-010: historical node identity mapping evidence missing
- PC-011: slots<->container mapping not evidenced

## FAIL

- PC-007: formal page consumes legacy fallback at runtime

## Rules

| rule | status | evidence |
| --- | --- | --- |
| PC-001 | PASS | slots+containerTree |
| PC-002 | PASS | group:identity |
| PC-003 | PASS | slots+groups |
| PC-004 | PASS | fieldOwnership |
| PC-005 | NOT_VERIFIED | slots.fieldRefs |
| PC-006 | PASS | pageComposition.class |
| PC-007 | FAIL | legacy_fallback_sources |
| PC-008 | NOT_VERIFIED | permission_evidence |
| PC-009 | NOT_VERIFIED | version_compatibility_evidence |
| PC-010 | NOT_VERIFIED | historical_node_identity_evidence |
| PC-011 | NOT_VERIFIED | slot_container_mapping |

## Evidence trust

| key | trusted | untrusted | total |
| --- | --- | --- | --- |
| legacy_fallback_sources | 2 | 0 | 2 |
| permission_evidence | 0 | 0 | 0 |
| version_compatibility_evidence | 1 | 0 | 1 |
| historical_node_identity_evidence | 2 | 0 | 2 |

