# Scene R3 Runtime Dashboard

更新时间：2026-09-04 14:41:57

## Summary

- `r3_scene_count`: 20
- `pass_count`: 20
- `fail_count`: 0
- `action_chain_success_count`: 20
- `action_chain_fallback_count`: 0
- `action_chain_fail_count`: 0
- `pass_rate`: 100.00%
- `action_chain_success_rate`: 100.00%
- `action_chain_fallback_rate`: 0.00%

## Gate Thresholds

- `max_action_chain_fail_count`: 0
- `min_pass_rate`: 100.00%
- `min_action_chain_success_rate`: 50.00%
- `max_action_chain_fallback_rate`: 50.00%

## Gate Result

- `result`: PASS
- `blocker_count`: 0
- `warning_count`: 0

## Checks

| scene_key | has_role_variants | has_data_sources | has_product_policy | primary_action_resolved | action_chain_openable | action_chain_status | action_chain_resolution | action_chain_route | role_zone_mapping_valid | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| contract.center | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | action_scene_ref | /s/contracts.workspace | ✅ | PASS |
| contracts.workspace | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /s/contract.center | ✅ | PASS |
| cost.analysis | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | action_scene_ref | /s/cost.project_cost_ledger | ✅ | PASS |
| cost.cost_compare | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /s/cost.analysis | ✅ | PASS |
| cost.project_cost_ledger | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | action_scene_ref | /s/cost.cost_compare | ✅ | PASS |
| data.dictionary | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /s/projects.list | ✅ | PASS |
| finance.center | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | action_scene_ref | /s/finance.payment_requests | ✅ | PASS |
| finance.payment_requests | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /s/finance.center | ✅ | PASS |
| finance.settlement_orders | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /s/finance.center | ✅ | PASS |
| finance.workspace | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | action_scene_ref | /s/finance.payment_requests | ✅ | PASS |
| my_work.workspace | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | action_scene_ref | /s/projects.list | ✅ | PASS |
| portal.capability_matrix | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /pm/dashboard | ✅ | PASS |
| portal.dashboard | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /pm/dashboard | ✅ | PASS |
| portal.lifecycle | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /pm/dashboard | ✅ | PASS |
| project.management | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /s/projects.ledger | ✅ | PASS |
| projects.dashboard | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /pm/dashboard | ✅ | PASS |
| projects.intake | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | non_ui_contract | N/A | ✅ | PASS |
| projects.ledger | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | action_scene_ref | /pm/dashboard | ✅ | PASS |
| projects.list | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | action_scene_ref | /s/projects.intake | ✅ | PASS |
| risk.center | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /pm/dashboard | ✅ | PASS |

