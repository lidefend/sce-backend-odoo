# Split Plan Queue

Generated from `complexity_budget_report.md` split-plan-required files.

## Summary

- Split-plan files: `48`
- P0: `1`
- P1: `23`
- P2: `24`

## Queue

| Priority | Lines | Owner | File | Decomposition Direction |
| --- | ---: | --- | --- | --- |
| P0 | 1857 | Frontend owner | `frontend/apps/web/src/pages/ContractFormPage.vue` | Extract composables, child panels, data adapters, and action handlers; keep the route component as orchestration shell. |
| P1 | 4725 | Platform owner | `addons/smart_core/core/unified_page_contract_v2_assembler.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 4571 | Platform owner | `addons/smart_core/tests/test_ui_contract_v2_boundaries.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 4312 | Platform owner | `addons/smart_core/handlers/ui_contract_v2.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P1 | 4188 | Platform owner | `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py` | Separate parser/assembler/dispatcher responsibilities and preserve backend source-of-truth boundary. |
| P1 | 3774 | Platform owner | `addons/smart_core/tests/test_unified_page_contract_v2_mobile_compact.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 3756 | Frontend owner | `frontend/apps/web/src/views/ActionView.vue` | Extract composables, child panels, data adapters, and action handlers; keep the route component as orchestration shell. |
| P1 | 3667 | Platform owner | `addons/smart_core/handlers/form_field_configuration.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P1 | 3380 | Platform owner | `addons/smart_core/tests/test_form_field_configuration_params.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 3351 | Construction backend owner | `addons/smart_construction_core/tests/test_p0_state_closure.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 3262 | Construction backend owner | `addons/smart_construction_core/models/core/material_acceptance.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P1 | 3234 | Construction backend owner | `addons/smart_construction_core/models/core/payment_request.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P1 | 3136 | Construction backend owner | `addons/smart_construction_core/security/sc_record_rules.xml` | Split data/view records by product domain and manifest load order. |
| P1 | 3016 | Platform owner | `addons/smart_core/tests/test_menu_configuration_audit.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 2875 | Platform owner | `addons/smart_core/core/workspace_home_contract_builder.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 2547 | Platform owner | `addons/smart_core/handlers/api_data.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P1 | 2461 | Platform owner | `addons/smart_core/delivery/menu_service.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 2442 | Platform owner | `addons/smart_core/handlers/system_init.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P1 | 2045 | Platform owner | `addons/smart_core/tests/test_odoo_native_alignment_boundaries.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 1844 | Platform owner | `addons/smart_core/handlers/menu_configuration.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P1 | 1791 | Platform owner | `addons/smart_core/core/page_contracts_builder.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 1752 | Platform owner | `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py` | Separate parser/assembler/dispatcher responsibilities and preserve backend source-of-truth boundary. |
| P1 | 1648 | Platform owner | `addons/smart_core/core/scene_ready_contract_builder.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 1553 | Platform owner | `addons/smart_core/app_config_engine/models/app_view_config.py` | Separate parser/assembler/dispatcher responsibilities and preserve backend source-of-truth boundary. |
| P2 | 2510 | Construction backend owner | `addons/smart_construction_core/tests/test_user_feedback_business_views.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P2 | 2340 | DevOps owner | `scripts/verify/backend_business_fact_model_audit.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 2304 | Frontend owner | `frontend/apps/web/src/app/contracts/v2/schema.ts` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 2181 | Construction backend owner | `addons/smart_construction_core/tests/test_p1_payment_request_capability.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P2 | 2171 | Construction backend owner | `addons/smart_construction_core/wizard/project_boq_import_wizard.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 2073 | Frontend owner | `frontend/apps/web/src/pages/ListPage.vue` | Extract composables, child panels, data adapters, and action handlers; keep the route component as orchestration shell. |
| P2 | 2001 | DevOps owner | `scripts/verify/industry_module_product_boundary_guard.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1999 | Construction backend owner | `addons/smart_construction_core/tests/test_project_authorization_foundation.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P2 | 1949 | Construction backend owner | `addons/smart_construction_core/models/core/project_core.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P2 | 1933 | Frontend owner | `frontend/apps/web/src/stores/session.ts` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1847 | Construction backend owner | `addons/smart_construction_core/tests/test_p1_finance_projection_authority.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P2 | 1769 | Construction backend owner | `addons/smart_construction_core/core_extension.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1738 | Construction backend owner | `addons/smart_construction_core/models/core/subcontract_management.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P2 | 1708 | DevOps owner | `scripts/verify/local_dev_payment_request_floorplan_submit.mjs` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1703 | Frontend owner | `frontend/apps/web/src/views/SceneView.vue` | Extract composables, child panels, data adapters, and action handlers; keep the route component as orchestration shell. |
| P2 | 1627 | Construction backend owner | `addons/smart_construction_core/models/core/settlement_order.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P2 | 1618 | DevOps owner | `scripts/ops/registry_audit_environment.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1588 | Frontend owner | `frontend/apps/web/src/layouts/AppShell.vue` | Extract composables, child panels, data adapters, and action handlers; keep the route component as orchestration shell. |
| P2 | 1542 | Construction backend owner | `addons/smart_construction_core/models/support/product_policy_sync.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P2 | 1515 | Construction backend owner | `addons/smart_construction_core/models/support/contract_center.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P2 | 632 | DevOps owner | `scripts/verify/registry.yaml` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 599 | DevOps owner | `scripts/audit/smoke_role_matrix.sh` | Move reusable logic into small scripts and keep shell as thin entrypoint. |
| P2 | 551 | DevOps owner | `scripts/ops/audit_project_actions.sh` | Move reusable logic into small scripts and keep shell as thin entrypoint. |
| P2 | 513 | DevOps owner | `scripts/dev/frontend_acceptance_runtime.sh` | Move reusable logic into small scripts and keep shell as thin entrypoint. |

## Enforcement Rule

- P0 files require a split plan before accepting non-defect feature additions.
- P1 files require owner review when touched.
- P2 files may be handled opportunistically, but should not grow without reason.
