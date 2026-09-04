# Scene R3 Runtime Dashboard

更新时间：2026-09-04 12:25:28

## Summary

- `r3_scene_count`: 21
- `pass_count`: 20
- `fail_count`: 1
- `action_chain_success_count`: 11
- `action_chain_fallback_count`: 9
- `action_chain_fail_count`: 1
- `pass_rate`: 95.24%
- `action_chain_success_rate`: 52.38%
- `action_chain_fallback_rate`: 42.86%

## Gate Thresholds

- `max_action_chain_fail_count`: 0
- `min_pass_rate`: 100.00%
- `min_action_chain_success_rate`: 50.00%
- `max_action_chain_fallback_rate`: 50.00%

## Gate Result

- `result`: FAIL (BLOCKER)
- `blocker_count`: 2
- `warning_count`: 0
- `BLOCKER`: action_chain_fail_count exceeded (1 > 0.0)
- `BLOCKER`: pass_rate below threshold (95.24% < 100.00%)

## Checks

| scene_key | has_role_variants | has_data_sources | has_product_policy | primary_action_resolved | action_chain_openable | action_chain_status | action_chain_resolution | action_chain_route | role_zone_mapping_valid | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| contract.center | ✅ | ✅ | ✅ | ✅ | ✅ | FALLBACK | self_target_fallback | /s/contract.center | ✅ | PASS |
| contracts.workspace | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /s/contract.center | ✅ | PASS |
| cost.analysis | ✅ | ✅ | ✅ | ✅ | ✅ | FALLBACK | self_target_fallback | /s/cost.analysis | ✅ | PASS |
| cost.cost_compare | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /s/cost.analysis | ✅ | PASS |
| cost.project_cost_ledger | ✅ | ✅ | ✅ | ✅ | ✅ | FALLBACK | self_target_fallback | /s/cost.project_cost_ledger | ✅ | PASS |
| data.dictionary | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /s/projects.list | ✅ | PASS |
| finance.center | ✅ | ✅ | ✅ | ✅ | ✅ | FALLBACK | self_target_fallback | /s/finance.center | ✅ | PASS |
| finance.payment_requests | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /s/finance.center | ✅ | PASS |
| finance.settlement_orders | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /s/finance.center | ✅ | PASS |
| finance.workspace | ✅ | ✅ | ✅ | ✅ | ✅ | FALLBACK | self_target_fallback | /s/finance.workspace | ✅ | PASS |
| my_work.workspace | ✅ | ✅ | ✅ | ✅ | ✅ | FALLBACK | self_target_fallback | /s/my_work.workspace | ✅ | PASS |
| portal.capability_matrix | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /pm/dashboard | ✅ | PASS |
| portal.dashboard | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /pm/dashboard | ✅ | PASS |
| portal.lifecycle | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /pm/dashboard | ✅ | PASS |
| project.management | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /s/projects.ledger | ✅ | PASS |
| projects.dashboard | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /pm/dashboard | ✅ | PASS |
| projects.dashboard_showcase | ❌ | ❌ | ❌ | ❌ | ❌ | FAIL | payload_missing |  | ❌ | FAIL |
| projects.intake | ✅ | ✅ | ✅ | ✅ | ✅ | FALLBACK | self_target_fallback | /s/projects.intake | ✅ | PASS |
| projects.ledger | ✅ | ✅ | ✅ | ✅ | ✅ | FALLBACK | related_scene_fuzzy | /pm/dashboard | ✅ | PASS |
| projects.list | ✅ | ✅ | ✅ | ✅ | ✅ | FALLBACK | related_scene_fuzzy | /s/projects.intake | ✅ | PASS |
| risk.center | ✅ | ✅ | ✅ | ✅ | ✅ | SUCCESS | related_scene_match | /pm/dashboard | ✅ | PASS |

