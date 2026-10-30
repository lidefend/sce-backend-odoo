# Test Inventory Summary

Generated from `test_inventory.csv`.

## Totals

- Total assets: `1629`
- Review queue: `4`
- Unknown runtime: `3`
- Long-running assets: `225`
- Manual gate review: `4`
- Aggregate-covered assets: `225`
- PR dedupe candidates: `1179`

## By Layer

| Layer | Count |
| --- | ---: |
| governance | 612 |
| contract | 412 |
| unit | 314 |
| odoo_integration | 147 |
| security | 50 |
| e2e | 49 |
| frontend_acceptance | 41 |
| gate | 2 |
| data_migration | 2 |

## By Decision Gate

| Decision Gate | Count |
| --- | ---: |
| pr_candidate | 1398 |
| integration_candidate | 175 |
| release_candidate | 47 |
| manual_review | 4 |
| release_required | 2 |
| local_iteration | 1 |
| pr_required | 1 |
| integration_required | 1 |

## By Disposition

| Disposition | Count |
| --- | ---: |
| deduplicate_before_required | 1179 |
| covered_by_aggregate | 220 |
| keep_integration_or_release_only | 174 |
| keep_release_only | 47 |
| canonical_entry | 5 |
| review_or_archive | 4 |

## By Aggregate Target

| Aggregate Target | Count |
| --- | ---: |
| verify.unified_page_contract.lite | 54 |
| verify.scene.runtime_boundary.gate | 17 |
| verify.unified_page_contract.v2 | 11 |
| verify.frontend.product.ready | 7 |
| verify.system_user_experience.full_browser | 5 |
| verify.backend.contract.closure.mainline | 5 |
| verify.finance_interfund.position.all | 5 |
| verify.form_structure.contract | 4 |
| verify.lowcode_config.customer_module_asset.pipeline | 4 |
| verify.backend.architecture.full.report.guard.schema.guard | 3 |
| verify.boundary.import_guard.strict.guard | 3 |
| verify.frontend.grouped_drift_summary.baseline.guard | 3 |
| verify.frontend.grouped_governance_brief.baseline.guard | 3 |
| verify.frontend.grouped_governance_trend_consistency.baseline.guard | 3 |
| verify.business_capability.productization_p1 | 3 |
| verify.portal.payment_request_approval_all_smoke.container | 3 |
| verify.release.v2_0_0.governance.guard | 3 |
| verify.contract.scene_coverage.guard | 3 |
| verify.smart_core.minimum_surface | 3 |
| verify.business_config.config_workbench_operation_quick | 2 |
| verify.backend.evidence.manifest.guard | 2 |
| verify.business.capability_baseline.guard | 2 |
| verify.business_form.productization.audit | 2 |
| verify.contract.assembler.semantic.schema.guard | 2 |
| verify.frontend.quick.gate | 2 |
| verify.grouped.governance.bundle | 2 |
| verify.intent.canonical_alias.snapshot.guard | 2 |
| verify.native_view.semantic_page | 2 |
| verify.non_demo_data_contamination | 2 |
| verify.e2e.ops_batch_smoke | 2 |
| verify.portal.entry_registry_quality_guard | 2 |
| verify.product.delivery.governance_truth | 2 |
| verify.project.dashboard.contract | 2 |
| verify.project.dashboard.snapshot | 2 |
| verify.project.management.acceptance | 2 |
| verify.release.capability.audit.schema.guard | 2 |
| verify.e2e.scene_admin | 2 |
| verify.e2e.subscription_smoke | 2 |
| make ci.local.quick | 1 |
| make ci | 1 |
| make test.e2e | 1 |
| make test.odoo.integration | 1 |
| make test.e2e.fixed_data.odoo | 1 |
| verify.business_config.config_workbench_operation_acceptance | 1 |
| verify.portal.ar_ap_company_summary_smoke.container | 1 |
| verify.portal.ar_ap_project_summary_smoke.container | 1 |
| verify.portal.list_shell_no_meta_smoke.container | 1 |
| verify.portal.list_shell_title_smoke.container | 1 |
| verify.portal.menu_scene_key_smoke.container | 1 |
| verify.menu.scene_resolve.container | 1 |
| verify.portal.scene_governance_action_strict.container | 1 |
| verify.portal.scene_package_ui_smoke.container | 1 |
| verify.portal.scene_auto_degrade_notify_strict.container | 1 |
| verify.portal.scene_auto_degrade_strict.container | 1 |
| scene.contract.export | 1 |
| verify.portal.scene_contract_export_smoke.container | 1 |
| verify.portal.scene_contract_smoke.container | 1 |
| verify.portal.scene_health_contract_smoke.container | 1 |
| verify.portal.scene_health_pagination_smoke.container | 1 |
| verify.portal.scene_package_dry_run_smoke.container | 1 |
| verify.portal.scene_observability_strict.container | 1 |
| verify.portal.scene_package_installed_smoke.container | 1 |
| verify.portal.scene_registry | 1 |
| verify.portal.view_contract_coverage_smoke.container | 1 |
| verify.portal.view_contract_shape.container | 1 |
| verify.formal_list_surface.no_test_placeholder_guard | 1 |
| verify.frontend.page_block_registry_guard | 1 |
| verify.frontend.page_block_renderer_smoke | 1 |
| verify.frontend.page_block_visual_snapshot_guard | 1 |
| verify.lowcode_config.customer_module_asset.release_hardening.guard | 1 |
| verify.delivery.material.cross_document_progress | 1 |
| verify.p1.daily_business_visible_contract.audit | 1 |
| verify.page_contract.role_orchestration_variance.guard | 1 |
| verify.page_contract.role_strategy_provider_split.guard | 1 |
| verify.role.capability_floor.guard | 1 |
| verify.role.capability_floor.prod_like.schema.guard | 1 |
| verify.scene.provider.registry.consumer.guard | 1 |
| verify.scene.provider.registry.guard | 1 |
| verify.scene.delivery.readiness | 1 |
| verify.smart_core.boundary_guard | 1 |
| verify.unified_page_contract.v2.harmony_h5_compile_acceptance.host | 1 |
| verify.unified_page_contract.v2.regression_audit.host | 1 |
| verify.unified_page_contract.v2.web_visual_acceptance.host | 1 |

