# Scenario Entry Navigation Contract - 2026-11-11

## Identity and boundary

- Repository: `sce-backend-odoo`
- Baseline: `fe2f8ba175a685988a24c26dad08139d81018b30`
- Branch: `fix/scenario-entry-nav-contract-20261111`
- Formal Product Layer: P1 product semantics with P0 initialization consumption cleanup
- Layer Target: single login-role/native-menu route authority, initialization consumption, and standard business role closure
- Modules: `smart_construction_core`, `smart_construction_scene`, `smart_core`
- Standard vs User-Specific: construction industry standard
- Why here: P1 owns native menu/action/group identities, standard role closure, and the business-scene state that is no longer a navigation authorization input.
- Why not elsewhere: the frontend cannot synthesize entries; `smart_core` supplies only the completed delivery authority; delivery-lane repair belongs to a separate P4 topic.
- Blast radius: final route authority, initialization consumption, My Work, enterprise initialization visibility through native groups, Business Full/Business Config Admin group closure, and role-surface precedence. Native ACL, publication, record rules, customer data, and frontend rendering remain unchanged.

## Product decision

- Login role plus native menu/action/ACL facts are the single navigation authority. No additional menu binding or exemption is introduced for My Work or enterprise initialization.
- Business-scene activation remains configuration/catalog state. It does not re-filter the final initialization navigation or direct route authority.
- `system.init` does not invoke another company/scene authority pass after delivery has completed; it seals and returns the already-authorized navigation result.
- My Work follows its `base.group_user` native menu/action declaration.
- Enterprise initialization follows its persistent `group_sc_cap_business_config_admin` native menu/action declaration.
- Business Config Admin is the full-business superset. It inherits Business Full; Business Full does not inherit Business Config Admin. When both match, role projection selects Business Config Admin.
- A Business Full principal may use the enterprise setup landing scene but must not receive the enterprise initialization sidebar menu without Business Config Admin.

## Acceptance

- Company scene enablement changes do not add or remove role/native-authorized routes.
- `system.init` final navigation and route authority contain My Work for an internal Business Full principal.
- `system.init` final navigation and route authority contain both My Work and enterprise initialization for Business Config Admin.
- Business Full does not receive the enterprise initialization sidebar entry.

## Delivery-lane follow-up

`make ci.local.iteration` currently rejects this backend-only diff as unmapped by the frontend incremental planner. That is a P4 delivery-lane coverage issue and must be handled in an independent P4 topic; it is not changed in this product branch.

## Validation

Results are recorded in `.agent/runs/SCENARIO-ENTRY-NAV-CONTRACT-20261111/run.json`. No full Quick, release audit, deployment, or production-data operation is implied.
