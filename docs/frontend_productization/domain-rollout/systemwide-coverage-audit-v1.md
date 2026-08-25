# Frontend Systemwide Coverage Audit v1

- Status: **FAIL**
- Primary centers: **10**
- Runtime menu/action surfaces: **88**
- Excluded non-product surfaces: **1**
- Covered surfaces: **70**
- Uncovered surfaces: **18**
- Runtime/authority gaps: **0**

## Primary-center coverage

| Center | Runtime | Covered | Uncovered |
|---|---:|---:|---:|
| workbench | 4 | 4 | 0 |
| project | 30 | 30 | 0 |
| contract | 7 | 7 | 0 |
| cost | 4 | 4 | 0 |
| finance | 11 | 11 | 0 |
| tax | 9 | 0 | 9 |
| accounting | 3 | 0 | 3 |
| reporting | 6 | 0 | 6 |
| administration | 8 | 8 | 0 |
| product_configuration | 6 | 6 | 0 |

## Uncovered formal runtime surfaces

- `tax` — `smart_construction_core.menu_sc_tax_certificate_registration_user` → `smart_construction_core.action_sc_tax_certificate_registration_user` (`sc.tax.certificate.registration`)
- `tax` — `smart_construction_core.menu_sc_invoice_prepaid_tax_user` → `smart_construction_core.action_sc_invoice_prepaid_tax_user` (`sc.invoice.registration`)
- `tax` — `smart_construction_core.menu_sc_invoice_application_user` → `smart_construction_core.action_sc_invoice_application_user` (`sc.invoice.registration`)
- `tax` — `smart_construction_core.menu_sc_invoice_registration_user` → `smart_construction_core.action_sc_invoice_registration_user` (`sc.invoice.registration`)
- `tax` — `smart_construction_core.menu_sc_output_invoice_change_registration` → `smart_construction_core.action_sc_output_invoice_change_registration` (`sc.output.invoice.adjustment`)
- `tax` — `smart_construction_core.menu_sc_invoice_input` → `smart_construction_core.action_sc_invoice_input` (`sc.invoice.registration`)
- `tax` — `smart_construction_core.menu_sc_tax_deduction_registration_user` → `smart_construction_core.action_sc_tax_deduction_registration_user` (`sc.tax.deduction.registration`)
- `tax` — `smart_construction_core.menu_sc_product_project_tax_deduction_v1` → `smart_construction_core.action_sc_product_project_tax_deduction_v1` (`sc.tax.deduction.registration`)
- `tax` — `smart_construction_core.menu_sc_product_tax_filing_v1` → `smart_construction_core.action_sc_product_tax_filing_v1` (`sc.tax.filing`)
- `accounting` — `smart_construction_core.menu_sc_account_journal_foundation` → `smart_construction_core.action_sc_account_journal_foundation` (`account.journal`)
- `accounting` — `smart_construction_core.menu_sc_analytic_account_foundation` → `smart_construction_core.action_sc_analytic_account_foundation` (`account.analytic.account`)
- `accounting` — `smart_construction_core.menu_sc_analytic_distribution_foundation` → `smart_construction_core.action_sc_analytic_distribution_foundation` (`account.analytic.distribution.model`)
- `reporting` — `smart_construction_core.menu_sc_project_operation_statistics_report` → `smart_construction_core.action_sc_project_operation_statistics_report` (`sc.operating.metrics.project`)
- `reporting` — `smart_construction_core.menu_sc_legacy_business_entity_map` → `smart_construction_core.action_sc_legacy_business_entity_map` (`sc.business.entity`)
- `reporting` — `smart_construction_core.menu_sc_comprehensive_cost_statistics_report` → `smart_construction_core.action_sc_comprehensive_cost_statistics_report` (`sc.comprehensive.cost.summary`)
- `reporting` — `smart_construction_core.menu_sc_fund_daily_summary` → `smart_construction_core.action_sc_fund_daily_summary` (`sc.fund.daily.summary`)
- `reporting` — `smart_construction_core.menu_sc_product_tax_report_v1` → `smart_construction_core.action_sc_product_tax_report_v1` (`sc.tax.filing`)
- `reporting` — `smart_construction_core.menu_sc_product_labor_subcontract_report_v1` → `smart_construction_core.action_sc_product_labor_subcontract_report_v1` (`sc.labor.subcontract.report`)

## Boundary

This report compares the locked ten-center runtime menu/action graph with exact menu/action identities in delivered domain evidence. Internal system management, demo addons, and customer overlays are excluded explicitly.
