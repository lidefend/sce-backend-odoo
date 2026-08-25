# Contract Domain Frontend Rollout v1

This report covers the repository formal-product runtime baseline for the contract center.
Demo, customer overlays, and user-specific visibility are deliberately excluded.

## Summary

- status: `PASS`
- formal actions: `7`
- models: `5`
- ready collection surfaces: `7`
- readable fallbacks: `0`
- structural forms: `7`
- fail-closed surfaces: `0`
- gaps: `0`

## Formal entries

| Menu | Action | Model | Views | Layered authority |
| --- | --- | --- | --- | --- |
| `smart_construction_core.menu_sc_p1_contract_change` | `smart_construction_core.action_sc_contract_change` | `sc.contract.change` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_contract_center`:[`smart_construction_core.group_sc_cap_business_initiator`, `smart_construction_core.group_sc_cap_contract_manager`, `smart_construction_core.group_sc_cap_contract_read`, `smart_construction_core.group_sc_cap_contract_user`, `smart_construction_core.group_sc_cap_purchase_manager`] → `smart_construction_core.menu_sc_p1_contract_change`:[`smart_construction_core.group_sc_cap_contract_read`] → action:[`smart_construction_core.group_sc_cap_contract_read`] |
| `smart_construction_core.menu_sc_p1_daily_contract` | `smart_construction_core.action_sc_general_contract` | `sc.general.contract` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_contract_center`:[`smart_construction_core.group_sc_cap_business_initiator`, `smart_construction_core.group_sc_cap_contract_manager`, `smart_construction_core.group_sc_cap_contract_read`, `smart_construction_core.group_sc_cap_contract_user`, `smart_construction_core.group_sc_cap_purchase_manager`] → `smart_construction_core.menu_sc_p1_daily_contract`:[`smart_construction_core.group_sc_cap_business_initiator`, `smart_construction_core.group_sc_cap_contract_manager`, `smart_construction_core.group_sc_cap_contract_read`, `smart_construction_core.group_sc_cap_contract_user`] → action:[`smart_construction_core.group_sc_cap_business_initiator`, `smart_construction_core.group_sc_cap_contract_manager`, `smart_construction_core.group_sc_cap_contract_read`, `smart_construction_core.group_sc_cap_contract_user`] |
| `smart_construction_core.menu_sc_p1_expense_contract` | `smart_construction_core.action_construction_contract_expense` | `construction.contract.expense` | tree:hierarchical_worksheet:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_contract_center`:[`smart_construction_core.group_sc_cap_business_initiator`, `smart_construction_core.group_sc_cap_contract_manager`, `smart_construction_core.group_sc_cap_contract_read`, `smart_construction_core.group_sc_cap_contract_user`, `smart_construction_core.group_sc_cap_purchase_manager`] → `smart_construction_core.menu_sc_p1_expense_contract`:[`smart_construction_core.group_sc_cap_contract_read`] → action:[`smart_construction_core.group_sc_cap_contract_manager`, `smart_construction_core.group_sc_cap_contract_read`, `smart_construction_core.group_sc_cap_contract_user`] |
| `smart_construction_core.menu_sc_p1_expense_settlement` | `smart_construction_core.action_sc_settlement_order_expense` | `sc.settlement.order` | tree:hierarchical_worksheet:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_contract_center`:[`smart_construction_core.group_sc_cap_business_initiator`, `smart_construction_core.group_sc_cap_contract_manager`, `smart_construction_core.group_sc_cap_contract_read`, `smart_construction_core.group_sc_cap_contract_user`, `smart_construction_core.group_sc_cap_purchase_manager`] → `smart_construction_core.menu_sc_p1_expense_settlement`:[`smart_construction_core.group_sc_cap_settlement_read`] → action:[`smart_construction_core.group_sc_cap_settlement_read`] |
| `smart_construction_core.menu_sc_p1_income_contract` | `smart_construction_core.action_construction_contract_income` | `construction.contract.income` | tree:hierarchical_worksheet:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_contract_center`:[`smart_construction_core.group_sc_cap_business_initiator`, `smart_construction_core.group_sc_cap_contract_manager`, `smart_construction_core.group_sc_cap_contract_read`, `smart_construction_core.group_sc_cap_contract_user`, `smart_construction_core.group_sc_cap_purchase_manager`] → `smart_construction_core.menu_sc_p1_income_contract`:[`smart_construction_core.group_sc_cap_contract_read`] → action:[`smart_construction_core.group_sc_cap_contract_manager`, `smart_construction_core.group_sc_cap_contract_read`, `smart_construction_core.group_sc_cap_contract_user`] |
| `smart_construction_core.menu_sc_p1_income_settlement` | `smart_construction_core.action_sc_settlement_order_income` | `sc.settlement.order` | tree:hierarchical_worksheet:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_contract_center`:[`smart_construction_core.group_sc_cap_business_initiator`, `smart_construction_core.group_sc_cap_contract_manager`, `smart_construction_core.group_sc_cap_contract_read`, `smart_construction_core.group_sc_cap_contract_user`, `smart_construction_core.group_sc_cap_purchase_manager`] → `smart_construction_core.menu_sc_p1_income_settlement`:[`smart_construction_core.group_sc_cap_settlement_read`] → action:[`smart_construction_core.group_sc_cap_settlement_read`] |
| `smart_construction_core.menu_sc_product_general_contract_settlement_v1` | `smart_construction_core.action_sc_product_general_contract_settlement_v1` | `sc.settlement.order` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_contract_center`:[`smart_construction_core.group_sc_cap_business_initiator`, `smart_construction_core.group_sc_cap_contract_manager`, `smart_construction_core.group_sc_cap_contract_read`, `smart_construction_core.group_sc_cap_contract_user`, `smart_construction_core.group_sc_cap_purchase_manager`] → `smart_construction_core.menu_sc_product_general_contract_settlement_v1`:[`smart_construction_core.group_sc_cap_contract_manager`, `smart_construction_core.group_sc_cap_contract_user`] → action:[`smart_construction_core.group_sc_cap_contract_manager`, `smart_construction_core.group_sc_cap_contract_user`] |

## Gap classification

No P0/P1 frontend rollout gaps were detected for the formal project-center entries.

## Acceptance routing

- Primary journey: a formal contract entry preserves its resolved action/menu and form authority.
- Security counterexample: an unauthorized user cannot gain entry or write authority.
- Any future unregistered `smart_*` view class fails this audit closed.
