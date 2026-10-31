# Page Composition Integrity Guard 1.1.0

- overall: NOT_VERIFIED
- executed_at: 2026-10-31T10:38:18.081070+00:00
- repository_sha: a9cd2fd5879d8a5358c2ad737602e0ae72644555
- page_classification: unclassified_historical

## Status counts

| status | count |
| --- | --- |
| PASS | 1 |
| FAIL | 0 |
| WARNING | 0 |
| NOT_VERIFIED | 10 |
| NOT_APPLICABLE | 0 |

## NOT_VERIFIED

- PC-001: business composition authority (slots) not declared; containerTree cannot substitute
- PC-002: identity slot not evidenced
- PC-003: no business section slots declared
- PC-004: ownership not declared
- PC-005: slot fieldRefs not available
- PC-007: fallback evidence is source/static; runtime consumption unproven
- PC-008: verified permission evidence missing; declaration alone is not proof
- PC-009: old-consumer regression evidence missing
- PC-010: historical node identity mapping evidence missing
- PC-011: slots<->container mapping not evidenced

## Rules

| rule | status | evidence |
| --- | --- | --- |
| PC-001 | NOT_VERIFIED | formStructureContract.slots |
| PC-002 | NOT_VERIFIED | slot:identity |
| PC-003 | NOT_VERIFIED | slots+groups |
| PC-004 | NOT_VERIFIED | fieldOwnership |
| PC-005 | NOT_VERIFIED | slots.fieldRefs |
| PC-006 | PASS | pageComposition.class |
| PC-007 | NOT_VERIFIED | legacy_fallback_sources |
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

