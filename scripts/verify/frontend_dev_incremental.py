#!/usr/bin/env python3
"""Run the smallest registered checks affected by cross-layer source changes.

This is a development feedback tool.  It deliberately never builds a candidate,
captures browser evidence, refreshes generated reports, or computes a candidate
fingerprint.  Those operations remain part of the one-shot exact-head
publication qualification flow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import sys
import types
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.ops.agent_run_context import (
    RunError,
    check_states,
    declared_check_targets,
    delta_paths,
    resolve_run,
    readback_path,
)
from scripts.ops.incremental_execution import (
    committed_runtime_tree_sha256,
    ENVIRONMENT_FIELDS,
    current_identity as incremental_current_identity,
    verified_receipt as incremental_verified_receipt,
    write_index as write_incremental_index,
)
from scripts.dev import changed_odoo_tests
from scripts.ci import ci_path_ownership

WATCH_ROOTS = (
    "frontend/apps/web/src",
    "frontend/apps/web/scripts",
    "frontend/apps/web/package.json",
    "frontend/apps/web/.eslintrc.cjs",
    "frontend/apps/web/tsconfig.strict.json",
    "frontend/packages/ui/src",
    "frontend/packages/ui/package.json",
    "frontend/packages/ui/tsconfig.json",
    "frontend/packages/design-tokens",
    "scripts/verify/frontend_",
    "scripts/verify/local_dev_enterprise_configuration_consumer",
    "scripts/ops/incremental_execution.py",
)
CHECKPOINT_AUTHORITY_PATHS = (
    "docs/architecture/p0_contract_producer_01/remediation_design.json",
    "scripts/verify/frontend_dev_incremental.py",
    "scripts/ops/incremental_execution.py",
    "make/frontend.mk",
)
STATE_PATH = ROOT / ".runtime/frontend-dev-validation/status.json"
FRONTEND_SOURCE_ROOTS = (
    "frontend/apps/web/src/",
    "frontend/packages/ui/src/",
)
FRONTEND_SOURCE_SUFFIXES = (".ts", ".tsx", ".vue")
BASE_FRONTEND_TARGETS = (
    "verify.frontend.lint.src",
    "verify.frontend.typecheck.strict",
)
FRONTEND_SOURCE_SCAN_TARGET = "verify.frontend.systemic.convergence.static"
FRONTEND_SOURCE_TARGETS = tuple(sorted((
    *BASE_FRONTEND_TARGETS,
    FRONTEND_SOURCE_SCAN_TARGET,
)))
COVERING_CHECK_TARGETS = {
    "audit.verification.lane_coverage.check": ("verify.verification.lane_coverage",),
}
NODE_TOOL_REQUIREMENTS = {
    "verify.frontend.professional_relation_lifecycle.unit": "esbuild",
    "verify.frontend.lint.scripts": "eslint",
    "verify.frontend.lint.src": "eslint",
    "verify.frontend.typecheck.strict": "vue-tsc",
    FRONTEND_SOURCE_SCAN_TARGET: "esbuild",
    "verify.frontend.professional_component_registry.unit": "esbuild",
    "verify.frontend.runtime_identity.unit": "esbuild",
    "verify.frontend.session_persistence.snapshot.unit": "esbuild",
    "verify.frontend.session_persistence.scheduler.unit": "esbuild",
    "verify.frontend.session_persistence.failure.unit": "esbuild",
    "verify.frontend.session_persistence.recovery.unit": "esbuild",
    "verify.frontend.canonical_form_presenter.unit": "esbuild",
    "verify.frontend.approval_contract.closure.unit": "esbuild",
    "verify.frontend.contract_v2_occurrence_authority.unit": "esbuild",
    "verify.frontend.contract_fidelity.plan.unit": "esbuild",
    "verify.frontend.contract_reason_dialog.browser": "node",
    "verify.frontend.primitive_adapter.unit": "esbuild",
    "verify.frontend.scene_primitive_adapter.unit": "esbuild",
    "verify.frontend.navigation_shell.unit": "esbuild",
    "verify.frontend.scene_entry_contract.unit": "esbuild",
    "verify.frontend.product_page_pattern.unit": "esbuild",
    "verify.frontend.action_view_surface_gate_runtime.unit": "esbuild",
    "verify.frontend.action_view_page_size_runtime.unit": "esbuild",
    "verify.frontend.cross_model_action_navigation.unit": "esbuild",
    "verify.frontend.auth_surface.guard": "node",
}
IMPLICIT_OFFLINE_TARGET_SUFFIXES = (
    ".assembler",
    ".contract",
    ".coverage",
    ".guard",
    ".lane_coverage",
    ".policy",
    ".unit",
)
REGISTRY_AUDIT_TARGET = "verify.test.coverage.registry"
REGISTRY_AUDIT_SELECTOR_PATHS = {
    ".github/workflows/professional_quality_gate.yml",
    "make/ci.mk",
    "make/contract.mk",
    "make/frontend.mk",
    "scripts/ci/backend_impact_plan.py",
    "scripts/ci/ci_risk_classifier.py",
    "scripts/verify/frontend_dev_incremental.py",
    "scripts/verify/test_coverage_registry.yaml",
    "scripts/verify/test_coverage_registry_audit.py",
    "scripts/verify/test_test_coverage_registry_audit.py",
}
TEST_TARGET_SUFFIXES = (
    ".extension_module_baseline",
    ".module_baseline",
    ".orm",
    ".test",
    ".tests",
    ".unit",
)
HOST_STANDALONE_TEST_FILES = {
    "addons/smart_core/tests/test_native_view_parser_surfaces.py",
}
REUSE_ENVIRONMENT_IDENTITY_FIELDS = ENVIRONMENT_FIELDS
TARGET_LAYER_ORDER = ("frontend", "backend", "contract", "docs", "governance")


@dataclass(frozen=True)
class Rule:
    fragments: tuple[str, ...]
    targets: tuple[str, ...]


RULES = (
    # Stable projection guards read these producer and consumer facts together.
    Rule((
        'addons/smart_construction_core/core_extension_policy_maps.py',
        'addons/smart_core/core/unified_page_contract_v2_assembler.py',
        'addons/smart_core/core/unified_page_contract_v2_runtime.py',
        'addons/smart_core/handlers/ui_contract_v2.py',
        'addons/smart_core/handlers/ui_contract_v2_adapters.py',
        'addons/smart_core/handlers/ui_contract_v2_projection.py',
        'addons/smart_core/utils/contract_governance_capabilities.py',
        'addons/smart_core/utils/delete_policy.py',
        'addons/smart_core/utils/native_modifier.py',
        'docs/architecture/unified_page_contract_v2/enum_registry.json',
        'docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json',
        'frontend/apps/web/scripts/low_code_global_stability_acceptance.mjs',
        'frontend/apps/web/src/app/action_runtime/useActionViewActionPresentationRuntime.ts',
        'frontend/apps/web/src/app/action_runtime/useActionViewContentDisplayRuntime.ts',
        'frontend/apps/web/src/app/action_runtime/useActionViewContractShapeRuntime.ts',
        'frontend/apps/web/src/app/action_runtime/useActionViewDisplayComputedRuntime.ts',
        'frontend/apps/web/src/app/action_runtime/useActionViewFilterComputedRuntime.ts',
        'frontend/apps/web/src/app/action_runtime/useActionViewPageDisplayStateRuntime.ts',
        'frontend/apps/web/src/app/action_runtime/useActionViewSurfaceIntentRuntime.ts',
        'frontend/apps/web/src/app/contracts/unifiedPageContractV2.ts',
        'frontend/apps/web/src/app/contracts/v2/schema.ts',
        'frontend/apps/web/src/app/contracts/v2/store.ts',
        'frontend/apps/web/src/app/contracts/v2/types.ts',
        'frontend/apps/web/src/pages/ContractFormPage.vue',
        'frontend/apps/web/src/pages/contractForm/canonicalFormActionExecutor.ts',
        'frontend/apps/web/src/pages/contractForm/contractFormHeaderCanonicalActions.ts',
        'frontend/apps/web/src/views/ActionView.vue',
        'scripts/verify/frontend_v2_policy_projection_guard.py',
        'scripts/verify/test_frontend_v2_policy_projection_guard.py',
        'scripts/verify/ui_contract_v2_contract_boundary_guard.py',
    ), ("verify.unified_page_contract.v2.stable_projection",)),
    Rule(tuple(json.loads((ROOT / "docs/architecture/p0_contract_producer_01/remediation_design.json")
                          .read_text(encoding="utf-8"))["source_evidence"]) + (
        "docs/architecture/p0_contract_producer_01/remediation_design.json",
        "scripts/verify/test_contract_fidelity_plan_guard.py",
        "scripts/verify/contract_fidelity_plan_guard.py",
    ), ("verify.frontend.contract_fidelity.plan.unit",)),
    Rule((
        "frontend/apps/web/scripts/contract_v2_occurrence_authority_test.ts",
        "frontend/apps/web/src/app/contracts/v2/schema.ts",
    ), ("verify.frontend.contract_v2_occurrence_authority.unit",)),
    Rule((
        "frontend/apps/web/scripts/professional_relation_lifecycle_model_test.ts",
        "frontend/apps/web/src/pages/contractForm/useRecordRelationshipFields.ts",
        "frontend/apps/web/src/pages/contractForm/useRelationRuntime.ts",
        "frontend/apps/web/src/pages/contractForm/professionalRelationLifecycleModel.ts",
        "frontend/apps/web/src/app/contracts/v2/store.ts",
    ), ("verify.frontend.professional_relation_lifecycle.unit",)),
    Rule((
        "addons/smart_construction_core/__manifest__.py",
        "addons/smart_construction_core/__init__.py",
        "addons/smart_construction_core/hooks.py",
    ), ("verify.smart_construction_core.module_baseline", "verify.extension.lifecycle.orm")),
    Rule((
        "addons/smart_construction_scene/__manifest__.py",
        "addons/smart_construction_scene/__init__.py",
        "addons/smart_construction_scene/hooks.py",
    ), ("verify.smart_construction_scene.module_baseline", "verify.extension.lifecycle.orm")),
    Rule((
        "addons/smart_construction_bundle/__manifest__.py",
        "addons/smart_construction_bundle/__init__.py",
        "addons/smart_construction_bundle/hooks.py",
    ), ("verify.smart_construction_bundle.extension_module_baseline", "verify.extension.lifecycle.orm")),
    Rule((
        "addons/smart_construction_bundle/migrations/0.1.2/",
        "addons/smart_construction_bundle/tests/__init__.py",
        "addons/smart_construction_bundle/tests/test_system_product_release.py",
    ), ("verify.smart_construction_bundle.system_product_baseline.orm", "verify.extension.lifecycle.orm")),
    Rule((
        "addons/smart_construction_portal/__manifest__.py",
        "addons/smart_construction_portal/__init__.py",
        "addons/smart_construction_portal/hooks.py",
    ), ("verify.smart_construction_portal.extension_module_baseline", "verify.extension.lifecycle.orm")),
    Rule((
        "addons/smart_license_core/__manifest__.py",
        "addons/smart_license_core/__init__.py",
        "addons/smart_license_core/hooks.py",
    ), ("verify.smart_license_core.extension_module_baseline", "verify.extension.lifecycle.orm")),
    Rule((
        "addons/smart_owner_core/__manifest__.py",
        "addons/smart_owner_core/__init__.py",
        "addons/smart_owner_core/hooks.py",
    ), ("verify.smart_owner_core.extension_module_baseline", "verify.extension.lifecycle.orm")),
    Rule((
        "addons/smart_owner_bundle/__manifest__.py",
        "addons/smart_owner_bundle/__init__.py",
        "addons/smart_owner_bundle/hooks.py",
    ), ("verify.smart_owner_bundle.extension_module_baseline", "verify.extension.lifecycle.orm")),
    # Baseline debt families retain explicit owning-module coverage. Unknown
    # paths still fail closed; these entries do not authorize generic skips.
    Rule((
        "addons/smart_core/app_config_engine/services/contract_service.py",
        "addons/smart_core/core/view_orchestrator.py",
        "addons/smart_core/handlers/business_config_change_set.py",
        "addons/smart_core/model/ui_business_config_contract.py",
        "addons/smart_core/tests/entry_namespace_test_support.py",
        "addons/smart_core/tests/test_auth_credential_framework.py",
        "addons/smart_core/tests/test_authentication_compatibility.py",
        "addons/smart_core/tests/test_business_config_change_set.py",
        "addons/smart_core/tests/test_contract_service_permission_guard_registry.py",
        "addons/smart_core/tests/test_platform_admin_boundary.py",
        "addons/smart_core/tests/test_platform_database_governance_orm.py",
        "addons/smart_core/tests/test_platform_maintenance_access_http.py",
        "addons/smart_core/tests/test_tenant_extension_storage.py",
        "addons/smart_core/tests/test_um_p1_contract_settlement_visibility_contract_orm.py",
        "addons/smart_core/tests/test_um_p1_cost_ledger_visibility_contract_orm.py",
        "addons/smart_core/tests/test_um_p1_interfund_financing_visibility_contract_orm.py",
        "addons/smart_core/tests/test_um_p1_invoice_deduction_visibility_contract_orm.py",
        "addons/smart_core/tests/test_um_p1_ownership_visibility_contract_orm.py",
        "addons/smart_core/tests/test_um_p1_payment_visibility_contract_orm.py",
        "addons/smart_core/tests/test_um_p2_interfund_relation_aggregation_orm.py",
        "addons/smart_core/tests/test_um_p2_invoice_relation_aggregation_orm.py",
        "addons/smart_core/tests/test_um_p2_payment_relation_aggregation_orm.py",
        "addons/smart_core/tests/test_um_p2_receipt_relation_aggregation_orm.py",
        "addons/smart_core/tests/test_um_p2_settlement_relation_aggregation_orm.py",
        "addons/smart_core/tests/test_um_p3_fund_plan_actual_event_allocation_orm.py",
        "addons/smart_core/tests/test_um_p3_material_settlement_purchase_authority_orm.py",
        "addons/smart_core/tests/test_um_p3_payment_ledger_request_permission_orm.py",
        "addons/smart_core/tests/test_um_p3_subcontract_cumulative_amount_orm.py",
        "addons/smart_core/tests/test_um_p3_subcontract_cumulative_settlement_orm.py",
        "addons/smart_core/tests/test_um_p3_subcontract_register_settlement_authority_orm.py",
        "addons/smart_core/tests/test_admin_vis_p3_project_record_rule_orm.py",
        "addons/smart_core/tests/test_chatter_timeline_authorization_orm.py",
        "addons/smart_core/tests/test_dictionary_scope_delivery.py",
        "addons/smart_core/tests/test_permission_contract_runtime_uid.py",
        "addons/smart_core/tests/test_form_structure_surface_capability_orm.py",
        "addons/smart_core/tests/test_user_activation.py",
    ), ("verify.smart_core.close_02.module_baseline",)),
    Rule((
        "addons/smart_core/handlers/business_config_surface.py",
        "addons/smart_core/tests/test_business_config_surface.py",
    ), ("verify.business_config.unit",)),
    Rule((
        "addons/smart_core/handlers/scene_health.py",
        "addons/smart_core/tests/test_scene_health_params.py",
    ), ("verify.p0_contract_producer.p0a.backend_unit",)),
    Rule((
        "addons/smart_core/tests/test_native_modifier.py",
    ), ("verify.frontend.collection_view_semantics.unit",)),
    Rule((
        "addons/smart_construction_scene/services/scene_package_service.py",
    ), ("verify.scene.company_route_scope_cache.orm",)),
    Rule((
        "addons/smart_construction_core/tests/test_um_p1_contract_settlement_visibility_contract_orm.py",
        "addons/smart_construction_core/tests/test_um_p1_cost_ledger_visibility_contract_orm.py",
        "addons/smart_construction_core/tests/test_um_p1_interfund_financing_visibility_contract_orm.py",
        "addons/smart_construction_core/tests/test_um_p1_invoice_deduction_visibility_contract_orm.py",
        "addons/smart_construction_core/tests/test_um_p1_ownership_visibility_contract_orm.py",
        "addons/smart_construction_core/tests/test_um_p1_payment_visibility_contract_orm.py",
        "addons/smart_construction_core/tests/test_um_p2_interfund_relation_aggregation_orm.py",
        "addons/smart_construction_core/tests/test_um_p2_invoice_relation_aggregation_orm.py",
        "addons/smart_construction_core/tests/test_um_p2_payment_relation_aggregation_orm.py",
        "addons/smart_construction_core/tests/test_um_p2_receipt_relation_aggregation_orm.py",
        "addons/smart_construction_core/tests/test_um_p2_settlement_relation_aggregation_orm.py",
        "addons/smart_construction_core/tests/test_um_p3_fund_plan_actual_event_allocation_orm.py",
        "addons/smart_construction_core/tests/test_um_p3_payment_ledger_request_permission_orm.py",
        "addons/smart_construction_core/tests/test_um_p3_subcontract_cumulative_amount_orm.py",
        "addons/smart_construction_core/tests/test_um_p3_subcontract_cumulative_settlement_orm.py",
        "addons/smart_construction_core/tests/test_um_p3_subcontract_register_settlement_authority_orm.py",
        "addons/smart_construction_core/tests/test_um_p3_material_settlement_purchase_authority_orm.py",
        "addons/smart_construction_core/tests/test_api_data_write_unlink_idempotency_backend.py",
        "addons/smart_construction_core/tests/test_capability_registry_service.py",
        "addons/smart_construction_core/tests/test_payment_request_action_surface_backend.py",
        "addons/smart_construction_core/tests/test_payment_request_available_actions_backend.py",
        "addons/smart_construction_core/tests/test_admin_vis_p3_project_record_rule_orm.py",
        "addons/smart_construction_core/tests/test_chatter_timeline_authorization_orm.py",
        "addons/smart_construction_core/tests/test_dictionary_scope_delivery.py",
        "addons/smart_construction_core/tests/test_permission_contract_runtime_uid.py",
        "addons/smart_construction_core/tests/test_form_structure_surface_capability_orm.py",
        "addons/smart_construction_core/tests/perm_matrix.py",
        "addons/smart_construction_core/tests/test_api_data_search_fields_extension.py",
        "addons/smart_construction_core/tests/test_approval_policy_toggle_backend.py",
        "addons/smart_construction_core/tests/test_business_data_ownership_gate.py",
        "addons/smart_construction_core/tests/test_context_workspace_native_lowcode.py",
        "addons/smart_construction_core/tests/test_contract_execution_position.py",
        "addons/smart_construction_core/tests/test_contract_payment_allocation_fact.py",
        "addons/smart_construction_core/tests/test_daily_contract_settlement_native_lowcode.py",
        "addons/smart_construction_core/tests/test_expense_claim_native_lowcode.py",
        "addons/smart_construction_core/tests/test_experience_role_surface.py",
        "addons/smart_construction_core/tests/test_feedback_evaluation_rt_http.py",
        "addons/smart_construction_core/tests/test_feedback_evaluation_rt_restore.py",
        "addons/smart_construction_core/tests/test_hr_payroll_native_lowcode.py",
        "addons/smart_construction_core/tests/test_invoice_native_lowcode.py",
        "addons/smart_construction_core/tests/test_ledger_summary_guarantee_native_lowcode.py",
        "addons/smart_construction_core/tests/test_light_forms_configuration_native_lowcode.py",
        "addons/smart_construction_core/tests/test_payment_execution_native_lowcode.py",
        "addons/smart_construction_core/tests/test_policy_document_capability.py",
        "addons/smart_construction_core/tests/test_project_authorization_foundation.py",
        "addons/smart_construction_core/tests/test_receipt_income_native_lowcode.py",
        "addons/smart_construction_core/tests/test_settlement_fact_immutability_v1.py",
        "addons/smart_construction_core/tests/test_source_bounded_data_space_rules.py",
        "addons/smart_construction_core/tests/test_system_permission_accounting.py",
        "addons/smart_construction_core/tests/test_system_permission_separation.py",
        "addons/smart_construction_core/tests/test_tax_certificate_registration.py",
        "addons/smart_construction_core/tests/test_tax_deduction_native_lowcode.py",
        "addons/smart_construction_core/tests/test_tender_guarantee_visible_fields.py",
        "addons/smart_construction_core/tests/test_usage_performance_native_lowcode.py",
        "addons/smart_construction_core/tests/test_user_feedback_business_views.py",
        "addons/smart_construction_core/views/menu_business_taxonomy.xml",
    ), ("verify.smart_construction_core.module_baseline",)),
    Rule((
        "addons/smart_construction_scene/tests/test_enterprise_initialization_journey.py",
        "addons/smart_construction_scene/tests/test_source_bounded_scene_rules.py",
    ), ("verify.smart_construction_scene.module_baseline",)),
    # Shared extension execution changes reach all owning module families.
    # Focused tags supplement these baselines; they cannot replace them.
    Rule((
        "addons/smart_core/core/extension_loader.py",
        "addons/smart_core/core/extension_hook_contracts.py",
        "addons/smart_core/core/system_init_extension_fact_merger.py",
        "addons/smart_construction_core/data/sc_extension_params.xml",
    ), (
        "verify.smart_core.close_02.module_baseline",
        "verify.smart_construction_core.module_baseline",
        "verify.smart_construction_scene.module_baseline",
        "verify.extension.lifecycle.orm",
    )),
    Rule((
        "scripts/ops/r10_performance_ab_profile.py",
        "scripts/ops/r10_performance_ab_lifecycle.py",
        "scripts/ops/test_r10_performance_ab_profile.py",
        "scripts/ops/test_r10_performance_ab_lifecycle.py",
        "config/ops/r10_performance_ab_profile.v1.json",
        "config/ops/r10_performance_ab_stack.yml",
        "scripts/ops/r10_performance_ab_continuity_contract_v1.json",
        "make/r10_performance.mk",
        "Makefile",
        "make/daily_candidate.mk",
    ), (
        "verify.r10.performance_ab.profile",
    )),
    Rule((
        "addons/smart_core/core/scene_provider.py",
        "addons/smart_core/core/scene_registry_provider.py",
        "addons/smart_core/core/scene_runtime_orchestrator.py",
        "addons/smart_core/governance/scene_normalizer.py",
        "addons/smart_core/core/system_init_runtime_context.py",
        "addons/smart_core/core/system_init_request_context.py",
        "addons/smart_core/adapters/odoo_nav_adapter.py",
        "addons/smart_core/tests/test_system_init_request_context.py",
    ), (
        "verify.backend.navigation_delivery.unit",
        "verify.system.performance.baseline.unit",
    )),
    Rule((
        "addons/smart_core/core/ui_base_contract_asset_producer.py",
        "addons/smart_core/core/ui_base_contract_asset_repository.py",
        "addons/smart_core/tests/test_ui_base_contract_asset_producer.py",
        "addons/smart_core/tests/test_ui_base_contract_asset_repository.py",
    ), (
        "verify.smart_core.ui_base_asset_refresh.unit",
    )),
    Rule((
        "addons/smart_core/tests/test_scene_provider_target_identity_merge.py",
    ), (
        "verify.frontend.scene_entry_contract.unit",
    )),
    Rule((
        "addons/smart_core/core/system_init_extension_fact_merger.py",
        "addons/smart_core/tests/test_system_init_extension_fact_merger.py",
    ), ("verify.backend.navigation_delivery.unit",)),
    Rule((
        "addons/smart_construction_scene/__init__.py",
        "addons/smart_construction_scene/core_extension.py",
        "addons/smart_construction_scene/tests/test_hook_authority_consumer.py",
        "addons/smart_core/core/extension_hook_contracts.py",
        "addons/smart_core/utils/extension_hooks.py",
        "scripts/verify/extension_hook_contract_guard.py",
        "scripts/verify/test_extension_hook_contract_guard.py",
        "scripts/verify/test_extension_hook_resolver.py",
    ), (
        "verify.extension.hook_contracts.unit",
        "verify.extension.hook_resolver.unit",
        "verify.extension.hook_authority.orm",
        "verify.extension.native_alignment.orm",
    )),
    Rule((
        "addons/smart_core/core/extension_loader.py",
        "addons/smart_core/core/handler_registry.py",
        "addons/smart_core/tests/test_extension_runtime_context.py",
        "scripts/verify/test_extension_runtime_context.py",
    ), (
        "verify.extension.runtime_context.unit",
        "verify.extension.runtime_context.orm",
    )),
    Rule((
        "addons/smart_core/core/intent_router.py",
        "addons/smart_core/handlers/login.py",
        "addons/smart_core/handlers/terminal_shell_v2.py",
        "addons/smart_core/handlers/ui_contract_v2_adapters.py",
        "addons/smart_core/security/credential_service.py",
        "addons/smart_core/security/intent_authorization.py",
        "addons/smart_core/security/intent_permission.py",
        "addons/smart_core/tests/test_intent_router_payload_envelope.py",
        "addons/smart_core/tests/test_login_company_boundary.py",
        "addons/smart_core/tests/test_login_identity_semantics.py",
        "addons/smart_core/tests/test_terminal_shell_v2_boundaries.py",
        "scripts/contract/snapshot_export.py",
        "scripts/verify/smart_core_boundary_guard.py",
        "scripts/verify/test_smart_core_boundary_guard.py",
    ), (
        "verify.extension.consumers.unit",
    )),
    Rule((
        "scripts/ops/apply_extension_modules.sh",
        "scripts/verify/extension_modules_guard.sh",
        "scripts/verify/test_extension_modules_guard.py",
    ), (
        "verify.extension.modules_guard.unit",
    )),
    Rule((
        "addons/smart_core/tests/test_extension_registry_lifecycle.py",
    ), (
        "verify.extension.lifecycle.orm",
    )),
    Rule((
        "scripts/ci/orm_result_guard.sh",
        "scripts/dev/local_test_runner.py",
    ), (
        "verify.orm.guard.self_test",
    )),
    Rule((
        "frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue",
        "frontend/apps/web/scripts/readonly_block_component_test.mjs",
        "frontend/apps/web/src/pages/contractForm/relationDescriptor.ts",
        "frontend/apps/web/scripts/relation_entry_option_limits_test.ts",
    ), ("verify.frontend.professional_relation_field.unit",)),
    Rule((
        "addons/smart_core/core/platform_minimum_nav_contract.py",
        "addons/smart_core/tests/test_platform_minimum_nav_contract.py",
    ), (
        "verify.backend.navigation_delivery.unit",
        "verify.daily.permission_truth.capability.orm",
    )),
    Rule((
        "addons/smart_core/tests/test_intent_smoke.py",
    ), (
        "verify.smart_core.intent_smoke.orm",
    )),
    Rule((
        "frontend/apps/web/scripts/route_authority_guard_test.ts",
        "frontend/apps/web/src/app/routeFailure.ts",
        "frontend/apps/web/src/router/index.ts",
        "frontend/apps/web/src/views/RouteErrorView.vue",
        "addons/smart_core/delivery/runtime_route_authority.py",
    ), (
        "verify.nav.pro01r.route_authority.unit",
        "verify.frontend.product_page_header.unit",
    )),
    Rule((
        "frontend/apps/web/src/app/relationReadRouteAuthority.ts",
        "frontend/apps/web/scripts/record_form_return_navigation_test.ts",
    ), (
        "verify.frontend.record_form_return.unit",
    )),
    Rule((
        "frontend/apps/web/src/app/pageIdentity.ts",
        "frontend/apps/web/src/app/pageIdentityAdapters.ts",
        "frontend/apps/web/src/app/pageIdentityRoute.ts",
        "frontend/apps/web/src/app/pageIdentityCoordinator.ts",
        "frontend/apps/web/src/app/pageIdentityRuntime.ts",
        "frontend/apps/web/src/app/usePublishedPageIdentity.ts",
        "scripts/verify/frontend_page_identity_smoke.js",
        "scripts/verify/frontend_page_identity_lifecycle_smoke.js",
        "scripts/verify/frontend_page_identity_guard.py",
    ), (
        "verify.frontend.page_identity",
    )),
    Rule((
        "addons/smart_core/core/system_init_scene_runtime_surface_builder.py",
        "addons/smart_core/core/system_init_scene_runtime_surface_context.py",
        "addons/smart_core/tests/test_system_init_scene_runtime_surface_builder.py",
    ), (
        "verify.system_init.menu_boundary.guard",
        "verify.daily.permission_truth.capability.orm",
    )),
    Rule((
        "make/dev_test.mk",
    ), (
        "verify.frontend.dev.incremental.unit",
        "verify.daily.permission_truth.capability.orm",
    )),
    Rule((
        "contracts/registry/",
    ), (
        "verify.semantic.registry.lint",
    )),
    Rule((
        "addons/smart_core/utils/native_field_descriptor.py",
    ), (
        "verify.frontend.collection_view_semantics.unit",
        "verify.semantic.registry.lint",
    )),
    Rule((
        "contracts/generated/contract_structure_fingerprint.json",
    ), (
        "verify.contract.structure_lock",
    )),
    Rule((
        "addons/smart_construction_core/views/core/project_views.xml",
        "addons/smart_construction_core/views/core/project_overview_views.xml",
        "scripts/verify/test_product_view_structure_contract.py",
    ), (
        "verify.product_view_structure.contract.unit",
    )),
    Rule((
        ".agent/",
    ), (
        "verify.agent.ledger.unit",
    )),
    Rule((
        "demo_addons/smart_construction_demo/",
    ), (
        "verify.demo.lifecycle.unit",
        "verify.demo.scenario_step.unit",
    )),
    Rule((
        "scripts/demo/verify.sh",
    ), (
        "verify.demo.lifecycle.unit",
    )),
    Rule((
        "scripts/verify/demo_scenario_step.py",
        "scripts/verify/test_demo_scenario_step.py",
    ), (
        "verify.demo.scenario_step.unit",
    )),
    Rule((
        "scripts/verify/demo_usage_foundation_role_scope_manifest.json",
        "scripts/verify/demo_usage_foundation_role_scope_probe.py",
        "scripts/verify/test_demo_usage_foundation_role_scope_probe.py",
    ), (
        "verify.demo.usage_foundation_role_scope.unit",
    )),
    Rule((
        "demo_addons/smart_construction_demo/tests/test_demo_golden_chain.py",
    ), (
        "verify.demo.lifecycle.unit",
        "verify.demo.scenario_step.unit",
        "verify.local.dev.golden_chain.orm",
    )),
    Rule((
        ".gitignore",
    ), (
        "verify.pr.push.unit",
    )),
    Rule((
        "config/acceptance/evolution_binding.v1.json",
        "scripts/ops/acceptance_evolution_integration.py",
        "scripts/verify/acceptance_evolution_binding_guard.py",
        "scripts/verify/test_acceptance_evolution_binding_guard.py",
        "scripts/verify/test_acceptance_evolution_integration.py",
    ), (
        "verify.acceptance.evolution.binding",
    )),
    Rule((
        "config/acceptance/frontend_presentation_targets.v1.json",
        "scripts/verify/frontend_product_page_header_browser.mjs",
    ), (
        "verify.frontend.presentation.lane.unit",
    )),
    Rule((
        "config/acceptance/backend_contract_instance_v1.json",
    ), (
        "verify.frontend.acceptance.environment.guard",
    )),
    Rule((
        "config/acceptance/backend_contract_instance_daily_v1.json",
    ), (
        "verify.daily_dev.acceptance_fixture.unit",
    )),
    Rule((
        "addons/smart_construction_core/tests/test_tender_award_fact.py",
    ), (
        "verify.tender_award_fact.orm",
    )),
    Rule((
        "addons/smart_core/handlers/route_authority_validate.py",
    ), (
        "verify.execute_button.authority.unit",
        "verify.product.entry_publication.unit",
    )),
    Rule((
        "scripts/verify/acceptance_contract_receipt_test.mjs",
    ), (
        "verify.frontend.list_surface_search_contract.unit",
    )),
    Rule((
        "scripts/verify/daily_demo_contract_api_acceptance.py",
    ), (
        "verify.daily.demo.contract.api.unit",
    )),
    Rule((
        "scripts/verify/daily_demo_runtime_performance.py",
    ), (
        "verify.local.dev.runtime.performance.unit",
    )),
    # Acceptance runtime rebuild, startup, artifact and carrier-discard inputs
    # form one P4 behavior lock. Leaving their tests unmapped forces a manual
    # L2 choice and can silently omit the exact runtime/tooling suite.
    Rule((
        "scripts/dev/backend_acceptance_up.sh",
        "scripts/verify/test_acceptance_artifact.py",
    ), (
        "verify.acceptance.artifact.unit",
    )),
    Rule((
        "scripts/dev/frontend_acceptance_baseline_rebuild.sh",
        "scripts/verify/test_frontend_acceptance_baseline_rebuild.py",
        "scripts/verify/test_frontend_acceptance_carrier_discard.py",
    ), (
        "verify.acceptance.runtime.tooling.unit",
    )),
    Rule((
        "scripts/ops/validation_delivery_plan.py",
        "scripts/verify/test_validation_delivery_plan.py",
    ), (
        "verify.validation.delivery.unit",
    )),
    Rule((
        "config/ci/path_ownership_v1.json",
        "config/ci/risk_tiering_v1.json",
        "scripts/ci/ci_path_ownership.py",
        "scripts/ci/test_ci_path_ownership.py",
    ), (
        "verify.ci.path_ownership.unit",
        "verify.ci.workflow.contract",
    )),
    Rule((
        "scripts/ci/ci_risk_classifier.py",
        "scripts/ci/test_ci_risk_classifier.py",
        "scripts/ci/test_ci_risk_workflow_contract.py",
        "scripts/ci/test_merge_policy_gate.py",
        "scripts/ci/release_condition.py",
        "scripts/ci/test_release_condition.py",
        "scripts/ci/test_release_candidate_gate.py",
        "scripts/ci/gitee_gate_plan.py",
        "scripts/ci/gitee_formal_executor.py",
        "scripts/verify/test_gitee_gate_plan.py",
        "scripts/verify/test_gitee_formal_executor.py",
    ), (
        "verify.ci.workflow.contract",
    )),
    Rule((
        "scripts/ci/contract_only_scope.py",
        "scripts/ci/test_contract_only_scope.py",
        "config/ci/contract_only_scopes.json",
    ), (
        "verify.ci.workflow.contract",
    )),
    Rule((
        "scripts/ci/frontend_",
        "scripts/ci/test_frontend_",
    ), (
        "verify.ci.path_ownership.unit",
        "verify.frontend.dev.incremental.unit",
    )),
    Rule((
        ".github/workflows/professional_quality_gate.yml",
        ".github/workflows/merge_policy_gate.yml",
        ".github/workflows/frontend_release_gate.yml",
        ".github/workflows/public_guard.yml",
        ".github/workflows/release_candidate_gate.yml",
        "scripts/ci/scheduled_validation.py",
        "scripts/ci/select_authoritative_workflow_run.py",
        "scripts/ci/test_select_authoritative_workflow_run.py",
        "scripts/ci/self_hosted_runner_cleanup.sh",
    ), (
        "verify.ci.workflow.contract",
    )),
    Rule((
        ".github/workflows/professional_quality_gate.yml",
        ".github/workflows/merge_policy_gate.yml",
        ".github/workflows/frontend_release_gate.yml",
        ".github/workflows/public_guard.yml",
        ".github/workflows/release_candidate_gate.yml",
        "scripts/ci/scheduled_validation.py",
        "scripts/ci/select_authoritative_workflow_run.py",
        "scripts/ci/test_select_authoritative_workflow_run.py",
        "scripts/ci/test_ci_risk_workflow_contract.py",
        "scripts/ci/test_merge_policy_gate.py",
        "scripts/ci/test_release_candidate_gate.py",
        "scripts/ci/release_condition.py",
        "scripts/ci/test_release_condition.py",
    ), (
        "verify.ci.scheduled_gates",
    )),
    Rule((
        "scripts/dev/frontend_acceptance_operation_entry.sh",
        "scripts/verify/frontend_release_ci_guard.py",
        "scripts/verify/test_frontend_release_ci_guard.py",
    ), (
        "verify.ci.scheduled_gates",
    )),
    Rule((
        "scripts/ci/main_full_release_dispatch.py",
        "scripts/ci/test_main_full_release_dispatch.py",
        "scripts/ci/main_full_release_evidence.py",
        "scripts/ci/test_main_full_release_evidence.py",
    ), (
        "verify.ci.scheduled_gates",
    )),
    Rule((
        "scripts/verify/frontend_static_release_audit.py",
    ), (
        "verify.ci.workflow.contract",
    )),
    Rule((
        "make/ci.mk",
    ), (
        "verify.frontend.dev.incremental.unit",
    )),
    Rule((
        "make/contract.mk",
    ), (
        "verify.semantic.registry.lint",
    )),
    Rule((
        "make/codex.mk",
    ), (
        "verify.branch.governance.consistency",
        "verify.ci.path_ownership.unit",
    )),
    Rule((
        "scripts/verify/branch_governance_consistency_guard.py",
        "scripts/verify/test_branch_governance_consistency_guard.py",
    ), (
        "verify.branch.governance.consistency",
    )),
    # Lint/typecheck configuration is part of the executable validation
    # contract. Changing a source root or supported extension must rerun both
    # source-wide targets rather than fall through as an unclassified path.
    Rule((
        "frontend/apps/web/package.json",
        "frontend/apps/web/.eslintrc.cjs",
        "frontend/apps/web/tsconfig.strict.json",
        "frontend/packages/ui/package.json",
        "frontend/packages/ui/tsconfig.json",
    ), BASE_FRONTEND_TARGETS),
    Rule((
        "frontend/packages/design-tokens/",
    ), (
        "verify.frontend.style_system.guard",
    )),
    Rule((
        "frontend/apps/web/vite.config.ts",
        "frontend/apps/web/src/env.d.ts",
        "frontend/apps/web/src/app/runtime/buildIdentity.ts",
        "frontend/apps/web/scripts/build_identity_test.ts",
        "frontend/apps/web/src/components/product-shell/ProductShellSidebarFooter.vue",
        "frontend/apps/web/src/layouts/AppShell.vue",
        "frontend/apps/web/src/main.ts",
        "frontend/apps/web/src/stores/session.ts",
        "frontend/apps/web/src/stores/sessionPersistence.ts",
        "frontend/apps/web/src/stores/navigationExpansionActions.ts",
        "frontend/apps/web/src/stores/navigationProjectionActions.ts",
        "frontend/apps/web/scripts/session_persistence_snapshot_test.ts",
        "frontend/apps/web/scripts/session_persistence_scheduler_test.ts",
        "frontend/apps/web/scripts/session_persistence_failure_test.ts",
        "frontend/apps/web/scripts/session_persistence_recovery_test.ts",
        "frontend/apps/web/scripts/session_persistence_performance_test.ts",
        "frontend/apps/web/scripts/standard_page_type_browser.mjs",
    ), (
        "verify.frontend.runtime_identity.unit",
        "verify.frontend.session_persistence.snapshot.unit",
        "verify.frontend.session_persistence.scheduler.unit",
        "verify.frontend.session_persistence.failure.unit",
        "verify.frontend.session_persistence.recovery.unit",
        "verify.frontend.primitive_adapter.unit",
        "verify.frontend.standard_preview.unit",
    )),
    Rule((
        "addons/smart_core/utils/product_release.py",
        "addons/smart_core/tests/test_runtime_release_identity.py",
    ), (
        "verify.platform.runtime_identity.unit",
    )),
    Rule((
        "scripts/dev/frontend_static_build.sh",
    ), (
        "verify.frontend.runtime_identity.unit",
    )),
    # Renderer registration is one executable contract spanning the generated
    # carrier, registry, extension entry point and their focused locks. A
    # registry change must never fall through to a generic typecheck only.
    Rule((
        "contracts/registry.yaml",
        "contracts/registry/component.yaml",
        "contracts/registry/registry.schema.json",
        "contracts/registry/semantic.yaml",
        "frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts",
        "frontend/apps/web/src/app/presentation/nodeComponentPresentation.ts",
        "frontend/apps/web/src/app/presentation/semantic_registry.generated.ts",
        "frontend/apps/web/src/app/presentation/industry_renderer_manifest.generated.ts",
        "frontend/apps/web/src/extensions/industryRenderers.ts",
        "frontend/apps/web/scripts/professional_component_registry_test.ts",
        "scripts/contract/generate_semantic_registry.py",
        "scripts/verify/frontend_professional_component_registry_guard.py",
        "scripts/verify/test_frontend_professional_component_registry_guard.py",
    ), (
        "verify.frontend.professional_component_registry.unit",
        "verify.semantic.registry.lint",
    )),
    Rule((
        "addons/smart_core/core/node_component_capabilities.py",
        "addons/smart_core/tests/test_node_component_capabilities.py",
    ), (
        "verify.node_component_capabilities.unit",
    )),
    Rule((
        "addons/smart_core/core/native_widget_profile.py",
        "addons/smart_core/core/contract_runtime/semantic_resolver.py",
        "addons/smart_core/core/contract_runtime/semantic_registry_generated.py",
        "addons/smart_core/app_config_engine/services/view_Parser/base.py",
        "addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py",
        "addons/smart_core/tests/test_native_view_parser_surfaces.py",
        "addons/smart_core/tests/test_unified_page_contract_v2_kanban_action_registry.py",
        "scripts/verify/test_native_widget_provenance.py",
    ), (
        "verify.native_advisory.unit",
        "verify.native_widget.provenance.unit",
        "verify.semantic.registry.lint",
        "verify.unified_page_contract.v2.assembler",
        "verify.unified_page_contract.v2.runtime",
    )),
    Rule((
        "scripts/audit/generate_frontend_component_driver_takeover_inventory.py",
        "scripts/audit/test_generate_frontend_component_driver_takeover_inventory.py",
        "docs/frontend_productization/rendering-detail/component-driver-takeover-inventory-v1.json",
    ), (
        "verify.frontend.component_driver_takeover.unit",
    )),
    Rule((
        "scripts/audit/generate_frontend_rendering_detail_inventory.py",
        "scripts/audit/generate_frontend_visual_projection_inventory.py",
        "scripts/audit/test_generate_frontend_rendering_detail_inventory.py",
        "scripts/audit/test_generate_frontend_visual_projection_inventory.py",
        "scripts/verify/frontend_rendering_detail_state_guard.py",
        "scripts/verify/test_frontend_rendering_detail_state_guard.py",
    ), (
        "verify.frontend.rendering_detail_state.unit",
    )),
    Rule((
        "frontend/apps/web/scripts/view_type_render_coverage_probe.ts",
        "scripts/verify/view_type_render_coverage_guard.py",
        "scripts/verify/test_view_type_render_coverage_guard.py",
    ), (
        "verify.frontend.view_type_render_coverage.guard",
    )),
    Rule((
        "scripts/verify/frontend_project_domain_rollout.py",
        "scripts/verify/frontend_project_domain_rollout_report.py",
        "scripts/verify/test_frontend_project_domain_rollout.py",
    ), (
        "verify.frontend.project_domain_rollout.unit",
    )),
    Rule((
        "scripts/verify/frontend_state_dashboard_browser.mjs",
    ), (
        "verify.frontend.state_dashboard.unit",
    )),
    Rule((
        "scripts/audit/native_scene_inventory.py",
        "scripts/audit/test_native_scene_inventory.py",
    ), (
        "verify.native_scene.inventory.unit",
    )),
    Rule((
        "scripts/verify/frontend_professional_detail_collection_guard.py",
        "scripts/verify/test_frontend_professional_detail_collection_guard.py",
    ), (
        "verify.frontend.professional_detail_collection.unit",
    )),
    Rule((
        "frontend/apps/web/src/components/MenuTree.vue",
        "frontend/apps/web/src/components/product-shell/ProductSideNavigation.vue",
        "scripts/verify/frontend_navigation_shell_guard.py",
        "scripts/verify/test_frontend_navigation_shell_guard.py",
    ), (
        "verify.frontend.navigation_shell.unit",
    )),
    Rule((
        "frontend/apps/web/src/components/design-system/ScDialog.vue",
        "frontend/apps/web/src/components/design-system/ScDrawer.vue",
        "frontend/apps/web/src/composables/useModalLifecycle.ts",
        "frontend/apps/web/src/views/ActionView.vue",
        "frontend/apps/web/src/components/attachment/AttachmentViewer.vue",
        "frontend/apps/web/src/components/GlobalMessagePanel.vue",
        "frontend/apps/web/src/components/product-shell/ProductMobileNavigationDrawer.vue",
        "scripts/verify/frontend_overlay_lifecycle_guard.py",
        "scripts/verify/test_frontend_overlay_lifecycle_guard.py",
    ), (
        "verify.frontend.overlay_lifecycle.unit",
    )),
    Rule((
        "scripts/verify/frontend_professional_business_value_guard.py",
        "scripts/verify/test_frontend_professional_business_value_guard.py",
    ), (
        "verify.frontend.professional_business_value.unit",
    )),
    Rule((
        "scripts/verify/frontend_scene_component_bridge_guard.py",
    ), (
        "verify.frontend.scene_component_bridge.guard",
    )),
    Rule((
        "docs/architecture/inline_style_allowlist.json",
        "scripts/verify/frontend_inline_style_guard.py",
        "scripts/verify/frontend_style_system_guard.py",
        "scripts/verify/test_frontend_inline_style_guard.py",
        "scripts/verify/test_design_token_system.py",
        "scripts/audit/generate_frontend_professionalization_baseline.py",
        "scripts/audit/test_generate_frontend_professionalization_baseline.py",
    ), (
        "verify.frontend.style_system.guard",
    )),
    Rule((
        "docs/architecture/text_containment_allowlist.json",
        "scripts/verify/frontend_text_containment_guard.py",
        "scripts/verify/test_frontend_text_containment_guard.py",
    ), (
        "verify.frontend.text_containment.guard",
    )),
    Rule((
        "docs/architecture/frontend_systemic_convergence_gates.json",
        "scripts/verify/frontend_systemic_convergence_gate_guard.py",
        "scripts/verify/test_frontend_systemic_convergence_gate_guard.py",
    ), (
        "verify.frontend.systemic.convergence.guard",
    )),
    Rule((
        "docs/architecture/split_usage_allowlist.json",
        "scripts/verify/frontend_split_usage_guard.py",
        "scripts/verify/test_frontend_split_usage_guard.py",
    ), (
        "verify.frontend.split_usage.guard",
    )),
    Rule((
        "frontend/apps/web/src/components/content/ScRichText.vue",
        "frontend/apps/web/src/utils/safeHtmlLinkTarget.ts",
        "frontend/apps/web/src/utils/sanitizeReadonlyHtml.ts",
        "frontend/apps/web/src/utils/sanitizeRestrictedHtml.ts",
        "frontend/apps/web/scripts/rich_text_component_browser_test.mjs",
        "scripts/verify/frontend_rich_text_guard.py",
        "scripts/verify/test_frontend_rich_text_guard.py",
    ), (
        "verify.frontend.rich_text.guard",
    )),
    Rule((
        "scripts/verify/daily_demo_runtime_performance.py",
        "scripts/verify/local_dev_runtime_performance.py",
        "scripts/verify/local_dev_runtime_performance_browser.mjs",
        "scripts/verify/local_dev_runtime_performance_browser.sh",
        "scripts/verify/local_dev_dev_acceptance_remediation_browser.mjs",
        "scripts/verify/test_local_dev_runtime_performance.py",
        "make/role_authority.mk",
    ), (
        "verify.local.dev.runtime.performance.unit",
    )),
    Rule((
        "scripts/verify/odoo_native_capability_explorer_probe.py",
        "scripts/verify/test_odoo_native_capability_explorer_probe.py",
    ), (
        "verify.odoo_native_capability_explorer.unit",
    )),
    Rule((
        "scripts/verify/test_menu_metadata_batch.py",
        "addons/smart_core/delivery/menu_service.py",
    ), (
        "verify.product.menu.metadata_batch.unit",
    )),
    Rule((
        "addons/smart_core/delivery/menu_service.py",
        "addons/smart_core/tests/test_delivery_menu_entry_target.py",
        "addons/smart_core/tests/test_menu_acl_carrier_authorization.py",
    ), (
        "verify.backend.navigation_delivery.unit",
    )),
    Rule((
        "addons/smart_core/delivery/navigation_contract_compiler.py",
        "addons/smart_core/handlers/system_init.py",
        "addons/smart_core/core/delivery_menu_defaults.py",
        "addons/smart_core/core/navigation_entry_target.py",
        "addons/smart_core/core/system_init_payload_builder.py",
        "addons/smart_core/tests/test_system_init_payload_builder_semantics.py",
        "addons/smart_core/tests/test_navigation_entry_target.py",
        "addons/smart_core/delivery/delivery_engine.py",
        "addons/smart_core/tests/test_navigation_contract_compiler.py",
        "addons/smart_core/tests/test_native_config_menu_projection.py",
        "addons/smart_core/tests/test_relation_entry_contract.py",
        "addons/smart_core/tests/test_system_init_final_route_authority_static.py",
    ), (
        "verify.backend.navigation_delivery.unit",
        "verify.system_init.menu_boundary.guard",
        "verify.scenario.center_projection.guard",
    )),
    Rule((
        "addons/smart_core/tests/test_platform_admin_duty_contract.py",
        "addons/smart_core/core/platform_duty_contract.py",
        "addons/smart_core/core/system_init_identity_payload.py",
        "addons/smart_core/security/platform_admin.py",
        "addons/smart_core/controllers/platform_duty_controller.py",
        "addons/smart_core/controllers/platform_ops_controller.py",
        "addons/smart_core/delivery/effective_delivery_service.py",
        "addons/smart_core/handlers/system_init.py",
        "addons/smart_core/views/platform_company_access_views.xml",
        "addons/smart_core/data/sc_platform_namespace_seed.xml",
        "frontend/apps/web/src/components/platform-duty/dutyAction.ts",
        "frontend/apps/web/src/components/platform-duty/dutyAction.test.ts",
        "frontend/apps/web/src/components/platform-duty/PlatformDutyPanel.vue",
    ), (
        "verify.platform.duty.contract.unit",
    )),
    Rule((
        "addons/smart_core/delivery/runtime_capability_catalog.py",
        "addons/smart_core/delivery/product_policy_catalog_sync_service.py",
        "addons/smart_core/tests/test_runtime_capability_catalog.py",
        "addons/smart_core/tests/test_backend_semantic_copy_supply.py",
    ), (
        "verify.runtime_capability_catalog.unit",
    )),
    Rule((
        "addons/smart_core/delivery/platform_capability_explorer.py",
        "addons/smart_core/delivery/platform_catalog_action_contract.py",
        "addons/smart_core/handlers/platform_capability_explorer.py",
        "addons/smart_core/tests/test_platform_capability_explorer.py",
        "addons/smart_construction_core/services/platform_capability_explorer_contributions.py",
        "addons/smart_construction_core/services/product_menu_source.py",
        "addons/smart_construction_core/tests/test_platform_capability_explorer_contributions.py",
        "scripts/verify/platform_capability_explorer_runtime_probe.py",
        "scripts/verify/test_platform_capability_explorer_runtime_probe.py",
        "scripts/ops/odoo_shell_exec.sh",
    ), (
        "verify.platform.capability_explorer.unit",
    )),
    Rule((
        "addons/smart_core/delivery/release_operator_read_model_service.py",
        "addons/smart_core/delivery/release_operator_surface_service.py",
        "addons/smart_core/delivery/release_audit_trail_service.py",
        "addons/smart_core/delivery/product_scene_composition.py",
        "addons/smart_core/delivery/platform_management_action_contract.py",
        "addons/smart_core/delivery/release_operator_contract_registry.py",
        "addons/smart_core/tests/test_release_operator_surface_copy_backend.py",
    ), (
        "verify.admin_close_01.backend.unit",
    )),
    Rule((
        "frontend/apps/web/src/api/platformCapabilityExplorer.ts",
        "frontend/apps/web/src/app/platformCapabilityExplorerPresentation.ts",
        "frontend/apps/web/src/app/platformCapabilityExplorerRequestGate.ts",
        "frontend/apps/web/src/app/releaseOperatorActionContract.ts",
        "frontend/apps/web/src/app/businessScenarioNavigation.ts",
        "frontend/apps/web/src/views/ReleaseOperatorView.vue",
        "frontend/apps/web/src/views/PlatformCapabilityExplorerView.vue",
        "frontend/apps/web/src/app/adminRouteAccess.ts",
        "frontend/apps/web/scripts/admin_route_access_test.ts",
        "frontend/apps/web/scripts/platform_capability_explorer_test.ts",
        "frontend/apps/web/scripts/platform_capability_explorer_browser.mjs",
        "frontend/apps/web/scripts/platform_capability_explorer_browser_support.mjs",
        "frontend/apps/web/scripts/platform_capability_explorer_browser_support_test.mjs",
    ), (
        "verify.frontend.platform_capability_explorer.unit",
    )),
    Rule((
        "frontend/apps/web/src/composables/useScenarioActivation.ts",
        "frontend/apps/web/src/components/scene/ScenarioActivationPanel.vue",
        "frontend/apps/web/scripts/workspace_scenario_lifecycle_test.ts",
    ), (
        "verify.frontend.workspace_scenario_lifecycle.unit",
    )),
    Rule((
        "addons/smart_core/core/page_contracts_builder.py",
        "addons/smart_core/core/action_target_schema.py",
    ), (
        "verify.frontend.page_contract_boundary.guard",
        "verify.page_contract.action_schema_semantics.guard",
        "verify.p0_contract_producer.p0c.unit",
    )),
    Rule((
        "addons/smart_core/core/unified_page_contract_v2_assembler.py",
        "addons/smart_core/handlers/ui_contract_v2.py",
        "frontend/apps/web/src/app/contracts/v2/fieldDescriptor.ts",
        "frontend/apps/web/src/app/contracts/v2/types.ts",
        "docs/architecture/p0_contract_producer_01/contract_v2_field_descriptor.schema.json",
        "frontend/apps/web/scripts/polymorphic_reference_real_contract_test.ts",
        "frontend/apps/web/scripts/relation_active_actions_real_contract_test.ts",
        "scripts/verify/p0_contract_producer_descriptor_evidence.py",
        "addons/smart_construction_core/tests/test_p0_contract_producer_p0a.py",
    ), (
        "verify.contract.polymorphic_reference.integration",
        "verify.contract.relation_active_actions.integration",
    )),
    Rule((
        "addons/smart_core/core/contract_version_negotiation.py",
        "addons/smart_core/core/page_block_data_contract.py",
        "addons/smart_core/core/page_block_action_contract.py",
        "addons/smart_core/core/contract_runtime/native_widget_contract.py",
        "addons/smart_core/core/contract_runtime/semantic_resolver.py",
        "addons/smart_core/core/unified_page_contract_v2_assembler.py",
        "addons/smart_core/core/unified_page_contract_v2_action.py",
        "addons/smart_core/handlers/ui_contract_v2.py",
        "addons/smart_core/tests/test_page_contracts_builder_boundaries.py",
        "addons/smart_construction_core/handlers/dashboard_company_enter.py",
        "addons/smart_construction_core/handlers/workspace_home_enter.py",
        "addons/smart_construction_core/services/dashboard_contract_builder.py",
        "addons/smart_construction_core/services/scene_block_schema.py",
        "addons/smart_construction_core/services/workspace_contract_builder.py",
        "addons/smart_construction_core/tests/test_p0_contract_producer_p0a.py",
        "addons/smart_construction_core/tests/test_p0_contract_producer_p0c.py",
        "addons/smart_core/tests/test_native_widget_contract_bridge.py",
        "addons/smart_core/tests/test_contract_runtime_semantic_resolver.py",
        "scripts/verify/p0_contract_producer_descriptor_evidence.py",
        "frontend/apps/web/scripts/p0_contract_producer_real_contract_decode_test.ts",
    ), (
        "verify.p0_contract_producer.p0a.backend_unit",
        "verify.p0_contract_producer.p0a.descriptor_conformance",
        "verify.p0_contract_producer.p0a.money",
        "verify.p0_contract_producer.p0a.unit",
        "verify.p0_contract_producer.p0c.orm",
        "verify.p0_contract_producer.p0c.unit",
    )),
    Rule((
        "frontend/apps/web/src/app/contracts/v2/carrierCapabilities.ts",
        "frontend/apps/web/src/app/pageOrchestration.ts",
        "frontend/apps/web/scripts/p0_contract_producer_p0c_test.ts",
        "addons/smart_core/tests/test_page_block_action_contract.py",
    ), (
        "verify.p0_contract_producer.p0c.unit",
    )),
    Rule((
        "addons/smart_core/handlers/execute_button.py",
        "addons/smart_construction_core/tests/fixtures/p0_c_fix01_action_button.json",
        "frontend/apps/web/src/app/action_runtime/useActionViewActionPresentationRuntime.ts",
        "frontend/apps/web/src/app/action_runtime/useActionViewActionRuntime.ts",
        "frontend/apps/web/src/app/action_runtime/useActionViewContractActionButtonRuntime.ts",
        "frontend/apps/web/src/app/runtime/actionViewContractActionRuntime.ts",
        "frontend/apps/web/scripts/p0_c_fix01_action_id_chain_test.ts",
    ), (
        "verify.execute_button.authority.unit",
        "verify.p0_c_fix01.action_id.orm",
        "verify.p0_c_fix01.action_id.unit",
        "verify.p0_contract_producer.p0c.orm",
        "verify.p0_contract_producer.p0c.unit",
    )),
    Rule((
        "scripts/verify/p0_contract_producer_money_evidence.py",
        "frontend/apps/web/scripts/p0_contract_producer_real_money_decode_test.ts",
    ), (
        "verify.p0_contract_producer.p0a.money",
    )),
    Rule((
        "scripts/verify/frontend_page_contract_boundary_guard.py",
        "scripts/verify/frontend_contract_route_guard.py",
    ), (
        "verify.frontend.page_contract_boundary.guard",
    )),
    Rule((
        "scripts/verify/web_contract_v2_frontend_architecture_guard.py",
    ), (
        "verify.unified_page_contract.v2.web_architecture",
    )),
    Rule((
        "scripts/verify/action_view_contract_action_runtime_smoke.js",
    ), (
        "verify.action_view_runtime_smoke.behavior",
    )),
    Rule((
        "config/contract/page_contract_v1_retirement_manifest.json",
    ), (
        "verify.contract.page_v1_zero_residue.guard",
    )),
    Rule((
        "scripts/verify/frontend_decision_authority.py",
        "scripts/verify/frontend_decision_authority_guard.py",
    ), (
        "verify.frontend.decision_authority.unit",
    )),
    Rule((
        "addons/smart_core/delivery/scene_shell_compiler.py",
        "addons/smart_core/tests/test_scene_shell_compiler.py",
    ), (
        "verify.scene.shell_compiler.unit",
    )),
    Rule((
        "frontend/apps/web/src/app/resolvers/sceneRegistry.ts",
        "frontend/apps/web/scripts/scene_shell_contract_test.ts",
    ), (
        "verify.frontend.scene_shell_contract.unit",
    )),
    Rule((
        "frontend/apps/web/scripts/logger_runtime_test.ts",
        "frontend/apps/web/src/utils/logger.ts",
        "scripts/verify/frontend_console_guard.py",
        "scripts/verify/test_frontend_console_guard.py",
    ), (
        "verify.frontend.console.guard",
    )),
    Rule((
        "frontend/apps/web/src/pages/contractForm/CanonicalActionBar.vue",
        "frontend/apps/web/src/pages/contractForm/ContractFormProductHeader.vue",
        "frontend/apps/web/src/pages/contractForm/professionalWorkflowModel.ts",
        "frontend/apps/web/src/pages/contractForm/workflowReasonTrigger.ts",
        "frontend/apps/web/src/components/design-system/ScDropdown.vue",
        "frontend/apps/web/src/components/design-system/ScPopover.vue",
        "frontend/packages/ui/src/components/primitives/SceneButton.vue",
        "frontend/apps/web/scripts/professional_workflow_model_test.ts",
        "frontend/apps/web/scripts/workflow_reason_trigger_test.ts",
        "frontend/apps/web/scripts/workflow_disabled_reason_browser_test.mjs",
        "scripts/verify/frontend_professional_workflow_guard.py",
        "scripts/verify/test_frontend_professional_workflow_guard.py",
    ), (
        "verify.frontend.professional_workflow.unit",
    )),
    Rule((
        "/app/presentation/businessValuePresentation.ts",
        "/app/presentation/collectionKanbanPresentation.ts",
        "/utils/fieldSemantics.ts",
        "/utils/display.ts",
        "/utils/localizedDisplay.ts",
        "/components/FieldValue.vue",
        "/pages/KanbanPage.vue",
        "/pages/listPage/listCellPresentation.ts",
        "/components/professional-fields/professionalBusinessValueModel.ts",
        "/components/professional-fields/ProfessionalBusinessValueControl.vue",
        "/components/professional-fields/professionalBaseFieldModel.ts",
        "/components/professional-fields/ProfessionalBaseFieldControl.vue",
        "/components/template/FormSection.vue",
        "/components/business/MyWorkApprovalWorkspace.vue",
        "/components/role-home/WorkspaceHome.vue",
        "/components/page/blocks/BlockMetricRow.vue",
        "/app/runtimeTimeZone.ts",
        "/app/contracts/actionViewActivityContract.ts",
        "/pages/ActivityTemplateNode.vue",
        "/components/professional-fields/PaymentSettlementIntroduceDialog.vue",
        "/app/presentation/productMyWorkPresentation.ts",
        "/app/presentation/boqImportPreview.ts",
        "/components/boq/BoqImportPreviewPanel.vue",
        "/components/template/X2ManyRelationRenderer.vue",
        "/pages/contractForm/ContractFormNativeCanvas.vue",
        "/pages/contractForm/RelationSearchDialog.vue",
        "frontend/apps/web/scripts/boq_import_preview_model_test.ts",
        "frontend/apps/web/scripts/duration_business_value_browser_test.mjs",
        "frontend/apps/web/scripts/list_surface_component_test.mjs",
        "frontend/apps/web/scripts/professional_business_value_model_test.ts",
        "scripts/verify/frontend_business_semantics_guard.py",
        "scripts/verify/test_frontend_business_semantics_guard.py",
        "scripts/verify/frontend_localized_display_contract_test.ts",
        "scripts/verify/frontend_collection_status_presentation.test.mjs",
        "scripts/verify/fe_polish_b1_presentation_test.ts",
        "scripts/verify/fe_polish_b1_browser.mjs",
    ), (
        "verify.frontend.business_semantics.unit",
        "verify.frontend.boq_import_preview.unit",
        "verify.frontend.professional_business_value.unit",
        "verify.frontend.canonical_form_presenter.unit",
        "verify.frontend.my_work_approval.guard",
        "verify.frontend.payment_settlement_introduce.amount.unit",
        "verify.frontend.hierarchical_worksheet.unit",
        "verify.frontend.action_surface_renderer_registry.unit",
        "verify.frontend.collection_view_semantics.unit",
        "verify.frontend.collection_kanban_record_card.unit",
        "verify.frontend.collection_row_cell.unit",
        "verify.frontend.standard_collection_composition.unit",
    )),
    Rule((
        "/components/template/FormSection.vue",
        "frontend/apps/web/scripts/relation_heading_component_test.mjs",
    ), (
        "verify.frontend.professional_detail_collection.unit",
    )),
    Rule((
        "scripts/verify/semantic_registry_lint.py",
        "scripts/verify/test_semantic_registry_lint.py",
        "scripts/verify/test_node_component_registry.py",
    ), (
        "verify.semantic.registry.lint",
    )),
    Rule((
        "addons/smart_construction_core/core_extension_contract_normalizers.py",
        "scripts/verify/test_construction_semantic_declarations.py",
    ), (
        "verify.semantic.registry.lint",
    )),
    # FormSection consumes the canonical field presentation contract. The broad
    # template rule contributes primitive/page-pattern suites; these explicit
    # rules add the field-to-section mapper and contract-v2 occurrence behaviour
    # locks. FE-PRODUCT-01's expression target joins this set after that target
    # becomes part of the shared baseline.
    Rule((
        "/components/template/FormSection.vue",
        "/components/template/formSection.mapper.ts",
        "/components/template/formSection.types.ts",
        "/app/presentation/contractFormPresenter.ts",
        "frontend/apps/web/scripts/canonical_form_presenter_test.ts",
    ), (
        "verify.frontend.canonical_form_presenter.unit",
        "verify.frontend.contract_v2_occurrence_authority.unit",
    )),
    # Backend collection tooling has its own offline behaviour locks. Keep it
    # in the existing local planner; this recommendation never authorizes ORM
    # reuse or changes required remote CI. Workflow security must be selected
    # here, rather than first discovering routing failures in final Quick.
    Rule((
        "scripts/ci/backend_impact_plan.py",
        "scripts/ci/test_backend_impact_plan.py",
        "scripts/ci/backend_suite_plan.py",
        "scripts/ci/test_backend_suite_plan.py",
        "scripts/ci/backend_changed_test_coverage.py",
        "scripts/ci/test_backend_changed_test_coverage.py",
        "scripts/ci/backend_test_receipt.py",
        "scripts/ci/test_backend_test_receipt.py",
        "scripts/ci/test_backend_test_suite_dispatch_contract.py",
        "scripts/verify/backend_contract_fact_readback_probe.py",
        "scripts/verify/test_backend_contract_fact_readback_probe.py",
        "scripts/test/test.sh",
        "scripts/ci/enforce_complexity_baseline_lock.py",
        "scripts/ci/test_complexity_baseline_report.py",
        "docs/engineering_convergence/complexity_baseline_lock.json",
        "Dockerfile",
        "docker-compose.test-isolation.yml",
        "scripts/test/dependency_baseline.py",
        "scripts/test/test_dependency_baseline.py",
        ".github/workflows/backend_test_suite.yml",
    ), (
        "verify.ci.workflow.contract",
    )),
    Rule((
        "scripts/ci/backend_iteration_lanes.py",
        "scripts/ci/test_backend_iteration_lanes.py",
        "scripts/ci/test_backend_test_suite_dispatch_contract.py",
    ), (
        "verify.backend_iteration_lanes.unit",
        "verify.ci.workflow.contract",
    )),
    Rule((
        ".github/workflows/backend_test_suite.yml",
        "scripts/verify/github_actions_security_guard.py",
        "scripts/verify/test_github_actions_security_guard.py",
    ), (
        "verify.github_actions.security",
    )),
    Rule(("scripts/dev/local_dev_demo_authority_verify.sh",
          "scripts/dev/local_environment_health.sh",
          "scripts/dev/local_environment_readiness.py",
          "scripts/verify/test_local_environment_readiness.py"), (
        "verify.local.env.readiness.unit",
        "audit.verification.lane_coverage.check",
    )),
    Rule((
        "scripts/release/static_proxy_target.mjs",
        "scripts/release/release_static_server.mjs",
        "scripts/dev/local_dev_candidate_frontend.py",
        "scripts/verify/test_local_dev_candidate_frontend.py",
        "scripts/verify/local_dev_candidate_visual_smoke.mjs",
        "scripts/verify/test_frontend_acceptance_runtime_profile.py",
        "scripts/verify/static_proxy_target_test.mjs",
    ), (
        "verify.local.dev.static_proxy_target.unit",
    )),
    Rule((
        "scripts/dev/changed_odoo_tests.py",
        "scripts/dev/local_test_inputs.py",
        "scripts/dev/run_changed_odoo_tests.py",
        "scripts/verify/test_changed_odoo_tests.py",
        "scripts/verify/test_local_test_inputs.py",
        "scripts/verify/test_run_changed_odoo_tests.py",
    ), (
        "verify.changed.odoo.tests.unit",
    )),
    Rule((
        "scripts/dev/local_test_runner.py",
        "scripts/dev/changed_odoo_tests.py",
        "scripts/verify/test_changed_odoo_tests.py",
        "docker-compose.test-isolation.yml",
        "docker-compose.yml",
        "scripts/verify/test_local_test_runner.py",
        "scripts/verify/test_local_development_lifecycle.py",
        "scripts/test/payment_approval_upgrade_rehearsal.py",
        "scripts/dev/local_dev_product_release_prepare.py",
        "scripts/dev/local_platform_control.py",
        "scripts/dev/local_platform_release_apply.py",
        "config/ops/local_platform_control.v1.json",
        "scripts/verify/test_local_dev_product_release_prepare.py",
        "scripts/verify/test_local_platform_control.py",
    ), (
        "verify.local.development_lifecycle.unit",
    )),
    Rule((
        "scripts/dev/local_dev_frontend_quick.py",
        "scripts/verify/test_local_dev_frontend_quick.py",
    ), (
        "verify.local.dev.frontend.quick.unit",
    )),
    Rule((
        "scripts/verify/local_dev_payment_settlement_component_journey.mjs",
        "scripts/verify/local_dev_payment_settlement_component_journey.sh",
    ), (
        "verify.local.dev.payment_settlement_journey.unit",
    )),
    Rule((
        "addons/smart_core/handlers/api_data_import.py",
        "addons/smart_core/tests/test_api_data_import_mapping.py",
    ), ("verify.smart_core.api_data_import.unit",)),
    Rule((
        "scripts/dev/enterprise_reconstruction.py",
        "scripts/verify/enterprise_reconstruction_browser.mjs",
        "scripts/verify/enterprise_reconstruction_import_browser.mjs",
        "scripts/verify/test_enterprise_reconstruction.py",
    ), (
        "verify.enterprise.reconstruction.unit",
    )),
    Rule((
        "scripts/verify/local_dev_enterprise_configuration_consumer.mjs",
        "scripts/verify/local_dev_enterprise_configuration_consumer.sh",
        "scripts/verify/local_dev_enterprise_configuration_consumer.test.mjs",
    ), (
        "verify.local.dev.enterprise_configuration.consumer.unit",
    )),
    Rule((
        "/views/LoginView.vue",
        "/views/AccountActivationView.vue",
        "/views/PasswordRecoveryView.vue",
    ), (
        "verify.frontend.auth_credential.guard",
        "verify.frontend.auth_surface.guard",
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
    Rule(("/layouts/AppShell.vue", "/layouts/AppShell.css", "/navigation/"), (
        "verify.frontend.navigation_shell.unit",
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
    Rule((
        "/views/SceneView.vue",
        "/app/sceneEntryContract.ts",
        "addons/smart_core/tests/test_scene_provider_target_identity_merge.py",
    ), (
        "verify.frontend.scene_entry_contract.unit",
        "verify.frontend.navigation_shell.unit",
    )),
    Rule((
        "frontend/packages/ui/src/primitive-port/",
        "frontend/apps/web/scripts/primitive_port_",
        "frontend/apps/web/tsconfig.primitive-port.json",
        "scripts/verify/frontend_primitive_port_guard.py",
        "scripts/verify/test_frontend_primitive_port_guard.py",
    ), (
        "verify.frontend.primitive_port.unit",
        "verify.frontend.scene_primitive_adapter.unit",
    )),
    Rule((
        "frontend/apps/web/src/components/design-system/scene-adapter/",
        "frontend/apps/web/scripts/scene_primitive_adapter_",
        "frontend/apps/web/scripts/scene_primitive_text_controls_test.mjs",
        "frontend/apps/web/tsconfig.scene-primitive-adapter.json",
        "scripts/verify/frontend_scene_primitive_adapter_guard.py",
        "scripts/verify/test_frontend_scene_primitive_adapter_guard.py",
    ), (
        "verify.frontend.scene_primitive_adapter.unit",
        "verify.frontend.scene_primitive_contract.behavior",
    )),
    Rule((
        "frontend/apps/web/scripts/scene_primitive_adapter_test.mjs",
    ), (
        "verify.frontend.scene_primitive_contract.behavior",
    )),
    Rule((
        "scripts/verify/frontend_primitive_adapter_guard.py",
        "scripts/verify/test_frontend_primitive_adapter_guard.py",
    ), (
        "verify.frontend.primitive_adapter.unit",
    )),
    Rule(("/components/design-system/", "frontend/packages/ui/"), (
        "verify.frontend.primitive_adapter.unit",
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
    # These views/pages carry a size ratchet that only `style_system.guard`
    # enforces, so a growing file must be routed to it instead of falling
    # through to the generic typecheck fallback.
    Rule((
        "/layouts/AppShell.vue",
        "/pages/ListPage.vue",
        "/pages/ContractFormPage.vue",
        "/pages/ContractFormRoute.vue",
        "/views/ActionView.vue",
        "scripts/verify/line_budgets.py",
    ), (
        "verify.frontend.style_system.guard",
    )),
    Rule((
        "frontend/apps/web/src/pages/ContractFormPage.vue",
        "frontend/apps/web/src/pages/contractForm/intakeAutosave.ts",
        "frontend/apps/web/src/pages/contractForm/useIntakeAutosaveRuntime.ts",
        "frontend/apps/web/src/pages/contractForm/useRecordPageLifecycle.ts",
        "frontend/apps/web/src/pages/contractForm/useRecordFormActions.ts",
        "frontend/apps/web/src/pages/contractForm/useRecordFormState.ts",
        "frontend/apps/web/scripts/intake_autosave_runtime_test.ts",
        "frontend/apps/web/scripts/create_default_hydration_test.ts",
        "frontend/apps/web/scripts/create_record_user_journey_test.ts",
        "frontend/apps/web/scripts/native_attachment_partial_failure_test.mjs",
        "frontend/apps/web/scripts/contract_form_save_failure_recovery_test.ts",
        "frontend/apps/web/scripts/contract_form_dirty_semantics_test.ts",
    ), (
        "verify.frontend.intake_autosave.unit",
        "verify.frontend.create_default_hydration.unit",
        "verify.frontend.create_record_user_journey.unit",
        "verify.frontend.contract_form_save_failure_recovery.unit",
        "verify.frontend.contract_form_dirty_semantics.unit",
        "verify.frontend.contract_basis.unit",
    )),
    Rule((
        "addons/smart_construction_core/services/contract_governance_overrides.py",
        "addons/smart_construction_core/tests/test_project_intake_contract_governance.py",
    ), (
        "verify.project_intake.contract_governance.unit",
        "verify.intake_autosave.contract.unit",
    )),
    Rule((
        "addons/smart_construction_core/migrations/17.0.0.183/post-migrate.py",
        "addons/smart_construction_core/tests/test_locked_menu_policy_initialization.py",
    ), (
        "verify.smart_construction_core.close_03.preview_promotion.orm",
    )),
    Rule((
        "addons/smart_construction_core/tests/test_project_initiation_native_lowcode.py",
    ), (
        "verify.project_intake.contract_governance.unit",
    )),
    Rule((
        "scripts/ops/test_promote_product_ten_center_policy.py",
    ), (
        "verify.product.menu.contract_v1.guard",
    )),
    Rule((
        "scripts/verify/close_03_intake_autosave_samples.mjs",
        "scripts/verify/close_03_intake_autosave_samples_validate.py",
    ), (
        "verify.backend.close_03.intake_autosave.samples",
    )),
    Rule((
        "scripts/verify/close_03_project_intake_browser.mjs",
    ), (
        "verify.intake_autosave.contract.unit",
    )),
    Rule((
        "scripts/verify/local_dev_native_projection_audit.py",
        "scripts/verify/test_local_dev_native_projection_audit.py",
    ), (
        "verify.local.dev.native_projection.audit.unit",
    )),
    Rule((
        "scripts/verify/product_menu_contract_v1_guard.py",
        "scripts/verify/test_product_menu_contract_v1_guard.py",
    ), (
        "verify.product.menu.contract_v1.guard",
    )),
    Rule((
        "addons/smart_construction_core/views/menu_product_contract_completion_v1.xml",
        "addons/smart_construction_core/views/menu_product_navigation_v2.xml",
        "addons/smart_construction_core/views/menu_product_primary_center_candidate_v1.xml",
        "addons/smart_construction_core/views/menu_product_project_wave1.xml",
    ), (
        "verify.product.menu.runtime_closeout.guard",
    )),
    Rule((
        "config/ops/local-platform-empty-addons/.gitkeep",
    ), (
        "verify.local.development_lifecycle.unit",
    )),
    Rule((
        "config/product_menu_release_manifest_v2.json",
        "scripts/verify/product_menu_release_manifest_v2_guard.py",
    ), (
        "verify.product.menu.contract_v1.guard",
        "verify.product.primary_center.baseline.guard",
    )),
    Rule((
        "scripts/verify/product_primary_center_baseline_guard.py",
    ), (
        "verify.product.primary_center.baseline.guard",
    )),
    Rule((
        "scripts/verify/product_primary_center_candidate_guard.py",
    ), (
        "verify.product.primary_center.candidate.guard",
    )),
    Rule((
        "scripts/verify/scenario_seed_runtime_readback.py",
    ), (
        "verify.nav01.native_authority.unit",
    )),
    Rule((
        "config/product_scenario_organization_v1.json",
        "addons/smart_construction_core/migrations/17.0.0.186/post-migrate.py",
        "addons/smart_construction_core/migrations/17.0.0.187/post-migrate.py",
        "scripts/audit/build_scenario_product_organization.py",
        "scripts/audit/test_build_scenario_product_organization.py",
    ), (
        "verify.product.scenario.organization.unit",
    )),
    Rule((
        "frontend/apps/web/src/pages/ContractFormRoute.vue",
        "frontend/apps/web/src/pages/contractFormRouteLoader.ts",
        "frontend/apps/web/src/app/performance/startupTiming.ts",
        "frontend/apps/web/scripts/startup_performance_test.ts",
        "frontend/apps/web/scripts/record_deep_link_evidence.mjs",
        "frontend/apps/web/scripts/record_deep_link_evidence.d.mts",
        "scripts/verify/local_dev_dev_acceptance_remediation_browser.mjs",
        "scripts/verify/local_dev_runtime_performance_browser.sh",
    ), (
        "verify.frontend.startup_performance.unit",
        "verify.frontend.dev_acceptance_remediation.unit",
    )),
    # ActionView 的 surface 展示形态与列表分页声明都由契约投影消费；改动入口视图
    # 或两个消费运行时都要跑对应行为锁，否则契约消费回归只能在部署面上暴露。
    Rule((
        "/views/ActionView.vue",
        "/app/action_runtime/useActionViewSelectionActionRuntime.ts",
        "/app/runtime/actionViewSelectionExportRuntime.ts",
        "/app/runtime/actionViewBatchRuntime.ts",
        "frontend/apps/web/scripts/action_view_selection_feedback_test.ts",
        "/app/runtime/actionViewInteractionRuntime.ts",
        "frontend/apps/web/scripts/action_view_collection_create_authority_test.ts",
        "scripts/verify/frontend_action_view_page_actions_guard.py",
        "scripts/verify/test_frontend_action_view_page_actions_guard.py",
        "/app/runtime/actionViewSurfaceGateRuntime.ts",
        "/app/runtime/actionViewListPageSizeRuntime.ts",
    ), (
        "verify.frontend.action_view_page_actions.unit",
        "verify.frontend.action_view_surface_gate_runtime.unit",
        "verify.frontend.action_view_page_size_runtime.unit",
        "verify.frontend.action_view_selection_feedback.unit",
        "verify.frontend.contract_basis.unit",
        "verify.frontend.style_system.guard",
    )),
    # 契约基础台账与它的守卫是 contract_basis 行为锁的直接输入。改台账/守卫
    # 却落到「未映射」会让这份完整性缺口只能靠人工挑目标，甚至漏跑到交付冻结。
    Rule((
        "scripts/verify/identity_architecture_audit_guard.py",
        "scripts/verify/test_identity_architecture_audit_guard.py",
    ), (
        "verify.identity.architecture.audit.unit",
    )),
    Rule((
        "docs/architecture/frontend_contract_basis_ledger.json",
        "scripts/verify/frontend_contract_basis_guard.py",
        "scripts/verify/test_frontend_contract_basis_guard.py",
    ), (
        "verify.frontend.contract_basis.unit",
        "verify.frontend.contract_basis.enforce",
    )),
    # The remediation plan, its audit matrix and Guard catalog are one
    # planning-only executable contract. Changes to either implementation or
    # declaration files must run the plan guard instead of relying on the
    # non-source documentation exemption.
    Rule((
        "docs/audit/fe_contract_fidelity_01/matrix.json",
        "docs/architecture/fe_contract_fidelity_02_remediation_plan.md",
        "docs/architecture/fe_contract_fidelity_02/remediation_plan.json",
        "docs/architecture/fe_contract_fidelity_02/guard_catalog.json",
        "scripts/verify/contract_fidelity_plan_guard.py",
        "scripts/verify/test_contract_fidelity_plan_guard.py",
    ), (
        "verify.frontend.contract_fidelity.plan.unit",
    )),
    Rule((
        "addons/smart_core/core/contract_version_compatibility.py",
        "scripts/verify/test_contract_version_compatibility.py",
    ), (
        "verify.frontend.contract_fidelity.plan.unit",
    )),
    # Guard registry rows and their audit implementation are one executable
    # contract. A disposition-only fix must run the full registry audit instead
    # of falling through as an unmapped verification-tool path.
    Rule((
        "scripts/verify/registry.yaml",
        "scripts/verify/guard_registry_audit.py",
        "scripts/verify/test_guard_registry_audit.py",
        "make/guards.mk",
    ), (
        "verify.guard.registry",
    )),
    # The P4-00 inventory generator, its tests and its discoverability entry
    # are one audit-only contract. They do not enter a required product gate,
    # but must route to their own non-zero unit check instead of becoming an
    # unmapped development path.
    Rule((
        "scripts/audit/generate_change_impact_verification_inventory.py",
        "scripts/audit/test_generate_change_impact_verification_inventory.py",
        "make/help.mk",
    ), (
        "verify.change_impact.verification.unit",
        "verify.change_impact.acceptance",
    )),
    Rule((
        "scripts/ops/change_impact_planner.py",
        "scripts/ops/change_impact_graph.py",
        "scripts/ops/change_impact_evidence.py",
        "scripts/ops/change_impact_acceptance.py",
        "scripts/ops/test_change_impact_planner.py",
        "scripts/ops/test_change_impact_graph.py",
        "scripts/ops/test_change_impact_evidence.py",
        "scripts/ops/typescript_change_facts.mjs",
    ), (
        "verify.change_impact.plan.unit",
        "verify.change_impact.acceptance",
    )),
    Rule((
        "scripts/verify/backend_authority_closure_guard.py",
        "scripts/verify/test_backend_authority_closure_guard.py",
    ), (
        "verify.backend.authority_closure.unit",
    )),
    Rule((
        "addons/smart_core/security/intent_authorization.py",
        "addons/smart_core/core/base_handler.py",
        "addons/smart_core/tests/test_base_handler_type_error.py",
        "addons/smart_core/tests/test_intent_permission_operation_policy.py",
    ), (
        "verify.intent_group.authorization.unit",
    )),
    Rule((
        "addons/smart_core/handlers/permission_check.py",
        "addons/smart_core/tests/test_permission_check_debug_boundary.py",
    ), (
        "verify.permission_check.availability.unit",
    )),
    Rule((
        "addons/smart_construction_core/handlers/my_work_complete.py",
        "addons/smart_construction_core/handlers/payment_request_approval.py",
        "addons/smart_construction_core/handlers/payment_request_execute.py",
        "addons/smart_construction_core/handlers/payment_request_settlement_introduce.py",
        "addons/smart_construction_core/handlers/risk_action_execute.py",
        "addons/smart_construction_core/tests/test_payment_domain_permission_isolation.py",
    ), (
        "verify.payment.authorization_boundary.orm",
    )),
    Rule((
        "addons/smart_construction_core/handlers/product_system_parameter_catalog.py",
        "addons/smart_construction_core/handlers/product_system_parameter_change.py",
    ), (
        "verify.product_system_parameter_catalog",
    )),
    Rule((
        "scripts/verify/test_capability_identity_boundary.py",
        "addons/smart_core/delivery/capability_service.py",
        "addons/smart_core/delivery/product_policy_catalog_sync_service.py",
        "addons/smart_construction_core/core_extension_capability_rows.py",
        "addons/smart_construction_core/models/support/product_policy_sync.py",
        "addons/smart_construction_core/services/product_capability_admission.py",
        "addons/smart_construction_core/services/capability_registry.py",
        "addons/smart_construction_core/services/product_menu_source.py",
    ), (
        "verify.capability.identity_boundary.unit",
    )),
    Rule((
        "addons/smart_construction_core/tests/test_capability_registry_service.py",
        "addons/smart_construction_core/tests/test_product_policy_fact_authority.py",
        "addons/smart_construction_core/tests/test_locked_menu_policy_initialization.py",
        "addons/smart_construction_core/migrations/17.0.0.182/post-migrate.py",
    ), (
        "verify.capability.identity_boundary.orm",
    )),
    Rule((
        "addons/smart_core/delivery/product_center_policy.py",
        "addons/smart_core/delivery/product_policy_normalization.py",
        "addons/smart_construction_core/services/product_center_policy.py",
        "addons/smart_construction_core/services/product_menu_source.py",
        "addons/smart_construction_core/data/product_primary_center_baseline_v1.json",
        "config/product_primary_center_baseline_v1.json",
        "config/product_menu_contract_v1.json",
        "addons/smart_construction_core/data/formal_business_product_menu_policy_v1.json",
        "addons/smart_construction_core/data/formal_business_product_menu_policy_v1.json.sha256",
        "scripts/verify/baselines/formal_business_product_menu_policy_v1.json",
        "scripts/verify/baselines/formal_business_product_menu_policy_v1.json.sha256",
        "scripts/verify/test_product_center_policy.py",
        "scripts/ops/promote_product_ten_center_policy.py",
    ), (
        "verify.product_center.policy.unit",
    )),
    Rule((
        "addons/smart_core/delivery/release_operator_read_model_service.py",
        "addons/smart_core/delivery/edition_release_snapshot_service.py",
        "addons/smart_core/delivery/product_center_policy.py",
        "addons/smart_core/delivery/product_policy_normalization.py",
        "addons/smart_core/handlers/release_operator.py",
    ), (
        "verify.product_center.policy.unit",
    )),
    Rule((
        "addons/smart_construction_core/models/support/product_scenario.py",
        "addons/smart_construction_core/services/product_center_policy.py",
        "config/product_primary_center_baseline_v1.json",
        "addons/smart_construction_core/migrations/17.0.0.184/post-migrate.py",
        "addons/smart_construction_core/tests/test_product_policy_fact_authority.py",
        "addons/smart_construction_core/tests/test_locked_menu_policy_initialization.py",
    ), (
        "verify.product_center.policy.unit",
        "verify.product_center.policy.orm",
    )),
    Rule((
        "addons/smart_construction_core/security/sc_role_entry_groups.xml",
        "addons/smart_construction_core/security/sc_discover_entry_groups.xml",
        "addons/smart_construction_core/security/sc_entry_groups.xml",
        "addons/smart_construction_core/security/sc_role_groups.xml",
        "addons/smart_construction_core/tests/test_business_category_entry_policy.py",
        "scripts/verify/role_capability_group_authority_guard.py",
        "scripts/verify/test_role_capability_group_authority_guard.py",
    ), (
        "verify.role_capability_group_authority.unit",
        "verify.frontend.navigation_shell.unit",
        "verify.role_surface.landing.contract.unit",
    )),
    Rule((
        "addons/smart_construction_core/data/menu_entry_group_rebinding.json",
        "docs/product/frontend_business_entry_acceptance_v1.csv",
    ), (
        "verify.role_capability_group_authority.unit",
        "verify.frontend.business_entry.matrix.universe",
    )),
    Rule((
        "addons/smart_construction_core/data/formal_business_product_menu_policy_v1.json",
        "addons/smart_construction_core/data/formal_business_product_menu_policy_v1.json.sha256",
        "config/product_menu_contract_v1.json",
        "scripts/verify/baselines/formal_business_product_menu_policy_v1.json",
        "scripts/verify/baselines/formal_business_product_menu_policy_v1.json.sha256",
    ), (
        "verify.product.menu.contract_v1.guard",
    )),
    Rule((
        "addons/smart_construction_core/views/menu_product_administration_wave1.xml",
        "scripts/verify/product_administration_center_wave1_guard.py",
        "scripts/verify/test_product_administration_center_wave1_guard.py",
    ), (
        "verify.product.administration_center.wave1.guard",
    )),
    Rule((
        "addons/smart_construction_core/models/support/scene_orchestration.py",
        "addons/smart_construction_core/tests/test_scene_publish_usage_backend.py",
    ), (
        "verify.scene.publication_authority.orm",
    )),
    Rule((
        "addons/smart_construction_core/data/view_orchestration_form_section_contract_data.xml",
    ), (
        "verify.page.finalize.authority.orm",
    )),
    Rule((
        "addons/smart_construction_core/core_extension.py",
        "addons/smart_construction_core/tests/test_core_extension_v2_finalize.py",
    ), (
        "verify.page.finalize.authority.orm",
        "verify.page.project_finalize.authority.orm",
    )),
    Rule((
        "addons/smart_construction_core/services/project_native_view_widget_payload_service.py",
        "addons/smart_construction_core/tests/test_project_native_view_widget_payload_service.py",
    ), (
        "verify.frontend.node_component.unit",
        "verify.frontend.node_component.component",
    )),
    Rule((
        "addons/smart_core/delivery/edition_release_snapshot_service.py",
        "addons/smart_core/delivery/product_scene_composition.py",
        "addons/smart_core/tests/test_release_preflight_target_validation.py",
    ), (
        "verify.daily.published_face.target.unit",
    )),
    Rule((
        "addons/smart_core/delivery/menu_service.py",
        "addons/smart_core/tests/test_delivery_menu_entry_target.py",
    ), (
        "verify.backend.navigation_delivery.unit",
        "verify.workspace.entry_authority.orm",
    )),
    Rule((
        "addons/smart_construction_bundle/tests/test_workspace_role_routes.py",
        "addons/smart_construction_bundle/tests/test_company_project_refund_workspace.py",
        "addons/smart_construction_bundle/tests/test_current_account_workspace.py",
        "addons/smart_construction_bundle/tests/test_team_loan_deduction_workspace.py",
    ), (
        "verify.workspace.entry_authority.orm",
    )),
    # 规划器自身的代码与它推荐的 make 目标定义是同一份契约：改规划器或改
    # make/frontend.mk 的目标名都要跑规划器自己的行为锁，否则「目标名漂移」会
    # 让最小复用变成 make 直接报错，又退回人工全量。
    Rule((
        "scripts/verify/frontend_dev_incremental.py",
        "scripts/verify/test_frontend_dev_incremental.py",
        "scripts/verify/test_incremental_environment.py",
        "scripts/ops/incremental_execution.py",
        "make/frontend.mk",
    ), (
        "verify.frontend.dev.incremental.unit",
    )),
    Rule((
        "scripts/ops/agent_run_context.py",
        "scripts/ops/generated_evidence_paths.py",
        "scripts/verify/test_agent_run_context.py",
    ), (
        "verify.agent.resume.unit",
    )),
    Rule((
        "scripts/ops/safe_branch_sync_main.py",
        "scripts/ops/generated_evidence_paths.py",
        "scripts/ops/test_safe_branch_sync_main.py",
    ), (
        "verify.workspace.branch.sync-main",
    )),
    Rule((
        "scripts/ops/gitee_published_branch_sync.py",
        "scripts/ops/github_published_branch_sync.py",
        "scripts/ops/test_gitee_published_branch_sync.py",
        "scripts/ops/test_github_published_branch_sync.py",
    ), (
        "verify.workspace.branch.sync-github.unit",
    )),
    Rule((
        "scripts/ops/branch_cleanup_safe.sh",
        "scripts/ops/test_safe_worktree_cleanup.py",
    ), (
        "verify.workspace.worktree.guard",
    )),
    Rule((
        "scripts/verify/baseline_iteration_execution_policy_guard.py",
        "scripts/verify/test_baseline_iteration_execution_policy_guard.py",
    ), (
        "verify.baseline.iteration.execution.policy",
    )),
    Rule((
        "make/codex.mk",
        "scripts/verify/test_pr_publish_preflight.py",
    ), (
        "verify.pr.push.unit",
    )),
    Rule((
        "make/codex.mk",
        "scripts/ops/pr_review_submit.py",
        "scripts/ops/test_pr_review_submit.py",
    ), (
        "verify.pr.review.unit",
    )),
    Rule((
        "scripts/ci/secret_scan.py",
        "scripts/ci/personal_data_scan.py",
        "scripts/ci/trusted_scan_scope.py",
        "scripts/ci/test_trusted_scan_scope.py",
        "scripts/verify/repository_clean_history_guard.py",
    ), (
        "verify.trusted_scan.unit",
    )),
    Rule((
        "scripts/verify/repository_clean_history_guard.py",
        "scripts/verify/test_repository_clean_history_guard.py",
    ), (
        "verify.repository.clean_history.unit",
    )),
    # The exact-head receipt verifier and both sides of its regression suite
    # are one executable contract. The consistency entry runs the verifier
    # tests and the branch-policy lock together, so this P4 input cannot fall
    # through as an unmapped path and lose its non-zero L2 execution.
    Rule((
        "scripts/ops/local_quick_evidence.py",
        "scripts/ops/test_local_quick_evidence.py",
        "scripts/verify/test_local_quick_evidence.py",
    ), (
        "verify.branch.governance.consistency",
    )),
    Rule((
        "scripts/ops/integration_cycle.py",
        "scripts/ops/test_integration_cycle.py",
    ), (
        "verify.integration.cycle.unit",
    )),
    Rule((
        "scripts/ops/quick_input_scope.py",
        "scripts/ops/test_quick_input_scope.py",
    ), (
        "verify.quick.input_scope.unit",
    )),
    Rule((
        "scripts/verify/construction_core_extension_policy_maps_split_guard.py",
        "scripts/verify/test_construction_core_extension_policy_maps_split_guard.py",
    ), (
        "verify.construction.policy_maps.unit",
    )),
    Rule((
        "scripts/verify/construction_core_extension_capability_rows_split_guard.py",
        "scripts/verify/construction_core_extension_contract_normalizers_split_guard.py",
        "scripts/verify/construction_core_extension_responsibility_map_guard.py",
        "docs/engineering_convergence/construction_core_extension_responsibility_map.md",
    ), (
        "verify.contract.architecture.suite",
    )),
    # The baseline-backed iteration policy guard is the authority for the
    # governed make lanes: it asserts that each lane still declares the targets
    # the execution policy depends on. Editing one of those lanes without
    # re-running it let a changed entry point go unchecked, and the lane was
    # reported as an unmapped path that demanded a hand-picked L2 target.
    Rule((
        "make/codex.mk",
        "make/runtime_ops.mk",
        "make/dev.mk",
        "make/ci.mk",
    ), (
        "verify.baseline.iteration.execution.policy",
    )),
    Rule((
        "scripts/dev/candidate_runtime_identity.py",
        "scripts/verify/test_candidate_runtime_identity.py",
        "scripts/verify/test_frontend_acceptance_candidate_guards.py",
    ), (
        "verify.candidate.profile.unit",
    )),
    Rule((
        "make/runtime_ops.mk",
        "scripts/dev/frontend_cached_dependencies_restore.sh",
        "scripts/dev/frontend_standard_preview.py",
        "scripts/dev/frontend_acceptance_runtime.sh",
        "scripts/dev/frontend_acceptance_up.sh",
        "scripts/test/frontend_productization_fixture.sh",
        "scripts/verify/frontend_menu_navigation_diagnostic.py",
        "scripts/verify/frontend_my_work_approval_browser.mjs",
        "scripts/verify/frontend_my_work_approval_runtime.py",
        "scripts/verify/frontend_my_work_approval_runtime_ids.py",
        "scripts/verify/contract_form_side_effect_regression_guard.py",
        "scripts/verify/test_frontend_release_local_entry.py",
        "scripts/verify/test_frontend_standard_preview.py",
    ), (
        "verify.frontend.standard_preview.unit",
    )),
    Rule((
        "scripts/db/create.sh",
        "scripts/test/frontend_acceptance_db_ensure.sh",
    ), (
        "verify.frontend.acceptance.db_preparation.unit",
    )),
    Rule((
        "scripts/verify/frontend_my_work_approval_guard.py",
    ), (
        "verify.frontend.my_work_approval.guard",
    )),
    Rule((
        "scripts/verify/frontend_product_page_header_guard.py",
        "scripts/verify/test_frontend_product_page_header_guard.py",
        "frontend/apps/web/src/components/product-page-header/ProductPageHeader.vue",
        "frontend/apps/web/src/app/activityPageTitle.ts",
        "frontend/apps/web/src/router/index.ts",
        "frontend/apps/web/src/views/SceneContractBlockGridView.vue",
        "frontend/apps/web/src/views/SceneView.vue",
        "frontend/apps/web/src/views/MyWorkView.vue",
        "frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts",
    ), (
        "verify.frontend.product_page_header.unit",
    )),
    Rule((
        "frontend/apps/web/scripts/dev_acceptance_remediation_test.ts",
    ), (
        "verify.frontend.dev_acceptance_remediation.unit",
        "verify.frontend.product_page_header.unit",
    )),
    Rule((
        "scripts/verify/frontend_delivery_hardening_guard.py",
        "scripts/verify/role_capability_group_authority_guard.py",
        "scripts/verify/test_frontend_delivery_hardening_guard.py",
        "scripts/verify/error_state_component_test.cjs",
        "addons/smart_construction_core/views/core/settlement_views.xml",
        "frontend/apps/web/src/components/StatusPanel.vue",
        "frontend/apps/web/src/pages/ContractFormRoute.vue",
        "frontend/apps/web/src/pages/contractFormRouteLoader.ts",
        "frontend/apps/web/src/App.vue",
        "frontend/apps/web/src/app/activityPageCacheIdentity.ts",
    ), (
        "verify.frontend.delivery_hardening.guard",
    )),
    Rule((
        "scripts/verify/frontend_authenticated_intent.mjs",
    ), (
        "verify.frontend.delivery_hardening.guard",
        "verify.frontend.standard_preview.unit",
    )),
    Rule((
        "scripts/verify/frontend_delivery_hardening_browser.mjs",
        "scripts/verify/test_frontend_delivery_hardening_guard.py",
    ), (
        "verify.frontend.standard_preview.unit",
        "verify.frontend.delivery_hardening.guard",
    )),
    Rule((
        "scripts/verify/frontend_payment_request_workflow_browser.mjs",
    ), (
        "verify.frontend.canonical_form_presenter.unit",
        "verify.frontend.product_page_header.unit",
    )),
    Rule((
        "addons/smart_construction_acceptance_fixture/tools/frontend_productization_fixture.py",
        "addons/smart_construction_acceptance_fixture/tests/__init__.py",
        "addons/smart_construction_acceptance_fixture/tests/test_business_scene_lifecycle.py",
        "addons/smart_construction_acceptance_fixture/tests/test_fixture_scenario_identity.py",
        "addons/smart_construction_acceptance_fixture/tests/test_scenario_navigation_maintenance.py",
        "scripts/verify/test_daily_acceptance_fixture_lane.py",
        "scripts/ops/dev_acceptance_release_probe.py",
    ), (
        "verify.daily_dev.acceptance_fixture.unit",
    )),
    Rule(("/pages/contractForm/", "/components/template/", "/app/presentation/contractFormPresenter.ts"), (
        "verify.frontend.canonical_form_presenter.unit",
        "verify.frontend.primitive_adapter.unit",
        "verify.frontend.product_page_pattern.unit",
        "verify.frontend.page_pattern_reference_parity.unit",
        # `useRecord*.ts` carry their own size ratchet in style_system.guard.
        "verify.frontend.style_system.guard",
    )),
    Rule(("/components/action/", "/components/product-list/"), (
        "verify.frontend.collection_action_toolbar.unit",
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
    Rule((
        "scripts/verify/frontend_page_pattern_reference_parity_guard.py",
        "scripts/verify/test_frontend_page_pattern_reference_parity_guard.py",
    ), (
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
    # The business-entry matrix shares one pure model, one scope adapter and one
    # reuse engine. A change to any of them moves the derivation or the reuse
    # decision, so route all of them to the engine unit test instead of letting
    # the matrix scripts fall through to the typecheck fallback.
    # The released list-surface acceptance probe carries a contract lock: editing the
    # probe without running its lock let a stale assertion survive until the daily
    # lane failed. Route the probe and its lock to the same non-zero unit target.
    Rule((
        "scripts/verify/frontend_list_surface_structure_browser.mjs",
        "scripts/verify/test_frontend_list_surface_search_contract.py",
    ), (
        "verify.frontend.list_surface_search_contract.unit",
    )),
    Rule((
        "scripts/verify/frontend_collection_row_cell_guard.py",
        "scripts/verify/test_frontend_collection_row_cell_guard.py",
    ), (
        "verify.frontend.collection_row_cell.unit",
    )),
    Rule((
        "scripts/verify/frontend_collection_aggregate_footer_guard.py",
        "scripts/verify/test_frontend_collection_aggregate_footer_guard.py",
    ), (
        "verify.frontend.collection_aggregate_footer.unit",
    )),
    Rule((
        "scripts/verify/frontend_list_optional_columns_contract_test.ts",
    ), (
        "verify.frontend.list_optional_columns.unit",
    )),
    Rule((
        "scripts/verify/local_dev_capability_",
        "scripts/verify/test_local_dev_capability_tooling.py",
    ), (
        "verify.local.dev.capability.tooling.unit",
    )),
    Rule((
        "scripts/verify/business_entry_matrix_",
        "scripts/verify/business_entry_negative_closures.mjs",
        "scripts/verify/released_navigation_target.mjs",
        "scripts/ops/evidence_scope.py",
        # The focused behaviour tests are part of the same contract: editing the
        # entry's tests without running them let the suite that locks the reuse
        # decision fall through to the generic typecheck fallback.
        "scripts/verify/test_business_entry_matrix_incremental.py",
        "scripts/verify/test_business_entry_matrix_",
        "scripts/verify/business_entry_matrix_scope_seed.py",
    ), (
        "verify.frontend.business_entry.evidence_scope.unit",
    )),
    Rule((
        "scripts/ops/acceptance_business_scene_enablement_reconcile.py",
        "scripts/verify/test_acceptance_business_scene_enablement_reconcile.py",
    ), (
        "verify.acceptance.business_scenes.reconcile.unit",
    )),
    Rule((
        "config/frontend/probe_toolchain_registry.json",
        "scripts/verify/local_dev_project_profile_write_browser.mjs",
        "scripts/verify/local_dev_project_profile_write_browser.sh",
        "scripts/verify/local_dev_project_profile_write_contract.mjs",
        "scripts/verify/local_dev_project_profile_write_contract.test.mjs",
        "scripts/verify/test_local_dev_project_profile_write_fixture.py",
        "scripts/verify/frontend_probe_toolchain_guard.py",
        "scripts/verify/test_frontend_probe_toolchain_guard.py",
    ), (
        "verify.local.dev.project_profile_write.unit",
    )),
    Rule((
        "scripts/ops/dev_acceptance_release_probe.py",
        "scripts/verify/test_dev_acceptance_release_identity.py",
    ), (
        "verify.frontend.acceptance.environment.guard",
    )),
    Rule((
        "config/security/secret_scan_false_positives.v1.json",
    ), (
        "security.secrets.scan",
    )),
    Rule((
        "addons/smart_construction_core/__init__.py",
        "addons/smart_construction_core/core_extension.py",
        "addons/smart_construction_core/services/capability_registry.py",
        "addons/smart_construction_core/tests/test_capability_registry_service.py",
        "addons/smart_construction_scene/services/capability_scene_targets.py",
        "addons/smart_core/core/capability_provider.py",
        "addons/smart_core/utils/extension_hooks.py",
    ), (
        "verify.daily.permission_truth.capability.orm",
    )),
    Rule((
        "addons/smart_construction_scene/tests/test_scene_registry_yaml_asset_merge.py",
    ), (
        "verify.navigation.publication_consumers.unit",
    )),
    Rule((
        "addons/smart_construction_scene/models/product_policy.py",
        "addons/smart_construction_scene/tests/test_tenant_scene_activation.py",
    ), (
        "verify.navigation.publication_consumers.unit",
        "verify.daily.permission_truth.capability.orm",
    )),
    Rule((
        "addons/smart_construction_scene/handlers/scenario_activation.py",
        "addons/smart_construction_scene/services/tenant_scene_activation.py",
        "addons/smart_construction_scene/services/scenario_activation_catalog.py",
        "addons/smart_construction_scene/tests/test_admin_close_01_platform_to_enterprise.py",
    ), (
        "verify.navigation.publication_consumers.unit",
        "verify.daily.permission_truth.capability.orm",
        "verify.admin_close_01.runtime.orm",
    )),
    Rule((
        "addons/smart_construction_core/core_extension_policy_maps.py",
        "addons/smart_construction_core/core_extension_actor_roles.py",
        "addons/smart_construction_core/data/formal_business_product_menu_policy_v1.json",
        "addons/smart_construction_core/data/formal_business_product_menu_policy_v1.json.sha256",
        "addons/smart_construction_core/data/product_menu_source.json",
        "addons/smart_construction_core/security/sc_capability_groups.xml",
        "addons/smart_construction_core/tests/test_role_surface_project_member.py",
        "addons/smart_construction_core/views/support/business_config_workbench_views.xml",
        "addons/smart_construction_core/views/support/enterprise_initialization_views.xml",
        "addons/smart_construction_core/views/support/my_work_views.xml",
        "addons/smart_core/views/ui_menu_config_policy_views.xml",
        "config/frontend/role_surface_exposure_declarations_v1.json",
        "scripts/verify/role_surface_exposure_declaration_guard.py",
        "scripts/verify/role_capability_group_authority_guard.py",
        "scripts/release/test_locked_menu_policy_contract.py",
        "scripts/verify/baselines/formal_business_product_menu_policy_v1.json",
        "scripts/verify/baselines/formal_business_product_menu_policy_v1.json.sha256",
        "scripts/verify/test_role_surface_exposure_declaration_guard.py",
    ), (
        "verify.role_capability_group_authority.unit",
        "verify.role_surface.landing.contract.unit",
        "verify.frontend.role_surface_exposure_declaration.guard",
        "verify.frontend.navigation_policy.unit",
        "verify.workflow_action_semantics.guard",
    )),
    Rule((
        "addons/smart_construction_scene/tests/__init__.py",
        "addons/smart_construction_scene/tests/test_company_route_scope_cache.py",
    ), (
        "verify.scene.company_route_scope_cache.orm",
    )),
    Rule((
        "addons/smart_construction_core/models/support/product_scenario.py",
        "addons/smart_construction_core/data/product_scenario_seed.xml",
        "addons/smart_construction_core/data/scenario_product_surface.json",
        "addons/smart_construction_core/services/scenario_product_declarations.py",
        "addons/smart_construction_core/migrations/17.0.0.180/pre-migrate.py",
        "addons/smart_construction_core/migrations/17.0.0.181/pre-migrate.py",
        "addons/smart_construction_core/tests/test_scenario_direct_entry_initialization.py",
    ), (
        "verify.daily.permission_truth.capability.orm",
        "verify.navigation.publication_consumers.unit",
        "verify.scenario.center_projection.guard",
    )),
    Rule((
        "addons/smart_construction_core/migrations/17.0.0.180/pre-migrate.py",
        "addons/smart_construction_core/migrations/17.0.0.181/pre-migrate.py",
        "addons/smart_construction_core/tests/test_scenario_direct_entry_initialization.py",
    ), (
        "verify.smart_construction_core.migration_compatibility.orm",
    )),
    Rule((
        "addons/smart_core/app_config_engine/services/dispatchers/nav_dispatcher.py",
        "addons/smart_core/delivery/product_center_policy.py",
        "addons/smart_core/delivery/product_policy_service.py",
        "addons/smart_construction_core/services/scenario_surface_projection.py",
    ), ("verify.navigation.projection.orm",)),
    Rule((
        "addons/smart_construction_core/services/scenario_surface_projection.py",
        "addons/smart_construction_core/services/scenario_product_declarations.py",
        "addons/smart_core/core/navigation_identity.py",
        "scripts/verify/scenario_center_projection_guard.py",
        "scripts/verify/scenario_surface_projection_guard.py",
        "scripts/verify/scene_fact_data_boundary_guard.py",
    ), (
        "verify.navigation.publication_consumers.unit",
        "verify.scenario.center_projection.guard",
    )),
    Rule((
        "addons/smart_construction_core/views/menu_product_configuration_wave1.xml",
    ), (
        "verify.product.configuration_center.wave1.guard",
        "verify.product.menu.contract_v1.guard",
        "verify.navigation.publication_consumers.unit",
    )),
    Rule((
        "scripts/verify/frontend_state_presentation_guard.py",
        "scripts/verify/test_frontend_state_presentation_guard.py",
    ), (
        "verify.frontend.state_dashboard.unit",
    )),
    Rule((
        "addons/smart_core/core/navigation_identity.py",
        "addons/smart_core/core/scene_nav_contract_builder.py",
        "addons/smart_core/tests/test_scene_nav_contract_builder.py",
    ), (
        "verify.nav01.native_authority.unit",
    )),
    Rule((
        "addons/smart_construction_scene/__init__.py",
        "addons/smart_construction_scene/core_extension.py",
        "addons/smart_construction_scene/data/project_management_scene.xml",
        "addons/smart_construction_scene/data/sc_scene_finance_payment_ledger.xml",
        "addons/smart_construction_scene/data/sc_scene_layout.xml",
        "addons/smart_construction_scene/data/sc_scene_list_profile.xml",
        "addons/smart_construction_scene/data/sc_scene_orchestration.xml",
        "addons/smart_construction_scene/data/sc_scene_tiles.xml",
        "addons/smart_construction_scene/models/__init__.py",
        "addons/smart_construction_scene/profiles/project_dashboard_scene_content.py",
        "addons/smart_construction_scene/profiles/scene_registry_content.py",
        "addons/smart_construction_scene/scene_registry.py",
        "addons/smart_construction_scene/services/business_scene_enablement.py",
        "addons/smart_construction_scene/tests/test_action_only_scene_semantic_supply.py",
    ), (
        "verify.daily.permission_truth.capability.orm",
        "verify.navigation.publication_consumers.unit",
        "verify.scenario.center_projection.guard",
    )),
    Rule((
        "addons/smart_construction_core/__manifest__.py",
        "addons/smart_construction_core/migrations/17.0.0.179/",
        "addons/smart_construction_core/views/support/product_scenario_views.xml",
    ), (
        "verify.daily.permission_truth.capability.orm",
        "verify.scenario.center_projection.guard",
    )),
    Rule((
        "scripts/verify/frontend_acceptance_login_probe.py",
        "scripts/verify/test_frontend_acceptance_login_probe.py",
    ), (
        "verify.frontend.acceptance_login_probe.unit",
    )),
    Rule((
        "scripts/ci/personal_data_false_positives.json",
    ), (
        "repository.clean_history.scan",
        "verify.repository.clean_history.unit",
        "security.personal_data_scan",
    )),
    # The payment action contract's reason presentation is consumed by the
    # contract action projector; keep the producer and its consumer test in one
    # executable routing unit instead of leaving a backend-only path unmapped.
    Rule((
        "addons/smart_construction_core/handlers/payment_request_available_actions.py",
        "addons/smart_construction_core/tests/test_payment_request_available_actions_backend.py",
        "addons/smart_construction_core/services/financial_workspace_contract.py",
        "addons/smart_construction_core/tests/test_p1_payment_request_capability.py",
    ), (
        "verify.frontend.contract_header_action.unit",
    )),
    Rule((
        "addons/smart_construction_core/models/core/payment_request.py",
        "addons/smart_construction_core/models/core/project_core.py",
        "addons/smart_construction_core/tests/test_workflow_contract_backend.py",
        "scripts/verify/test_payment_approval_state_machine.py",
    ), (
        "verify.workflow_contract.be_close_01.unit",
        "verify.workflow_contract.be_close_01.orm",
        "verify.payment.approval_state_machine.unit",
    )),
    Rule((
        "addons/smart_construction_core/models/support/operating_metrics.py",
        "addons/smart_construction_core/models/core/payment_request.py",
        "addons/smart_construction_core/services/payment_request_work_item_service.py",
        "addons/smart_construction_core/handlers/payment_request_available_actions.py",
        "addons/smart_construction_core/tests/test_payment_request_work_item_service.py",
        "addons/smart_construction_core/tests/test_payment_request_available_actions_backend.py",
    ), ("verify.payment.work_projection.orm",)),
    # HTTP sample validation is authoritative only when the probe or its
    # executable fixture changes. Backend model and ORM contract edits must not
    # require unrelated acceptance samples that may not exist in every worktree.
    Rule((
        "scripts/verify/test_be_close_01_workflow_contract_http_probe.py",
        "scripts/verify/be_close_01_workflow_contract_http_probe.py",
        "scripts/verify/be_close_01_workflow_contract_runtime_ids.py",
    ), (
        "verify.workflow_contract.be_close_01.unit",
        "verify.workflow_contract.be_close_01.orm",
        "verify.workflow_contract.be_close_01.samples",
        "verify.payment.approval_state_machine.unit",
    )),
    Rule((
        "scripts/dev/frontend_acceptance_operation_entry.sh",
    ), (
        "verify.frontend.standard_preview.unit",
    )),
    Rule((
        "scripts/ops/github_published_branch_sync.py",
        "scripts/ops/test_github_published_branch_sync.py",
    ), (
        "verify.workspace.branch.sync-github.unit",
    )),
    Rule((
        "addons/smart_construction_core/services/review_work_item_service.py",
        "addons/smart_construction_core/tests/test_approval_contract_closure.py",
        "scripts/verify/test_general_contract_review_authority.py",
    ), (
        "verify.general_contract.review_authority.unit",
        "verify.approval.contract_closure.orm",
    )),
    Rule((
        "addons/smart_construction_core/services/__init__.py",
        "addons/smart_construction_core/services/project_dashboard_service.py",
        "addons/smart_construction_core/services/project_evidence_summary_service.py",
        "addons/smart_construction_core/tests/__init__.py",
        "addons/smart_construction_core/tests/test_project_evidence_summary_service.py",
        "scripts/verify/project_management_contract_guard.py",
        "scripts/verify/project_dashboard_assembly_guard.py",
        "scripts/verify/project_dashboard_block_schema_guard.py",
        "scripts/verify/project_dashboard_metric_semantics_guard.py",
    ), (
        "verify.project.dashboard.contract",
    )),
    Rule((
        "scripts/verify/project_dashboard_contract_snapshot_export.py",
        "scripts/verify/project_dashboard_snapshot_freshness_guard.py",
    ), (
        "verify.project.dashboard.snapshot",
    )),
    Rule((
        "addons/smart_construction_core/models/support/workflow_contract_service.py",
        "addons/smart_construction_core/views/core/payment_request_views.xml",
    ), (
        "verify.approval.contract_closure.orm",
        "verify.unified_page_contract.v2.assembler",
        "verify.unified_page_contract.v2.action",
        "verify.unified_page_contract.v2.status",
        "verify.unified_page_contract.v2.runtime",
    )),
    Rule((
        "addons/smart_core/core/workflow_contract_injection.py",
        "addons/smart_core/models/workflow_contract.py",
        "addons/smart_core/tests/test_workflow_contract_platform.py",
    ), (
        "verify.workflow_contract.platform.orm",
    )),
    Rule((
        "frontend/apps/web/src/pages/contractForm/contractActionPresentation.ts",
        "frontend/apps/web/scripts/approval_contract_closure_test.ts",
        "frontend/apps/web/src/api/executeButton.ts",
        "frontend/apps/web/src/pages/contractForm/useFormActionRuntime.ts",
        "frontend/packages/schema/src/index.ts",
    ), (
        "verify.frontend.approval_contract.closure.unit",
        "verify.frontend.contract_header_action.unit",
        "verify.frontend.canonical_form_presenter.unit",
    )),
    Rule((
        "addons/smart_core/core/unified_page_contract_v2_assembler.py",
        "addons/smart_core/tests/test_unified_page_contract_v2_mobile_compact.py",
    ), (
        "verify.unified_page_contract.v2.assembler",
        "verify.unified_page_contract.v2.action",
        "verify.unified_page_contract.v2.status",
        "verify.unified_page_contract.v2.runtime",
    )),
    # V2.7 moved semantic production through the industry layout finalizer,
    # record-error proof identity, and the client/runtime projection carriers.
    # Each path has a distinct registered behavioural lock; a shared generic
    # frontend fallback would either miss the owning assertion or run unrelated
    # product gates.
    Rule((
        "addons/smart_construction_core/core_extension_project_layout.py",
    ), (
        "verify.unified_page_contract.v2.assembler",
    )),
    Rule((
        "addons/smart_core/core/record_error_proof.py",
        "addons/smart_core/tests/test_record_error_proof.py",
    ), (
        "verify.record_error_proof.unit",
    )),
    Rule((
        "addons/smart_core/core/unified_page_contract_v2_client.py",
        "scripts/verify/unified_page_contract_v2_client_guard.py",
    ), (
        "verify.unified_page_contract.v2.client",
    )),
    Rule((
        "addons/smart_core/core/unified_page_contract_v2_runtime.py",
        "addons/smart_core/tests/test_unified_page_contract_v2_runtime.py",
        "scripts/verify/unified_page_contract_v2_runtime_guard.py",
    ), (
        "verify.unified_page_contract.v2.runtime",
    )),
    Rule((
        "addons/smart_core/tests/test_contract_projection_json_boundaries.py",
        "scripts/verify/close_02_backend_contract_samples.mjs",
        "scripts/verify/close_02_backend_contract_samples_validate.py",
    ), (
        "verify.smart_core.search_contract.close_02.unit",
    )),
    Rule((
        "scripts/verify/close_02_field_query_browser_journeys.mjs",
    ), (
        "verify.frontend.dev.incremental.unit",
        "verify.frontend.playwright_vendor_coupling.guard",
    )),
    Rule((
        "addons/smart_core/core/native_action_view_set.py",
        "addons/smart_core/app_config_engine/services/resolvers/action_resolver.py",
        "addons/smart_core/handlers/ui_contract_preview.py",
        "addons/smart_core/tests/test_native_action_view_set_integration.py",
        "scripts/verify/test_native_action_view_set.py",
    ), (
        "verify.native_action.view_set.unit",
        "verify.native_action.view_set.orm",
        "verify.unified_page_contract.v2.assembler",
        "verify.contract.entry_equivalence.guard",
    )),
    Rule((
        "addons/smart_core/core/native_action_search_view.py",
        "addons/smart_core/app_config_engine/models/app_search_config.py",
        "addons/smart_core/app_config_engine/models/app_view_config.py",
        "addons/smart_core/tests/test_native_action_search_view_integration.py",
        "scripts/verify/test_native_action_search_view.py",
    ), (
        "verify.native_action.search_view.unit",
        "verify.native_action.search_view.orm",
        "verify.unified_page_contract.v2.assembler",
        "verify.contract.entry_equivalence.guard",
    )),
    Rule((
        "addons/smart_core/core/native_action_contract.py",
        "addons/smart_core/app_config_engine/utils/payload.py",
        "addons/smart_core/handlers/ui_contract.py",
        "addons/smart_core/tests/test_native_action_contract_integration.py",
        "scripts/verify/test_native_action_contract.py",
    ), (
        "verify.native_action.contract.unit",
        "verify.native_action.contract.orm",
        "verify.unified_page_contract.v2.assembler",
    )),
    Rule((
        "addons/smart_core/core/native_view_occurrence.py",
        "addons/smart_core/tests/test_native_occurrence_contract_integration.py",
        "scripts/verify/test_native_occurrence_contract.py",
    ), (
        "verify.native_occurrence.contract.unit",
        "verify.native_occurrence.contract.orm",
        "verify.unified_page_contract.v2.assembler",
    )),
    Rule((
        "scripts/verify/backend_contract_lifecycle_authority_guard.py",
    ), (
        "verify.backend.contract_lifecycle.authority",
    )),
    Rule((
        "scripts/verify/unified_page_contract_v2_intent_guard.py",
    ), (
        "verify.unified_page_contract.v2.intent",
    )),
    Rule((
        "frontend/apps/web/src/app/contracts/actionViewSurfaceContract.ts",
        "frontend/apps/web/src/app/action_runtime/useActionViewModeRuntime.ts",
        "frontend/apps/web/scripts/collection_view_semantics_test.ts",
        "frontend/apps/web/scripts/action_view_field_filter_runtime_test.ts",
    ), (
        "verify.frontend.contract_record_action_state.unit",
        "verify.frontend.collection_view_semantics.unit",
    )),
    Rule((
        "frontend/apps/web/scripts/cross_model_action_navigation_test.ts",
        "frontend/apps/web/src/app/navigationContext.ts",
    ), (
        "verify.frontend.cross_model_action_navigation.unit",
    )),
    Rule((
        "addons/smart_core/core/native_advisory.py",
        "addons/smart_core/core/draft_feedback.py",
        "addons/smart_core/core/node_component_validation.py",
        "addons/smart_core/tests/test_native_advisory.py",
        "addons/smart_core/tests/test_node_component_validation.py",
        "addons/smart_construction_core/tests/test_conditioned_processing_feedback.py",
        "addons/smart_construction_core/tests/test_company_project_refund_feedback.py",
    ), (
        "verify.native_advisory.unit",
        "verify.node_component_validation.unit",
        "verify.local.dev.conditioned.feedback.orm",
    )),
    Rule((
        "frontend/apps/web/src/app/contracts/v2/schema.ts",
        "frontend/apps/web/src/app/contracts/v2/types.ts",
    ), (
        "verify.frontend.canonical_form_presenter.unit",
        "verify.frontend.contract_record_action_state.unit",
    )),
    Rule((
        "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json",
        "docs/architecture/unified_page_contract_v2/examples/",
        "addons/smart_core/core/contract_lifecycle.py",
    ), (
        "verify.backend.contract_lifecycle.authority",
        "verify.frontend.contract_v2_render_authority.unit",
        "verify.unified_page_contract.v2.schema",
    )),
    Rule((
        "scripts/verify/contract_v2_render_authority_matrix.py",
        "docs/frontend_productization/rendering-detail/contract-v2-render-authority-matrix-v1.json",
    ), (
        "verify.frontend.contract_v2_render_authority.unit",
    )),
    Rule((
        "scripts/verify/docs_links.py",
        "scripts/verify/test_docs_links.py",
    ), (
        "verify.docs.links",
    )),
    Rule((
        "scripts/verify/frontend_contract_record_action_state.test.mjs",
    ), (
        "verify.frontend.contract_record_action_state.unit",
    )),
    Rule((
        "scripts/verify/unified_page_contract_v2_schema_guard.py",
        "scripts/verify/test_unified_page_contract_v2_schema_guard.py",
    ), (
        "verify.unified_page_contract.v2.schema",
    )),
    Rule((
        "scripts/verify/native_view_workflow_action_coverage_guard.py",
        "scripts/verify/test_native_view_workflow_action_coverage_guard.py",
    ), (
        "verify.native_view.workflow_action_coverage",
    )),
    Rule((
        "scripts/verify/contract_form_runtime_state_protocol_guard.py",
    ), (
        "verify.contract.architecture.suite",
    )),
    Rule((
        "addons/smart_core/tests/test_execute_button_server_action_boundaries.py",
        "addons/smart_core/handlers/execute_button.py",
    ), (
        "verify.execute_button.authority.unit",
        "verify.approval.contract_closure.orm",
    )),
    Rule((
        "scripts/audit/workflow_state_inventory.py",
    ), (
        "verify.workflow_action_semantics.guard",
    )),
    # The relation acceptance runner owns the placeholder classification used
    # by its public-control assertion; changing it requires the real journey.
    Rule((
        "scripts/verify/record_relation_roundtrip_acceptance.js",
        "scripts/verify/test_frontend_probe_toolchain_guard.py",
    ), (
        "verify.frontend.delivery_hardening.guard",
    )),
    # The v2 contract handler chain (handler + projection + structure authority)
    # is consumed by the backend form-contract unit suites.  Without this rule the
    # chain falls through as an unmapped path, so editing the contract builder
    # while running only frontend targets left a runtime NameError
    # (`project_form_structure_surfaces` iterating an undefined name) undetected
    # locally on 2026-10-10 until the served contract failed for every model.
    # The app-config page assembler is part of the same assembled output: the v2
    # handler injects its business-category policy and relation entry/search
    # dialog contracts before assembling and caching the page, and the assembler
    # guard's cache-identity fingerprint includes it. Without this route a change
    # there only failed when the frozen candidate ran Quick.
    Rule((
        "addons/smart_core/handlers/ui_contract_v2.py",
        "addons/smart_core/handlers/ui_contract_v2_projection.py",
        "addons/smart_core/core/form_structure_authority.py",
        "addons/smart_core/core/native_view_projection.py",
        "addons/smart_core/core/unified_page_contract_v2_modifier_dependencies.py",
        "addons/smart_core/app_config_engine/services/dispatchers/action_dispatcher.py",
        "addons/smart_core/app_config_engine/services/assemblers/page_assembler.py",
        "addons/smart_core/tests/test_action_dispatcher_server_mapping.py",
        "addons/smart_core/app_config_engine/models/app_view_config.py",
        "addons/smart_core/tests/test_ui_contract_v2_boundaries.py",
        "addons/smart_core/tests/test_odoo_native_alignment_boundaries.py",
    ), (
        "verify.business_config.formal_list.unit",
        "verify.form_structure_authority_unification.unit",
        "verify.unified_page_contract.v2.assembler",
        "verify.contract.entry_equivalence.guard",
    )),
    Rule((
        "addons/smart_construction_core/data/runtime_user_defaults.xml",
        "addons/smart_construction_core/models/support/organization_department.py",
        "addons/smart_construction_core/models/support/runtime_user_management.py",
        "addons/smart_construction_core/security/runtime_user_permission_groups.xml",
        "addons/smart_construction_core/views/support/organization_department_views.xml",
        "addons/smart_construction_core/views/support/runtime_user_management_views.xml",
    ), ("verify.runtime_user_management.orm", "verify.smart_construction_core.module_baseline")),
    Rule((
        "addons/smart_construction_core/security/contract_settlement_capability_bridge.xml",
        "addons/smart_construction_core/security/ir.model.access.csv",
    ), ("verify.role_capability_group_authority.unit", "verify.smart_construction_core.module_baseline")),
    Rule((
        "addons/smart_core/models/res_users_group_authority.py",
        "addons/smart_core/models/group_authority_reconciliation.py",
        "addons/smart_core/security/group_assignment.py",
        "addons/smart_core/tests/test_group_authority_sources.py",
    ), ("verify.group_authority.sources.orm",)),
    Rule((
        "addons/smart_construction_core/models/support/task_extend.py",
        "addons/smart_construction_core/tests/test_native_company_project_isolation.py",
    ), ("verify.auth02.native_isolation.orm",)),
    Rule((
        "addons/smart_construction_core/models/support/__init__.py",
    ), ("verify.backend.model_declaration.guard", "verify.smart_construction_core.module_baseline")),
    Rule((
        "addons/smart_construction_core/data/tenant/scoped_business_models.v1.json",
        "scripts/verify/data_scope_declarations.json",
    ), ("verify.sc_data_scope.rule_coverage", "verify.smart_construction_core.module_baseline")),
    Rule((
        "addons/smart_core/models/res_users_group_authority.py",
    ), ("verify.system.permission_role.assignment.unit", "verify.smart_core.close_02.module_baseline",
        "verify.smart_construction_core.module_baseline")),
    Rule((
        "addons/smart_core/models/__init__.py",
        "addons/smart_core/models/res_users.py",
        "addons/smart_core/models/subscription.py",
        "addons/smart_core/models/ir_rule_company_authorization.py",
        "addons/smart_core/security/platform_company_access.py",
        "addons/smart_core/security/auth.py",
        "addons/smart_core/security/credential_service.py",
        "addons/smart_core/handlers/login.py",
        "addons/smart_core/handlers/system_init.py",
        "addons/smart_core/views/platform_company_access_views.xml",
        "addons/smart_core/tests/test_platform_multi_company.py",
        "addons/smart_core/tests/platform_company_test_support.py",
        "addons/smart_core/tests/test_auth_credential_framework.py",
        "addons/smart_core/tests/test_data_space_boundary.py",
    ), ("verify.platform.multi_company.orm", "verify.smart_core.close_02.module_baseline")),
    Rule((
        "addons/smart_construction_core/services/business_capability_authorization.py",
        "addons/smart_construction_core/services/business_role_capabilities.py",
        "addons/smart_construction_core/models/support/business_role.py",
        "addons/smart_construction_core/models/support/business_role_change.py",
        "addons/smart_construction_core/models/support/approval_policy.py",
        "addons/smart_construction_core/models/support/tier_definition_ext.py",
        "addons/smart_construction_core/security/business_role_security.xml",
        "addons/smart_construction_core/views/support/business_role_views.xml",
        "addons/smart_construction_core/tests/test_business_role.py",
    ), ("verify.business_role.orm",)),
    Rule((
        "addons/smart_construction_core/services/business_capability_authorization.py",
        "addons/smart_construction_core/services/capability_registry.py",
        "addons/smart_construction_core/core_extension_capability_rows.py",
        "addons/smart_construction_core/tests/test_capability_registry_service.py",
        "scripts/verify/test_business_capability_authorization.py",
    ), ("verify.business_capability.authorization.unit", "verify.business_capability.authorization.orm",
        "verify.smart_construction_core.module_baseline")),
    Rule((
        "addons/smart_core/handlers/api_data.py",
    ), ("verify.smart_core.api_data_import.unit", "verify.smart_core.close_02.module_baseline")),
    Rule((
        "addons/smart_core/security/group_assignment.py",
        "scripts/verify/test_group_assignment.py",
    ), (
        "verify.system.permission_role.assignment.unit",
        "verify.runtime_user_management.orm",
    )),
    Rule((
        "addons/smart_construction_core/tests/test_runtime_user_management.py",
    ), (
        "verify.runtime_user_management.orm",
    )),
    Rule((
        "addons/smart_construction_core/tests/test_product_job.py",
    ), (
        "verify.product_job.orm",
    )),
    # Low-code workbench reads are behaviorally owned by the frontend consumer
    # suite. The approval editor additionally has its own target because it
    # preserves immediate-effect policy semantics and a multi-step write path.
    Rule((
        "frontend/apps/web/src/app/contextEpoch.ts",
        "frontend/apps/web/src/views/BusinessConfigSurfaceView.vue",
        "frontend/apps/web/src/views/businessConfigSurface/BusinessConfigEditorPanels.vue",
        "frontend/apps/web/src/views/businessConfigSurface/useBusinessConfigEditorIntent.ts",
        "frontend/apps/web/src/views/businessConfigSurface/useBusinessConfigProductExperience.ts",
        "frontend/apps/web/src/views/businessConfigSurface/useBusinessConfigPublishLifecycle.ts",
        "frontend/apps/web/src/views/businessConfigSurface/useBusinessConfigRemediationLifecycle.ts",
        "frontend/apps/web/src/views/businessConfigSurface/useBusinessConfigScopeLifecycle.ts",
        "frontend/apps/web/src/views/businessConfigSurface/useBusinessConfigVersions.ts",
        "frontend/apps/web/scripts/business_config_context_race_test.mjs",
        "scripts/verify/low_code_publish_boundary_guard.mjs",
        "scripts/verify/low_code_workbench_product_guard.py",
    ), (
        "verify.business_config.unit",
    )),
    Rule((
        "frontend/apps/web/src/app/contextEpoch.ts",
        "frontend/apps/web/src/views/businessConfigSurface/useBusinessConfigApprovalEditor.ts",
        "frontend/apps/web/src/views/businessConfigSurface/useBusinessConfigEditorIntent.ts",
        "frontend/apps/web/src/views/businessConfigSurface/useBusinessConfigRemediationLifecycle.ts",
        "frontend/apps/web/scripts/business_config_approval_target_test.mjs",
    ), (
        "verify.business_config.approval_targets.unit",
    )),
    # Enterprise initialization facts and scene enablement share the navigation
    # publication consumer suite. Its focused readiness contract test is
    # registered in the same Make target as the existing tenant activation and
    # navigation regressions.
    Rule((
        "addons/smart_construction_scene/services/enterprise_readiness_diagnosis.py",
        "addons/smart_construction_core/tests/test_enterprise_setup_native_contracts.py",
        "addons/smart_construction_scene/tests/test_enterprise_readiness_contract.py",
    ), (
        "verify.navigation.publication_consumers.unit",
    )),
    # Request-scoped route authority and contract projection identity are both
    # backend consumers of the assembled page contract. Keep each path on its
    # existing non-zero L2 owner so the inner loop cannot silently skip a cache
    # identity or principal-signature change.
    Rule((
        "addons/smart_core/delivery/runtime_route_authority.py",
        "addons/smart_core/delivery/effective_delivery_inputs.py",
        "addons/smart_core/delivery/effective_delivery_service.py",
        "addons/smart_core/delivery/product_policy_service.py",
        "addons/smart_core/models/release_management.py",
        "addons/smart_core/tests/test_route_authority_single_consumer.py",
        "addons/smart_core/tests/__init__.py",
        "addons/smart_core/tests/test_entry_publication_authority.py",
        "addons/smart_core/tests/test_principal_group_signature_request_scope.py",
        "addons/smart_core/tests/test_principal_group_signature_request_scope_orm.py",
    ), (
        "verify.product.entry_publication.unit",
    )),
    Rule((
        "addons/smart_core/tests/test_load_contract_response_cache.py",
        "addons/smart_core/utils/load_contract_response_cache.py",
    ), (
        "verify.business_config.formal_list.unit",
    )),
    Rule((
        "scripts/verify/test_coverage_registry.yaml",
        "scripts/verify/test_test_coverage_registry_audit.py",
    ), (
        "verify.test.coverage.registry",
    )),
    Rule((
        "scripts/verify/unified_page_contract_v2_assembler_guard.py",
        "scripts/verify/test_unified_page_contract_v2_assembler_guard.py",
    ), (
        "verify.unified_page_contract.v2.assembler",
    )),
    Rule((
        "scripts/verify/test_form_structure_authority_unification.py",
        "scripts/verify/frontend_v2_policy_projection_guard.py",
        "scripts/verify/test_frontend_v2_policy_projection_guard.py",
    ), (
        "verify.form_structure_authority_unification.unit",
    )),
    # The renderer implements the declared presentation vocabulary that the
    # projection publishes.  Editing the renderer's vocabulary block, the token
    # set in `ui_contract_v2_projection.py`, or the parity guard itself must route
    # to that guard: without this route the projection can publish a declared
    # token the renderer implements no rule for (the whole-region collapse defect)
    # and no local target reports it, so it only surfaces on the served contract.
    Rule((
        "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue",
        "addons/smart_core/handlers/ui_contract_v2_projection.py",
        "scripts/verify/form_container_presentation_consumption_guard.py",
    ), (
        "verify.form_container_presentation.guard",
    )),
    Rule((
        "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue",
        "frontend/apps/web/src/components/template/NativeNodeComponent.vue",
        "frontend/apps/web/src/components/template/NativeSmartAction.vue",
        "scripts/verify/frontend_native_form_action_presentation_guard.py",
        "scripts/verify/test_frontend_native_form_action_presentation_guard.py",
    ), (
        "verify.frontend.native_form_action_presentation.unit",
    )),
    # The product tree may not carry a customer identity; the governed duty
    # binding under ops_root replaces it, and the customer side of it was last
    # detected at the frozen candidate instead of in the inner loop. Editing the
    # declaration, the resolver, the duty entry that consumes it, the delivered
    # customer-addon tree, the recovery contract, the duty stack surface or the
    # boundary guard itself therefore routes to the boundary guard and the
    # resolver's own unit target.
    Rule((
        "config/ops/daily_runtime_database_duties.v1.json",
        "config/ops/daily_runtime_duty_stack",
        "scripts/ops/daily_runtime_duty_identity.py",
        "scripts/ops/daily_runtime_database_duty.py",
        "scripts/ops/daily_runtime_tenant_topology_inventory.py",
        "scripts/ops/daily_runtime_tenant_addons_deliver.py",
        "scripts/ops/daily_runtime_tenant_recovery_contract_v1.json",
        "scripts/ops/test_daily_runtime_duty_identity.py",
        "scripts/verify/tenant_product_payload_boundary_guard.py",
    ), (
        "verify.tenant.product_payload_boundary",
        "verify.daily.runtime.duty.identity.unit",
    )),
    # The daily-runtime read-only inventories and the governed stand-down entry
    # each carry their own non-zero unit target. Editing one of those tools, its
    # tests, or the declaration it consumes used to fall through to
    # "unmapped", so the inner loop could only recommend the target by hand --
    # which is exactly how a layered run silently loses its L2 layer. Each tool
    # routes to its own target only; routing them as one group would recommend
    # four unrelated lanes for a one-file edit.
    Rule((
        "scripts/ops/daily_runtime_legacy_stack_retire.py",
        "scripts/ops/test_daily_runtime_legacy_stack_retire.py",
        "config/ops/daily_runtime_retired_stacks.v1.json",
    ), (
        "verify.daily.runtime.legacy_stack.retire",
    )),
    Rule((
        "scripts/ops/daily_runtime_routing_inventory.py",
        "scripts/ops/test_daily_runtime_routing_inventory.py",
    ), (
        "verify.daily.runtime.routing.inventory",
    )),
    Rule((
        "scripts/ops/daily_runtime_tenant_topology_inventory.py",
        "scripts/ops/test_daily_runtime_tenant_topology_inventory.py",
    ), (
        "verify.daily.runtime.tenant.topology.inventory",
    )),
    Rule((
        "scripts/ops/daily_runtime_data_ownership_probe.py",
        "scripts/ops/test_daily_runtime_data_ownership_probe.py",
    ), (
        "verify.daily.runtime.data_ownership.probe",
    )),
    Rule((
        "scripts/ops/daily_runtime_lifecycle_fixture_prepare.py",
        "scripts/ops/test_daily_runtime_lifecycle_fixture_prepare.py",
    ), (
        "verify.daily.runtime.lifecycle_fixture.prepare",
    )),
    # The remaining daily-runtime duty tools each own a non-zero unit target.
    # The 2026-10-16 duty-binding change edited five of them plus their tests and
    # the inner loop could only report `unmappedPathCount=10`: a whole set of
    # governed tools whose L2 layer was selected by hand or not at all. Each one
    # routes to the lane that actually executes it.
    Rule((
        "scripts/ops/daily_runtime_mail_sender_prepare.py",
        "scripts/ops/test_daily_runtime_mail_sender_prepare.py",
    ), (
        "verify.daily.runtime.mail_sender.prepare",
    )),
    Rule((
        "scripts/ops/daily_runtime_data_space_onboard.py",
        "scripts/ops/test_daily_runtime_data_space_onboard.py",
    ), (
        "verify.daily.runtime.data_space.onboard",
    )),
    Rule((
        "scripts/ops/daily_runtime_database_identity_inventory.py",
        "scripts/ops/test_daily_runtime_database_identity_inventory.py",
    ), (
        "verify.daily.runtime.database.identity.inventory",
    )),
    Rule((
        "scripts/ops/daily_runtime_nav_pro_fixture_prepare.py",
        "scripts/ops/test_daily_runtime_nav_pro_fixture_prepare.py",
    ), (
        "verify.daily.runtime.nav_pro_fixture.prepare",
    )),
    Rule((
        "scripts/ops/daily_runtime_record_identity_resolve.py",
        "scripts/ops/test_daily_runtime_record_identity_resolve.py",
    ), (
        "verify.daily.runtime.record_identity.resolve",
    )),
    Rule((
        "scripts/ops/daily_runtime_published_face_converge.py",
        "scripts/ops/test_daily_runtime_published_face_converge.py",
    ), (
        "verify.daily.runtime.published_face.converge",
    )),
    # Build identity spans the deployment build alignment, source-revision
    # declaration, receipt/verifier and their orchestration. Route the whole
    # set to its offline behavior lock; the live candidate target remains a
    # separate deployment step.
    Rule((
        "scripts/ops/daily_runtime_build_identity.py",
        "scripts/ops/test_daily_runtime_build_identity.py",
        "scripts/ops/daily_runtime_frontend_build_align.py",
        "scripts/ops/test_daily_runtime_frontend_build_align.py",
        "scripts/ops/daily_runtime_source_revision_align.py",
        "scripts/ops/test_daily_runtime_source_revision_align.py",
        "scripts/ops/daily_runtime_release_orchestration.py",
        "scripts/ops/test_daily_runtime_release_orchestration.py",
    ), (
        "verify.daily.runtime.deployment_identity.unit",
    )),
    Rule((
        "scripts/ops/daily_candidate_bundle_sync.py",
        "scripts/ops/test_daily_candidate_bundle_sync.py",
    ), (
        "verify.daily.runtime.candidate.bundle_sync",
    )),
    Rule((
        "scripts/ops/daily_runtime_bundle_sync.py",
        "scripts/ops/test_daily_runtime_bundle_sync.py",
    ), (
        "verify.daily.runtime.main.bundle_sync",
    )),
    # The duty entry's own suite is the behavior lock of the phase machinery the
    # declaration drives; its test file was unmapped while the entry itself was
    # claimed by the identity rule, so a test-only edit selected nothing.
    Rule((
        "scripts/ops/daily_runtime_database_duty.py",
        "scripts/ops/test_daily_runtime_database_duty.py",
    ), (
        "verify.daily.runtime.database.duty",
    )),
    # The Odoo config renderer is consumed by the duty stack and by the release
    # lane; its own test runs inside `test.unit`, which is the layer that would
    # actually catch a broken render.
    Rule((
        "scripts/render_odoo_conf.py",
    ), (
        "test.unit",
    )),
    # The duty recovery tool decides whether a duty's database and its filestore
    # still form one recoverable pair. It classifies attachment bodies, Odoo's
    # empty garbage-collection markers and unexplained files separately, because
    # comparing "files on disk" with "distinct store_fname" cannot tell a broken
    # attachment from a marker `_mark_for_gc` is supposed to leave behind. Editing
    # the tool, its contract or its tests has to route to its own non-zero target;
    # otherwise a semantic regression there is only reported at the frozen
    # candidate, which is exactly what happened on 2026-10-16.
    Rule((
        "scripts/ops/daily_candidate_data_continuity.py",
        "scripts/ops/test_daily_candidate_data_continuity.py",
        "scripts/ops/daily_candidate_data_continuity_contract_v1.json",
    ), (
        "verify.daily.duty.recovery",
    )),
    # The verification-lane registries decide which dead surface is an accounted
    # allowance and which divergence still blocks. Editing the instrument, its
    # tests, its frozen baseline, its dispositions or its exemptions has to route
    # to that lane's own non-zero target: a registration that stops being true is
    # a defect of this file set, and it is only reported by that gate.
    Rule((
        "scripts/audit/verification_lane_coverage.py",
        "scripts/audit/test_verification_lane_coverage.py",
        "scripts/audit/verification_lane_baseline.json",
        "scripts/audit/verification_lane_dispositions.json",
        "scripts/audit/verification_lane_exemptions.json",
        "scripts/ops/pre-commit_refresh_generated.sh",
    ), (
        "verify.verification.lane_coverage",
    )),
    Rule((
        "config/frontend/authoritative_navigation.json",
        "scripts/verify/frontend_navigation_audit.mjs",
        "scripts/verify/frontend_navigation_audit.test.mjs",
        "scripts/verify/frontend_release_navigation_policy_guard.py",
        "scripts/verify/test_frontend_release_navigation_policy_guard.py",
        "scripts/verify/frontend_release_audit.py",
        "scripts/verify/test_frontend_release_audit.py",
    ), (
        "verify.frontend.navigation_policy.unit",
    )),
    Rule((
        "scripts/release/frontend_release_evidence.py",
        "scripts/verify/test_frontend_release_evidence_bundle.py",
    ), (
        "verify.frontend.evidence_bundle.unit",
    )),
    # INDUSTRY-BUSINESS-MODEL-02 spans project orchestration, plan/WBS/task
    # boundaries, formal settlement authority and BOQ task assignment. These
    # paths must route to the batch's focused ORM and read-only content audit
    # rather than becoming unmapped merely because the targets are registered
    # separately in the active run.
    Rule((
        "addons/smart_construction_core/handlers/my_work_summary.py",
        "addons/smart_construction_core/models/core/boq.py",
        "addons/smart_construction_core/models/core/cost_domain.py",
        "addons/smart_construction_core/models/core/plan_management.py",
        "addons/smart_construction_core/models/core/project_core.py",
        "addons/smart_construction_core/models/core/settlement.py",
        "addons/smart_construction_core/models/support/document_center.py",
        "addons/smart_construction_core/models/support/task_extend.py",
        "addons/smart_construction_core/services/my_work_aggregate_service.py",
        "addons/smart_construction_core/services/project_context_contract.py",
        "addons/smart_construction_core/services/project_creation_service.py",
        "addons/smart_construction_core/services/project_dashboard_builders/project_header_builder.py",
        "addons/smart_construction_core/services/project_dashboard_builders/project_metrics_builder.py",
        "addons/smart_construction_core/services/project_dashboard_builders/project_progress_builder.py",
        "addons/smart_construction_core/services/project_dashboard_builders/project_risk_builder.py",
        "addons/smart_construction_core/services/project_execution_builders/project_execution_next_actions_builder.py",
        "addons/smart_construction_core/services/project_execution_builders/project_execution_readiness_precheck_builder.py",
        "addons/smart_construction_core/services/project_execution_builders/project_execution_tasks_builder.py",
        "addons/smart_construction_core/services/project_execution_consistency_guard.py",
        "addons/smart_construction_core/services/project_execution_item_projection_service.py",
        "addons/smart_construction_core/services/project_plan_bootstrap_builders/project_plan_tasks_builder.py",
        "addons/smart_construction_core/services/project_task_state_support.py",
        "addons/smart_construction_core/views/core/plan_management_views.xml",
        "addons/smart_construction_core/wizard/project_task_from_boq_wizard.py",
        "scripts/e2e/e2e_boq_to_wbs_task_preflight.py",
        "scripts/verify/industry_business_model_02_data_audit.py",
    ), (
        "verify.industry_business_model_02.orm",
        "verify.industry_business_model_02.data_audit",
    )),
    Rule(('config/frontend/acceptance_environments_v1.json', 'scripts/dev/frontend_acceptance_carrier_common.sh', 'scripts/dev/frontend_acceptance_runtime_profile.py', 'scripts/dev/frontend_release_disposable.py', 'scripts/verify/g1_acceptance_baseline_guard.py', 'scripts/verify/test_frontend_release_disposable.py', 'scripts/verify/test_g1_acceptance_baseline_guard.py'), ("verify.acceptance.disposable.unit",)),
)
FALLBACK_TARGET = "verify.frontend.typecheck.strict"
LANE_COVERAGE_TARGET = "audit.verification.lane_coverage.check"
VERIFICATION_SURFACE_PREFIXES = (
    "make/",
    ".github/workflows/",
    "scripts/audit/verification_lane_",
    "scripts/verify/registry.yaml",
    "scripts/verify/guard_registry_audit.py",
    "scripts/verify/test_guard_registry_audit.py",
    "scripts/verify/frontend_dev_incremental.py",
    "scripts/verify/test_frontend_dev_incremental.py",
    "scripts/ops/local_quick_evidence.py",
    "scripts/ops/test_local_quick_evidence.py",
    "docs/audit/guard_registry/",
)
FORBIDDEN_DEVELOPMENT_TARGET_PARTS = ("quick", "build", "browser", "release", "fingerprint")
DEVELOPMENT_ALLOWED_CANDIDATE_LIGHT_TARGETS = frozenset({
    "verify.quick.input_scope.unit",
    "verify.local.dev.frontend.quick.unit",
})
# Run bookkeeping and narrative documentation carry no frontend source input:
# reconciling `.agent/` state or writing an iteration record must never be reported
# as an unmapped product path, otherwise every continuation or record update would
# demand a manual L2 selection that has nothing to select. Narrative docs are a
# documentation-only change, which the recorded reuse decision
# (.agent/decisions/evidence-reuse-identity.yaml) states does not invalidate a unit.
NON_SOURCE_PATH_PREFIXES = (".agent/", "docs/")
NON_SOURCE_PATHS = ("AGENTS.md",)
MODULE_BASELINE_TARGETS = {
    "smart_core": {"verify.smart_core.close_02.module_baseline"},
    "smart_construction_core": {"verify.smart_construction_core.module_baseline"},
    "smart_construction_scene": {"verify.smart_construction_scene.module_baseline"},
}
TEST_AUXILIARY_PREFIXES = {
    ("smart_construction_acceptance_fixture", "tools/"),
}
CHANNEL_ALL = "all"
CHANNEL_BACKEND = "backend"
CHANNEL_FRONTEND = "frontend"
CHANNELS = (CHANNEL_ALL, CHANNEL_BACKEND, CHANNEL_FRONTEND)
SHARED_TARGET_MARKERS = (
    ".assembler.",
    ".descriptor.",
    ".registry.",
    ".schema.",
    ".semantic.",
    "contract_v2",
    "contract_fidelity",
    "contract_shape",
    "contract_structure",
    "p0_contract_producer",
    "unified_page_contract",
)
CONTRACT_PATH_MARKERS = (
    "/contracts/",
    "/assemblers/",
    "contract",
    "descriptor",
    "page_orchestration",
    "schema",
    "semantic_registry",
)


def changed_test_target(module: str) -> str:
    return "verify.changed_tests.orm"


def is_contract_handoff_target(target: str) -> bool:
    lowered = target.lower()
    return (
        any(marker in lowered for marker in SHARED_TARGET_MARKERS)
        or target.startswith(("verify.contract.", "verify.semantic."))
        or "contract" in target_layers([target])
    )


def is_contract_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    return any(marker in normalized for marker in CONTRACT_PATH_MARKERS)


def shared_contract_targets_for_paths(paths: list[str]) -> set[str]:
    selected: set[str] = set()
    for path in paths:
        if is_contract_path(path):
            selected.update(select_iteration_targets([path]))
    return selected


def channel_target_class(target: str) -> str:
    """Classify one target as backend, frontend or shared contract/governance."""
    if target == REGISTRY_AUDIT_TARGET:
        return CHANNEL_BACKEND
    lowered = target.lower()
    layers = target_layers([target])
    if (
        is_contract_handoff_target(target)
        or "docs" in layers
        or "governance" in layers
    ):
        return "shared"
    if "frontend" in layers:
        return CHANNEL_FRONTEND
    if "backend" in layers:
        return CHANNEL_BACKEND
    return "shared"


def select_channel_targets(
    targets: set[str] | list[str],
    channel: str,
    *,
    paths: list[str] | None = None,
) -> list[str]:
    if channel not in CHANNELS:
        raise ValueError(f"unknown validation channel: {channel}")
    selected = set(targets)
    if channel == CHANNEL_ALL:
        return sorted(selected)
    contract_targets = shared_contract_targets_for_paths(paths or [])
    allowed = {channel, "shared"}
    return sorted(
        target
        for target in selected
        if channel_target_class(target) in allowed
        or target in contract_targets
    )


def channel_target_sets(
    targets: set[str] | list[str],
    *,
    paths: list[str] | None = None,
) -> dict[str, list[str]]:
    complete = set(targets)
    contract_targets = shared_contract_targets_for_paths(paths or [])
    backend = set(select_channel_targets(
        complete,
        CHANNEL_BACKEND,
        paths=paths,
    ))
    frontend = set(select_channel_targets(
        complete,
        CHANNEL_FRONTEND,
        paths=paths,
    ))
    union = backend | frontend
    if union != complete:
        missing = sorted(complete - union)
        raise RuntimeError(
            "channel partition is incomplete: " + ", ".join(missing)
        )
    return {
        "backend": sorted(backend),
        "frontend": sorted(frontend),
        "shared": sorted(backend & frontend),
        "sharedContract": sorted(
            target
            for target in backend & frontend
            if is_contract_handoff_target(target)
            or target in contract_targets
        ),
        "backendOnly": sorted(backend - frontend),
        "frontendOnly": sorted(frontend - backend),
    }


def remote_integration_targets(targets: set[str] | list[str]) -> set[str]:
    """Full module baselines belong to exact-head remote PR integration."""
    return {
        target
        for target in targets
        if target.endswith(".module_baseline")
    }


def remote_scope_projection(paths: list[str]) -> dict:
    """Describe remote responsibility from the shared path-ownership registry.

    This projection does not select backend modules or frontend targets; those
    remain owned by the exact-head remote planners. It records which remote
    authorities must run, using the same path ownership facts as the CI risk
    and backend impact entries.
    """
    normalized = sorted({
        path.replace("\\", "/")
        for path in paths
        if path.strip()
    })
    ownership = ci_path_ownership.classify_paths(normalized)
    categories = {
        path: category_id
        for path, category_id in ownership.assignments.items()
        if category_id not in ("__unknown__", "__invalid__")
    }
    backend_runtime_paths = sorted(
        path
        for path in categories
        if ownership.category_for(path)
        and ownership.category_for(path).backend_runtime
    )
    frontend_paths = sorted(
        path
        for path in categories
        if ownership.category_for(path)
        and ownership.category_for(path).frontend
    )
    frontend_full_paths = sorted(
        path
        for path in categories
        if ownership.category_for(path)
        and ownership.category_for(path).frontend_full
    )
    backend_seed_modules = sorted({
        parts[1]
        for path in normalized
        if len(parts := path.split("/")) >= 2
        and parts[0] in ("addons", "demo_addons")
        and re.fullmatch(r"[a-z_][a-z0-9_]*", parts[1])
    })
    return {
        "authority": "exact_head_remote_planners",
        "pathOwnershipRegistry": "config/ci/path_ownership_v1.json",
        "backendSuiteRequired": bool(
            backend_runtime_paths
            or ownership.unknown_paths
            or ownership.invalid_paths
        ),
        "backendSeedModules": backend_seed_modules,
        "frontendReleaseGateRequired": bool(frontend_paths),
        "frontendFullRequired": bool(frontend_full_paths),
        "controlPlaneChanged": ownership.control_plane_changed,
        "pathOwnershipToolChecks": list(ownership.tool_checks),
        "ownershipCategories": sorted(set(categories.values())),
        "backendRuntimePaths": backend_runtime_paths,
        "frontendPaths": frontend_paths,
        "unknownPaths": list(ownership.unknown_paths),
        "invalidPaths": list(ownership.invalid_paths),
        "selection": {
            "backend": "owning_and_transitive_consumer_module_baseline_at_exact_head",
            "frontend": "risk_selected_release_lane_at_exact_head",
            "controlPlane": "registered_owner_tool_checks_at_exact_head",
        },
    }


def is_registry_audit_input(path: str) -> bool:
    """Return whether a path can change declared test coverage or its selector."""
    normalized = path.replace("\\", "/")
    if normalized in REGISTRY_AUDIT_SELECTOR_PATHS:
        return True
    parts = normalized.split("/")
    if len(parts) < 4 or parts[0] not in ("addons", "demo_addons"):
        return False
    relative = "/".join(parts[2:])
    if relative == "tests/__init__.py":
        return True
    return (
        relative.startswith("tests/")
        and relative.endswith(".py")
        and Path(relative).name.startswith("test_")
    )


def select_targets(paths: list[str]) -> list[str]:
    selected: set[str] = set(ci_path_ownership.classify_paths(paths).local_tool_checks)
    for path in paths:
        normalized = path.replace("\\", "/")
        path_targets: set[str] = set()
        for rule in RULES:
            if any(fragment in normalized for fragment in rule.fragments):
                path_targets.update(rule.targets)
        # A mapped backend/tool path must not mask an unmapped frontend path
        # in the same change set. Resolve the fallback per path, then union.
        if not path_targets and normalized.startswith(
            ("frontend/apps/web/", "frontend/packages/ui/")
        ):
            path_targets.add(FALLBACK_TARGET)
        if normalized.startswith("frontend/apps/web/scripts/") and normalized.endswith(FRONTEND_SOURCE_SUFFIXES):
            path_targets.add("verify.frontend.lint.scripts")
        if (
            normalized.startswith(FRONTEND_SOURCE_ROOTS)
            and normalized.endswith(FRONTEND_SOURCE_SUFFIXES)
        ):
            # A focused rule supplements the source-wide baseline; it never
            # replaces lint or strict typechecking.
            path_targets.update(FRONTEND_SOURCE_TARGETS)
        selected.update(path_targets)
    targets = sorted(selected)
    if any(
        part in target
        for target in targets
        if target not in DEVELOPMENT_ALLOWED_CANDIDATE_LIGHT_TARGETS
        for part in FORBIDDEN_DEVELOPMENT_TARGET_PARTS
    ):
        raise RuntimeError("development validation selected a candidate-only target")
    return targets


def select_iteration_targets(paths: list[str]) -> list[str]:
    """Select affected checks for a local iteration.

    Tests with a focused ORM owner keep that owner. Bare test files otherwise
    run only their changed classes. A production change in the same module
    retains the owning-module baseline.
    """
    selected = set(select_targets(paths))
    if any(is_registry_audit_input(path) for path in paths):
        selected.add(REGISTRY_AUDIT_TARGET)
    if any(
        path.replace("\\", "/").startswith(VERIFICATION_SURFACE_PREFIXES)
        for path in paths
    ):
        selected.add(LANE_COVERAGE_TARGET)
    changed_test_modules: set[str] = set()
    test_only_focused_orm: dict[str, set[str]] = {}
    production_modules: set[str] = set()
    for path in paths:
        normalized = path.replace("\\", "/")
        if normalized in HOST_STANDALONE_TEST_FILES:
            continue
        match = re.match(r"addons/([a-z][a-z0-9_]*)/(.+)$", normalized)
        if not match:
            continue
        module, relative = match.groups()
        if (
            not relative.startswith("tests/")
            and not any(
                module == owner and relative.startswith(prefix)
                for owner, prefix in TEST_AUXILIARY_PREFIXES
            )
        ):
            production_modules.add(module)
            continue
        if not (
            Path(relative).name.startswith("test_")
            and relative.endswith(".py")
        ):
            continue
        if not changed_odoo_tests.odoo_test_classes(ROOT / normalized):
            continue
        module_targets = set(select_targets([normalized]))
        module_baselines = MODULE_BASELINE_TARGETS.get(module, set())
        focused_orm = {
            target
            for target in module_targets
            if target.endswith(".orm") and target not in module_baselines
        }
        if focused_orm:
            test_only_focused_orm.setdefault(module, set()).update(focused_orm)
        else:
            changed_test_modules.add(module)
    for module in sorted(changed_test_modules - production_modules):
        selected.difference_update(MODULE_BASELINE_TARGETS.get(module, set()))
        selected.difference_update(test_only_focused_orm.get(module, set()))
        selected.add(changed_test_target(module))
    return sorted(selected)


def target_layers(targets: set[str] | list[str]) -> list[str]:
    """Describe the product layers represented by selected verification targets."""
    layers: set[str] = set()
    for target in targets:
        if target.startswith("verify.frontend."):
            layers.add("frontend")
        elif (
            target.startswith(
                (
                    "verify.backend.",
                    "verify.smart_core.",
                    "verify.smart_construction_",
                )
            )
            or target.endswith(".orm")
            or ".module_baseline" in target
            or ".extension_module_baseline" in target
        ):
            layers.add("backend")
        elif target.startswith(("verify.docs.", "docs.")):
            layers.add("docs")
        elif target.startswith(("verify.contract.", "contract.")):
            layers.add("contract")
        else:
            layers.add("governance")
    return [layer for layer in TARGET_LAYER_ORDER if layer in layers]


def implicitly_registered_offline_targets(targets: set[str]) -> set[str]:
    """Treat pure target families as registered without widening runtime reuse."""
    return {
        target
        for target in targets
        if target.endswith(IMPLICIT_OFFLINE_TARGET_SUFFIXES)
    }


def watched_files() -> list[Path]:
    files: set[Path] = set()
    for relative in WATCH_ROOTS:
        source = ROOT / relative
        if source.is_file():
            files.add(source)
        elif source.is_dir():
            files.update(path for path in source.rglob("*") if path.is_file())
    return sorted(files)


def content_snapshot() -> dict[str, str]:
    result: dict[str, str] = {}
    for path in watched_files():
        relative = path.relative_to(ROOT).as_posix()
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


def _git_paths(root: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
    )
    return [value.decode("utf-8") for value in result.stdout.split(b"\0") if value]


def _paths_since(root: Path, revision: str) -> list[str]:
    paths = set(
        _git_paths(
            root,
            "diff",
            "--no-renames",
            "--name-only",
            "-z",
            f"{revision}..HEAD",
        )
    )
    paths.update(_git_paths(root, "diff", "--no-renames", "--name-only", "-z"))
    paths.update(_git_paths(root, "diff", "--no-renames", "--cached", "--name-only", "-z"))
    paths.update(_git_paths(root, "ls-files", "--others", "--exclude-standard", "-z"))
    return sorted(paths)


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, descendant],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _receipt_identity_resumable(
    receipt_identity: object,
    current_identity: dict,
    receipt_head: str,
) -> bool:
    """Require current verifier identity without treating cleanliness as validity."""
    if not isinstance(receipt_identity, dict) or not _full_sha(receipt_head):
        return False
    receipt_runtime = receipt_identity.get("runtimeTreeSha256")
    current_runtime = current_identity.get("runtimeTreeSha256")
    if (
        not _full_digest(receipt_runtime)
        or (
            (receipt_head == current_identity.get("head")
             or receipt_identity.get("worktreeClean") is not True)
            and receipt_runtime != current_runtime
        )
        or receipt_identity.get("authoritySha256")
        != current_identity.get("authoritySha256")
        or any(
            receipt_identity.get(field) != current_identity.get(field)
            for field in REUSE_ENVIRONMENT_IDENTITY_FIELDS
        )
    ):
        return False
    return True


def invalidated_targets_since_receipt(
    root: Path,
    receipt_head: str,
    receipt_identity: dict,
    current_identity: dict,
) -> set[str]:
    """Return targets whose inputs changed after a reusable source receipt.

    HEAD and cleanliness are provenance. An advanced HEAD is reusable only when
    no path since that source selects the requested target. Equivalent committed
    and dirty runtime bytes keep the same identity and require no path replay.
    """
    same_runtime_identity = (
        receipt_identity.get("runtimeTreeSha256")
        == current_identity.get("runtimeTreeSha256")
        and receipt_identity.get("authoritySha256")
        == current_identity.get("authoritySha256")
        and all(
            receipt_identity.get(field) == current_identity.get(field)
            for field in REUSE_ENVIRONMENT_IDENTITY_FIELDS
        )
    )
    if receipt_head == current_identity.get("head") or same_runtime_identity:
        return set()
    return set(select_iteration_targets(_paths_since(root, receipt_head)))


def resumable_receipt_results(
    root: Path,
    paths: list[str],
    targets: list[str],
    *,
    identity: dict | None = None,
    channel: str | None = None,
    run_id: str | None = None,
) -> tuple[Path | None, str, dict[str, dict]]:
    """Carry verified targets from a prior exact execution identity.

    A prior aggregate receipt can contain passed targets even when another
    target was interrupted, or can be a complete passed execution whose source
    later changed. Those target logs remain useful when the source head is still
    an ancestor, the verifier authority is unchanged, and the requested target
    was actually executed. For an unchanged HEAD, the complete current runtime
    tree must also match, so a dirty candidate can resume but changed runtime
    bytes cannot reuse an older result. For an advanced HEAD, targets selected by
    commits or dirty paths since that head are removed here so every caller,
    including shared-contract handoff, applies the same invalidation predicate.
    """
    execution_root = root / ".runtime/frontend-dev-validation/executions"
    if not execution_root.is_dir():
        return None, "", {}
    receipts = sorted(
        execution_root.glob("*/receipt.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    expected_targets = sorted(set(targets))
    current_identity = identity or current_execution_identity(root)
    current_head = str(current_identity.get("head", ""))
    best = None
    for receipt_path in receipts:
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if channel is not None and receipt.get("channel") != channel:
                continue
            if run_id is not None and receipt.get("runId") != run_id:
                continue
            receipt_identity = receipt.get("identity")
            if not isinstance(receipt_identity, dict):
                continue
            head = str(receipt_identity.get("head", ""))
            source_targets = receipt.get("requiredTargets")
            if (
                receipt.get("status") not in ("interrupted", "passed", "failed")
                or not _full_sha(head)
                or not _full_sha(current_head)
                or not _receipt_identity_resumable(
                    receipt_identity,
                    current_identity,
                    head,
                )
                or not isinstance(source_targets, list)
                or any(not isinstance(target, str) for target in source_targets)
                or len(set(source_targets)) != len(source_targets)
                or not set(expected_targets).intersection(source_targets)
            ):
                continue
            same_runtime_identity = (
                receipt_identity.get("runtimeTreeSha256")
                == current_identity.get("runtimeTreeSha256")
                and receipt_identity.get("authoritySha256")
                == current_identity.get("authoritySha256")
            )
            if not same_runtime_identity and not _is_ancestor(
                root, head, current_head
            ):
                continue
            results: dict[str, dict] = {}
            for row in receipt.get("targetResults", []):
                target = row.get("target")
                if target not in expected_targets or target not in source_targets or target in results:
                    continue
                if row.get("status") != "passed" or row.get("returncode") != 0:
                    continue
                log = Path(str(row.get("log", "")))
                if not log.is_absolute():
                    log = root / log
                if (
                    not log.is_file()
                    or not log.resolve().is_relative_to(root.resolve())
                    or hashlib.sha256(log.read_bytes()).hexdigest() != row.get("logSha256")
                ):
                    continue
                carried = dict(row)
                carried["reusedFrom"] = _json_path(receipt_path, root)
                carried["reuseReason"] = "verified passed target from prior execution"
                results[target] = carried
            invalidated = invalidated_targets_since_receipt(
                root,
                head,
                receipt_identity,
                current_identity,
            )
            results = {
                target: row
                for target, row in results.items()
                if target not in invalidated
            }
            if results:
                complete_pass = (
                    receipt.get("status") == "passed"
                    and not receipt.get("notRunTargets")
                )
                candidate = (
                    0 if complete_pass else 1,
                    receipt_path,
                    head,
                    results,
                )
                if best is None or candidate[0] < best[0]:
                    best = candidate
        except (OSError, ValueError, KeyError, TypeError):
            continue
    if best is not None:
        _, receipt_path, head, results = best
        return receipt_path, head, results
    return None, "", {}


def channel_receipt_complete_pass(
    receipt_path: Path | None,
    targets: set[str] | list[str],
) -> bool:
    """Require a complete passed receipt for cross-channel target reuse."""
    if receipt_path is None:
        return False
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        rows = receipt.get("targetResults")
        if (
            receipt.get("status") != "passed"
            or receipt.get("verificationPassed") is not True
            or receipt.get("notRunTargets")
            or not isinstance(rows, list)
        ):
            return False
        passed = {
            row.get("target")
            for row in rows
            if isinstance(row, dict)
            and row.get("status") == "passed"
            and row.get("returncode") == 0
        }
        return set(targets) <= passed
    except (OSError, ValueError, TypeError):
        return False


def worktree_changed_paths(root: Path = ROOT, base_ref: str = "origin/main") -> list[str]:
    merge_base = subprocess.run(
        ["git", "-C", str(root), "merge-base", "HEAD", base_ref],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    paths = set(_git_paths(root, "diff", "--no-renames", "--name-only", "-z", f"{merge_base}..HEAD"))
    paths.update(_git_paths(root, "diff", "--no-renames", "--name-only", "-z"))
    paths.update(_git_paths(root, "diff", "--no-renames", "--cached", "--name-only", "-z"))
    paths.update(_git_paths(root, "ls-files", "--others", "--exclude-standard", "-z"))
    return sorted(paths)


def _full_sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(
        char in "0123456789abcdef" for char in value
    )


def _full_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value
    )


def _ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, descendant],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def _committed_paths_between(root: Path, source: str, head: str) -> list[str]:
    return sorted(
        _git_paths(
            root,
            "diff",
            "--no-renames",
            "--name-only",
            "-z",
            f"{source}..{head}",
        )
    )


def _historical_blob(root: Path, head: str, path: str) -> bytes:
    if path.startswith("/") or ".." in Path(path).parts:
        raise ValueError("historical authority path must stay inside the repository")
    return subprocess.run(
        ["git", "-C", str(root), "show", f"{head}:{path}"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def _historical_target_mapping(root: Path, head: str, paths: list[str]) -> list[str]:
    """Evaluate target mapping with the historical verifier source from Git."""
    source_path = "scripts/verify/frontend_dev_incremental.py"
    source = _historical_blob(root, head, source_path)
    module_name = f"_historical_frontend_dev_incremental_{head[:12]}"
    module = types.ModuleType(module_name)
    module.__file__ = str(root / source_path)
    sys.modules[module_name] = module
    try:
        exec(compile(source, module.__file__, "exec"), module.__dict__)
        selector = module.__dict__.get("select_targets")
    finally:
        sys.modules.pop(module_name, None)
    if not callable(selector):
        raise ValueError("historical verifier has no target selector")
    selected = selector(paths)
    if (
        not isinstance(selected, list)
        or any(not isinstance(target, str) or not target for target in selected)
        or len(set(selected)) != len(selected)
    ):
        raise ValueError("historical target selector returned an invalid target set")
    return selected


def _checkpoint_receipt_closed(root: Path, receipt: dict) -> bool:
    """Prove one execution receipt is a complete, closed affected-target execution."""
    try:
        identity = receipt.get("identity")
        if (
            receipt.get("schemaVersion") != 1
            or receipt.get("mode") != "development_incremental_execution"
            or receipt.get("status") != "passed"
            or receipt.get("verificationPassed") is not True
            or receipt.get("testsRun") is not True
            or not isinstance(identity, dict)
            or identity.get("worktreeClean") is not True
            or not _full_sha(identity.get("head"))
            or not _full_sha(identity.get("tree"))
            or not _full_digest(identity.get("runtimeTreeSha256"))
            or not isinstance(identity.get("authoritySha256"), dict)
            or not identity.get("authoritySha256")
        ):
            return False
        head = str(identity["head"])
        tree = subprocess.run(
            ["git", "-C", str(root), "rev-parse", f"{head}^{{tree}}"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        if tree != identity["tree"]:
            return False
        if committed_runtime_tree_sha256(root, head) != identity["runtimeTreeSha256"]:
            return False
        authority = identity["authoritySha256"]
        if set(authority) != set(CHECKPOINT_AUTHORITY_PATHS):
            return False
        for path in CHECKPOINT_AUTHORITY_PATHS:
            digest = authority.get(path)
            if not _full_digest(digest):
                return False
            if hashlib.sha256(_historical_blob(root, head, path)).hexdigest() != digest:
                return False
        changed_paths = receipt.get("changedPaths")
        baseline = receipt.get("iterationBaselineSha")
        required = receipt.get("requiredTargets")
        target_order = receipt.get("targetOrder")
        results = receipt.get("targetResults")
        not_run = receipt.get("notRunTargets")
        if (
            not isinstance(changed_paths, list)
            or not changed_paths
            or any(not isinstance(path, str) or not path for path in changed_paths)
            or not isinstance(required, list)
            or not required
            or any(not isinstance(target, str) or not target for target in required)
            or len(set(required)) != len(required)
            or target_order != required
            or not isinstance(results, list)
            or not isinstance(not_run, list)
            or not_run
            or not _full_sha(baseline)
        ):
            return False
        if sorted(changed_paths) != _committed_paths_between(root, baseline, head):
            return False
        expected_targets = _historical_target_mapping(root, head, changed_paths)
        if expected_targets != required:
            return False
        result_targets: list[str] = []
        for row in results:
            if not isinstance(row, dict):
                return False
            target = row.get("target")
            if (
                not isinstance(target, str)
                or row.get("status") != "passed"
                or row.get("returncode") != 0
            ):
                return False
            result_targets.append(target)
            log = Path(str(row.get("log", "")))
            if not log.is_absolute():
                log = root / log
            if (
                not log.is_file()
                or not log.resolve().is_relative_to(root.resolve())
                or hashlib.sha256(log.read_bytes()).hexdigest() != row.get("logSha256")
            ):
                return False
        return result_targets == required
    except (OSError, ValueError, TypeError, KeyError, subprocess.CalledProcessError):
        return False


def _checkpoint_chain_verified(
    root: Path,
    baseline_sha: str,
    head: str,
    receipts_by_head: dict[str, list[dict]],
    visited: frozenset[str] = frozenset(),
) -> bool:
    if head == baseline_sha:
        return True
    if head in visited:
        return False
    visited = visited | {head}
    for receipt in receipts_by_head.get(head, []):
        if not _checkpoint_receipt_closed(root, receipt):
            continue
        parent = receipt.get("iterationBaselineSha")
        kind = receipt.get("iterationBaselineKind")
        if not _full_sha(parent) or not _ancestor(root, parent, head):
            continue
        if kind == "run_baseline":
            if parent == baseline_sha:
                return True
            continue
        if kind == "verified_incremental_receipt" and _checkpoint_chain_verified(
            root, baseline_sha, parent, receipts_by_head, visited
        ):
            return True
    return False


def latest_verified_iteration_checkpoint(root: Path, baseline_sha: str) -> tuple[str, str]:
    """Resolve the closest checkpoint with a closed, recursively verified receipt chain."""
    execution_root = root / ".runtime/frontend-dev-validation/executions"
    if not execution_root.is_dir():
        return baseline_sha, "run_baseline"
    current_head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    receipts_by_head: dict[str, list[dict]] = {}
    receipt_candidates: list[tuple[float, str]] = []
    for receipt_path in execution_root.glob("*/receipt.json"):
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            identity = receipt.get("identity") if isinstance(receipt.get("identity"), dict) else {}
            head = identity.get("head")
            if not _full_sha(head) or not _ancestor(root, baseline_sha, head) or not _ancestor(root, head, current_head):
                continue
            receipts_by_head.setdefault(head, []).append(receipt)
            receipt_candidates.append((receipt_path.stat().st_mtime, head))
        except (OSError, ValueError, TypeError, KeyError, subprocess.CalledProcessError):
            continue
    candidates: list[tuple[int, float, str]] = []
    for modified, head in receipt_candidates:
        try:
            if not _checkpoint_chain_verified(root, baseline_sha, head, receipts_by_head):
                continue
            distance = int(
                subprocess.run(
                    ["git", "-C", str(root), "rev-list", "--count", f"{baseline_sha}..{head}"],
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                ).stdout.strip()
            )
            candidates.append((distance, modified, head))
        except (OSError, ValueError, TypeError, KeyError, subprocess.CalledProcessError):
            continue
    if not candidates:
        return baseline_sha, "run_baseline"
    _, _, checkpoint = max(candidates, key=lambda item: (item[0], item[1]))
    return checkpoint, "verified_incremental_receipt"


def iteration_scope(root: Path, run: dict) -> tuple[str, str, list[str]]:
    checkpoint, kind = latest_verified_iteration_checkpoint(root, run["baseline_sha"])
    return checkpoint, kind, _paths_since(root, checkpoint)


def validation_exclusion_targets(run: dict) -> set[str]:
    declaration = run.get("validation_exclusions") or []
    if isinstance(declaration, dict):
        declaration = declaration.get("targets") or []
    if not isinstance(declaration, list) or any(
        not isinstance(target, str) or not target.startswith("verify.")
        for target in declaration
    ):
        raise RunError("validation_exclusions.targets must contain verify targets")
    return set(declaration)


def iteration_plan(root: Path = ROOT, channel: str = CHANNEL_ALL) -> int:
    selected = resolve_run(root)
    if selected is None:
        raise RunError("no registered run; select/register one goal before iteration")
    relative, run = selected
    if run["status"] in ("completed", "superseded"):
        raise RunError("selected run is closed; register/select the next task")
    checks = check_states(root, run)
    checkpoint, checkpoint_kind, paths = iteration_scope(root, run)
    excluded = validation_exclusion_targets(run)
    required = set(select_iteration_targets(paths)) - excluded
    registered = declared_check_targets(run) | implicitly_registered_offline_targets(
        required
    )
    return print_plan(
        paths,
        channel=channel,
        source=relative,
        checks=checks,
        registered_targets=registered,
        iteration_baseline_sha=checkpoint,
        iteration_baseline_kind=checkpoint_kind,
        excluded_targets=excluded,
    )


def print_plan(
    paths: list[str],
    *,
    channel: str = CHANNEL_ALL,
    source: str = "explicit_paths",
    checks: dict | None = None,
    registered_targets: set[str] | None = None,
    iteration_baseline_sha: str = "",
    iteration_baseline_kind: str = "",
    excluded_targets: set[str] | None = None,
) -> int:
    excluded_targets = excluded_targets or set()
    full_affected = set(select_iteration_targets(paths)) - excluded_targets
    partition = channel_target_sets(full_affected, paths=paths)
    channel_affected = set(select_channel_targets(
        full_affected,
        channel,
        paths=paths,
    ))
    deferred_remote = remote_integration_targets(channel_affected)
    required_targets = channel_affected - deferred_remote
    shared_targets = set(partition["shared"]) - deferred_remote
    shared_contract_targets = (
        set(partition["sharedContract"]) - deferred_remote
    )
    blocked = blocked_check_targets(checks or {})
    reusable, covered_by = reusable_execution_targets(
        required_targets,
        checks or {},
        blocked=blocked,
        include_all_exact=True,
    )
    targets = required_targets | {
        check["target"] for check in (checks or {}).values()
    }
    targets -= excluded_targets
    targets.difference_update(reusable | blocked)
    unmapped_paths = [
        path
        for path in paths
        if not select_iteration_targets([path])
        and not path.replace("\\", "/").startswith(NON_SOURCE_PATH_PREFIXES)
        and path.replace("\\", "/") not in NON_SOURCE_PATHS
    ]
    registration_missing = (
        sorted((required_targets - reusable) - registered_targets)
        if registered_targets is not None
        else []
    )
    payload = {
        "schemaVersion": 1,
        "scopeSource": source,
        "iterationBaselineSha": iteration_baseline_sha,
        "iterationBaselineKind": iteration_baseline_kind,
        "recordedChecks": checks or {},
        "mode": "development_incremental_plan",
        "channel": channel,
        "status": "recommendation_only",
        "registrationMode": "planner_managed",
        "changedPathCount": len(paths),
        "requiredTargets": sorted(required_targets),
        "deferredRemoteTargets": sorted(deferred_remote),
        "remoteIntegrationScope": remote_scope_projection(paths),
        "completeAffectedTargets": sorted(full_affected),
        "channelAffectedTargets": sorted(channel_affected),
        "sharedTargets": sorted(shared_targets),
        "sharedContractTargets": sorted(shared_contract_targets),
        "backendOnlyTargets": partition["backendOnly"],
        "frontendOnlyTargets": partition["frontendOnly"],
        "channelHandoffRequired": (
            channel == CHANNEL_FRONTEND and bool(shared_contract_targets)
        ),
        "targets": sorted(targets),
        "requiredLayers": target_layers(required_targets),
        "executionLayers": target_layers(targets),
        "reusedTargets": sorted(reusable),
        "reusedTargetCoverage": covered_by,
        "blockedTargets": sorted(blocked),
        "registrationMissingTargets": registration_missing,
        "excludedTargets": sorted(excluded_targets),
        "unmappedPathCount": len(unmapped_paths),
        "unmappedPaths": unmapped_paths,
        "executionReady": bool(required_targets)
        and not unmapped_paths
        and not (required_targets & blocked),
        "candidateEvidence": False,
        "testsRun": False,
        "manualNonZeroL2Required": bool(unmapped_paths),
    }
    print(f"[local.incremental.plan] {json.dumps(payload, sort_keys=True)}")
    return 0


def reusable_check_targets(checks: dict) -> set[str]:
    """Targets whose every recorded check is reusable at the current inputs."""
    grouped: dict[str, list[str]] = {}
    for check in checks.values():
        grouped.setdefault(check["target"], []).append(check["status"])
    return {
        target
        for target, states in grouped.items()
        if all(state == "reusable" for state in states)
    }


def reusable_execution_targets(
    required: set[str] | list[str],
    checks: dict,
    *,
    blocked: set[str] | None = None,
    include_all_exact: bool = False,
) -> tuple[set[str], dict[str, str]]:
    """Resolve exact and covering reusable targets for one execution scope."""
    required_set = set(required) - set(blocked or ())
    exact = reusable_check_targets(checks)
    reusable = set(exact) if include_all_exact else exact & required_set
    reusable -= set(blocked or ())
    covered_by: dict[str, str] = {}
    for target, covering_targets in COVERING_CHECK_TARGETS.items():
        if target not in required_set or target in reusable:
            continue
        source = next(
            (candidate for candidate in covering_targets if candidate in exact),
            None,
        )
        if source is not None:
            reusable.add(target)
            covered_by[target] = source
    return reusable, covered_by


def reusable_check_results(checks: dict) -> dict[str, dict]:
    """Return complete target rows for reusable declared checks."""
    grouped: dict[str, list[dict]] = {}
    for check in checks.values():
        grouped.setdefault(check["target"], []).append(check)
    results: dict[str, dict] = {}
    for target, states in grouped.items():
        if not all(state.get("status") == "reusable" for state in states):
            continue
        sources = [
            state
            for state in states
            if isinstance(state.get("source_receipt"), str)
            and isinstance(state.get("source_log"), str)
            and _full_digest(state.get("source_log_sha256"))
        ]
        if not sources:
            continue
        source = sources[0]
        results[target] = {
            "target": target,
            "status": "passed",
            "returncode": 0,
            "durationSeconds": 0.0,
            "log": source["source_log"],
            "logSha256": source["source_log_sha256"],
            "reusedFrom": source["source_receipt"],
            "reuseReason": "declared check reused from unchanged receipt",
            "testCount": source.get("test_count", 0),
        }
    return results


def reusable_execution_results(
    checks: dict,
    reusable: set[str],
    covered_by: dict[str, str],
) -> dict[str, dict]:
    """Materialize exact and covering reusable result rows."""
    exact = reusable_check_results(checks)
    results = {
        target: dict(row)
        for target, row in exact.items()
        if target in reusable and target not in covered_by
    }
    for target, source_target in covered_by.items():
        source = exact.get(source_target)
        if source is None:
            continue
        row = dict(source)
        row["target"] = target
        row["reuseReason"] = f"covered by reusable {source_target}"
        results[target] = row
    return results


def blocked_check_targets(checks: dict) -> set[str]:
    """Targets carrying an unchanged failed or dependency-blocked check."""
    grouped: dict[str, list[str]] = {}
    for check in checks.values():
        grouped.setdefault(check["target"], []).append(check["status"])
    return {
        target
        for target, states in grouped.items()
        if any(state in ("failed", "blocked") for state in states)
    }


def write_state(
    *,
    status: str,
    paths: list[str],
    targets: list[str],
    returncode: int | None,
    channel: str = CHANNEL_ALL,
    run_id: str | None = None,
    receipt: str | None = None,
    reason: str = "",
    target_results: list[dict] | None = None,
) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    target_results = target_results or []
    executed_results = [
        row for row in target_results if not row.get("reusedFrom")
    ]
    test_count = sum(
        row.get("testCount")
        for row in target_results
        if type(row.get("testCount")) is int
    )
    payload = {
        "schemaVersion": 1,
        "mode": "development_incremental",
        "channel": channel,
        "runId": run_id,
        "status": status,
        "changedPaths": paths,
        "targets": targets,
        "returncode": returncode,
        "reason": reason,
        "receipt": receipt,
        "targetReceipts": target_results,
        "testsRun": bool(executed_results),
        "checksExecuted": len(executed_results),
        "checksReused": len(target_results) - len(executed_results),
        "testTargetCount": sum(
            row.get("executionKind") == "test" for row in executed_results
        ),
        "staticCheckCount": sum(
            row.get("executionKind") == "static" for row in executed_results
        ),
        "testCount": test_count,
        "verificationPassed": status == "passed",
        "candidateEvidence": False,
        "heavyValidationIncluded": False,
    }
    STATE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _json_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _execution_directory(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        directory = requested
    else:
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        directory = root / ".runtime/frontend-dev-validation/executions" / (
            f"{stamp}-{os.getpid()}-{time.time_ns() % 1_000_000_000}"
        )
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def current_execution_identity(root: Path = ROOT) -> dict:
    return incremental_current_identity(
        root,
        (
            Path(__file__).resolve(),
            root / "scripts/ops/incremental_execution.py",
            root / "make/frontend.mk",
        ),
    )


def _write_receipt(directory: Path, payload: dict) -> Path:
    path = directory / "receipt.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def environment_blockers(root: Path, targets: list[str]) -> list[str]:
    """Known toolchain prerequisites, checked before any target starts.

    A missing dependency is an environment blocker, not a product failure. The
    rule is intentionally limited to registered Node tools used by this planner;
    unknown command failures remain visible as target failures instead of being
    guessed into a pass or blocked state.
    """
    required = {
        tool
        for target in targets
        for tool in [NODE_TOOL_REQUIREMENTS.get(target)]
        if tool
    }
    binary_root = root / "frontend/apps/web/node_modules/.bin"
    missing = [
        f"frontend/apps/web/node_modules/.bin/{tool}"
        for tool in sorted(required)
        if not (binary_root / tool).is_file()
        or not os.access(binary_root / tool, os.X_OK)
    ]
    return missing


def target_execution_kind(target: str) -> str:
    """Classify the repository-level proof a Make target is expected to emit."""
    lowered = target.lower()
    if (
        lowered.startswith("verify.changed_tests")
        or lowered.endswith(TEST_TARGET_SUFFIXES)
    ):
        return "test"
    if (
        lowered.endswith(
            (
                ".assembler",
                ".contract",
                ".coverage",
                ".guard",
                ".lane_coverage",
                ".policy",
                ".registry",
                ".static",
            )
        )
        or ".lint" in lowered
        or ".typecheck" in lowered
    ):
        return "static"
    return "command"


UNITTEST_SUMMARY_PATTERN = re.compile(r"(?im)^Ran (\d+) tests? in [^\n]*$")
UNITTEST_FAILURE_PATTERN = re.compile(r"(?im)^FAILED\b")
UNITTEST_SUCCESS_PATTERN = re.compile(r"(?im)^OK\b")
UNITTEST_SKIP_PATTERN = re.compile(r"\bskipped=(\d+)\b", re.IGNORECASE)
GENERIC_TEST_SUMMARY_PATTERNS = (
    re.compile(
        r"(?im)^.*\b(?:PASS|PASSED|OK)\b.*"
        r"\b(?:cases|checks|assertions|count|scenarios|tests)=(\d+)\b.*$"
    ),
    re.compile(r"(?im)^\s*(\d+)\s+(?:cases|checks|assertions|tests?)\s+passed\b.*$"),
)



TAP_TESTS_PATTERN = re.compile(r"(?m)^# tests (\d+)[ \t]*$")


def tap_execution_metrics(output: str, summary: re.Match) -> dict:
    """Require Node TAP's complete terminal counters; a plan/count is not success."""
    tail = output[summary.start():]
    counters = {}
    for key in ("tests", "suites", "pass", "fail", "cancelled", "skipped", "todo"):
        values = re.findall(rf"(?m)^# {key} (\d+)[ \t]*$", tail)
        if len(values) == 1:
            counters[key] = int(values[0])
    duration = re.findall(r"(?m)^# duration_ms (\d+(?:\.\d+)?)[ \t]*$", tail)
    complete = len(counters) == 7 and len(duration) == 1
    collected = int(summary.group(1))
    consistent = complete and sum(
        counters[key] for key in ("pass", "fail", "cancelled", "skipped", "todo")
    ) == collected
    status = "unknown"
    if consistent:
        status = "failed" if counters["fail"] or counters["cancelled"] else "ok"
    if re.search(r"(?m)^Bail out!", output):
        status = "failed"
    passed = counters.get("pass", 0)
    failed = counters.get("fail", 0)
    skipped = counters.get("skipped", 0)
    executed = passed + failed if consistent else 0
    return {
        "testCount": executed,
        "testCollectedCount": collected,
        "testPassedCount": passed,
        "testFailedCount": failed,
        "testSkippedCount": skipped,
        "testTodoCount": counters.get("todo", 0),
        "testCancelledCount": counters.get("cancelled", 0),
        "testCountObservations": 1,
        "testSummaryStatus": status,
        "testSummarySource": "tap-summary",
        "explicitZeroTestEvidence": collected == 0,
        "allTestsSkippedEvidence": collected > 0 and skipped == collected,
        "testExecutionEvidence": "tap-summary" if consistent and executed > 0 else "none",
    }


