# NATIVE-SCENE-01 / P0-3 + P0-5 · Native Action Contract Delivery

Status: implementation complete; exact-head CI and independent review pending.

Date: 2026-11-16

Baseline main: `56ded801d95cd2a30c9c8f976379e060936a9c3d`

## 1. Boundary

- Formal Product Layer: P0 platform kernel product.
- Module: `addons/smart_core` and the generic Web Contract Decoder/ActionView.
- Objective: publish and consume one native Action-level control contract in the
  same delivery batch.
- Exclusions: P0-4 occurrence identity, AST migration, Widget/Renderer redesign,
  Calendar/Gantt/Dashboard and every industry-specific presentation.

## 2. Required contract

The public `nativeActionContract` carries:

- Action identity and optional entry references;
- Action-scoped domain/context;
- Action-bound Search identity;
- ordered, selectable View Set rows and active/default view;
- projection, client-renderer and business-execution readiness as separate axes.

## 3. Implementation result

### 3.1 Backend producer

`addons/smart_core/core/native_action_contract.py:94-240` adds a pure producer
that consumes only facts already resolved by ActionResolver/PageAssembler. It:

- preserves Odoo's effective `action.views` order and duplicate same-type rows;
- publishes Action identity, optional Menu entry references, Domain/Context scope,
  Search identity and the active/default View;
- keeps projection availability, backend contract readiness, client renderer
  readiness and business execution readiness independent;
- omits the root contract when no ordered View row can be resolved instead of
  publishing an invalid placeholder View type;
- performs no Odoo lookup and grants no permission.

`addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:934-970`
enriches each View row with its resolved XMLID and projection status. The existing
Action identity remains separate from Menu identity.

`addons/smart_core/core/unified_page_contract_v2_assembler.py:1254-1268` publishes
the contract as the optional V2 root `nativeActionContract`.

### 3.2 Protocol

The schema version is now `2.3.0` with a closed `nativeActionContract` definition:

- `docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json:359`
- schema SHA256:
  `6b889eaa521cb7d564f27853a7e0d0c1e771da1d50e682e4d041027af056a887`
- ActionViewType, ordered View, Search and readiness-axis definitions are closed
  objects; unknown fields fail validation.
- An Action with no resolvable ordered View does not publish a placeholder
  `nativeActionContract`; the page remains on the existing model projection path.

### 3.3 Frontend consumption

- `frontend/apps/web/src/app/contracts/v2/schema.ts:2656-2819` strictly decodes
  the new root and cross-checks model, active View and Search identity.
- `frontend/apps/web/src/app/contracts/actionViewSurfaceContract.ts:152-196`
  derives available collection modes from `orderedViews/selectable`, excluding
  non-ready and unsupported rows, and reads the default mode from the contract.
- `frontend/apps/web/src/views/ActionView.vue:1750-1762` uses that authority for
  the active/default View and treats the delivered View Set as exclusive.
- `frontend/apps/web/src/app/action_runtime/useActionViewModeRuntime.ts:32-49`
  refuses a switch to a mode absent from the delivered View Set, including the
  empty-set case.
- Model-only pages without an Action continue without a fabricated contract.

### 3.4 Runtime-discovered Search identity closure

The first exact-head `local` list acceptance exposed a real contract-consistency
defect: `nativeActionContract.search` was published, while the sibling
`searchContract.nativeIdentity` was omitted by the V2 search projection. The
strict Decoder therefore stopped the payment-request list with
`ContractV2DecodeError`.

The correction carries the already-resolved `nativeIdentity` into
`searchContract` and adds an Odoo integration assertion that both contracts
publish the same Search View ID and authority. The browser client and acceptance
declarations now advertise contract version `2.3.x` as well.

## 4. Verification

Passed:

- `make verify.native_action.contract.unit`: 7 tests.
- `make verify.native_action.contract.orm`: 3 tests, including a real Odoo
  Window Action projected into V2.
- `make verify.unified_page_contract.v2.schema`: PASS.
- `make verify.unified_page_contract.v2.assembler`: PASS, cache v60.
- `make verify.backend.contract_lifecycle.authority`: PASS, schema 2.3.0.
- `make verify.frontend.contract_record_action_state.unit`: PASS, 33 checks.
- `make verify.frontend.collection_view_semantics.unit`: PASS.
- `make verify.frontend.professional_component_registry.unit`: PASS, 162 tests.
- `make verify.frontend.dev.incremental.unit`: PASS, 159 tests.
- `make verify.frontend.typecheck.strict`: PASS.
- `make verify.semantic.registry.lint`: PASS.
- `make verify.unified_page_contract.v2.intent`: PASS.
- `make verify.frontend.contract_v2_render_authority.unit`: PASS, 361 fields,
  unclassified=0.
- `make verify.native_scene.inventory.unit`: PASS, generated inventory current.
- Selected docs guards `inventory`, `contract_sync`, `temp_guard` and
  `product_boundary`: PASS.
- `make ci.local.iteration`: PASS, 21 affected targets on candidate
  `00afae6d41306c10b74c6fbfa4125e30c145bf86`. Receipt:
  `.runtime/frontend-dev-validation/executions/20261116T141811Z-4002020-425895752/receipt.json`.
- `make ci.delivery.freeze.prepare`: PASS on the same candidate.

`make verify.docs.links` remains **not passed**: 72 missing links are reported.
The report contains no missing link sourced from this batch's implementation
record or Unified Page Contract files; this is classified as a pre-existing
`baseline_evidence_defect`, not a P0-3/P0-5 pass claim.

The governed delivery plan still requires `daily_runtime_entry` and
`list_surface_structure` runtime evidence. This batch did not have runtime
environment/credential authority for those checks, so they remain not run rather
than being counted as product passes.

## 5. L1-L4

- L1 Odoo facts: PASS for Action ordering, View IDs, Search View and model.
- L2 backend contract: PASS for producer, V2 schema and real ORM projection.
- L3 frontend contract consumption: PASS for strict Decoder, View navigation
  authority and actual switch rejection. No Renderer redesign was involved.
- L4 business acceptance: NOT RUN. This batch did not execute role/browser journeys;
  the real Odoo ORM carrier is L2/L3 evidence, not L4.

## 6. Boundary and next step

P0-4 occurrence unification and AST migration remain excluded. The next
verification step is the exact-head `ci.local.iteration`, delivery freeze
preparation, independent review and remote required checks.
