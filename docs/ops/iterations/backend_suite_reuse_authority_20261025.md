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

## Validation responsibility mapping (read-only, 2026-10-25)

Converge the existing system into three responsibility domains instead of
building a new validation platform. Read-only inventory; no gate is modified.

### Domains

- A 平台内核: database -> runtime contract. Prove the contract is correct,
  complete, trusted and consistent with the current request context.
- B 前端运行时: contract -> user interface. Prove generic consumption and
  interaction mechanisms.
- C 真实用户旅程: end-to-end combination and deployment/role/data differences.
- 支撑-业务: the Odoo module business logic (state transitions, ACL) that feeds A.
- 支撑-工程/安全: repo hygiene, secrets, tenant boundaries, CI tooling.

### Quick gate mapping (`ci.local.quick.run`, 52 targets)

Domain A (platform kernel, contract generation):
- verify.contract.page_v1_zero_residue.guard
- verify.contract.structure_lock
- verify.unified_page_contract.v2 (schema/assembler/status/action/data/runtime/client/intent)
- verify.contract.architecture.suite (responsibility maps and split guards)
- verify.contract.list_preference.single_application
- verify.contract.gate_case_normalisation.unit
- verify.contract_form_runtime_state.behavior
- verify.action_view_runtime_smoke.behavior
- verify.ui_contract.delivery_surface.unit
- verify.product.menu.metadata_batch.unit
- capability checks: write.idempotency, boq.export, boq.dangerous.import,
  boq.line.patch, overview.rich.text.patch, visualization.chart
- verify.smart_core.ui_base_asset_refresh.unit

Domain B (frontend consumption):
- verify.frontend.lint.src
- verify.frontend.dev.incremental.unit
- verify.frontend.chart_engine.guard, verify.frontend.chart_dataset.unit
- verify.frontend.boq_line_patch.unit, verify.frontend.overview_rich_text.unit
- verify.frontend.scoped_preference.runtime.unit
- verify.frontend.static.image.decoupling
- verify.menu_config_tree_editor.behavior

Domain C: absent from Quick. Journeys live in browser acceptance lanes
(business_entry matrix, relation_roundtrip, list_surface, contract lifecycle).

Supporting (engineering/security/boundary, not A/B/C):
- ci.generated_evidence.preflight, security.legacy_credential_guard,
  verify.repository.clean_history, verify.product.release.version
- verify.tenant.* (data responsibility, module set matrix, payload boundary,
  product legacy boundary, legacy xmlid boundary, product fresh install)
- architecture.complexity_baseline_lock
- verify.pr.push.unit, verify.quick.input_scope.unit, verify.quick.evidence.unit
- verify.local.dev.runtime.performance.unit, verify.system.performance.baseline.unit

Observation: the Quick gate is roughly one third A, one fifth B, zero C, and
about half supporting/engineering/security. It is not a contract-correctness
gate; it mixes correctness, hygiene and boundary.

### Remote workflows

- backend_test_suite: 支撑-业务 (module Odoo ORM tests; the ~10-minute suite).
- professional_quality_gate: A/B guard suite + backend_impact_suite + python310.
- frontend_release_gate: B + release evidence bundle.
- public_guard, release_candidate_gate, merge_policy_gate: 支撑-工程/安全.

### Key findings

1. Schema-only vs source correctness: verify.contract.structure_lock and the
   unified_page_contract.v2 schema guard prove structural validity, not that
   the contract reflects real Odoo facts. The source/permission/semantic
   correctness proof (runtime readback) is missing for the Docker Odoo suite.

2. Duplicate permission/boundary invariants: verify.tenant.* (six guards) and
   the contract architecture split guards re-check overlapping permission and
   boundary invariants from different entry points; each is separately wired
   and separately counted.

3. Deployment acceptance inside Quick: verify.local.dev.runtime.performance.unit
   and verify.system.performance.baseline.unit measure environment-sensitive
   runtime performance, not a per-candidate correctness invariant.

4. Dependency mapping gaps: many A/B guards read JSON/config/contract
   declarations and overlays that are outside the backend suite
   `EXECUTION_INPUTS` closure; the backend `known_inputs_sha256` does not
   capture external package identity, dynamic SQL or dynamic contract reads.

Next: decide, from this map, which gaps to close first (platform-kernel
contract consistency proof), before modifying any gate.

## Platform-kernel contract consistency proof: plan + test skeleton

### Existing foundation

- `scripts/verify/backend_contract_fact_readback_probe.py` already captures, in
  one READ ONLY snapshot, the native source facts and the final
  `ui.contract.v2` contract for a registered actor/action/record, verifies the
  source/contract lifecycle binding, and emits `backend-contract-fact-readback/v1`.
  It is currently a local diagnostic with blockers:
  not_ci_execution, query_dependency_closure_incomplete,
  related_model_permission_closure_incomplete, platform_execution_not_attested,
  and projection_value_coverage_incomplete (relations/derived fields uncovered).