## By Runtime

| Runtime | Count |
| --- | ---: |
| <5m | 1400 |
| 10-30m | 176 |
| 30-60m | 49 |
| unknown | 3 |
| 10-15m | 1 |

## By Owner

| Owner | Count |
| --- | ---: |
| architecture owner | 612 |
| platform owner | 412 |
| test owner | 315 |
| backend owner | 147 |
| security owner | 50 |
| qa owner | 49 |
| frontend owner | 42 |
| data owner | 2 |

## By Directory

| Directory | Count |
| --- | ---: |
| scripts/verify | 1411 |
| scripts/ops | 111 |
| frontend/apps/web/scripts | 48 |
| scripts/ci | 33 |
| scripts/audit | 10 |
| make | 5 |
| scripts/e2e | 5 |
| scripts/diag | 4 |
| scripts/prod | 2 |

## Review Queue

| ID | Layer | Entrypoint | Reason |
| --- | --- | --- | --- |
| T-ASSET-54c78be1 | unit | `scripts/diag/fe_smoke.sh` | status=review |
| T-ASSET-54d71152 | unit | `scripts/diag/test-default-menu.py` | status=review |
| T-ASSET-c174a850 | unit | `scripts/diag/test-frontend-changes.sh` | status=review |
| T-ASSET-5c6d7f00 | unit | `scripts/diag/test-menu-issue.sh` | status=review |

## Unknown Runtime Assets

| ID | Layer | Entrypoint |
| --- | --- | --- |
| T-ASSET-54c78be1 | unit | `scripts/diag/fe_smoke.sh` |
| T-ASSET-c174a850 | unit | `scripts/diag/test-frontend-changes.sh` |
| T-ASSET-5c6d7f00 | unit | `scripts/diag/test-menu-issue.sh` |

## PR Dedupe Candidate Sample

