# Base Configuration Domain Frontend Rollout v1

This report covers the repository formal-product runtime baseline for the base_configuration center.
Demo, customer overlays, and user-specific visibility are deliberately excluded.

## Summary

- status: `PASS`
- formal actions: `6`
- models: `6`
- ready collection surfaces: `5`
- readable fallbacks: `0`
- structural forms: `6`
- fail-closed surfaces: `0`
- gaps: `0`

## Formal entries

| Menu | Action | Model | Views | Layered authority |
| --- | --- | --- | --- | --- |
| `smart_construction_core.menu_sc_approval_policy` | `smart_construction_core.action_sc_approval_policy` | `sc.approval.policy` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_business_config_center`:[`smart_construction_core.group_sc_cap_business_config_admin`] → `smart_construction_core.menu_sc_approval_policy`:[`smart_construction_core.group_sc_cap_business_config_admin`] → action:[`smart_construction_core.group_sc_cap_business_config_admin`] |
| `smart_construction_core.menu_sc_business_config_workbench` | `smart_construction_core.action_sc_business_config_workbench` | `ui.business.config.contract` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_business_config_center`:[`smart_construction_core.group_sc_cap_business_config_admin`] → `smart_construction_core.menu_sc_business_config_workbench`:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_core.group_smart_core_admin`, `smart_core.group_smart_core_business_config_admin`] → action:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_core.group_smart_core_admin`, `smart_core.group_smart_core_business_config_admin`] |
| `smart_construction_core.menu_sc_product_data_permission_v1` | `smart_construction_core.action_sc_product_data_permission_v1` | `res.users` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_business_config_center`:[`smart_construction_core.group_sc_cap_business_config_admin`] → `smart_construction_core.menu_sc_product_data_permission_v1`:[`smart_construction_core.group_sc_cap_config_admin`] → action:[`smart_construction_core.group_sc_cap_config_admin`] |
| `smart_construction_core.menu_sc_product_numbering_rule_v1` | `smart_construction_core.action_sc_product_numbering_rule_v1` | `ir.sequence` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_business_config_center`:[`smart_construction_core.group_sc_cap_business_config_admin`] → `smart_construction_core.menu_sc_product_numbering_rule_v1`:[`smart_construction_core.group_sc_cap_config_admin`] → action:[`smart_construction_core.group_sc_cap_config_admin`] |
| `smart_construction_core.menu_sc_product_system_parameter_v1` | `smart_construction_core.action_sc_product_system_parameter_v1` | `sc.product.system.settings` | form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_business_config_center`:[`smart_construction_core.group_sc_cap_business_config_admin`] → `smart_construction_core.menu_sc_product_system_parameter_v1`:[`smart_construction_core.group_sc_cap_config_admin`] → action:[`smart_construction_core.group_sc_cap_config_admin`] |
| `smart_construction_core.menu_ui_form_field_policy_business_config` | `smart_construction_core.action_ui_form_field_policy_business_config` | `ui.form.field.policy` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_business_config_center`:[`smart_construction_core.group_sc_cap_business_config_admin`] → `smart_construction_core.menu_ui_form_field_policy_business_config`:[`smart_construction_core.group_sc_cap_business_config_admin`] → action:[`smart_construction_core.group_sc_cap_business_config_admin`] |

## Gap classification

No P0/P1 frontend rollout gaps were detected for the formal base_configuration-center entries.

## Acceptance routing

- Primary journey: a formal base_configuration entry preserves its resolved action/menu and form authority.
- Security counterexample: an unauthorized user cannot gain entry or write authority.
- Any future unregistered `smart_*` view class fails this audit closed.
