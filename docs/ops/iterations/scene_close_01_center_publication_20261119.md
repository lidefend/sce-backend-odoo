# SCENE-CLOSE-01 Center Publication Authority

Status: active

Base: `b974c32423d14f20960bf959c844a6b92334bc1a`

Branch: `feature/scene-close-01-center-publication-authority-20261119`

## Product result

An administrator can edit product-center names, order and entry placement;
the change remains a draft until release, runtime navigation consumes the
active released snapshot, capability diagnostics explain the same center and
version, and rollback restores the previous center definition.

## Scope

- Stable center identity from the locked ten-center product baseline.
- Center definitions and menu placement in the existing product policy and
  release snapshot chain.
- Release-operator maintenance parameters, options and authoritative readback.
- Capability-explorer center explanation from the active released policy.
- Minimal frontend consumption in the existing release operator, capability
  explorer and native scenario maintenance surfaces.

## Exclusions

- Composite scenario dependency/version convergence.
- Versioning all scenario fields or lifecycle state.
- Automatic scenario creation or business-category inference.
- Deployment or production mutation.

## Contract validation

Odoo-native menus, actions, ACLs, models and installed module facts are inputs,
not claims owned by this change. Validation therefore checks this repository's
contract boundary rather than rebuilding or retesting Odoo capabilities.

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| Exact base and dirty scope | passed | `make agent.run.resume` | Current run resolves with `outside_scope=[]` |
| Producer declaration | passed | backend capability-explorer and catalog-action unit tests | Contract declares accepted fields, release-state options, readback fields and stable intent |
| Strict consumer | passed | frontend capability-explorer contract tests | Frontend stops on missing fields, undeclared values, absent readback and identity mismatch |
| Existing contract families | passed | admin management backend, product-center policy and capability identity units | Ensure the new admission contract does not alter existing projection semantics |
| Static/frontend quality | passed | contract-basis, design-system component-driver, lint and strict typecheck | The new controls remain contract-driven and use the registered design system |
| ORM, module baseline, upgrade and browser | excluded | owner direction | They would retest Odoo-native capability existence rather than this repository's contract logic |

Observed contract results:

- backend capability explorer: 24 + 9 + 2 passed
- frontend capability explorer: 46 contract cases passed, plus platform-duty and route-access checks
- admin management backend: 90 passed
- product-center policy: 8 passed
- capability identity boundary: 12 passed
- incremental planner: 185 passed
- frontend contract basis: 15 passed; open defects 0
- design-system component driver: 18 passed; required 33, missing 0, raw 0
- lint: 0 errors
- strict typecheck: exit 0

The closed contract gaps are:

1. Release-state choices now come from the backend action declaration instead
   of a frontend constant.
2. The frontend requires every declared accepted field before sending the
   admission intent.
3. Every declared write readback field is required before success is shown.
4. Empty or identity-mismatched readback fails closed.
5. The product-draft route is consumed from the backend declaration.

ORM and baseline commands started before the owner clarified this boundary were
interrupted and are not counted as passes.

## PR #943 CI remediation

The first exact-head run of PR #943 failed only in
`frontend_release_gate / managed_orm`; `merge_policy_gate` was a dependent
failure. Two acceptance navigation tests still expected legacy center
identities:

- `smart_construction_core.menu_sc_project_center`
- `construction.会计账务中心`

The candidate correctly returns the stable keys
`construction.center.project` and `construction.center.accounting`. This is a
baseline-evidence defect, not a product regression.

The fixture tests now derive the expected key from the P1
`center_identity(...).stable_key` contract instead of hard-coding either the
legacy XMLID or display-name key. Local ORM remains excluded by owner direction;
the new exact-head remote `managed_orm` run is the authoritative verification.

## Owner review remediation

The exact-head owner review identified contract-production and consumption
gaps without requiring ORM. The candidate now addresses them in the existing
contract chain:

1. Catalog admission updates only the selected compatibility capability. It no
   longer regenerates unrelated capabilities or scene-home source fields.
2. Qualification summaries, selected status, and compatibility fields use full
   product keys. Construction `standard/preview` are explicit projections of
   `construction.standard` and `construction.preview`.
3. Non-construction snapshots establish release authority, and generic
   published center keys are consumed directly instead of being filtered by
   the construction ten-center alias table.
4. Each catalog row declares `catalog_admission.enabled/reason_code/blockers`.
   The frontend combines this per-entry declaration with the global maintenance
   action instead of treating generic native validity as admission readiness.
5. Declared center sequence `0` is preserved through normalization,
   placement updates, and runtime projection.
6. The center editor strictly decodes editable fields, field constraints,
   accepted parameters, save-action availability, and authoritative readback.
   Missing declarations or invalid sequence values stop the action.
7. Catalog admission freezes entry identity before awaiting the write and uses
   that frozen identity for readback validation. Closing or switching details
   cannot attach the write to another entry.
8. `rollback_snapshot` execution now uses the dedicated
   `rollback_to_snapshot()` service, preserving the existing approval chain.

The obsolete product-group selector with no declared query or filter behavior
was removed until a backend behavior contract is introduced.

## Second owner review remediation

The platform-management surface now follows the same product contract model as
the business pages:

- `platform_management_action_contract.py` owns static P0 action identity,
  labels, intents, accepted inputs, editable field options, confirmation and
  readback requirements.
- The existing read model remains the dynamic authority. It binds the current
  product, actor, object, permissions and state to those definitions.
- Existing handlers remain the execution authority. The frontend no longer
  supplies freeze, sync, policy, page-policy, approval or rollback intents and
  parameters by convention.

Additional review corrections:

1. Re-adding an existing entry preserves maintained label, access level,
   sequence, intent and role restrictions.
2. Capability merge distinguishes the compatibility alias from a same-page
   business capability by capability identity.
3. Declared center sequence `0` survives P0 navigation-node construction and
   capability catalog numeric projection.
4. Pending approval rows now contain a complete decorated `approve_action`.
5. Policy and page-policy actions declare their complete accepted fields and
   selectable options.
6. Center-save readback must identify the same product in policy, readback and
   surface.
7. Backend numeric declarations require actual finite integers; `null` and
   `false` are rejected.
8. Rollback declarations and execution reject inactive target snapshots.

## Platform management as a product

The platform management page is now treated as a product surface driven by P0
configuration facts:

- `platform_management_action_contract.py` owns stable action labels, intents,
  accepted fields, editable options, confirmation requirements and readback
  requirements.
- The read model binds those facts to the current product, actor, target object,
  permissions and state.
- Existing `release.operator.*` handlers and document services remain the
  execution authority and revalidate current facts.
- The frontend executes the declared action object directly for freeze, sync,
  policy save, page policy, approval and rollback. It no longer reconstructs
  intents or falls back to missing parameters.
- Pending approval rows expose a complete decorated `approve_action`.
- Policy and page-policy actions declare the full accepted input sets and
  selectable options.

The platform action registry entry identifies the contract version. The
definitions and the current dynamic binding remain separate facts.
