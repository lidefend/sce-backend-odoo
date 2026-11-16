# NATIVE-SCENE-01 / P0-4 Validation Governance

Status: supporting P4 implementation; product authority unchanged.

Date: 2026-11-17

Baseline main: `7dc7f393aafd3ccd4e35fed45d75108993155324`

## 1. Scope and Boundary

This batch governs only the validation path needed to deliver the P0-4 contract:

- Formal Product Layer: P4 operations/delivery tooling supporting P0.
- Modules: `smart_core` contract candidate plus isolated frontend acceptance.
- Standard vs User-Specific: platform-neutral validation mechanics.
- Why Here: the defects are in CI impact mapping, candidate runtime identity and
  merge-evidence recording.
- Why Not Elsewhere: no Odoo business model, ACL, View, Renderer, Parser or
  persistent product schema changed.
- Rollback: revert the P4 commit independently; the P0 contract remains valid.

## 2. Defects and Repairs

### Unknown acceptance inputs no longer force every backend module

`backend_impact_plan.py` treated three exact contract inputs as unknown:

- `config/acceptance/backend_contract_instance_v1.json`
- `config/acceptance/backend_contract_instance_daily_v1.json`
- `config/contract/page_contract_v1_retirement_manifest.json`

The fail-closed fallback therefore selected every runnable backend module even
though the existing incremental frontend authority already knew the exact
consumers. `config/ci/path_ownership_v1.json` now classifies each exact input as
non-runtime control plane and routes it to its declared owning check. Unknown
paths still fail closed; no directory or wildcard exemption was added.

### Candidate runtime identity now has one producer and one validator

The candidate browser guard required
`.runtime/candidate-acceptance/candidate-runtime-identity.json`, but no governed
entry produced it after replacing or reusing the candidate backend.
`scripts/dev/candidate_runtime_identity.py` now:

- reads the active `sc_platform_namespace.namespace_id` from the candidate DB;
- binds it to the exact source SHA, database and Compose project;
- writes atomically under `.runtime`;
- rejects missing, malformed, stale or cross-project receipts.

`backend.acceptance.up` invokes the producer after validating both a reused and a
replaced candidate carrier. The browser guard consumes the same validator rather
than parsing an unbound JSON field inline.

The candidate profile also refuses the historical local default fixture password
at profile load. A candidate operator must supply
`SC_ACCEPTANCE_FIXTURE_PASSWORD` explicitly, so credential provenance is known
before any service or browser work starts.

### Integration evidence recording is part of the integration entry

`verify.frontend.acceptance.integration` now records the three affected merge
evidence suites after all browser lanes pass. Operators no longer need to find a
timestamped relation-roundtrip directory manually before merge admission.
Suite-specific validation still remains in `acceptance_evolution_record.py`.

## 3. Verification

The supporting P4 batch requires non-zero targeted tests for:

- backend impact and path ownership;
- candidate profile and runtime identity production;
- candidate guard failure modes;
- standard-preview runtime integration;
- acceptance evolution evidence recording.

These tests are prerequisites, not substitutes for the exact-head candidate
browser evidence and required GitHub checks.