def test_execution_metrics(output: str) -> dict:
    """Read the final attributable runner summary, not incidental log text."""
    unittest_summaries = list(UNITTEST_SUMMARY_PATTERN.finditer(output))
    generic_candidates: list[tuple[int, int]] = []
    for pattern in GENERIC_TEST_SUMMARY_PATTERNS:
        generic_candidates.extend(
            (match.start(), int(match.group(1)))
            for match in pattern.finditer(output)
        )
    unittest_candidate = unittest_summaries[-1] if unittest_summaries else None
    generic_candidate = max(generic_candidates) if generic_candidates else None
    tap_summaries = list(TAP_TESTS_PATTERN.finditer(output))
    if tap_summaries and tap_summaries[-1].start() > max(
        unittest_candidate.start() if unittest_candidate else -1,
        generic_candidate[0] if generic_candidate else -1,
    ):
        return tap_execution_metrics(output, tap_summaries[-1])
    if unittest_candidate is not None and (
        generic_candidate is None or unittest_candidate.start() > generic_candidate[0]
    ):
        summary = unittest_candidate
        collected = int(summary.group(1))
        tail = output[summary.end():]
        failure = UNITTEST_FAILURE_PATTERN.search(tail)
        success = UNITTEST_SUCCESS_PATTERN.search(tail)
        summary_status = (
            "failed"
            if failure and (not success or failure.start() < success.start())
            else "ok"
            if success
            else "unknown"
        )
        skip_match = UNITTEST_SKIP_PATTERN.search(tail)
        skipped = min(int(skip_match.group(1)), collected) if skip_match else 0
        executed = max(collected - skipped, 0)
        evidence_source = "unittest-summary"
    elif generic_candidate is not None:
        _, collected = generic_candidate
        skipped = 0
        executed = collected
        summary_status = "ok"
        evidence_source = "runner-summary"
    else:
        collected = 0
        skipped = 0
        executed = 0
        summary_status = "unknown"
        evidence_source = "none"
    return {
        "testCount": executed,
        "testCollectedCount": collected,
        "testSkippedCount": skipped,
        "testCountObservations": 1 if evidence_source != "none" else 0,
        "testSummaryStatus": summary_status,
        "testSummarySource": evidence_source,
        "explicitZeroTestEvidence": evidence_source != "none" and collected == 0,
        "allTestsSkippedEvidence": collected > 0 and executed == 0,
        "testExecutionEvidence": (
            evidence_source if executed > 0 else "none"
        ),
    }