| ID | Layer | Entrypoint | Owner |
| --- | --- | --- | --- |
| T-ASSET-9b0df816 | frontend_acceptance | `frontend/apps/web/scripts/bootstrap_inventory_policy_test.mjs` | frontend owner |
| T-ASSET-0775b9c5 | frontend_acceptance | `frontend/apps/web/scripts/business_config_approval_target_test.mjs` | frontend owner |
| T-ASSET-22671f34 | frontend_acceptance | `frontend/apps/web/scripts/business_config_draft_scope_race_test.mjs` | frontend owner |
| T-ASSET-45afe216 | frontend_acceptance | `frontend/apps/web/scripts/business_form_all_category_direct_acceptance.mjs` | frontend owner |
| T-ASSET-9a9e78e4 | frontend_acceptance | `frontend/apps/web/scripts/business_form_frontend_full_walk_acceptance.mjs` | frontend owner |
| T-ASSET-82495e35 | frontend_acceptance | `frontend/apps/web/scripts/designer_draft_ownership_test.mjs` | frontend owner |
| T-ASSET-dd6c390a | frontend_acceptance | `frontend/apps/web/scripts/designer_popup_readiness_test.mjs` | frontend owner |
| T-ASSET-cd9f3642 | frontend_acceptance | `frontend/apps/web/scripts/field_configuration_component_test.mjs` | frontend owner |
| T-ASSET-7dad7b75 | frontend_acceptance | `frontend/apps/web/scripts/frontend_core_journeys_audit.mjs` | frontend owner |
| T-ASSET-3069491e | frontend_acceptance | `frontend/apps/web/scripts/frontend_product_baseline_guard.mjs` | frontend owner |
| T-ASSET-eabbe08b | frontend_acceptance | `frontend/apps/web/scripts/frontend_product_maturity_audit.mjs` | frontend owner |
| T-ASSET-da43b053 | security | `frontend/apps/web/scripts/frontend_role_journey_audit.mjs` | security owner |
| T-ASSET-0d3124c5 | frontend_acceptance | `frontend/apps/web/scripts/handling_entry_catalog_smoke.mjs` | frontend owner |
| T-ASSET-df4ac839 | contract | `frontend/apps/web/scripts/list_selection_contract_smoke.mjs` | platform owner |
| T-ASSET-ad47d598 | frontend_acceptance | `frontend/apps/web/scripts/list_surface_component_test.mjs` | frontend owner |
| T-ASSET-14218ba4 | frontend_acceptance | `frontend/apps/web/scripts/low_code_business_config_acceptance.mjs` | frontend owner |
| T-ASSET-c3b3712e | frontend_acceptance | `frontend/apps/web/scripts/low_code_change_set_acceptance.mjs` | frontend owner |
| T-ASSET-77f48a3d | frontend_acceptance | `frontend/apps/web/scripts/low_code_form_group_matrix_acceptance.mjs` | frontend owner |
| T-ASSET-bb44facb | frontend_acceptance | `frontend/apps/web/scripts/low_code_global_stability_acceptance.mjs` | frontend owner |
| T-ASSET-a0d00b5e | frontend_acceptance | `frontend/apps/web/scripts/low_code_menu_navigation_alignment_acceptance.mjs` | frontend owner |
| T-ASSET-140558e9 | frontend_acceptance | `frontend/apps/web/scripts/low_code_safe_open_acceptance.mjs` | frontend owner |
| T-ASSET-434bff97 | frontend_acceptance | `frontend/apps/web/scripts/low_code_workbench_fault_acceptance.mjs` | frontend owner |
| T-ASSET-cb6e1d4e | frontend_acceptance | `frontend/apps/web/scripts/low_code_workbench_product_acceptance.mjs` | frontend owner |
| T-ASSET-5512810b | frontend_acceptance | `frontend/apps/web/scripts/native_attachment_partial_failure_test.mjs` | frontend owner |
| T-ASSET-1d7ccca7 | frontend_acceptance | `frontend/apps/web/scripts/node_component_consumption_component_test.mjs` | frontend owner |
| T-ASSET-68bbc50c | frontend_acceptance | `frontend/apps/web/scripts/onchange_roundtrip_race_test.mjs` | frontend owner |
| T-ASSET-d399ae8e | frontend_acceptance | `frontend/apps/web/scripts/product_navigation_boundary_acceptance.mjs` | frontend owner |
| T-ASSET-4e842a94 | frontend_acceptance | `frontend/apps/web/scripts/product_page_structure_guard.mjs` | frontend owner |
| T-ASSET-b6809406 | frontend_acceptance | `frontend/apps/web/scripts/professional_collaboration_message_component_test.mjs` | frontend owner |
| T-ASSET-fade93bd | security | `frontend/apps/web/scripts/public_auth_bootstrap_test.mjs` | security owner |
| T-ASSET-73b78feb | frontend_acceptance | `frontend/apps/web/scripts/readonly_block_component_test.mjs` | frontend owner |
| T-ASSET-521a645d | frontend_acceptance | `frontend/apps/web/scripts/relation_heading_component_test.mjs` | frontend owner |
| T-ASSET-d6b3571c | frontend_acceptance | `frontend/apps/web/scripts/standard_list_lowcode_loop_test.mjs` | frontend owner |
| T-ASSET-e3e6a20e | frontend_acceptance | `frontend/apps/web/scripts/standard_project_save_scope_test.mjs` | frontend owner |
| T-ASSET-2ee377b3 | frontend_acceptance | `frontend/apps/web/scripts/user_template_coverage_acceptance.mjs` | frontend owner |
| T-ASSET-beea2cfb | frontend_acceptance | `frontend/apps/web/scripts/user_visible_surface_visual_coverage_summary_guard.mjs` | frontend owner |
| T-ASSET-e3676e89 | frontend_acceptance | `frontend/apps/web/scripts/weighted_relation_component_test.mjs` | frontend owner |
| T-ASSET-d3b121fb | governance | `scripts/audit/boundary_audit_smart_core.py` | architecture owner |
| T-ASSET-3953a76f | governance | `scripts/audit/scene_config_audit.js` | architecture owner |
| T-ASSET-fcc65a7c | unit | `scripts/audit/test_generate_frontend_component_driver_takeover_inventory.py` | test owner |
| T-ASSET-d1103341 | unit | `scripts/audit/test_generate_frontend_official_design_alignment_inventory.py` | test owner |
| T-ASSET-00c29c9c | unit | `scripts/audit/test_generate_frontend_professionalization_baseline.py` | test owner |
| T-ASSET-733f2d2d | unit | `scripts/audit/test_generate_frontend_rendering_detail_inventory.py` | test owner |
| T-ASSET-768b0a5d | unit | `scripts/audit/test_generate_frontend_visual_projection_inventory.py` | test owner |
| T-ASSET-73b723f2 | unit | `scripts/audit/test_verification_lane_coverage.py` | test owner |
| T-ASSET-1ba143bf | governance | `scripts/ci/assert_audit_tp08.py` | architecture owner |
| T-ASSET-c0d084cf | unit | `scripts/ci/backend_test_receipt.py` | test owner |
| T-ASSET-c7dce78f | contract | `scripts/ci/enforce_contract_structure_lock.py` | platform owner |
| T-ASSET-0998f4e2 | governance | `scripts/ci/frontend_professional_extension_guard.py` | architecture owner |
| T-ASSET-8aca182b | governance | `scripts/ci/gate_audit.sh` | architecture owner |
| T-ASSET-198f94bf | governance | `scripts/ci/gate_audit_tp08.sh` | architecture owner |
| T-ASSET-7deba7cf | contract | `scripts/ci/generate_contract_structure_fingerprint.py` | platform owner |
| T-ASSET-a39a5fd5 | unit | `scripts/ci/generate_e2e_journey_matrix.py` | test owner |
| T-ASSET-57f07a83 | unit | `scripts/ci/generate_test_inventory.py` | test owner |
| T-ASSET-ef22b02b | unit | `scripts/ci/gitee_ci_acceptance.py` | test owner |
| T-ASSET-1215d178 | unit | `scripts/ci/gitee_ci_acceptance_check.py` | test owner |
| T-ASSET-ac0ebfd4 | unit | `scripts/ci/summarize_test_inventory.py` | test owner |
| T-ASSET-197bfe6a | unit | `scripts/ci/test_backend_impact_plan.py` | test owner |
| T-ASSET-ed18de8c | unit | `scripts/ci/test_backend_suite_plan.py` | test owner |
| T-ASSET-33ece664 | unit | `scripts/ci/test_backend_test_receipt.py` | test owner |
| T-ASSET-0a7689dc | contract | `scripts/ci/test_backend_test_suite_dispatch_contract.py` | platform owner |
| T-ASSET-a827439b | unit | `scripts/ci/test_ci_risk_classifier.py` | test owner |
| T-ASSET-a49b9b15 | contract | `scripts/ci/test_ci_risk_workflow_contract.py` | platform owner |
| T-ASSET-896df66d | governance | `scripts/ci/test_frontend_professional_extension_guard.py` | architecture owner |
| T-ASSET-4aeb0d9d | unit | `scripts/ci/test_lane_telemetry.py` | test owner |
| T-ASSET-d1231964 | unit | `scripts/ci/test_merge_policy_gate.py` | test owner |
| T-ASSET-1f405243 | unit | `scripts/ci/test_node_syntax_check.py` | test owner |
| T-ASSET-75503495 | unit | `scripts/ci/test_parallel_scan.py` | test owner |
| T-ASSET-5667b2a2 | unit | `scripts/ci/test_personal_data_scan.py` | test owner |
| T-ASSET-10d5f8e2 | unit | `scripts/ci/test_release_candidate_gate.py` | test owner |
| T-ASSET-ccec5b8a | unit | `scripts/ci/test_secret_scan.py` | test owner |
| T-ASSET-09519198 | security | `scripts/ci/test_select_authoritative_workflow_run.py` | security owner |
| T-ASSET-283f7618 | unit | `scripts/ci/test_trusted_scan_group.py` | test owner |
| T-ASSET-0b3a1e93 | unit | `scripts/ci/test_trusted_scan_scope.py` | test owner |
| T-ASSET-8e19db96 | contract | `scripts/ci/verify_contract_form_split_evidence.py` | platform owner |
| T-ASSET-7cd524e7 | contract | `scripts/ops/contract_product_acceptance_policy_restore.py` | platform owner |
| T-ASSET-03995c68 | contract | `scripts/ops/formal_list_surface_test_contract_cleanup.py` | platform owner |
| T-ASSET-800856cc | contract | `scripts/ops/operation_strategy_contract_surface_backfill.py` | platform owner |
| T-ASSET-e9de3f62 | contract | `scripts/ops/repair_unbound_structural_form_contract.py` | platform owner |
| T-ASSET-95bca637 | contract | `scripts/ops/settlement_contract_surface_backfill.py` | platform owner |
| ... | ... | 1099 more | ... |

