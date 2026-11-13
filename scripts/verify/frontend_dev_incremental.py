#!/usr/bin/env python3
"""Run the smallest registered frontend checks affected by live source changes.

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
import subprocess
import time
import sys
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
)
from scripts.ops.incremental_execution import (
    current_identity as incremental_current_identity,
    verified_receipt as incremental_verified_receipt,
    write_index as write_incremental_index,
)

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
    "scripts/ops/incremental_execution.py",
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
NODE_TOOL_REQUIREMENTS = {
    "verify.frontend.lint.src": "eslint",
    "verify.frontend.typecheck.strict": "vue-tsc",
    "verify.frontend.professional_component_registry.unit": "esbuild",
    "verify.frontend.runtime_identity.unit": "esbuild",
    "verify.frontend.canonical_form_presenter.unit": "esbuild",
    "verify.frontend.approval_contract.closure.unit": "esbuild",
    "verify.frontend.contract_v2_occurrence_authority.unit": "esbuild",
    "verify.frontend.contract_reason_dialog.browser": "node",
    "verify.frontend.primitive_adapter.unit": "esbuild",
    "verify.frontend.scene_primitive_adapter.unit": "esbuild",
    "verify.frontend.navigation_shell.unit": "esbuild",
    "verify.frontend.scene_entry_contract.unit": "esbuild",
    "verify.frontend.product_page_pattern.unit": "esbuild",
    "verify.frontend.action_view_surface_gate_runtime.unit": "esbuild",
    "verify.frontend.action_view_page_size_runtime.unit": "esbuild",
    "verify.frontend.auth_surface.guard": "node",
}


@dataclass(frozen=True)
class Rule:
    fragments: tuple[str, ...]
    targets: tuple[str, ...]


RULES = (
    Rule((
        "addons/smart_core/tests/test_intent_smoke.py",
        "addons/smart_core/core/platform_minimum_nav_contract.py",
        "addons/smart_core/tests/test_platform_minimum_nav_contract.py",
    ), (
        "verify.backend.navigation_delivery.unit",
        "verify.daily.permission_truth.capability.orm",
    )),
    Rule((
        "frontend/apps/web/scripts/route_authority_guard_test.ts",
        "addons/smart_core/delivery/runtime_route_authority.py",
    ), (
        "verify.nav.pro01r.route_authority.unit",
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
        "contracts/generated/contract_structure_fingerprint.json",
    ), (
        "verify.contract.structure_lock",
    )),
    Rule((
        ".agent/",
    ), (
        "verify.agent.ledger.unit",
    )),
    Rule((
        ".gitignore",
    ), (
        "verify.pr.push.unit",
    )),
    Rule((
        "config/acceptance/evolution_binding.v1.json",
        "scripts/verify/acceptance_evolution_binding_guard.py",
        "scripts/verify/test_acceptance_evolution_binding_guard.py",
    ), (
        "verify.acceptance.evolution.binding",
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
        "scripts/ci/gitee_gate_plan.py",
        "scripts/ci/gitee_formal_executor.py",
        "scripts/verify/test_gitee_gate_plan.py",
        "scripts/verify/test_gitee_formal_executor.py",
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
    ), (
        "verify.ci.workflow.contract",
        "verify.github_actions.security",
    )),
    Rule((
        "make/ci.mk",
        "scripts/verify/frontend_static_release_audit.py",
    ), (
        "verify.ci.workflow.contract",
    )),
    Rule((
        "make/contract.mk",
    ), (
        "verify.semantic.registry.lint",
    )),
    Rule((
        "make/codex.mk",
    ), (
        "verify.ci.path_ownership.unit",
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
        "frontend/apps/web/src/stores/session.ts",
        "frontend/apps/web/scripts/standard_page_type_browser.mjs",
    ), (
        "verify.frontend.runtime_identity.unit",
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
        "scripts/audit/generate_frontend_component_driver_takeover_inventory.py",
        "scripts/audit/test_generate_frontend_component_driver_takeover_inventory.py",
        "docs/frontend_productization/rendering-detail/component-driver-takeover-inventory-v1.json",
    ), (
        "verify.frontend.component_driver_takeover.unit",
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
        "addons/smart_core/tests/test_intent_smoke.py",
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
        "/components/FieldValue.vue",
        "/pages/KanbanPage.vue",
        "/pages/listPage/listCellPresentation.ts",
        "/components/professional-fields/professionalBusinessValueModel.ts",
        "/components/professional-fields/ProfessionalBusinessValueControl.vue",
        "/components/professional-fields/professionalBaseFieldModel.ts",
        "/components/business/MyWorkApprovalWorkspace.vue",
        "/app/presentation/productMyWorkPresentation.ts",
        "/app/presentation/boqImportPreview.ts",
        "/components/boq/BoqImportPreviewPanel.vue",
        "/components/template/X2ManyRelationRenderer.vue",
        "/pages/contractForm/ContractFormNativeCanvas.vue",
        "/pages/contractForm/RelationSearchDialog.vue",
        "frontend/apps/web/scripts/boq_import_preview_model_test.ts",
        "scripts/verify/frontend_business_semantics_guard.py",
        "scripts/verify/test_frontend_business_semantics_guard.py",
        "scripts/verify/frontend_localized_display_contract_test.ts",
        "scripts/verify/frontend_collection_status_presentation.test.mjs",
        "scripts/verify/fe_polish_b1_presentation_test.ts",
        "scripts/verify/fe_polish_b1_browser.mjs",
    ), (
        "verify.frontend.business_semantics.unit",
        "verify.frontend.boq_import_preview.unit",
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
    # FormSection consumes the canonical field presentation contract. The broad
    # template rule contributes primitive/page-pattern suites; these explicit
    # rules add the field-to-section mapper and contract-v2 occurrence behaviour
    # locks. FE-PRODUCT-01's expression target joins this set after that target
    # becomes part of the shared baseline.
    Rule((
        "/components/template/FormSection.vue",
        "/components/template/formSection.mapper.ts",
        "/components/template/formSection.types.ts",
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
        "scripts/ci/backend_test_receipt.py",
        "scripts/ci/test_backend_test_receipt.py",
        "scripts/ci/test_backend_test_suite_dispatch_contract.py",
        "scripts/verify/backend_contract_fact_readback_probe.py",
        "scripts/verify/test_backend_contract_fact_readback_probe.py",
        "scripts/test/test.sh",
        ".github/workflows/backend_test_suite.yml",
    ), (
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
        "scripts/verify/test_frontend_acceptance_runtime_profile.py",
        "scripts/verify/static_proxy_target_test.mjs",
    ), (
        "verify.local.dev.static_proxy_target.unit",
    )),
    Rule((
        "scripts/verify/local_dev_payment_settlement_component_journey.mjs",
        "scripts/verify/local_dev_payment_settlement_component_journey.sh",
        "scripts/verify/test_local_development_lifecycle.py",
    ), (
        "verify.local.dev.payment_settlement_journey.unit",
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
    Rule(("/views/SceneView.vue", "/app/sceneEntryContract.ts"), (
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
    ), (
        "verify.frontend.style_system.guard",
    )),
    # ActionView 的 surface 展示形态与列表分页声明都由契约投影消费；改动入口视图
    # 或两个消费运行时都要跑对应行为锁，否则契约消费回归只能在部署面上暴露。
    Rule((
        "/views/ActionView.vue",
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
        "verify.frontend.contract_basis.unit",
        "verify.frontend.style_system.guard",
    )),
    # 契约基础台账与它的守卫是 contract_basis 行为锁的直接输入。改台账/守卫
    # 却落到「未映射」会让这份完整性缺口只能靠人工挑目标，甚至漏跑到交付冻结。
    Rule((
        "docs/architecture/frontend_contract_basis_ledger.json",
        "scripts/verify/frontend_contract_basis_guard.py",
        "scripts/verify/test_frontend_contract_basis_guard.py",
    ), (
        "verify.frontend.contract_basis.unit",
        "verify.frontend.contract_basis.enforce",
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
        "addons/smart_construction_core/security/sc_role_entry_groups.xml",
        "addons/smart_construction_core/tests/test_business_category_entry_policy.py",
    ), (
        "verify.frontend.navigation_shell.unit",
        "verify.role_surface.landing.contract.unit",
    )),
    Rule((
        "addons/smart_construction_core/data/formal_business_product_menu_policy_v1.json",
        "addons/smart_construction_core/data/formal_business_product_menu_policy_v1.json.sha256",
        "config/product_menu_contract_v1.json",
        "scripts/verify/baselines/formal_business_product_menu_policy_v1.json",
        "scripts/verify/baselines/formal_business_product_menu_policy_v1.json.sha256",
        "scripts/verify/test_menu_metadata_batch.py",
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
        "addons/smart_core/delivery/edition_release_snapshot_service.py",
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
        "scripts/ops/incremental_execution.py",
        "scripts/ops/agent_run_context.py",
        "scripts/ops/generated_evidence_paths.py",
        "scripts/verify/test_agent_run_context.py",
        "make/frontend.mk",
    ), (
        "verify.frontend.dev.incremental.unit",
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
    # The exact-head receipt verifier and both sides of its regression suite
    # are one executable contract. The consistency entry runs the verifier
    # tests and the branch-policy lock together, so this P4 input cannot fall
    # through as an unmapped path and lose its non-zero L2 execution.
    Rule((
        "scripts/ops/local_quick_evidence.py",
        "scripts/ops/quick_input_scope.py",
        "scripts/ops/test_local_quick_evidence.py",
        "scripts/ops/test_quick_input_scope.py",
        "scripts/verify/test_local_quick_evidence.py",
    ), (
        "verify.branch.governance.consistency",
    )),
    Rule((
        "scripts/verify/construction_core_extension_policy_maps_split_guard.py",
        "scripts/verify/test_construction_core_extension_policy_maps_split_guard.py",
    ), (
        "verify.construction.policy_maps.unit",
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
        "make/runtime_ops.mk",
        "scripts/dev/frontend_cached_dependencies_restore.sh",
        "scripts/dev/frontend_standard_preview.py",
        "scripts/dev/frontend_acceptance_runtime.sh",
        "scripts/dev/frontend_acceptance_up.sh",
        "scripts/db/create.sh",
        "scripts/test/frontend_acceptance_db_ensure.sh",
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
        "scripts/verify/frontend_my_work_approval_guard.py",
    ), (
        "verify.frontend.my_work_approval.guard",
    )),
    Rule((
        "scripts/verify/frontend_product_page_header_guard.py",
        "scripts/verify/test_frontend_product_page_header_guard.py",
        "frontend/apps/web/src/router/index.ts",
        "frontend/apps/web/src/views/MyWorkView.vue",
    ), (
        "verify.frontend.product_page_header.unit",
    )),
    Rule((
        "scripts/verify/frontend_delivery_hardening_guard.py",
        "scripts/verify/test_frontend_delivery_hardening_guard.py",
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
        "addons/smart_construction_acceptance_fixture/tools/frontend_productization_fixture.py",
        "addons/smart_construction_acceptance_fixture/tests/test_business_scene_lifecycle.py",
        "addons/smart_construction_acceptance_fixture/tests/test_scenario_navigation_maintenance.py",
        "scripts/verify/test_daily_acceptance_fixture_lane.py",
        "scripts/ops/dev_acceptance_release_probe.py",
    ), (
        "verify.daily_dev.acceptance_fixture.unit",
    )),
    Rule(("/pages/contractForm/", "/components/template/"), (
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
        "scripts/verify/frontend_list_optional_columns_contract_test.ts",
    ), (
        "verify.frontend.list_optional_columns.unit",
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
        "scripts/verify/business_entry_matrix_scope_seed.py",
    ), (
        "verify.frontend.business_entry.evidence_scope.unit",
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
        "scripts/release/test_locked_menu_policy_contract.py",
        "scripts/verify/baselines/formal_business_product_menu_policy_v1.json",
        "scripts/verify/baselines/formal_business_product_menu_policy_v1.json.sha256",
        "scripts/verify/test_role_surface_exposure_declaration_guard.py",
    ), (
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
        "addons/smart_construction_core/migrations/17.0.0.180/pre-migrate.py",
        "addons/smart_construction_core/migrations/17.0.0.181/pre-migrate.py",
        "addons/smart_construction_core/tests/test_scenario_direct_entry_initialization.py",
    ), (
        "verify.daily.permission_truth.capability.orm",
        "verify.navigation.publication_consumers.unit",
        "verify.scenario.center_projection.guard",
    )),
    Rule((
        "addons/smart_construction_core/services/scenario_surface_projection.py",
        "scripts/verify/scenario_center_projection_guard.py",
        "scripts/verify/scenario_surface_projection_guard.py",
        "scripts/verify/scene_fact_data_boundary_guard.py",
    ), (
        "verify.navigation.publication_consumers.unit",
        "verify.scenario.center_projection.guard",
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
        "verify.repository.clean_history",
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
        "addons/smart_construction_core/services/review_work_item_service.py",
        "addons/smart_construction_core/tests/__init__.py",
        "addons/smart_construction_core/tests/test_approval_contract_closure.py",
        "scripts/verify/test_general_contract_review_authority.py",
    ), (
        "verify.general_contract.review_authority.unit",
        "verify.approval.contract_closure.orm",
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
    Rule((
        "addons/smart_core/core/native_advisory.py",
        "addons/smart_core/core/draft_feedback.py",
        "addons/smart_core/core/node_component_validation.py",
        "addons/smart_core/tests/test_native_advisory.py",
        "addons/smart_construction_core/tests/test_conditioned_processing_feedback.py",
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
    )),
    Rule((
        "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json",
        "docs/architecture/unified_page_contract_v2/examples/",
        "addons/smart_core/core/contract_lifecycle.py",
    ), (
        "verify.backend.contract_lifecycle.authority",
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
        "addons/smart_core/app_config_engine/services/assemblers/page_assembler.py",
        "addons/smart_core/tests/test_ui_contract_v2_boundaries.py",
    ), (
        "verify.business_config.formal_list.unit",
        "verify.form_structure_authority_unification.unit",
        "verify.unified_page_contract.v2.assembler",
        "verify.contract.entry_equivalence.guard",
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
    ), (
        "verify.test.coverage.registry",
    )),
    Rule((
        "scripts/verify/unified_page_contract_v2_assembler_guard.py",
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
)
FALLBACK_TARGET = "verify.frontend.typecheck.strict"
FORBIDDEN_DEVELOPMENT_TARGET_PARTS = ("quick", "build", "browser", "release", "fingerprint")
# Run bookkeeping and narrative documentation carry no frontend source input:
# reconciling `.agent/` state or writing an iteration record must never be reported
# as an unmapped product path, otherwise every continuation or record update would
# demand a manual L2 selection that has nothing to select. Narrative docs are a
# documentation-only change, which the recorded reuse decision
# (.agent/decisions/evidence-reuse-identity.yaml) states does not invalidate a unit.
NON_SOURCE_PATH_PREFIXES = (".agent/", "docs/")
NON_SOURCE_PATHS = ("AGENTS.md",)


def select_targets(paths: list[str]) -> list[str]:
    selected: set[str] = set()
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
        if (
            normalized.startswith(FRONTEND_SOURCE_ROOTS)
            and normalized.endswith(FRONTEND_SOURCE_SUFFIXES)
        ):
            # A focused rule supplements the source-wide baseline; it never
            # replaces lint or strict typechecking.
            path_targets.update(BASE_FRONTEND_TARGETS)
        selected.update(path_targets)
    targets = sorted(selected)
    if any(part in target for target in targets for part in FORBIDDEN_DEVELOPMENT_TARGET_PARTS):
        raise RuntimeError("development validation selected a candidate-only target")
    return targets


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


def resumable_receipt_results(
    root: Path,
    paths: list[str],
    targets: list[str],
) -> tuple[Path | None, str, dict[str, dict]]:
    """Carry verified target prefixes from a clean interrupted execution.

    An interrupted aggregate receipt can contain many completed targets before
    the operator stops the current target. Those target logs remain useful when
    the source head is still an ancestor and the target set is identical. The
    caller removes targets affected by commits or dirty paths since that head.
    """
    execution_root = root / ".runtime/frontend-dev-validation/executions"
    if not execution_root.is_dir():
        return None, "", {}
    receipts = sorted(
        execution_root.glob("*/receipt.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    expected_paths = sorted(set(paths))
    expected_targets = sorted(set(targets))
    for receipt_path in receipts:
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            head = str(receipt.get("identity", {}).get("head", ""))
            if (
                receipt.get("status") != "interrupted"
                or not receipt.get("identity", {}).get("worktreeClean")
                or len(head) != 40
                or sorted(receipt.get("changedPaths", [])) != expected_paths
                or sorted(receipt.get("requiredTargets", [])) != expected_targets
            ):
                continue
            subprocess.run(
                ["git", "-C", str(root), "merge-base", "--is-ancestor", head, "HEAD"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            results: dict[str, dict] = {}
            for row in receipt.get("targetResults", []):
                target = row.get("target")
                if target not in expected_targets or target in results:
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
                carried["reuseReason"] = "verified target prefix from interrupted execution"
                results[target] = carried
            if results:
                return receipt_path, head, results
        except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError):
            continue
    return None, "", {}


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


def iteration_plan(root: Path = ROOT) -> int:
    selected = resolve_run(root)
    if selected is None:
        raise RunError("no registered run; select/register one goal before iteration")
    relative, run = selected
    if run["status"] in ("completed", "superseded"):
        raise RunError("selected run is closed; register/select the next task")
    checks = check_states(root, run)
    return print_plan(
        delta_paths(root, run["baseline_sha"]),
        source=relative,
        checks=checks,
        registered_targets=declared_check_targets(run),
    )


def print_plan(
    paths: list[str],
    *,
    source: str = "explicit_paths",
    checks: dict | None = None,
    registered_targets: set[str] | None = None,
) -> int:
    required_targets = set(select_targets(paths))
    grouped: dict[str, list[str]] = {}
    for check in (checks or {}).values():
        grouped.setdefault(check["target"], []).append(check["status"])
    reusable = {target for target, states in grouped.items() if all(state == "reusable" for state in states)}
    blocked = {target for target, states in grouped.items() if any(state in ("failed", "blocked") for state in states)}
    targets = required_targets | set(grouped)
    targets.difference_update(reusable | blocked)
    unmapped_paths = [
        path
        for path in paths
        if not select_targets([path])
        and not path.replace("\\", "/").startswith(NON_SOURCE_PATH_PREFIXES)
        and path.replace("\\", "/") not in NON_SOURCE_PATHS
    ]
    registration_missing = (
        sorted(required_targets - registered_targets)
        if registered_targets is not None
        else []
    )
    payload = {
        "schemaVersion": 1,
        "scopeSource": source,
        "recordedChecks": checks or {},
        "mode": "development_incremental_plan",
        "status": "recommendation_only",
        "registrationMode": "planner_managed",
        "changedPathCount": len(paths),
        "requiredTargets": sorted(required_targets),
        "targets": sorted(targets),
        "reusedTargets": sorted(reusable),
        "blockedTargets": sorted(blocked),
        "registrationMissingTargets": registration_missing,
        "unmappedPathCount": len(unmapped_paths),
        "unmappedPaths": unmapped_paths,
        "executionReady": bool(required_targets)
        and not unmapped_paths
        and not (required_targets & blocked),
        "candidateEvidence": False,
        "testsRun": False,
        "manualNonZeroL2Required": bool(unmapped_paths),
    }
    print(f"[frontend.dev.incremental.plan] {json.dumps(payload, sort_keys=True)}")
    return 0


def write_state(
    *,
    status: str,
    paths: list[str],
    targets: list[str],
    returncode: int | None,
    receipt: str | None = None,
    reason: str = "",
    target_results: list[dict] | None = None,
) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schemaVersion": 1,
        "mode": "development_incremental",
        "status": status,
        "changedPaths": paths,
        "targets": targets,
        "returncode": returncode,
        "reason": reason,
        "receipt": receipt,
        "targetReceipts": target_results or [],
        "testsRun": bool(target_results),
        "checksExecuted": len(target_results or []),
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


def _run_make_target(target: str, root: Path, log_path: Path) -> dict:
    command = ["make", "--no-print-directory", target]
    started = time.time()
    try:
        result = subprocess.run(
            command,
            cwd=root,
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
            "status": "blocked",
            "returncode": None,
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
            "status": "interrupted",
            "returncode": 130,
            "durationSeconds": round(duration, 3),
            "log": str(log_path),
            "logSha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
        }
    duration = time.time() - started
    output = result.stdout or ""
    log_path.write_text(output, encoding="utf-8")
    if result.returncode == 0:
        status = "passed"
    else:
        status = "failed"
    print(output, end="" if output.endswith("\n") else "\n", flush=True)
    return {
        "target": target,
        "command": command,
        "status": status,
        "returncode": result.returncode,
        "durationSeconds": round(duration, 3),
        "log": str(log_path),
        "logSha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
    }


def execute_targets(
    paths: list[str],
    *,
    root: Path = ROOT,
    registered_targets: set[str] | None = None,
    blocked_targets: set[str] | None = None,
    receipt_dir: Path | None = None,
    worktree_identity: dict | None = None,
) -> int:
    paths = sorted(set(paths))
    targets = select_targets(paths)
    identity = worktree_identity or current_execution_identity(root)
    unmapped_paths = [
        path
        for path in paths
        if not select_targets([path])
        and not path.replace("\\", "/").startswith(NON_SOURCE_PATH_PREFIXES)
        and path.replace("\\", "/") not in NON_SOURCE_PATHS
    ]
    registration_missing = (
        sorted(set(targets) - registered_targets)
        if registered_targets is not None
        else []
    )
    blocked = sorted(set(targets) & (blocked_targets or set()))
    environment_missing = environment_blockers(root, targets)
    payload = {
        "schemaVersion": 1,
        "mode": "development_incremental_execution",
        "status": "not_run",
        "registrationMode": "planner_managed",
        "identity": identity,
        "changedPaths": paths,
        "requiredTargets": targets,
        "targetOrder": targets,
        "targetResults": [],
        "notRunTargets": [],
        "registrationMissingTargets": registration_missing,
        "blockedTargets": blocked,
        "environmentMissing": environment_missing,
        "unmappedPathCount": len(unmapped_paths),
        "unmappedPaths": unmapped_paths,
        "candidateEvidence": False,
        "heavyValidationIncluded": False,
        "testsRun": False,
        "verificationPassed": False,
        "reason": "",
    }
    if environment_missing:
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
    if payload["status"] == "blocked":
        receipt_directory = _execution_directory(root, receipt_dir)
        receipt = _write_receipt(receipt_directory, payload)
        write_state(
            status="blocked",
            paths=paths,
            targets=targets,
            returncode=2,
            receipt=_json_path(receipt, root),
            reason=payload["reason"],
            target_results=payload["targetResults"],
        )
        print(
            "[frontend.dev.incremental] BLOCKED "
            f"reason={payload['reason']} receipt={_json_path(receipt, root)}"
        )
        return 2
    if not targets:
        payload.update(status="not_run", reason="no relevant L2 checks")
        receipt_directory = _execution_directory(root, receipt_dir)
        receipt = _write_receipt(receipt_directory, payload)
        write_state(
            status="not_run",
            paths=paths,
            targets=[],
            returncode=0,
            receipt=_json_path(receipt, root),
            reason=payload["reason"],
        )
        print(f"[frontend.dev.incremental] NOT_RUN reason=no_relevant_l2 receipt={_json_path(receipt, root)}")
        return 0

    source_receipt = incremental_verified_receipt(root, paths, targets, identity)
    resume_receipt, resume_head, carried_results = (
        resumable_receipt_results(root, paths, targets)
        if source_receipt is None and identity.get("worktreeClean")
        else (None, "", {})
    )
    if resume_receipt is not None:
        invalidated = set(select_targets(_paths_since(root, resume_head)))
        carried_results = {
            target: row
            for target, row in carried_results.items()
            if target not in invalidated
        }
    receipt_directory = _execution_directory(root, receipt_dir)
    if source_receipt is not None:
        payload.update(
            status="passed",
            reason="reused identical passed execution",
            reused=True,
            sourceReceipt=_json_path(source_receipt, root),
            reusedTargetCount=len(targets),
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
            receipt=_json_path(receipt, root),
            reason=payload["reason"],
            target_results=[],
        )
        print(
            "[frontend.dev.incremental] PASS "
            f"reused={_json_path(source_receipt, root)} receipt={_json_path(receipt, root)}"
        )
        return 0

    print(
        f"[frontend.dev.incremental] EXECUTE paths={len(paths)} "
        f"targets={','.join(target for target in targets if target not in carried_results)}"
        + (
            f" resumed={len(carried_results)} source={_json_path(resume_receipt, root)}"
            if resume_receipt is not None
            else ""
        ),
        flush=True,
    )
    write_state(status="running", paths=paths, targets=targets, returncode=None)
    for target in targets:
        if target in carried_results:
            payload["targetResults"].append(carried_results[target])
            continue
        log_path = receipt_directory / f"{target}.log"
        result = _run_make_target(target, root, log_path)
        result["log"] = _json_path(log_path, root)
        payload["targetResults"].append(result)
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
    executed = {result["target"] for result in payload["targetResults"]}
    payload["notRunTargets"] = [target for target in targets if target not in executed]
    payload["testsRun"] = bool(payload["targetResults"])
    payload["verificationPassed"] = payload["status"] == "passed"
    payload["executedTargetCount"] = len(payload["targetResults"]) - len(carried_results)
    payload["reusedTargetCount"] = len(carried_results)
    if resume_receipt is not None:
        payload["sourceReceipt"] = _json_path(resume_receipt, root)
    payload["reused"] = bool(carried_results)
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
        receipt=_json_path(receipt, root),
        reason=payload["reason"],
        target_results=payload["targetResults"],
    )
    if payload["status"] == "passed":
        write_incremental_index(root, paths, targets, identity, receipt)
    print(
        f"[frontend.dev.incremental] {payload['status'].upper()} "
        f"executed={payload['executedTargetCount']} "
        f"reason={payload['reason']} receipt={_json_path(receipt, root)}"
    )
    return returncode


def execute_worktree(root: Path = ROOT) -> int:
    selected = resolve_run(root)
    if selected is None:
        raise RunError("no registered run; select/register one goal before iteration")
    _, run = selected
    if run["status"] in ("completed", "superseded"):
        raise RunError("selected run is closed; register/select the next task")
    paths = delta_paths(root, run["baseline_sha"])
    required = set(select_targets(paths))
    checks = check_states(root, run)
    blocked = {
        target
        for target in required
        if any(
            check["target"] == target and check["status"] in ("failed", "blocked")
            for check in checks.values()
        )
    }
    return execute_targets(
        paths,
        root=root,
        registered_targets=declared_check_targets(run),
        blocked_targets=blocked,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", help="watch source content and validate after each settled batch")
    parser.add_argument(
        "--plan-worktree",
        action="store_true",
        help="recommend affected frontend L2 targets without running them",
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
    print("[frontend.dev.watch] watching; candidate build/browser/fingerprint are excluded", flush=True)
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
        print("[frontend.dev.watch] stopped")
        return 0


def main() -> int:
    args = parse_args()
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
            return iteration_plan()
        except RunError as exc:
            raise SystemExit(f"run reconciliation required: {exc}") from exc
    if args.execute_worktree:
        if args.path:
            raise SystemExit("--execute-worktree does not accept --path")
        try:
            return execute_worktree()
        except RunError as exc:
            raise SystemExit(f"run reconciliation required: {exc}") from exc
    if not args.path:
        raise SystemExit(
            "at least one --path is required outside --watch, --plan-* and --execute-worktree modes"
        )
    return execute_targets(args.path)


if __name__ == "__main__":
    raise SystemExit(main())
