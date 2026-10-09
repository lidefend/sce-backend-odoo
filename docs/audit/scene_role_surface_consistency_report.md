# Scene Role Surface Consistency Report

更新时间：2026-10-09 14:02:57

## Summary

- `role_count`: 10
- `r3_scene_count`: 22
- `errors`: 0
- `warnings`: 17

## Role Overrides

| role_code | candidates | candidate_missing | menu_overlap | r3_scene_hits | status |
| --- | ---: | ---: | ---: | ---: | --- |
| business_config_admin | 4 | 1 | 0 | 0 | PASS |
| business_full | 2 | 1 | 0 | 0 | PASS |
| cost | 3 | 1 | 0 | 1 | PASS |
| executive | 7 | 1 | 0 | 15 | PASS |
| finance | 4 | 1 | 0 | 10 | PASS |
| owner | 4 | 1 | 0 | 0 | PASS |
| pm | 8 | 1 | 0 | 18 | PASS |
| project_member | 3 | 1 | 0 | 0 | PASS |
| restricted | 1 | 1 | 0 | 0 | PASS |
| system_admin | 1 | 1 | 0 | 0 | PASS |

## R3 Scene Role Variants

| scene_key | role_variant_count | unknown_roles | status |
| --- | ---: | --- | --- |
| contract.center | 2 |  | PASS |
| contracts.workspace | 2 |  | PASS |
| cost.analysis | 2 |  | PASS |
| cost.cost_compare | 2 |  | PASS |
| cost.project_cost_ledger | 2 |  | PASS |
| data.dictionary | 2 |  | PASS |
| finance.center | 2 |  | PASS |
| finance.payment_requests | 2 |  | PASS |
| finance.settlement_orders | 0 |  | PASS |
| finance.workspace | 2 |  | PASS |
| my_work.workspace | 2 |  | PASS |
| portal.capability_matrix | 2 |  | PASS |
| portal.dashboard | 2 |  | PASS |
| portal.lifecycle | 2 |  | PASS |
| portal.notifications | 3 |  | PASS |
| portal.shortcuts | 3 |  | PASS |
| project.management | 2 |  | PASS |
| projects.dashboard | 2 |  | PASS |
| projects.intake | 2 |  | PASS |
| projects.ledger | 2 |  | PASS |
| projects.list | 2 |  | PASS |
| risk.center | 2 |  | PASS |

## Warnings

- finance.settlement_orders: role_variants empty for R3 scene
- role_surface_overrides.business_config_admin: landing_scene_candidate not in inventory/payload (workspace.home)
- role_surface_overrides.business_config_admin: no R3 scene role_variants coverage
- role_surface_overrides.business_full: landing_scene_candidate not in inventory/payload (workspace.home)
- role_surface_overrides.business_full: no R3 scene role_variants coverage
- role_surface_overrides.cost: landing_scene_candidate not in inventory/payload (workspace.home)
- role_surface_overrides.executive: landing_scene_candidate not in inventory/payload (workspace.home)
- role_surface_overrides.finance: landing_scene_candidate not in inventory/payload (workspace.home)
- role_surface_overrides.owner: landing_scene_candidate not in inventory/payload (workspace.home)
- role_surface_overrides.owner: no R3 scene role_variants coverage
- role_surface_overrides.pm: landing_scene_candidate not in inventory/payload (workspace.home)
- role_surface_overrides.project_member: landing_scene_candidate not in inventory/payload (workspace.home)
- role_surface_overrides.project_member: no R3 scene role_variants coverage
- role_surface_overrides.restricted: landing_scene_candidate not in inventory/payload (workspace.home)
- role_surface_overrides.restricted: no R3 scene role_variants coverage
- role_surface_overrides.system_admin: landing_scene_candidate not in inventory/payload (workspace.home)
- role_surface_overrides.system_admin: no R3 scene role_variants coverage

