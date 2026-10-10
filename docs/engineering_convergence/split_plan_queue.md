# Split Plan Queue

Generated from `complexity_budget_report.md` split-plan-required files.

## Summary

- Split-plan files: `62`
- P0: `0`
- P1: `30`
- P2: `32`

## Queue

| Priority | Lines | Owner | File | Decomposition Direction |
| --- | ---: | --- | --- | --- |
| P1 | 7146 | DevOps owner | `scripts/verify/frontend_scene_component_bridge_guard.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 5423 | Platform owner | `addons/smart_core/tests/test_ui_contract_v2_boundaries.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 5294 | DevOps owner | `scripts/verify/business_config_approval_runtime_smoke.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 5176 | Platform owner | `addons/smart_core/core/unified_page_contract_v2_assembler.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 4979 | DevOps owner | `scripts/verify/local_dev_candidate_visual_smoke.mjs` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 4682 | Platform owner | `addons/smart_core/tests/test_unified_page_contract_v2_mobile_compact.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 4492 | DevOps owner | `scripts/verify/test_payment_approval_state_machine.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 4434 | Platform owner | `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py` | Separate parser/assembler/dispatcher responsibilities and preserve backend source-of-truth boundary. |
| P1 | 4344 | Platform owner | `addons/smart_core/handlers/ui_contract_v2.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P1 | 3740 | Frontend owner | `frontend/apps/web/src/views/ActionView.vue` | Extract composables, child panels, data adapters, and action handlers; keep the route component as orchestration shell. |
| P1 | 3652 | Construction backend owner | `addons/smart_construction_core/models/core/payment_request.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P1 | 3646 | Platform owner | `addons/smart_core/handlers/form_field_configuration.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P1 | 3472 | Construction backend owner | `addons/smart_construction_core/models/core/material_acceptance.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P1 | 3455 | Construction backend owner | `addons/smart_construction_core/tests/test_p0_state_closure.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 3416 | Platform owner | `addons/smart_core/tests/test_form_field_configuration_params.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 3268 | Construction backend owner | `addons/smart_construction_core/security/sc_record_rules.xml` | Split data/view records by product domain and manifest load order. |
| P1 | 3131 | Platform owner | `addons/smart_core/tests/test_menu_configuration_audit.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 3066 | Construction backend owner | `addons/smart_construction_core/tests/test_p1_payment_request_capability.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 3011 | Construction backend owner | `addons/smart_construction_core/tests/test_user_feedback_business_views.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 2875 | Platform owner | `addons/smart_core/core/workspace_home_contract_builder.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 2771 | Platform owner | `addons/smart_core/delivery/menu_service.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 2675 | Platform owner | `addons/smart_core/handlers/api_data.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P1 | 2454 | Platform owner | `addons/smart_core/handlers/system_init.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P1 | 2068 | Platform owner | `addons/smart_core/tests/test_odoo_native_alignment_boundaries.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P1 | 1901 | Platform owner | `addons/smart_core/handlers/menu_configuration.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P1 | 1841 | Platform owner | `addons/smart_core/core/page_contracts_builder.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 1801 | Platform owner | `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py` | Separate parser/assembler/dispatcher responsibilities and preserve backend source-of-truth boundary. |
| P1 | 1650 | Platform owner | `addons/smart_core/core/scene_ready_contract_builder.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P1 | 1553 | Platform owner | `addons/smart_core/app_config_engine/models/app_view_config.py` | Separate parser/assembler/dispatcher responsibilities and preserve backend source-of-truth boundary. |
| P1 | 1521 | Platform owner | `addons/smart_core/handlers/business_config_surface.py` | Extract parsing, validation, assembly, and response mapping into owned services. |
| P2 | 2515 | Frontend owner | `frontend/apps/web/src/app/contracts/v2/schema.ts` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 2340 | DevOps owner | `scripts/verify/backend_business_fact_model_audit.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 2225 | DevOps owner | `scripts/verify/test_frontend_professional_component_registry_guard.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 2205 | Construction backend owner | `addons/smart_construction_core/wizard/project_boq_import_wizard.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 2186 | Frontend owner | `frontend/apps/web/src/pages/ListPage.vue` | Assessed Wave3 Round12 (no further split value; component/helper extraction done, max logic block 51 lines). Keep under P2 growth guard. |
| P2 | 2120 | DevOps owner | `scripts/verify/local_dev_project_profile_write_browser.mjs` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 2093 | Construction backend owner | `addons/smart_construction_core/models/core/subcontract_management.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P2 | 2001 | DevOps owner | `scripts/verify/industry_module_product_boundary_guard.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1999 | Construction backend owner | `addons/smart_construction_core/tests/test_project_authorization_foundation.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P2 | 1977 | Frontend owner | `frontend/apps/web/src/stores/session.ts` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1963 | Frontend owner | `frontend/apps/web/src/pages/ContractFormPage.vue` | Assessed Wave3 Round2 (no further split value; 5587→1857 integration shell). Keep under P2 growth guard. |
| P2 | 1940 | Construction backend owner | `addons/smart_construction_core/core_extension.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1932 | Construction backend owner | `addons/smart_construction_core/models/core/project_core.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P2 | 1923 | DevOps owner | `scripts/verify/frontend_professional_component_registry_guard.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1876 | Construction backend owner | `addons/smart_construction_core/tests/test_p1_finance_projection_authority.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P2 | 1761 | DevOps owner | `scripts/verify/local_dev_payment_request_floorplan_submit.mjs` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1727 | Construction backend owner | `addons/smart_construction_core/models/support/workflow_contract_service.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P2 | 1713 | Construction backend owner | `addons/smart_construction_core/tests/test_context_workspace_native_lowcode.py` | Split fixtures, scenario builders, and assertion groups by behavior area. |
| P2 | 1693 | DevOps owner | `scripts/verify/registry.yaml` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1678 | Frontend owner | `frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue` | Extract composables, child panels, data adapters, and action handlers; keep the route component as orchestration shell. |
| P2 | 1656 | Frontend owner | `frontend/apps/web/src/views/SceneView.vue` | Extract composables, child panels, data adapters, and action handlers; keep the route component as orchestration shell. |
| P2 | 1645 | Frontend owner | `frontend/apps/web/src/components/template/FormSection.vue` | Extract composables, child panels, data adapters, and action handlers; keep the route component as orchestration shell. |
| P2 | 1630 | Architecture owner | `addons/smart_construction_acceptance_fixture/tools/frontend_productization_fixture.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1621 | Construction backend owner | `addons/smart_construction_core/models/core/settlement_order.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P2 | 1618 | DevOps owner | `scripts/ops/registry_audit_environment.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1609 | Frontend owner | `frontend/apps/web/src/layouts/AppShell.vue` | Extract composables, child panels, data adapters, and action handlers; keep the route component as orchestration shell. |
| P2 | 1569 | Construction backend owner | `addons/smart_construction_core/models/support/product_policy_sync.py` | Extract service methods for cross-model workflow, amount, and policy logic. |
| P2 | 1568 | DevOps owner | `scripts/verify/test_frontend_standard_preview.py` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 1218 | DevOps owner | `scripts/verify/test_coverage_registry.yaml` | Define owner-specific decomposition plan before adding unrelated behavior. |
| P2 | 672 | DevOps owner | `scripts/dev/frontend_acceptance_runtime.sh` | Move reusable logic into small scripts and keep shell as thin entrypoint. |
| P2 | 599 | DevOps owner | `scripts/audit/smoke_role_matrix.sh` | Move reusable logic into small scripts and keep shell as thin entrypoint. |
| P2 | 551 | DevOps owner | `scripts/ops/audit_project_actions.sh` | Move reusable logic into small scripts and keep shell as thin entrypoint. |

## Enforcement Rule

- P0 files require a split plan before accepting non-defect feature additions.
- P1 files require owner review when touched.
- P2 files may be handled opportunistically, but should not grow without reason.
