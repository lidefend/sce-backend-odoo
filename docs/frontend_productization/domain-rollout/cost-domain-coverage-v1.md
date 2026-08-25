# Cost Domain Frontend Rollout v1

This report covers the repository formal-product runtime baseline for the cost center.
Demo, customer overlays, and user-specific visibility are deliberately excluded.

## Summary

- status: `PASS`
- formal actions: `4`
- models: `3`
- ready collection surfaces: `4`
- readable fallbacks: `3`
- structural forms: `4`
- fail-closed surfaces: `0`
- gaps: `0`

## Formal entries

| Menu | Action | Model | Views | Layered authority |
| --- | --- | --- | --- | --- |
| `smart_construction_core.menu_sc_p1_cost_ledger` | `smart_construction_core.action_project_cost_ledger` | `project.cost.ledger` | tree:table:ready, form:form_structure:structural, pivot:pivot:readable_fallback, graph:graph:readable_fallback | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_cost_center`:[public] → `smart_construction_core.menu_sc_p1_cost_ledger`:[`smart_construction_core.group_sc_cap_cost_manager`, `smart_construction_core.group_sc_cap_cost_user`] → action:[`smart_construction_core.group_sc_cap_cost_manager`, `smart_construction_core.group_sc_cap_cost_read`, `smart_construction_core.group_sc_cap_cost_user`] |
| `smart_construction_core.menu_sc_p1_cost_plan` | `smart_construction_core.action_project_cost_plan` | `project.cost.plan` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_cost_center`:[public] → `smart_construction_core.menu_sc_p1_cost_plan`:[`smart_construction_core.group_sc_cap_cost_manager`, `smart_construction_core.group_sc_cap_cost_user`] → action:[`smart_construction_core.group_sc_cap_cost_read`] |
| `smart_construction_core.menu_sc_p1_profit_analysis` | `smart_construction_core.action_project_profit_compare` | `project.profit.compare` | tree:table:ready, form:form_structure:structural, pivot:pivot:readable_fallback | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_cost_center`:[public] → `smart_construction_core.menu_sc_p1_profit_analysis`:[`smart_construction_core.group_sc_cap_cost_manager`, `smart_construction_core.group_sc_cap_cost_user`] → action:[`smart_construction_core.group_sc_cap_cost_manager`, `smart_construction_core.group_sc_cap_cost_read`, `smart_construction_core.group_sc_cap_cost_user`] |
| `smart_construction_core.menu_sc_p1_project_budget` | `smart_construction_core.action_project_budget` | `project.cost.plan` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_cost_center`:[public] → `smart_construction_core.menu_sc_p1_project_budget`:[`smart_construction_core.group_sc_cap_cost_manager`, `smart_construction_core.group_sc_cap_cost_user`] → action:[`smart_construction_core.group_sc_cap_cost_manager`, `smart_construction_core.group_sc_cap_cost_read`, `smart_construction_core.group_sc_cap_cost_user`] |

## Gap classification

No P0/P1 frontend rollout gaps were detected for the formal cost-center entries.

## Acceptance routing

- Primary journey: a formal cost entry preserves its resolved action/menu and form authority.
- Security counterexample: an unauthorized user cannot gain entry or write authority.
- Any future unregistered `smart_*` view class fails this audit closed.
