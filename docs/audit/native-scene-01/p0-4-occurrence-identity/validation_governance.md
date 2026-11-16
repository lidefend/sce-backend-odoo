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

### Assembled-contract cache fingerprints include the native View producer

The cache guard now includes
`addons/smart_core/app_config_engine/services/assemblers/page_assembler.py`
in the assembled-contract input digest. A change to native View identity
production can no longer reuse a previously assembled response merely because
the handler and core assembler file hashes stayed unchanged.

### Integration evidence recording is part of the integration entry

`verify.frontend.acceptance.integration` now records the three affected merge
evidence suites after all browser lanes pass. Operators no longer need to find a
timestamped relation-roundtrip directory manually before merge admission.
Suite-specific validation still remains in `acceptance_evolution_record.py`.

### Acceptance integration is plan-first and reuse-first

The previous integration entry still invoked presentation, list and relation
browser suites unconditionally. That contradicted the existing
`acceptance_evolution_binding.v1` planner: a contract-only or list-only change
could execute two unrelated paid browser lanes, and a candidate with reusable
suite evidence still rebuilt the preview and performed every browser journey.

`scripts/ops/acceptance_evolution_integration.py` now consumes the existing
acceptance plan and evidence carry-forward rules:

1. resolve the exact base/head and required evidence suites;
2. mark each required suite RUN or REUSE from its declared input fingerprint;
3. execute preparation and suite targets only when at least one suite is RUN;
4. record new evidence through `acceptance_evolution_record.py`;
5. carry forward unchanged suites through the existing validated input hash.

The integration runbook is declared beside each suite in
`config/acceptance/evolution_binding.v1.json`. It contains the governed Make
targets and the evidence path/glob, so the runner cannot hardcode one product
surface. Integration route metadata is excluded from the semantic suite input
fingerprint: changing where a test is launched does not invalidate browser
evidence when the browser inputs and assertions are unchanged.

`acceptance.integration.plan` is read-only and writes
`.runtime/acceptance-evolution/integration-plan.json`. A plan with no RUN suite
performs no preview build, backend start, database write or browser launch.

An already-covered suite may be rerun only with
`SC_ACCEPTANCE_REVERIFY_SUITES` plus `SC_ACCEPTANCE_REVERIFY_REASON`. A full
runtime rerun requires `SC_ACCEPTANCE_FULL=1` and
`SC_ACCEPTANCE_FULL_REASON`. Empty reasons fail before any runtime mutation.

## 3. Verification

The supporting P4 batch requires non-zero targeted tests for:

- backend impact and path ownership;
- candidate profile and runtime identity production;
- candidate guard failure modes;
- standard-preview runtime integration;
- acceptance evolution evidence recording;
- plan/reuse decisions, explicit rerun reasons, declared target order and
  zero-runtime behavior for an all-reusable plan.

These tests are prerequisites, not substitutes for the exact-head candidate
browser evidence and required GitHub checks.
