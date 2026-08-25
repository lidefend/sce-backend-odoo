# Administration Domain Frontend Rollout v1

This report covers the repository formal-product runtime baseline for the administration center.
Demo, customer overlays, and user-specific visibility are deliberately excluded.

## Summary

- status: `PASS`
- formal actions: `8`
- models: `6`
- ready collection surfaces: `8`
- readable fallbacks: `0`
- structural forms: `8`
- fail-closed surfaces: `0`
- gaps: `0`

## Formal entries

| Menu | Action | Model | Views | Layered authority |
| --- | --- | --- | --- | --- |
| `smart_construction_core.menu_sc_certificate_registration` | `smart_construction_core.action_sc_certificate_registration` | `sc.document.admin.document` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_hr_admin_center`:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_construction_core.group_sc_cap_business_initiator`] → `smart_construction_core.menu_sc_certificate_registration`:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_construction_core.group_sc_cap_business_initiator`] → action:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_construction_core.group_sc_cap_business_initiator`] |
| `smart_construction_core.menu_sc_organization_department` | `smart_construction_core.action_sc_organization_department` | `hr.department` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_hr_admin_center`:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_construction_core.group_sc_cap_business_initiator`] → `smart_construction_core.menu_sc_organization_department`:[`smart_construction_core.group_sc_cap_data_read`] → action:[`smart_construction_core.group_sc_cap_data_read`] |
| `smart_construction_core.menu_sc_payroll_management` | `smart_construction_core.action_sc_payroll_management` | `sc.hr.payroll.document` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_hr_admin_center`:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_construction_core.group_sc_cap_business_initiator`] → `smart_construction_core.menu_sc_payroll_management`:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_construction_core.group_sc_cap_business_initiator`] → action:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_construction_core.group_sc_cap_business_initiator`] |
| `smart_construction_core.menu_sc_product_job_management_v1` | `smart_construction_core.action_sc_product_job_management_v1` | `hr.job` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_hr_admin_center`:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_construction_core.group_sc_cap_business_initiator`] → `smart_construction_core.menu_sc_product_job_management_v1`:[`smart_construction_core.group_sc_cap_business_config_admin`] → action:[`smart_construction_core.group_sc_cap_business_config_admin`] |
| `smart_construction_core.menu_sc_product_office_asset_v1` | `smart_construction_core.action_sc_product_office_asset_v1` | `sc.office.asset` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_hr_admin_center`:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_construction_core.group_sc_cap_business_initiator`] → `smart_construction_core.menu_sc_product_office_asset_v1`:[`smart_construction_core.group_sc_cap_business_config_admin`] → action:[`smart_construction_core.group_sc_cap_business_config_admin`] |
| `smart_construction_core.menu_sc_product_policy_document_v1` | `smart_construction_core.action_sc_product_policy_document_v1` | `sc.document.admin.document` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_hr_admin_center`:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_construction_core.group_sc_cap_business_initiator`] → `smart_construction_core.menu_sc_product_policy_document_v1`:[`smart_construction_core.group_sc_cap_business_config_admin`] → action:[`smart_construction_core.group_sc_cap_business_config_admin`] |
| `smart_construction_core.menu_sc_product_social_fund_v1` | `smart_construction_core.action_sc_product_social_fund_v1` | `sc.hr.payroll.document` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_hr_admin_center`:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_construction_core.group_sc_cap_business_initiator`] → `smart_construction_core.menu_sc_product_social_fund_v1`:[`smart_construction_core.group_sc_cap_business_config_admin`] → action:[`smart_construction_core.group_sc_cap_business_config_admin`] |
| `smart_construction_core.menu_sc_runtime_user_management` | `smart_construction_core.action_sc_runtime_user_management` | `res.users` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_hr_admin_center`:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_construction_core.group_sc_cap_business_initiator`] → `smart_construction_core.menu_sc_runtime_user_management`:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_core.group_smart_core_admin`] → action:[`smart_construction_core.group_sc_cap_business_config_admin`, `smart_core.group_smart_core_admin`] |

## Gap classification

No P0/P1 frontend rollout gaps were detected for the formal administration-center entries.

## Acceptance routing

- Primary journey: a formal administration entry preserves its resolved action/menu and form authority.
- Security counterexample: an unauthorized user cannot gain entry or write authority.
- Any future unregistered `smart_*` view class fails this audit closed.