- `backend_test_receipt.readback_closure_blockers` / `readback_witness_closure`
  already map that witness onto runtime_contract_readback (no mismatches) and
  fact_scope_readback (full projection parity).

### Minimal closed loop

1. Wire the readback probe into the Docker Odoo backend suite so each receipt
   carries the witness for one representative model/action per module. First
   increment only attaches the witness; it does not yet authorize reuse.
2. Extend value parity from direct scalars to declared relation projections:
   a relation field is comparable only when its target model and permission
   projection are declared; otherwise it stays uncovered (fail closed).
3. Close the dependency closure (deferred Stage 2 import/SQL work) so
   query_dependency_closure_incomplete and
   related_model_permission_closure_incomplete can resolve.
4. Attest platform execution (workflow definition + artifact attempt) so
   platform_execution_not_attested can resolve.
5. Only when all six reuse_closure dimensions close does
   receipt_reuse_authorized authorize REUSE; otherwise RUN or BLOCK.

### Test skeleton (unit, pure functions first)

- backend_test_receipt: readback_witness_closure returns
  runtime_contract_readback=True only when mismatch_fields is empty; returns
  fact_scope_readback=True only when full_projection_parity and no mismatches;
  projection_value_coverage_incomplete set otherwise.
- backend_contract_fact_readback_probe.value_parity: direct scalar fields with
  equal source/projection/fact values are checked; relation, derived, related,
  translate and company_dependent fields are uncovered; a mismatched scalar is
  a mismatch field; a missing field is uncovered.
- backend_test_receipt.record: when a readback witness is supplied it is bound
  to the receipt head and carried into the receipt; a witness whose source_head
  differs from the receipt head is refused.
- backend_suite_plan.select_historical_receipts: a Docker receipt with a valid
  readback witness, authenticated platform origin, attested execution
  definition and complete dependency closure resolves to REUSE; any missing
  dimension stays RUN or BLOCK.

Implementation order follows the loop: wire probe -> extend parity -> close
closure -> attest execution -> authorize reuse.

## Implementation status (2026-10-25)

- Probe wiring: readback witness attached for smart_construction_demo; role and
  action parameterized through CANDIDATE_ROLE_XMLID / CANDIDATE_ACTION_XMLID.
- Relation parity: value_parity compares a relation field only when its
  comodel_name and declared model + can_read projection are both present.
- Dependency closure: external imports and literal SQL execute sites are
  extracted, unresolved sites fail closed, and dependency_closure_complete is a
  real verdict propagated into receipts.
- Execution attestation: attest_execution_definition is wired into
  verify_github_origin from the candidate source tree.
- Admission: verify_github_origin derives every blocker from the authenticated
  receipt state and stamps reuse_authority=verified_six_dimension_closure only
  when none remain; receipt_reuse_authorized accepts that stamp alongside the
  isolated execution authority.

## Verified end-to-end (2026-10-25)

The readback witness now attaches in CI. The smart_construction_demo receipt
carries `readback_closure` with `runtime_contract_readback=True`: 24 comparable
scalar fields (amount, currency_id, date_request, state, and 20 others) have
zero mismatches across source, projection and readback. The witness also marks
derived/context-dependent fields, undeclared relation projections and
missing-value fields as uncovered, so `fact_scope_readback` stays False and
`projection_value_coverage_incomplete` remains - the intended fail-closed
result until relation parity and missing-value handling are extended.

Two CI-only defects were found and fixed during the end-to-end run:
- the probe invoked odoo_shell_exec.sh outside RUN_ENV and outside the CI
  one-off compose carrier; a dedicated scripts/ci/run_contract_fact_readback.sh
  now mirrors test.sh (compose run --rm, explicit DB and addons-path, no -c).
- discover_receipt_locators could exceed the 256-locator selection cap once
  enough successful runs accumulated; it now stops at MAX_LOCATORS.

Remaining: artifact_attempt_attested has no trusted source because the GitHub
artifact API does not expose the upload attempt, so Docker Odoo receipts stay
RUN. fact_scope_readback and target_dependency_closure stay open for the demo
receipt as expected (uncovered fields and unresolved inputs). Whole-product
acceptance remains separate and untouched.

## PR732 conflict closeout (2026-10-26)

Owner requested conflict resolution. Preserve local unpublished `af95e73170c30c16f43a6b0a53ddcc2ab4d349b7`
and published `2500d48bafe606b2c10763aa634e01d1ea941a20`; target main is
`b69f01fac19ab8c889baa540f44b25e34f7ee994`. No product or database changes.

Six conflicts are execution index, test registration, design document, complexity,
asset inventory and its summary. Move the existing low-code import away from the
shared EOF append point, preserving discovery. Main's design is the newer superset.
The active pre-commit regenerates reports, so hand-copying main's summary is not
a stable preparation. Extend only the existing summary path in the governed
report resolver; keep recovery bundle, exact refs and all other conflict rejection.
53 sync tests and iteration pass; successful-merge tests assert exact conflict set
and report bytes. Independent plan review confirmed preservation. Full merge
result, generated-evidence refresh, frozen review and current-head gates follow.
