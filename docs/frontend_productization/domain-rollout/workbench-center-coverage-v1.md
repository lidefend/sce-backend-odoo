# Workbench Center Frontend Rollout v1

This report covers the repository formal-product runtime baseline for the workbench_center center.
Demo, customer overlays, and user-specific visibility are deliberately excluded.

## Summary

- status: `PASS`
- formal actions: `4`
- models: `4`
- ready collection surfaces: `5`
- readable fallbacks: `1`
- structural forms: `4`
- fail-closed surfaces: `0`
- gaps: `0`

## Formal entries

| Menu | Action | Model | Views | Layered authority |
| --- | --- | --- | --- | --- |
| `smart_construction_core.menu_sc_operating_metrics_project` | `smart_construction_core.action_sc_operating_metrics_project` | `sc.operating.metrics.project` | tree:table:ready, form:form_structure:structural, pivot:pivot:readable_fallback | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_workspace_center`:[public] → `smart_construction_core.menu_sc_operating_metrics_project`:[`smart_construction_core.group_sc_cap_cost_read`, `smart_construction_core.group_sc_cap_finance_read`, `smart_construction_core.group_sc_cap_project_read`] → action:[`smart_construction_core.group_sc_cap_cost_user`] |
| `smart_construction_core.menu_sc_product_message_notification_v1` | `smart_construction_core.action_sc_product_message_notification_v1` | `mail.notification` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_workspace_center`:[public] → `smart_construction_core.menu_sc_product_message_notification_v1`:[`smart_construction_core.group_sc_cap_project_read`] → action:[`smart_construction_core.group_sc_cap_project_read`] |
| `smart_construction_core.menu_sc_project_kanban` | `smart_construction_core.action_project_dashboard` | `project.project` | kanban:workflow_board:ready, tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_workspace_center`:[public] → `smart_construction_core.menu_sc_project_kanban`:[`smart_construction_core.group_sc_cap_project_read`] → action:[`smart_construction_core.group_sc_cap_project_read`] |
| `smart_construction_core.menu_sc_workbench_my_todo_fact` | `smart_construction_core.action_sc_workbench_task_center` | `sc.workbench.item` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_workspace_center`:[public] → `smart_construction_core.menu_sc_workbench_my_todo_fact`:[`smart_construction_core.group_sc_internal_user`] → action:[`smart_construction_core.group_sc_task_entry_access`] |

## Gap classification

No P0/P1 frontend rollout gaps were detected for the formal workbench_center-center entries.

## Acceptance routing

- Primary journey: a formal workbench_center entry preserves its resolved action/menu and form authority.
- Security counterexample: an unauthorized user cannot gain entry or write authority.
- Any future unregistered `smart_*` view class fails this audit closed.