## Dedupe Hotspots

| Family | Count |
| --- | ---: |
| `scripts/verify/construction_core_extension` | 13 |
| `scripts/verify/test_local_dev` | 10 |
| `scripts/verify/test_frontend_collection` | 9 |
| `scripts/verify/test_frontend_professional` | 9 |
| `scripts/verify/test_frontend_release` | 7 |
| `scripts/verify/test_contract_snapshot` | 6 |
| `scripts/audit/test_generate_frontend` | 5 |
| `scripts/verify/contract_governance_form` | 5 |
| `scripts/verify/backend_contract_lifecycle` | 4 |
| `scripts/verify/daily_demo_contract` | 4 |
| `scripts/verify/test_daily_demo` | 4 |
| `scripts/verify/test_frontend_acceptance` | 4 |
| `scripts/verify/test_gitee_formal` | 4 |
| `scripts/verify/test_native_view` | 4 |
| `scripts/verify/test_product_view` | 4 |
| `scripts/verify/frontend_acceptance_environment` | 3 |
| `scripts/verify/frontend_financial_workspace` | 3 |
| `scripts/verify/frontend_page_identity` | 3 |
| `scripts/verify/test_backend_contract` | 3 |
| `scripts/verify/test_contract_slo` | 3 |
| `scripts/verify/test_frontend_contract` | 3 |
| `scripts/verify/test_gitee_ci` | 3 |
| `scripts/verify/test_gitee_frontend` | 3 |
| `scripts/verify/test_platform_database` | 3 |
| `scripts/verify/test_system_permission` | 3 |
| `frontend/apps/web/scripts/low_code_workbench` | 2 |
| `scripts/ci/test_backend_test` | 2 |
| `scripts/ci/test_ci_risk` | 2 |
| `scripts/ci/test_trusted_scan` | 2 |
| `scripts/verify/business_form_policy` | 2 |