def _run_make_target(target: str, root: Path, log_path: Path) -> dict:
    command = ["make", "--no-print-directory", target]
    execution_kind = target_execution_kind(target)
    started = time.time()
    try:
        # Incremental ORM targets share the profile-selected schema-bound test
        # template and clone a fresh database per target. A caller may select a
        # declared superset module; otherwise bundle is the narrow default.
        env = dict(os.environ, LOCAL_TEST_REUSE_DATABASE="1")
        if not str(env.get("LOCAL_TEST_TEMPLATE_MODULE") or "").strip():
            env["LOCAL_TEST_TEMPLATE_MODULE"] = "smart_construction_bundle"
        result = subprocess.run(
            command,
            cwd=root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except OSError as exc:
        duration = time.time() - started
        log_path.write_text(
            f"COMMAND: {' '.join(command)}\nSTATUS: blocked\nREASON: {exc}\n",
            encoding="utf-8",
        )
        return {
            "target": target,
            "command": command,
            "executionKind": execution_kind,
            "status": "blocked",
            "returncode": None,
            "testCount": None,
            "testExecutionEvidence": "none",
            "durationSeconds": round(duration, 3),
            "reason": str(exc),
            "log": str(log_path),
            "logSha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
        }
    except KeyboardInterrupt:
        duration = time.time() - started
        log_path.write_text(
            f"COMMAND: {' '.join(command)}\nSTATUS: interrupted\n",
            encoding="utf-8",
        )
        return {
            "target": target,
            "command": command,
            "executionKind": execution_kind,
            "status": "interrupted",
            "returncode": 130,
            "testCount": None,
            "testExecutionEvidence": "none",
            "durationSeconds": round(duration, 3),
            "log": str(log_path),
            "logSha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
        }
    duration = time.time() - started
    output = result.stdout or ""
    log_path.write_text(output, encoding="utf-8")
    metrics = test_execution_metrics(output)
    if result.returncode == 0:
        no_test_execution = (
            execution_kind == "test"
            and (
                metrics["testSummaryStatus"] != "ok"
                or metrics["explicitZeroTestEvidence"]
                or metrics["allTestsSkippedEvidence"]
                or metrics["testCount"] <= 0
                or metrics["testExecutionEvidence"] == "none"
            )
        )
        if no_test_execution:
            status = "failed"
            status_reason = (
                "test target reported a failed final runner summary"
                if metrics["testSummaryStatus"] == "failed"
                else "test target reported zero collected tests"
                if metrics["explicitZeroTestEvidence"]
                else "test target skipped every collected test"
                if metrics["allTestsSkippedEvidence"]
                else "test target has no successful final runner summary"
                if metrics["testCount"] > 0 and metrics["testSummaryStatus"] != "ok"
                else "test target reported zero executed tests"
            )
        else:
            status = "passed"
            status_reason = ""
    else:
        status = "failed"
        status_reason = "target exited nonzero"
    print(output, end="" if output.endswith("\n") else "\n", flush=True)
    payload = {
        "target": target,
        "command": command,
        "executionKind": execution_kind,
        "status": status,
        "returncode": result.returncode,
        "durationSeconds": round(duration, 3),
        "log": str(log_path),
        "logSha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
        **metrics,
    }
    if status_reason:
        payload["statusReason"] = status_reason
    return payload


def execute_targets(
    paths: list[str],
    *,
    root: Path = ROOT,
    channel: str = CHANNEL_ALL,
    run_id: str | None = None,
    registered_targets: set[str] | None = None,
    blocked_targets: set[str] | None = None,
    reusable_targets: set[str] | None = None,
    reusable_results: dict[str, dict] | None = None,
    non_reusable_targets: set[str] | None = None,
    receipt_dir: Path | None = None,
    worktree_identity: dict | None = None,
    iteration_checkpoint_sha: str = "",
    iteration_checkpoint_kind: str = "",
    excluded_targets: set[str] | None = None,
) -> int:
    paths = sorted(set(paths))
    excluded_targets = excluded_targets or set()
    full_affected = [
        target for target in select_iteration_targets(paths)
        if target not in excluded_targets
    ]
    partition = channel_target_sets(full_affected, paths=paths)
    channel_affected = select_channel_targets(
        full_affected,
        channel,
        paths=paths,
    )
    deferred_remote = remote_integration_targets(channel_affected)
    required_targets = [
        target for target in channel_affected
        if target not in deferred_remote
    ]
    shared_targets = [
        target for target in partition["shared"]
        if target not in deferred_remote
    ]
    shared_contract_targets = [
        target for target in partition["sharedContract"]
        if target not in deferred_remote
    ]
    blocked = sorted(set(required_targets) & (blocked_targets or set()))
    reusable = sorted(
        (set(required_targets) & (reusable_targets or set())) - set(blocked)
    )
    reusable_results = {
        target: dict(row)
        for target, row in (reusable_results or {}).items()
        if target in reusable
    }
    reusable_evidence_missing = sorted(set(reusable) - set(reusable_results))
    identity = worktree_identity or current_execution_identity(root)
    handoff_receipt = None
    handoff_results: dict[str, dict] = {}
    handoff_missing = (
        channel == CHANNEL_FRONTEND and bool(shared_contract_targets)
    )
    if channel == CHANNEL_FRONTEND and shared_contract_targets:
        handoff_receipt, _, handoff_results = resumable_receipt_results(
            root,
            paths,
            shared_contract_targets,
            identity=identity,
            channel=CHANNEL_BACKEND,
            run_id=run_id,
        )
        handoff_missing = (
            set(handoff_results) != set(shared_contract_targets)
            or not channel_receipt_complete_pass(
                handoff_receipt,
                shared_contract_targets,
            )
        )
    handoff_targets = set(handoff_results) if not handoff_missing else set()
    targets = [
        target
        for target in required_targets
        if target not in reusable and target not in handoff_targets
    ]
    unmapped_paths = [
        path
        for path in paths
        if not select_iteration_targets([path])
        and not path.replace("\\", "/").startswith(NON_SOURCE_PATH_PREFIXES)
        and path.replace("\\", "/") not in NON_SOURCE_PATHS
    ]
    registration_missing = (
        sorted((set(required_targets) - set(reusable)) - registered_targets)
        if registered_targets is not None
        else []
    )
    environment_missing = environment_blockers(root, targets)
    payload = {
        "schemaVersion": 1,
        "mode": "development_incremental_execution",
        "channel": channel,
        "runId": run_id,
        "iterationBaselineSha": iteration_checkpoint_sha,
        "iterationBaselineKind": iteration_checkpoint_kind,
        "status": "not_run",
        "registrationMode": "planner_managed",
        "identity": identity,
        "changedPaths": paths,
        "requiredTargets": required_targets,
        "deferredRemoteTargets": sorted(deferred_remote),
        "remoteIntegrationScope": remote_scope_projection(paths),
        "completeAffectedTargets": sorted(full_affected),
        "channelAffectedTargets": channel_affected,
        "sharedTargets": shared_targets,
        "sharedContractTargets": shared_contract_targets,
        "backendOnlyTargets": partition["backendOnly"],
        "frontendOnlyTargets": partition["frontendOnly"],
        "channelHandoffRequired": (
            channel == CHANNEL_FRONTEND and bool(shared_contract_targets)
        ),
        "channelHandoffStatus": (
            "not_required"
            if channel != CHANNEL_FRONTEND or not shared_contract_targets
            else "missing" if handoff_missing else "ready"
        ),
        "backendHandoffReceipt": (
            _json_path(handoff_receipt, root) if handoff_receipt else None
        ),
        "requiredLayers": target_layers(required_targets),
        "executionLayers": target_layers(targets),
        "targetOrder": required_targets,
        "executionTargetOrder": targets,
        "reusedTargets": reusable,
        "targetResults": [],
        "notRunTargets": [],
        "registrationMissingTargets": registration_missing,
        "excludedTargets": sorted(excluded_targets),
        "blockedTargets": blocked,
        "reusableEvidenceMissingTargets": reusable_evidence_missing,
        "environmentMissing": environment_missing,
        "unmappedPathCount": len(unmapped_paths),
        "unmappedPaths": unmapped_paths,
        "candidateEvidence": False,
        "heavyValidationIncluded": False,
        "testsRun": False,
        "testTargetCount": 0,
        "staticCheckCount": 0,
        "testCount": 0,
        "verificationPassed": False,
        "reason": "",
    }
    if handoff_missing:
        payload.update(
            status="blocked",
            reason="backend contract handoff receipt is required for frontend shared targets",
            notRunTargets=targets,
        )
    elif environment_missing:
        payload.update(
            status="blocked",
            reason="required frontend toolchain dependencies are missing",
            notRunTargets=targets,
        )
    elif unmapped_paths:
        payload.update(
            status="blocked",
            reason="unmapped changed paths require an explicit registered target",
            notRunTargets=targets,
        )
    elif blocked:
        payload.update(
            status="blocked",
            reason="an unchanged recorded failure must be diagnosed before retry",
            notRunTargets=targets,
        )
    elif reusable_evidence_missing:
        payload.update(
            status="blocked",
            reason="reusable target evidence is incomplete",
            notRunTargets=targets,
        )
    if payload["status"] == "blocked":
        receipt_directory = _execution_directory(root, receipt_dir)
        receipt = _write_receipt(receipt_directory, payload)
        write_state(
            status="blocked",
            paths=paths,
            targets=targets,
            returncode=2,
            channel=channel,
            run_id=run_id,
            receipt=_json_path(receipt, root),
            reason=payload["reason"],
            target_results=payload["targetResults"],
        )
        print(
            "[local.incremental] BLOCKED "
            f"reason={payload['reason']} receipt={_json_path(receipt, root)}"
        )
        return 2
    if not targets:
        reused_rows = {
            **{
                target: reusable_results[target]
                for target in reusable
                if target in reusable_results
            },
            **handoff_results,
        }
        if reused_rows:
            payload.update(
                status="passed",
                reason="all required targets reused from unchanged receipts",
                testsRun=False,
                verificationPassed=True,
                executedTargetCount=0,
                reusedTargetCount=len(reused_rows),
                targetResults=[
                    reused_rows[target]
                    for target in required_targets
                    if target in reused_rows
                ],
                reused=True,
            )
        else:
            payload.update(status="not_run", reason="no relevant L2 checks")
        receipt_directory = _execution_directory(root, receipt_dir)
        receipt = _write_receipt(receipt_directory, payload)
        if reused_rows:
            write_incremental_index(
                root,
                paths,
                required_targets,
                identity,
                receipt,
            )
        write_state(
            status=payload["status"],
            paths=paths,
            targets=[],
            returncode=0,
            channel=channel,
            run_id=run_id,
            receipt=_json_path(receipt, root),
            reason=payload["reason"],
            target_results=payload["targetResults"],
        )
        if reused_rows:
            print(
                "[local.incremental] PASS "
                f"reused_targets={len(reused_rows)} receipt={_json_path(receipt, root)}"
            )
        else:
            print(f"[local.incremental] NOT_RUN reason=no_relevant_l2 receipt={_json_path(receipt, root)}")
        return 0

    # A content-identical aggregate cannot override a declared stale dependency
    # (for example a changed runtime readback outside the Git source tree).
    source_receipt = (
        None if set(required_targets) & (non_reusable_targets or set())
        else incremental_verified_receipt(
            root, paths, required_targets, identity,
            channel=None if channel == CHANNEL_ALL else channel,
            run_id=None if channel == CHANNEL_ALL else run_id,
        )
    )
    resume_receipt, _, carried_results = (
        resumable_receipt_results(
            root,
            paths,
            targets,
            identity=identity,
            channel=None if channel == CHANNEL_ALL else channel,
            run_id=run_id,
        )
        if source_receipt is None
        else (None, "", {})
    )
    if resume_receipt is not None:
        carried_results = {
            target: row
            for target, row in carried_results.items()
            if target not in (non_reusable_targets or set())
        }
    receipt_directory = _execution_directory(root, receipt_dir)
    if source_receipt is not None:
        payload.update(
            status="passed",
            reason="reused identical passed execution",
            reused=True,
            sourceReceipt=_json_path(source_receipt, root),
            reusedTargetCount=len(required_targets),
            reusedTargets=required_targets,
            notRunTargets=[],
            testsRun=False,
            verificationPassed=True,
            executedTargetCount=0,
        )
        receipt = _write_receipt(receipt_directory, payload)
        write_state(
            status="passed",
            paths=paths,
            targets=targets,
            returncode=0,
            channel=channel,
            run_id=run_id,
            receipt=_json_path(receipt, root),
            reason=payload["reason"],
            target_results=[],
        )
        print(
            "[local.incremental] PASS "
            f"reused={_json_path(source_receipt, root)} receipt={_json_path(receipt, root)}"
        )
        return 0

    print(
        f"[local.incremental] EXECUTE paths={len(paths)} "
        f"layers={','.join(target_layers(targets))} "
        f"targets={','.join(target for target in targets if target not in carried_results)}"
        + (
            f" resumed={len(carried_results)} source={_json_path(resume_receipt, root)}"
            if resume_receipt is not None
            else ""
        ),
        flush=True,
    )
    write_state(
        status="running",
        paths=paths,
        targets=targets,
        returncode=None,
        channel=channel,
        run_id=run_id,
    )
    result_rows = dict(reusable_results)
    result_rows.update(handoff_results)
    executed_targets: set[str] = set()
    for target in targets:
        if target in carried_results:
            result_rows[target] = carried_results[target]
            continue
        log_path = receipt_directory / f"{target}.log"
        result = _run_make_target(target, root, log_path)
        result["log"] = _json_path(log_path, root)
        result_rows[target] = result
        executed_targets.add(target)
        if result["status"] == "interrupted":
            payload.update(status="interrupted", reason="operator interrupted the target")
            break
        if result["status"] == "blocked":
            payload.update(status="blocked", reason=result.get("reason", "target could not start"))
            break
        if result["status"] == "failed":
            payload.update(status="failed", reason=f"{target} exited nonzero")
            break
    if payload["status"] == "not_run":
        payload.update(status="passed", reason="all required targets exited zero")
    payload["targetResults"] = [
        result_rows[target] for target in required_targets if target in result_rows
    ]
    payload["notRunTargets"] = [
        target
        for target in targets
        if target not in executed_targets and target not in carried_results
    ]
    payload["testsRun"] = bool(executed_targets)
    payload["testTargetCount"] = sum(
        result.get("executionKind") == "test"
        for target, result in result_rows.items()
        if target in executed_targets
    )
    payload["staticCheckCount"] = sum(
        result.get("executionKind") == "static"
        for target, result in result_rows.items()
        if target in executed_targets
    )
    payload["testCount"] = sum(
        result.get("testCount")
        for target, result in result_rows.items()
        if target in executed_targets
        and type(result.get("testCount")) is int
    )
    payload["verificationPassed"] = payload["status"] == "passed"
    payload["executedTargetCount"] = len(executed_targets)
    reused = sorted(set(reusable) | set(carried_results) | handoff_targets)
    payload["reusedTargets"] = reused
    payload["reusedTargetCount"] = len(reused)
    if resume_receipt is not None:
        payload["sourceReceipt"] = _json_path(resume_receipt, root)
    payload["reused"] = bool(reused)
    receipt = _write_receipt(receipt_directory, payload)
    returncode = {
        "passed": 0,
        "failed": 1,
        "blocked": 2,
        "interrupted": 130,
    }[payload["status"]]
    write_state(
        status=payload["status"],
        paths=paths,
        targets=targets,
        returncode=returncode,
        channel=channel,
        run_id=run_id,
        receipt=_json_path(receipt, root),
        reason=payload["reason"],
        target_results=payload["targetResults"],
    )
    if payload["status"] == "passed":
        write_incremental_index(root, paths, required_targets, identity, receipt)
    print(
        f"[local.incremental] {payload['status'].upper()} "
        f"layers={','.join(payload['requiredLayers'])} "
        f"executed={payload['executedTargetCount']} "
        f"reason={payload['reason']} receipt={_json_path(receipt, root)}"
    )
    return returncode



def governed_environment_identity(root: Path, run: dict, required: set[str]) -> dict:
    identity = current_execution_identity(root)
    runtime_checks = {key: check for key, check in run['checks'].items()
                      if check['target'] in required and check.get('kind') != 'offline'}
    if not runtime_checks:
        return identity
    observed = {}
    for key, check in runtime_checks.items():
        if 'readback' not in check:
            continue
        path = root / readback_path(root, check['readback'])
        if path.is_file():
            observed[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    identity['environmentIdentitySha256'] = hashlib.sha256(json.dumps({
        'host': identity.get('environmentIdentitySha256'),
        'declared_environment': run['environment'],
    }, sort_keys=True).encode()).hexdigest()
    # Incomplete runtime observations never certify an equivalent environment.
    identity['environmentReadbackSha256'] = (
        hashlib.sha256(json.dumps(observed, sort_keys=True).encode()).hexdigest()
        if len(observed) == len(runtime_checks) else ''
    )
    return identity


def execute_worktree(
    root: Path = ROOT,
    channel: str = CHANNEL_ALL,
) -> int:
    selected = resolve_run(root)
    if selected is None:
        raise RunError("no registered run; select/register one goal before iteration")
    _, run = selected
    if run["status"] in ("completed", "superseded"):
        raise RunError("selected run is closed; register/select the next task")
    checkpoint, checkpoint_kind, paths = iteration_scope(root, run)
    excluded = validation_exclusion_targets(run)
    required = set(select_iteration_targets(paths)) - excluded
    checks = check_states(root, run)
    registered = declared_check_targets(run) | implicitly_registered_offline_targets(
        required
    )
    blocked = blocked_check_targets(checks) & required
    reusable, covered_by = reusable_execution_targets(
        required,
        checks,
        blocked=blocked,
    )
    reusable_results = reusable_execution_results(checks, reusable, covered_by)
    return execute_targets(
        paths,
        root=root,
        channel=channel,
        run_id=run["id"],
        registered_targets=registered,
        blocked_targets=blocked,
        reusable_targets=reusable,
        reusable_results=reusable_results,
        non_reusable_targets=(required - registered) | {
            check["target"] for check_id, check in checks.items()
            if check["status"] == "stale"
            or (run["checks"].get(check_id, {}).get("kind", "runtime") != "offline"
                and check["status"] != "reusable")
        },
        iteration_checkpoint_sha=checkpoint,
        iteration_checkpoint_kind=checkpoint_kind,
        excluded_targets=excluded,
        worktree_identity=governed_environment_identity(root, run, required),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--channel",
        choices=CHANNELS,
        default=CHANNEL_ALL,
        help="all, backend-only or frontend-only target scope",
    )
    parser.add_argument("--watch", action="store_true", help="watch source content and validate after each settled batch")
    parser.add_argument(
        "--plan-worktree",
        action="store_true",
        help="recommend affected cross-layer L2 targets without running them",
    )
    parser.add_argument("--plan-branch", action="store_true", help="explicit whole-branch comparison for review; not daily continuation")
    parser.add_argument(
        "--execute-worktree",
        action="store_true",
        help="execute every required affected L2 target for the registered run",
    )
    parser.add_argument("--path", action="append", default=[], help="validate an explicit repository-relative path")
    parser.add_argument("--interval", type=float, default=0.75)
    parser.add_argument("--debounce", type=float, default=0.8)
    return parser.parse_args()


def watch(interval: float, debounce: float) -> int:
    previous = content_snapshot()
    write_state(status="watching", paths=[], targets=[], returncode=None)
    print("[local.incremental.watch] watching; candidate build/browser/fingerprint are excluded", flush=True)
    try:
        while True:
            time.sleep(interval)
            current = content_snapshot()
            paths = changed_paths(previous, current)
            if not paths:
                continue
            time.sleep(debounce)
            settled = content_snapshot()
            paths = changed_paths(previous, settled)
            execute_targets(paths)
            previous = settled
    except KeyboardInterrupt:
        write_state(status="stopped", paths=[], targets=[], returncode=0)
        print("[local.incremental.watch] stopped")
        return 0


def main() -> int:
    args = parse_args()
    if args.channel != CHANNEL_ALL and not (
        args.plan_worktree or args.execute_worktree
    ):
        raise SystemExit("--channel is only supported with --plan-worktree or --execute-worktree")
    if sum((args.watch, args.plan_worktree, args.plan_branch, args.execute_worktree)) > 1:
        raise SystemExit(
            "--watch, --plan-worktree, --plan-branch and --execute-worktree are mutually exclusive"
        )
    if args.plan_branch:
        if args.path:
            raise SystemExit("--plan-branch does not accept --path")
        return print_plan(worktree_changed_paths(), source="explicit_whole_branch_review")
    if args.watch:
        return watch(args.interval, args.debounce)
    if args.plan_worktree:
        if args.path:
            raise SystemExit("--plan-worktree does not accept --path")
        try:
            return iteration_plan(channel=args.channel)
        except RunError as exc:
            raise SystemExit(f"run reconciliation required: {exc}") from exc
    if args.execute_worktree:
        if args.path:
            raise SystemExit("--execute-worktree does not accept --path")
        try:
            return execute_worktree(channel=args.channel)
        except RunError as exc:
            raise SystemExit(f"run reconciliation required: {exc}") from exc
    if not args.path:
        raise SystemExit(
            "at least one --path is required outside --watch, --plan-* and --execute-worktree modes"
        )
    targets = set(select_iteration_targets(args.path))
    return execute_targets(args.path, non_reusable_targets=
        targets - implicitly_registered_offline_targets(targets))


if __name__ == "__main__":
    raise SystemExit(main())
