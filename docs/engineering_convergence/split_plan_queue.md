# Split Plan Queue

Generated from `complexity_budget_report.md` split-plan-required files.

## Summary

- Split-plan files: `38`
- P0: `1`
- P1: `19`
- P2: `18`

## Queue

| Priority | Lines | Owner | File | Decomposition Direction |
| --- | ---: | --- | --- | --- |
| P0 | 1799 | Frontend owner | `frontend/apps/web/src/pages/ContractFormPage.vue` | Extract composables, child panels, data adapters, and action handlers; keep the route component as orchestration shell. |
| P1 | 3683 | Frontend owner | `frontend/apps/web/src/views/ActionView.vue` | Extract composables, child panels, data adapters, and action handlers; keep the route component as orchestration shell. |
| P1 | 3664 | Platform owner | `addons/smart_core/handlers/form_field_configuration.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P1 | 3364 | Platform owner | `addons/smart_core/tests/test_form_field_configuration_params.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 3331 | Platform owner | `addons/smart_core/handlers/ui_contract_v2.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P1 | 3329 | Construction backend owner | `addons/smart_construction_core/tests/test_p0_state_closure.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 3087 | Construction backend owner | `addons/smart_construction_core/models/core/material_acceptance.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P1 | 3046 | Platform owner | `addons/smart_core/core/workspace_home_contract_builder.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 3027 | Platform owner | `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py` | Separate parser/assembler/dispatcher responsibilities and preserve backend source-of-truth boundary. |
| P1 | 2912 | Platform owner | `addons/smart_core/tests/test_menu_configuration_audit.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 2467 | Platform owner | `addons/smart_core/core/unified_page_contract_v2_assembler.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 2424 | Platform owner | `addons/smart_core/handlers/api_data.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P1 | 2382 | Platform owner | `addons/smart_core/handlers/system_init.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P1 | 1931 | Platform owner | `addons/smart_core/tests/test_ui_contract_v2_boundaries.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 1927 | Platform owner | `addons/smart_core/delivery/menu_service.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 1861 | Platform owner | `addons/smart_core/handlers/menu_configuration.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P1 | 1746 | Platform owner | `addons/smart_core/core/page_contracts_builder.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 1652 | Platform owner | `addons/smart_core/tests/test_odoo_native_alignment_boundaries.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 1634 | Platform owner | `addons/smart_core/core/scene_ready_contract_builder.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 1546 | Platform owner | `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py` | Separate parser/assembler/dispatcher responsibilities and preserve backend source-of-truth boundary. |
| P2 | 2610 | Construction backend owner | `addons/smart_construction_core/security/sc_record_rules.xml` | Split data/view records by product domain and manifest load order. |
| P2 | 2492 | Construction backend owner | `addons/smart_construction_core/tests/test_user_feedback_business_views.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P2 | 2294 | Frontend owner | `frontend/apps/web/src/pages/ListPage.vue` | Extract composables, child panels, data adapters, and action handlers; keep the route component as orchestration shell. |
| P2 | 2289 | Construction backend owner | `addons/smart_construction_core/models/core/project_core.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P2 | 2051 | DevOps owner | `scripts/verify/backend_business_fact_model_audit.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 2028 | Construction backend owner | `addons/smart_construction_core/models/support/product_policy_sync.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P2 | 1999 | Construction backend owner | `addons/smart_construction_core/tests/test_project_authorization_foundation.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P2 | 1983 | Construction backend owner | `addons/smart_construction_core/models/core/payment_request.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P2 | 1865 | Frontend owner | `frontend/apps/web/src/stores/session.ts` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1741 | Frontend owner | `frontend/apps/web/src/views/SceneView.vue` | Extract composables, child panels, data adapters, and action handlers; keep the route component as orchestration shell. |
| P2 | 1656 | Construction backend owner | `addons/smart_construction_core/models/core/subcontract_management.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P2 | 1628 | DevOps owner | `scripts/verify/industry_module_product_boundary_guard.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1618 | DevOps owner | `scripts/ops/registry_audit_environment.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1591 | Construction backend owner | `addons/smart_construction_core/models/support/direct_acceptance_formal_visible_fields.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P2 | 1570 | Construction backend owner | `addons/smart_construction_core/core_extension.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1523 | Construction backend owner | `addons/smart_construction_core/wizard/project_boq_import_wizard.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 599 | DevOps owner | `scripts/audit/smoke_role_matrix.sh` | Move reusable logic into small scripts and keep shell as thin entrypoint. |
| P2 | 551 | DevOps owner | `scripts/ops/audit_project_actions.sh` | Move reusable logic into small scripts and keep shell as thin entrypoint. |

## Enforcement Rule

- P0 files require a split plan before accepting non-defect feature additions.
- P1 files require owner review when touched.
- P2 files may be handled opportunistically, but should not grow without reason.
