# Scenario Entry Navigation Contract - 2026-11-11

## Identity and boundary

- Repository: `sce-backend-odoo`
- Baseline: `fe2f8ba175a685988a24c26dad08139d81018b30`
- Branch: `fix/scenario-entry-nav-contract-20261111`
- Formal Product Layer: P1 product semantics with P0 initialization consumption cleanup
- Layer Target: single login-role/native-menu authority, composition-only scenario layer, final route projection, and standard business role closure
- Modules: `smart_construction_core`, `smart_construction_scene`, `smart_core`
- Standard vs User-Specific: construction industry standard
- Why here: P1 owns native menu/action/group identities, standard role closure, and the business-scene state that is no longer a navigation authorization input.
- Why not elsewhere: the frontend cannot synthesize entries; `smart_core` supplies only the completed delivery authority; delivery-lane repair belongs to a separate P4 topic.
- Blast radius: final route authority, initialization consumption, My Work, enterprise initialization visibility through native groups, Business Full/Business Config Admin group closure, and role-surface precedence. Native ACL, publication, record rules, customer data, and frontend rendering remain unchanged.

## Product decision

- Login role plus native menu/action/ACL facts are the single navigation authority. No additional menu binding or exemption is introduced for My Work or enterprise initialization.
- Business-scene activation remains configuration/catalog state. It does not re-filter the final initialization navigation or direct route authority.
- `system.init` does not invoke another company/scene authority pass after delivery has completed; it seals and returns the already-authorized navigation result.
- Route is not a maintained fact. Native action contexts, product-entry sources and scene carriers do not store URL routes.
- Scene composition references existing `menu/action` identities. The final navigation projection derives `/s/{scene_key}` or `/a/{action_id}?menu_id={menu_id}` from the composed node identity.
- `system.init` returns the same final scenarioized navigation tree and route authority after mechanical route projection.
- My Work follows its `base.group_user` native menu/action declaration.
- Enterprise initialization follows its persistent `group_sc_cap_business_config_admin` native menu/action declaration.
- Business Config Admin is the full-business superset. It inherits Business Full; Business Full does not inherit Business Config Admin. When both match, role projection selects Business Config Admin.
- A Business Full principal may use the enterprise setup landing scene but must not receive the enterprise initialization sidebar menu without Business Config Admin.

## Acceptance

- Company scene enablement changes do not add or remove role/native-authorized routes.
- `system.init` final navigation and route authority contain My Work for an internal Business Full principal.
- `system.init` final navigation and route authority contain both My Work and enterprise initialization for Business Config Admin.
- Business Full does not receive the enterprise initialization sidebar entry.
- No production view or action declares `sc_web_route`.
- Scene data, scene registry and product-entry sources contain no maintained route URL.

## Delivery-lane follow-up

`make ci.local.iteration` currently rejects this backend-only diff as unmapped by the frontend incremental planner. That is a P4 delivery-lane coverage issue and must be handled in an independent P4 topic; it is not changed in this product branch.

The same run resolves the iteration index correctly but the delivery planner still reports:

`frontend.dev.incremental: unmapped changed paths require an explicit registered target`.

This is classified as `validation_tool_defect` / P4, not a product failure. It must not be repaired by adding frontend semantics or changing the runtime contract.

## Validation

Results are recorded in `.agent/runs/SCENARIO-ENTRY-NAV-CONTRACT-20261111/run.json`.

Passed:

- `make verify.backend.navigation_delivery.unit`
- `make verify.navigation.publication_consumers.unit`
- `make verify.construction.policy_maps.unit`
- `make verify.system_init.menu_boundary.guard`
- `make verify.scene.fact_data.boundary.unit`
- `make verify.product_menu_release_gate.contract.unit`
- `make verify.frontend.scene_entry_contract.unit`
- `python3 addons/smart_construction_scene/tests/test_action_only_scene_semantic_supply.py`
- `python3 addons/smart_construction_scene/tests/test_scene_registry_yaml_asset_merge.py`

- `make acceptance.module.upgrade MODULE=smart_core,smart_construction_core,smart_construction_scene`
  on `ceff9ad3f90ec363a6cc472241fffddabb3262cc`
- `make acceptance.frontend.fixture_orm` on final product code
  `701c0766da1cfbb7b5c84b8a00e7cf68a3b7ef5b`:
  47 passed, 0 failed, 0 errors

Runtime evidence:

- Business Full receives `(714, 962)` for My Work at `/s/my_work.workspace`
  and does not receive enterprise initialization.
- Business Config Admin receives `(714, 962)` and `(713, 961)`, at
  `/s/my_work.workspace` and `/s/enterprise.setup`.
- Both pairs are in final `navigation.nav`, allowed route-authority buckets and
  `entry_target`; neither carries `BUSINESS_SCENARIO_CONFIGURATION_MISSING`.
- The acceptance test archives only historical construction release snapshots
  inside its rollback-only transaction so the current maintained P1 policy is
  tested instead of a prior immutable snapshot.

Original runtime log:
`.runtime/acceptance/fixture_orm_20261111T053901Z.log`.

No full Quick, release audit, deployment, or production-data operation is implied.
