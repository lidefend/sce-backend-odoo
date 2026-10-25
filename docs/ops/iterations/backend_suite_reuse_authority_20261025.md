# Backend-suite evidence reuse authority

Goal: establish an authoritative mechanism that proves a historical successful
backend result still applies to the current candidate, and authorize REUSE only
when every required dimension is independently attested. This is not a
REUSE-ratio target.

## Stage 1 audit (2026-10-25)

Authority: `scripts/ci/backend_test_receipt.py`, `scripts/ci/backend_suite_plan.py`,
`scripts/ci/backend_impact_plan.py`, `.github/workflows/backend_test_suite.yml`,
`.github/workflows/professional_quality_gate.yml`.

### Reuse-closure model

`backend_test_receipt.reuse_closure` defines six dimensions:

1. platform_source_authenticated
2. artifact_attempt_attested
3. execution_definition_attested
4. runtime_contract_readback
5. fact_scope_readback
6. target_dependency_closure

### Dimension status

#### 1. platform_source_authenticated — TRUSTED

`verify_github_origin` authenticates the run (repository id/full_name, head_sha,
completed/success, event, workflow path), the artifact (id/name/expired,
workflow_run origin), the platform archive sha256 digest, the receipt provenance
(GITHUB_REPOSITORY/RUN_ID/RUN_ATTEMPT/JOB), and the source tree against the git
commit. Returns `platform_origin=verified`.

#### 2. artifact_attempt_attested — MISSING

`verify_github_origin` returns `artifact_attempt=not_attested`. The artifact name
and the receipt attempt field are producer assertions; the platform API binds
only run id and head. The attempt number is not yet authenticated to the
platform's actual attempt.

#### 3. execution_definition_attested — PARTIAL

`attest_execution_definition` exists and binds workflow bytes to platform
provenance (referenced_workflows / merge revision) and verifies the executed
workflow bytes against the verified source definition. It is only invoked inside
`isolated_history` for `ISOLATED_MODULE`; it is not wired into
`verify_github_origin` for the general Docker Odoo backend modules.

#### 4. runtime_contract_readback — MISSING

`readback_witness_closure` requires a witness with schema
`backend-contract-fact-readback/v1` carrying source_sha256 + contract_sha256 +
value_parity. The Docker Odoo backend suite does not emit this witness, so the
blocker stays open.

#### 5. fact_scope_readback — MISSING

Same witness; requires full projection value parity (no mismatches, no uncovered
fields). Not captured for the Docker Odoo suite.

#### 6. target_dependency_closure — MISSING

`record()` writes `input_binding` with `policy=whole-tracked-tree/v1` (a
conservative whole-tree hash). `backend_suite_plan` computes
`known_inputs_sha256` over `EXECUTION_INPUTS` only and explicitly "does not
certify imports, external packages, dynamic contracts or SQL reads".
`scope_reference` returns `dependency_closure_complete=False`.

### Trusted sources already present

- `context()`: db/redis/odoo image ids (sha256), docker/compose versions,
  runner os/arch.
- `python_environment()`: python version/implementation, executable sha256,
  installed packages (name/version/RECORD sha256), os release.
- `workflow_definition_observation()`: GITHUB_WORKFLOW_SHA/REF (producer
  observed, not attested).
- Isolated pure-Python authority: Docker run with `--network none --read-only
  --cap-drop ALL --security-opt no-new-privileges --user 65534`, bound snapshot,
  execution.log marker, test IDs. This is the only path that yields
  `isolated_execution_authority=verified_workflow_execution`, for
  `ISOLATED_MODULE=smart_construction_scene` only.

### Reuse gate today

`receipt_reuse_authorized` authorizes only when
`isolated_execution_authority == verified_workflow_execution`. Docker Odoo
backend receipts never carry that authority, so they always resolve to RUN.
This is a fail-closed design, not a missing toggle.

### What stages 2-5 must close

- Stage 2: certify `target_dependency_closure` (Python imports, external
  packages, dynamic contracts, SQL reads, database/fixture dependencies).
- Stage 3: attest artifact attempt and wire `attest_execution_definition` into
  `verify_github_origin` for the Docker Odoo suite.
- Stage 4: capture a `backend-contract-fact-readback/v1` witness (module version,
  database image/initialization state, test configuration, runtime contract).
- Stage 5: extend `receipt_reuse_authorized` / `select_historical_receipts` to
  authorize REUSE only when all six dimensions close; otherwise RUN or BLOCK.