## Residual Dedupe Hotspot Disposition

| Family | Count | Owner | Gate Decision | Disposition |
| --- | ---: | --- | --- | --- |
| `scripts/verify/construction_core_extension` | 13 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_local_dev` | 10 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_frontend_collection` | 9 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_frontend_professional` | 9 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_frontend_release` | 7 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_contract_snapshot` | 6 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/audit/test_generate_frontend` | 5 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/contract_governance_form` | 5 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/backend_contract_lifecycle` | 4 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/daily_demo_contract` | 4 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_daily_demo` | 4 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_frontend_acceptance` | 4 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_gitee_formal` | 4 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_native_view` | 4 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_product_view` | 4 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/frontend_acceptance_environment` | 3 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/frontend_financial_workspace` | 3 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/frontend_page_identity` | 3 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_backend_contract` | 3 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_contract_slo` | 3 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_frontend_contract` | 3 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_gitee_ci` | 3 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_gitee_frontend` | 3 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_platform_database` | 3 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_system_permission` | 3 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `frontend/apps/web/scripts/low_code_workbench` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/ci/test_backend_test` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/ci/test_ci_risk` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/ci/test_trusted_scan` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/business_form_policy` | 2 | architecture owner | owner-reviewed PR candidates | Retain as explicit PR candidates; no confirmed aggregate gate covers both policy coverage and field-hit audit. |
| `scripts/verify/contract_business_category` | 2 | platform owner | owner-reviewed PR candidates | Retain as explicit PR candidates; action audit and binding audit are only wrapped by separate ops scripts. |
| `scripts/verify/contract_form_runtime` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/contract_slo_telemetry` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/contract_supply_chain` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/daily_demo_walkthrough` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/form_m2_payment` | 2 | test owner | owner-reviewed PR candidates | Retain as explicit PR candidates; acceptance pair has no confirmed Make aggregate. |
| `scripts/verify/form_m3_purchase` | 2 | test owner | owner-reviewed PR candidates | Retain as explicit PR candidates; purchase/order-line acceptance pair has no confirmed Make aggregate. |
| `scripts/verify/formal_entry_metadata` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/frontend_action_view` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/frontend_contract_domain` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/frontend_contract_record` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/frontend_evidence_capture` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/frontend_my_work` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/frontend_product_page` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/frontend_professional_relation` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/frontend_systemwide_coverage` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/intent_smoke_utils` | 2 | platform owner | helper debt, no aggregate gate | Retain as helper debt; utility modules are consumed by multiple smokes and should not be marked covered by one gate. |
| `scripts/verify/local_dev_project` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/local_dev_runtime` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/material_business_category` | 2 | architecture owner | owner-reviewed PR candidates | Retain as explicit PR candidates; action and binding audits are only wrapped by separate ops scripts. |
| `scripts/verify/material_settlement_payment` | 2 | architecture owner | owner-reviewed PR candidates | Retain as explicit PR candidates; approval policy and reversal audits are not covered by the traceability aggregate. |
| `scripts/verify/p1_payment_request` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/product_primary_center` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_business_entry` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_data_space` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_demo_usage` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_form_structure` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_formal_entry` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_frontend_form` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_frontend_product` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_frontend_standard` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_frontend_systemwide` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_gitee_pr` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_product_configuration` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_product_menu` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_product_primary` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_sc_data` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_scene_company` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_scene_inventory` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_tenant_payload` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/test_um_p3` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
| `scripts/verify/ui_contract_v2` | 2 | test owner | requires owner review | Requires owner review before mapping to an aggregate gate. |
