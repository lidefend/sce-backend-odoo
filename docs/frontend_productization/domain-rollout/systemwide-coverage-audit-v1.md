# Frontend Systemwide Coverage Audit v1

- Status: **FAIL**
- Primary centers: **10**
- Runtime menu/action surfaces: **88**
- Excluded non-product surfaces: **1**
- Covered surfaces: **82**
- Uncovered surfaces: **6**
- Runtime/authority gaps: **0**

## Primary-center coverage

| Center | Runtime | Covered | Uncovered |
|---|---:|---:|---:|
| workbench | 4 | 4 | 0 |
| project | 30 | 30 | 0 |
| contract | 7 | 7 | 0 |
| cost | 4 | 4 | 0 |
| finance | 11 | 11 | 0 |
| tax | 9 | 9 | 0 |
| accounting | 3 | 3 | 0 |
| reporting | 6 | 0 | 6 |
| administration | 8 | 8 | 0 |
| product_configuration | 6 | 6 | 0 |

## Uncovered formal runtime surfaces

- `reporting` — `smart_construction_core.menu_sc_project_operation_statistics_report` → `smart_construction_core.action_sc_project_operation_statistics_report` (`sc.operating.metrics.project`)
- `reporting` — `smart_construction_core.menu_sc_legacy_business_entity_map` → `smart_construction_core.action_sc_legacy_business_entity_map` (`sc.business.entity`)
- `reporting` — `smart_construction_core.menu_sc_comprehensive_cost_statistics_report` → `smart_construction_core.action_sc_comprehensive_cost_statistics_report` (`sc.comprehensive.cost.summary`)
- `reporting` — `smart_construction_core.menu_sc_fund_daily_summary` → `smart_construction_core.action_sc_fund_daily_summary` (`sc.fund.daily.summary`)
- `reporting` — `smart_construction_core.menu_sc_product_tax_report_v1` → `smart_construction_core.action_sc_product_tax_report_v1` (`sc.tax.filing`)
- `reporting` — `smart_construction_core.menu_sc_product_labor_subcontract_report_v1` → `smart_construction_core.action_sc_product_labor_subcontract_report_v1` (`sc.labor.subcontract.report`)

## Boundary

This report compares the locked ten-center runtime menu/action graph with exact menu/action identities in delivered domain evidence. Internal system management, demo addons, and customer overlays are excluded explicitly.
