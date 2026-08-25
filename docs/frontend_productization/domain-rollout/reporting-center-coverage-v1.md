# Reporting Center Frontend Rollout v1

This report covers the repository formal-product runtime baseline for the reporting_center center.
Demo, customer overlays, and user-specific visibility are deliberately excluded.

## Summary

- status: `PASS`
- formal actions: `6`
- models: `6`
- ready collection surfaces: `6`
- readable fallbacks: `9`
- structural forms: `4`
- fail-closed surfaces: `0`
- gaps: `0`

## Formal entries

| Menu | Action | Model | Views | Layered authority |
| --- | --- | --- | --- | --- |
| `smart_construction_core.menu_sc_comprehensive_cost_statistics_report` | `smart_construction_core.action_sc_comprehensive_cost_statistics_report` | `sc.comprehensive.cost.summary` | tree:table:ready, form:form_structure:structural, pivot:pivot:readable_fallback, graph:graph:readable_fallback | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_data_center`:[public] → `smart_construction_core.menu_sc_comprehensive_cost_statistics_report`:[`smart_construction_core.group_sc_cap_business_initiator`, `smart_construction_core.group_sc_cap_contract_manager`, `smart_construction_core.group_sc_cap_contract_read`, `smart_construction_core.group_sc_cap_contract_user`, `smart_construction_core.group_sc_cap_cost_manager`, `smart_construction_core.group_sc_cap_cost_read`, `smart_construction_core.group_sc_cap_cost_user`, `smart_construction_core.group_sc_cap_finance_manager`, `smart_construction_core.group_sc_cap_finance_read`, `smart_construction_core.group_sc_cap_finance_user`] → action:[`smart_construction_core.group_sc_cap_business_initiator`, `smart_construction_core.group_sc_cap_contract_manager`, `smart_construction_core.group_sc_cap_contract_read`, `smart_construction_core.group_sc_cap_contract_user`, `smart_construction_core.group_sc_cap_cost_manager`, `smart_construction_core.group_sc_cap_cost_read`, `smart_construction_core.group_sc_cap_cost_user`, `smart_construction_core.group_sc_cap_finance_manager`, `smart_construction_core.group_sc_cap_finance_read`, `smart_construction_core.group_sc_cap_finance_user`] |
| `smart_construction_core.menu_sc_fund_daily_summary` | `smart_construction_core.action_sc_fund_daily_summary` | `sc.fund.daily.summary` | tree:table:ready, form:form_structure:structural, pivot:pivot:readable_fallback, graph:graph:readable_fallback | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_data_center`:[public] → `smart_construction_core.menu_sc_fund_daily_summary`:[`smart_construction_core.group_sc_cap_finance_manager`, `smart_construction_core.group_sc_cap_finance_read`, `smart_construction_core.group_sc_cap_finance_user`] → action:[`smart_construction_core.group_sc_cap_finance_manager`, `smart_construction_core.group_sc_cap_finance_read`, `smart_construction_core.group_sc_cap_finance_user`] |
| `smart_construction_core.menu_sc_legacy_business_entity_map` | `smart_construction_core.action_sc_legacy_business_entity_map` | `sc.business.entity` | tree:table:ready | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_data_center`:[public] → `smart_construction_core.menu_sc_legacy_business_entity_map`:[`smart_construction_core.group_sc_cap_finance_read`] → action:[`smart_construction_core.group_sc_cap_finance_read`] |
| `smart_construction_core.menu_sc_product_labor_subcontract_report_v1` | `smart_construction_core.action_sc_product_labor_subcontract_report_v1` | `sc.labor.subcontract.report` | pivot:pivot:readable_fallback, graph:graph:readable_fallback, tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_data_center`:[public] → `smart_construction_core.menu_sc_product_labor_subcontract_report_v1`:[`smart_construction_core.group_sc_cap_data_read`] → action:[`smart_construction_core.group_sc_cap_data_read`] |
| `smart_construction_core.menu_sc_product_tax_report_v1` | `smart_construction_core.action_sc_product_tax_report_v1` | `sc.tax.filing` | pivot:pivot:readable_fallback, graph:graph:readable_fallback, tree:table:ready | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_data_center`:[public] → `smart_construction_core.menu_sc_product_tax_report_v1`:[`smart_construction_core.group_sc_cap_data_read`] → action:[`smart_construction_core.group_sc_cap_data_read`] |
| `smart_construction_core.menu_sc_project_operation_statistics_report` | `smart_construction_core.action_sc_project_operation_statistics_report` | `sc.operating.metrics.project` | tree:table:ready, form:form_structure:structural, pivot:pivot:readable_fallback | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_data_center`:[public] → `smart_construction_core.menu_sc_project_operation_statistics_report`:[`smart_construction_core.group_sc_cap_cost_read`, `smart_construction_core.group_sc_cap_finance_read`, `smart_construction_core.group_sc_cap_project_read`] → action:[`smart_construction_core.group_sc_cap_cost_read`, `smart_construction_core.group_sc_cap_finance_read`, `smart_construction_core.group_sc_cap_project_read`] |

## Gap classification

No P0/P1 frontend rollout gaps were detected for the formal reporting_center-center entries.

## Acceptance routing

- Primary journey: a formal reporting_center entry preserves its resolved action/menu and form authority.
- Security counterexample: an unauthorized user cannot gain entry or write authority.
- Any future unregistered `smart_*` view class fails this audit closed.
