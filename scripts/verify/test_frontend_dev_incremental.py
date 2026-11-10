from __future__ import annotations

import io
import re
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from scripts.verify.frontend_dev_incremental import (
    BASE_FRONTEND_TARGETS,
    FALLBACK_TARGET,
    FRONTEND_SOURCE_ROOTS,
    FRONTEND_SOURCE_SUFFIXES,
    RULES,
    execute_targets,
    iteration_plan,
    print_plan,
    select_targets,
    worktree_changed_paths,
)
from scripts.ops.incremental_execution import current_identity, reuse_identity
from scripts.verify.frontend_style_system_guard import (
    RECORD_RUNTIME_SIZE_LIMITS,
    SIZE_LIMITS,
)

ROOT = Path(__file__).resolve().parents[2]


class FrontendDevelopmentIncrementalTest(unittest.TestCase):
    def test_semantic_registry_declarations_keep_generator_and_lint(self) -> None:
        self.assertEqual(
            select_targets([
                "contracts/registry/component.yaml",
                "contracts/registry/registry.schema.json",
            ]),
            ["verify.semantic.registry.lint"],
        )

    def test_acceptance_evolution_inputs_select_their_binding_lock(self) -> None:
        for path in (
            "config/acceptance/evolution_binding.v1.json",
            "scripts/verify/acceptance_evolution_binding_guard.py",
            "scripts/verify/test_acceptance_evolution_binding_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.acceptance.evolution.binding"],
                )

    def test_delivery_plan_inputs_select_the_delivery_unit(self) -> None:
        for path in (
            "scripts/ops/validation_delivery_plan.py",
            "scripts/verify/test_validation_delivery_plan.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.validation.delivery.unit"],
                )

    def test_component_takeover_inputs_select_their_inventory_lock(self) -> None:
        for path in (
            "scripts/audit/generate_frontend_component_driver_takeover_inventory.py",
            "scripts/audit/test_generate_frontend_component_driver_takeover_inventory.py",
            "docs/frontend_productization/rendering-detail/component-driver-takeover-inventory-v1.json",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.frontend.component_driver_takeover.unit"],
                )

    def test_contract_structure_fingerprint_keeps_its_lock(self) -> None:
        self.assertEqual(
            select_targets(["contracts/generated/contract_structure_fingerprint.json"]),
            ["verify.contract.structure_lock"],
        )

    def test_form_section_host_changes_select_ssr_detail_collection(self) -> None:
        self.assertIn(
            "verify.frontend.professional_detail_collection.unit",
            select_targets(["frontend/apps/web/src/components/template/FormSection.vue"]),
        )

    def test_relation_heading_ssr_test_selects_its_executor(self) -> None:
        self.assertEqual(
            select_targets(["frontend/apps/web/scripts/relation_heading_component_test.mjs"]),
            ["verify.frontend.professional_detail_collection.unit"],
        )

    def test_professional_workflow_guard_selects_its_nonzero_executor(self) -> None:
        for path in (
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
        ):
            with self.subTest(path=path):
                targets = select_targets([path])
                self.assertIn("verify.frontend.professional_workflow.unit", targets)
                self.assertNotIn("verify.frontend.native_form_action_presentation.browser", targets)

    def test_overlay_lifecycle_inputs_select_the_shared_primitive_guard(self) -> None:
        for path in (
            "frontend/apps/web/src/components/design-system/ScDialog.vue",
            "frontend/apps/web/src/components/design-system/ScDrawer.vue",
            "frontend/apps/web/src/composables/useModalLifecycle.ts",
            "frontend/apps/web/src/views/ActionView.vue",
            "frontend/apps/web/src/components/attachment/AttachmentViewer.vue",
            "frontend/apps/web/src/components/GlobalMessagePanel.vue",
            "frontend/apps/web/src/components/product-shell/ProductMobileNavigationDrawer.vue",
            "scripts/verify/frontend_overlay_lifecycle_guard.py",
            "scripts/verify/test_frontend_overlay_lifecycle_guard.py",
        ):
            with self.subTest(path=path):
                self.assertIn(
                    "verify.frontend.overlay_lifecycle.unit",
                    select_targets([path]),
                )

    def test_professional_workflow_unit_executes_interaction_browser(self) -> None:
        source = (ROOT / "make/frontend.mk").read_text(encoding="utf-8")
        block = source.split("verify.frontend.professional_workflow.unit:", 1)[1].split(
            ".PHONY:", 1
        )[0]
        self.assertIn(
            "node frontend/apps/web/scripts/workflow_disabled_reason_browser_test.mjs",
            block,
        )

    def test_primitive_port_inputs_select_port_contract(self) -> None:
        source_targets = set(select_targets([
            "frontend/packages/ui/src/primitive-port/types.ts",
        ]))
        self.assertIn("verify.frontend.primitive_port.unit", source_targets)
        self.assertIn("verify.frontend.scene_primitive_adapter.unit", source_targets)
        self.assertTrue(set(BASE_FRONTEND_TARGETS).issubset(source_targets))

        for path in (
            "frontend/apps/web/scripts/primitive_port_runtime_test.ts",
            "frontend/apps/web/scripts/primitive_port_type_test.ts",
            "frontend/apps/web/tsconfig.primitive-port.json",
            "scripts/verify/frontend_primitive_port_guard.py",
            "scripts/verify/test_frontend_primitive_port_guard.py",
        ):
            with self.subTest(path=path):
                self.assertIn("verify.frontend.primitive_port.unit", select_targets([path]))

    def test_scene_primitive_adapter_inputs_select_real_component_contract(self) -> None:
        for path in (
            "frontend/apps/web/src/components/design-system/scene-adapter/ScSceneButton.vue",
            "frontend/apps/web/src/components/design-system/scene-adapter/buttonContract.ts",
            "frontend/apps/web/scripts/scene_primitive_adapter_test.mjs",
            "frontend/apps/web/scripts/scene_primitive_adapter_bundle.mjs",
            "frontend/apps/web/scripts/scene_primitive_text_controls_test.mjs",
            "frontend/apps/web/tsconfig.scene-primitive-adapter.json",
            "scripts/verify/frontend_scene_primitive_adapter_guard.py",
            "scripts/verify/test_frontend_scene_primitive_adapter_guard.py",
        ):
            with self.subTest(path=path):
                self.assertIn(
                    "verify.frontend.scene_primitive_adapter.unit",
                    select_targets([path]),
                )

    def test_scene_button_behavior_test_change_runs_real_browser_contract(self) -> None:
        targets = select_targets([
            "frontend/apps/web/scripts/scene_primitive_adapter_test.mjs",
        ])
        self.assertIn("verify.frontend.scene_primitive_adapter.unit", targets)
        self.assertIn("verify.frontend.scene_primitive_contract.behavior", targets)

    def test_scene_text_and_adapter_changes_run_real_browser_contract(self) -> None:
        for path in (
            "frontend/apps/web/src/components/design-system/scene-adapter/ScSceneInput.vue",
            "frontend/apps/web/scripts/scene_primitive_text_controls_test.mjs",
        ):
            with self.subTest(path=path):
                self.assertIn(
                    "verify.frontend.scene_primitive_contract.behavior",
                    select_targets([path]),
                )

    def test_action_view_create_boundary_selects_its_executable_contract(self) -> None:
        for path in (
            "frontend/apps/web/src/views/ActionView.vue",
            "frontend/apps/web/src/app/runtime/actionViewInteractionRuntime.ts",
            "frontend/apps/web/scripts/action_view_collection_create_authority_test.ts",
            "scripts/verify/frontend_action_view_page_actions_guard.py",
            "scripts/verify/test_frontend_action_view_page_actions_guard.py",
        ):
            with self.subTest(path=path):
                self.assertIn(
                    "verify.frontend.action_view_page_actions.unit",
                    select_targets([path]),
                )

    def test_business_value_semantics_select_cross_page_executor(self) -> None:
        for path in (
            "frontend/apps/web/src/app/presentation/businessValuePresentation.ts",
            "frontend/apps/web/src/pages/KanbanPage.vue",
            "frontend/apps/web/src/pages/contractForm/ContractFormNativeCanvas.vue",
            "frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue",
            "scripts/verify/frontend_business_semantics_guard.py",
            "scripts/verify/frontend_localized_display_contract_test.ts",
            "scripts/verify/frontend_collection_status_presentation.test.mjs",
        ):
            with self.subTest(path=path):
                self.assertIn(
                    "verify.frontend.business_semantics.unit",
                    select_targets([path]),
                )
        self.assertIn(
            "verify.frontend.boq_import_preview.unit",
            select_targets(["frontend/apps/web/src/app/presentation/boqImportPreview.ts"]),
        )

    def test_navigation_and_release_evidence_tools_select_their_units(self) -> None:
        for path in (
            "config/frontend/authoritative_navigation.json",
            "scripts/verify/frontend_navigation_audit.mjs",
            "scripts/verify/frontend_navigation_audit.test.mjs",
            "scripts/verify/frontend_release_navigation_policy_guard.py",
            "scripts/verify/test_frontend_release_navigation_policy_guard.py",
            "scripts/verify/frontend_release_audit.py",
            "scripts/verify/test_frontend_release_audit.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.frontend.navigation_policy.unit"],
                )
        for path in (
            "scripts/release/frontend_release_evidence.py",
            "scripts/verify/test_frontend_release_evidence_bundle.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.frontend.evidence_bundle.unit"],
                )

    def test_backend_collection_inputs_select_only_offline_workflow_checks(self) -> None:
        for path in (
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
        ):
            with self.subTest(path=path):
                self.assertEqual(select_targets([path]), ["verify.ci.workflow.contract"])

    def test_backend_workflow_selects_security_before_final_delivery(self) -> None:
        self.assertEqual(select_targets([".github/workflows/backend_test_suite.yml"]), [
            "verify.ci.workflow.contract", "verify.github_actions.security",
        ])

    def test_action_semantics_backend_paths_select_existing_executors(self) -> None:
        self.assertIn(
            "verify.frontend.contract_header_action.unit",
            select_targets([
                "addons/smart_construction_core/services/financial_workspace_contract.py",
                "addons/smart_construction_core/tests/test_p1_payment_request_capability.py",
            ]),
        )
        for path in (
            "addons/smart_core/core/unified_page_contract_v2_assembler.py",
            "addons/smart_core/tests/test_unified_page_contract_v2_mobile_compact.py",
        ):
            with self.subTest(path=path):
                targets = select_targets([path])
                for target in (
                    "verify.unified_page_contract.v2.assembler",
                    "verify.unified_page_contract.v2.action",
                    "verify.unified_page_contract.v2.status",
                    "verify.unified_page_contract.v2.runtime",
                ):
                    self.assertIn(target, targets)
        self.assertEqual(
            select_targets([
                "addons/smart_core/tests/test_execute_button_server_action_boundaries.py",
            ]),
            ["verify.approval.contract_closure.orm", "verify.execute_button.authority.unit"],
        )
        self.assertEqual(
            select_targets(["scripts/audit/workflow_state_inventory.py"]),
            ["verify.workflow_action_semantics.guard"],
        )

    def test_contract_visibility_proof_inputs_select_their_executors(self) -> None:
        self.assertEqual(
            select_targets([
                "frontend/apps/web/src/app/contracts/v2/schema.ts",
                "frontend/apps/web/src/app/contracts/v2/types.ts",
            ]),
            [
                "verify.frontend.canonical_form_presenter.unit",
                "verify.frontend.lint.src",
                "verify.frontend.typecheck.strict",
            ],
        )
        for path in (
            "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json",
            "docs/architecture/unified_page_contract_v2/examples/form_project.json",
            "addons/smart_core/core/contract_lifecycle.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.backend.contract_lifecycle.authority"],
                )
        for path in (
            "scripts/verify/unified_page_contract_v2_schema_guard.py",
            "scripts/verify/test_unified_page_contract_v2_schema_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.unified_page_contract.v2.schema"],
                )
        for path in (
            "scripts/verify/native_view_workflow_action_coverage_guard.py",
            "scripts/verify/test_native_view_workflow_action_coverage_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.native_view.workflow_action_coverage"],
                )
        self.assertEqual(
            select_targets(["scripts/verify/frontend_authenticated_intent.mjs"]),
            [
                "verify.frontend.delivery_hardening.guard",
                "verify.frontend.standard_preview.unit",
            ],
        )
        for path in (
            "scripts/verify/frontend_delivery_hardening_browser.mjs",
            "scripts/verify/test_frontend_delivery_hardening_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    [
                        "verify.frontend.delivery_hardening.guard",
                        "verify.frontend.standard_preview.unit",
                    ],
                )
        self.assertEqual(
            select_targets(["scripts/verify/contract_form_runtime_state_protocol_guard.py"]),
            ["verify.contract.architecture.suite"],
        )
        for path in (
            "addons/smart_construction_core/__init__.py",
            "addons/smart_construction_scene/services/capability_scene_targets.py",
            "addons/smart_core/core/capability_provider.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.daily.permission_truth.capability.orm"],
                )
        self.assertEqual(
            select_targets(["addons/smart_construction_core/core_extension.py"]),
            [
                "verify.daily.permission_truth.capability.orm",
                "verify.page.finalize.authority.orm",
                "verify.page.project_finalize.authority.orm",
            ],
        )
        self.assertEqual(
            select_targets(["addons/smart_construction_core/services/capability_registry.py"]),
            [
                "verify.capability.identity_boundary.unit",
                "verify.daily.permission_truth.capability.orm",
            ],
        )
        for path in (
            "addons/smart_construction_scene/models/product_policy.py",
            "addons/smart_construction_scene/tests/test_tenant_scene_activation.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    [
                        "verify.daily.permission_truth.capability.orm",
                        "verify.navigation.publication_consumers.unit",
                    ],
                )
        self.assertEqual(
            select_targets(["addons/smart_construction_core/models/support/product_scenario.py"]),
            [
                "verify.daily.permission_truth.capability.orm",
                "verify.navigation.publication_consumers.unit",
            ],
        )
        self.assertEqual(
            select_targets([
                "addons/smart_construction_scene/tests/test_company_route_scope_cache.py",
            ]),
            ["verify.scene.company_route_scope_cache.orm"],
        )
        for path in (
            "scripts/verify/frontend_acceptance_login_probe.py",
            "scripts/verify/test_frontend_acceptance_login_probe.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.frontend.acceptance_login_probe.unit"],
                )
        self.assertEqual(
            select_targets(["scripts/ci/personal_data_false_positives.json"]),
            ["verify.repository.clean_history"],
        )
        for path in (
            "scripts/verify/frontend_v2_policy_projection_guard.py",
            "scripts/verify/test_frontend_v2_policy_projection_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.form_structure_authority_unification.unit"],
                )

    def test_backend_security_guard_selects_its_own_tests(self) -> None:
        for path in ("scripts/verify/github_actions_security_guard.py",
                     "scripts/verify/test_github_actions_security_guard.py"):
            self.assertEqual(select_targets([path]), ["verify.github_actions.security"])

    def test_backend_authority_closure_guard_selects_its_own_unit(self) -> None:
        for path in (
            "scripts/verify/backend_authority_closure_guard.py",
            "scripts/verify/test_backend_authority_closure_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.backend.authority_closure.unit"],
                )

    def test_approval_contract_inputs_select_backend_and_frontend_owners(self) -> None:
        self.assertEqual(
            set(select_targets([
                "addons/smart_construction_core/services/review_work_item_service.py",
            ])),
            {
                "verify.general_contract.review_authority.unit",
                "verify.approval.contract_closure.orm",
            },
        )
        frontend_targets = set(select_targets([
            "frontend/apps/web/src/pages/contractForm/contractActionPresentation.ts",
        ]))
        self.assertTrue({
                "verify.frontend.approval_contract.closure.unit",
                "verify.frontend.contract_header_action.unit",
                "verify.frontend.canonical_form_presenter.unit",
                "verify.frontend.lint.src",
                "verify.frontend.typecheck.strict",
        } <= frontend_targets)

    def test_authorization_boundary_paths_select_their_owning_checks(self) -> None:
        self.assertEqual(
            select_targets(["addons/smart_core/security/intent_authorization.py"]),
            ["verify.intent_group.authorization.unit"],
        )
        self.assertEqual(
            select_targets(["addons/smart_core/handlers/permission_check.py"]),
            ["verify.permission_check.availability.unit"],
        )
        self.assertEqual(
            select_targets(["addons/smart_construction_core/handlers/payment_request_approval.py"]),
            ["verify.payment.authorization_boundary.orm"],
        )

    def test_capability_identity_paths_select_their_owning_check(self) -> None:
        for path in (
            "scripts/verify/test_capability_identity_boundary.py",
            "addons/smart_construction_core/services/product_menu_source.py",
            "addons/smart_core/delivery/capability_service.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.capability.identity_boundary.unit"],
                )
        self.assertEqual(
            select_targets(["addons/smart_construction_core/services/capability_registry.py"]),
            [
                "verify.capability.identity_boundary.unit",
                "verify.daily.permission_truth.capability.orm",
            ],
        )
        self.assertEqual(
            select_targets(["addons/smart_construction_core/tests/test_capability_registry_service.py"]),
            [
                "verify.capability.identity_boundary.orm",
                "verify.daily.permission_truth.capability.orm",
            ],
        )
        self.assertEqual(
            select_targets([
                "addons/smart_construction_core/data/formal_business_product_menu_policy_v1.json"
            ]),
            ["verify.product.menu.contract_v1.guard"],
        )

    def test_scene_publication_paths_select_their_owning_check(self) -> None:
        for path in (
            "addons/smart_construction_core/models/support/scene_orchestration.py",
            "addons/smart_construction_core/tests/test_scene_publish_usage_backend.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.scene.publication_authority.orm"],
                )

    def test_page_finalize_paths_select_their_owning_check(self) -> None:
        for path in (
            "addons/smart_construction_core/data/view_orchestration_form_section_contract_data.xml",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.page.finalize.authority.orm"],
                )
        self.assertEqual(
            select_targets(["addons/smart_construction_core/core_extension.py"]),
            [
                "verify.daily.permission_truth.capability.orm",
                "verify.page.finalize.authority.orm",
                "verify.page.project_finalize.authority.orm",
            ],
        )
        self.assertEqual(
            select_targets([
                "addons/smart_construction_core/tests/test_core_extension_v2_finalize.py"
            ]),
            [
                "verify.page.finalize.authority.orm",
                "verify.page.project_finalize.authority.orm",
            ],
        )

    def test_unknown_backend_tool_stays_unmapped(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan(["scripts/ci/unknown_backend_collector.py"])
        payload = json.loads(output.getvalue().split("] ", 1)[1])
        self.assertTrue(payload["manualNonZeroL2Required"])
        self.assertEqual(payload["targets"], [])
        self.assertFalse(payload["candidateEvidence"])
        self.assertFalse(payload["testsRun"])

    def test_backend_mapping_does_not_mask_unknown_frontend_input(self) -> None:
        paths = ["scripts/ci/backend_test_receipt.py",
                 "frontend/apps/web/src/newFeature.ts"]
        expected = sorted({
            "verify.ci.workflow.contract",
            FALLBACK_TARGET,
            *BASE_FRONTEND_TARGETS,
        })
        self.assertEqual(select_targets(paths), expected)
        self.assertEqual(select_targets(list(reversed(paths))), expected)

    def test_mixed_known_frontend_and_backend_keeps_both_scopes(self) -> None:
        frontend = "frontend/apps/web/src/views/LoginView.vue"
        backend = "scripts/ci/backend_test_receipt.py"
        self.assertEqual(select_targets([frontend, backend]),
                         sorted(set(select_targets([frontend]) + select_targets([backend]))))

    def test_known_frontend_mapping_does_not_mask_another_unknown_path(self) -> None:
        known = "frontend/apps/web/src/views/LoginView.vue"
        self.assertIn(FALLBACK_TARGET, select_targets([
            known, "frontend/apps/web/src/newFeature.ts",
        ]))

    def test_auth_entry_changes_select_only_auth_surface_checks(self) -> None:
        targets = select_targets(["frontend/apps/web/src/views/LoginView.vue"])
        self.assertEqual(
            targets,
            [
                "verify.frontend.auth_credential.guard",
                "verify.frontend.auth_surface.guard",
                "verify.frontend.lint.src",
                "verify.frontend.page_pattern_reference_parity.unit",
                "verify.frontend.typecheck.strict",
            ],
        )

    def test_activation_and_recovery_changes_share_auth_surface_checks(self) -> None:
        for path in (
            "frontend/apps/web/src/views/AccountActivationView.vue",
            "frontend/apps/web/src/views/PasswordRecoveryView.vue",
        ):
            self.assertEqual(
                select_targets([path]),
                [
                    "verify.frontend.auth_credential.guard",
                    "verify.frontend.auth_surface.guard",
                    "verify.frontend.lint.src",
                    "verify.frontend.page_pattern_reference_parity.unit",
                    "verify.frontend.typecheck.strict",
                ],
            )

    def test_related_changes_are_merged_and_deduplicated(self) -> None:
        targets = select_targets(
            [
                "frontend/apps/web/src/layouts/AppShell.vue",
                "frontend/apps/web/src/layouts/AppShell.css",
                "frontend/apps/web/src/components/design-system/ScCard.vue",
            ]
        )
        self.assertEqual(targets.count("verify.frontend.page_pattern_reference_parity.unit"), 1)
        self.assertIn("verify.frontend.navigation_shell.unit", targets)
        self.assertIn("verify.frontend.primitive_adapter.unit", targets)

    def test_scene_route_change_recommends_scene_entry_contract(self) -> None:
        # The scene runtime is cached by <KeepAlive> and its route ownership rule
        # must be re-verified whenever the view or the rule module changes.
        for path in (
            "frontend/apps/web/src/views/SceneView.vue",
            "frontend/apps/web/src/app/sceneEntryContract.ts",
        ):
            self.assertEqual(
                select_targets([path]),
                [
                    "verify.frontend.lint.src",
                    "verify.frontend.navigation_shell.unit",
                    "verify.frontend.scene_entry_contract.unit",
                    "verify.frontend.typecheck.strict",
                ],
            )

    def test_size_ratcheted_files_route_to_the_size_guard(self) -> None:
        # A file with a size ratchet can only be caught by style_system.guard.
        # If the ratchet is extended without extending the routing, the file
        # silently falls back to typecheck and can grow past its limit again.
        ratcheted = [path.relative_to(Path(__file__).resolve().parents[2]).as_posix() for path in SIZE_LIMITS]
        ratcheted += [
            f"frontend/apps/web/src/pages/contractForm/{name}"
            for name in RECORD_RUNTIME_SIZE_LIMITS
        ]
        self.assertTrue(ratcheted)
        for path in ratcheted:
            with self.subTest(path=path):
                self.assertIn("verify.frontend.style_system.guard", select_targets([path]))

    def test_contract_basis_ledger_and_guard_changes_route_to_the_contract_gate(self) -> None:
        # The ledger and its guard are the direct inputs of the contract-basis
        # behavioural lock. A change to either one that falls through as
        # "unmapped" leaves the completeness gap to be found only at delivery
        # freeze time, so both must route to the contract gate explicitly.
        for path in (
            "docs/architecture/frontend_contract_basis_ledger.json",
            "scripts/verify/frontend_contract_basis_guard.py",
            "scripts/verify/test_frontend_contract_basis_guard.py",
        ):
            with self.subTest(path=path):
                targets = select_targets([path])
                self.assertIn("verify.frontend.contract_basis.unit", targets)
                self.assertIn("verify.frontend.contract_basis.enforce", targets)

    def test_guard_registry_inputs_route_to_the_registry_audit(self) -> None:
        for path in (
            "scripts/verify/registry.yaml",
            "scripts/verify/guard_registry_audit.py",
            "scripts/verify/test_guard_registry_audit.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(select_targets([path]), ["verify.guard.registry"])

    def test_contract_handler_chain_routes_to_its_backend_unit_suites(self) -> None:
        # The v2 contract handler chain is asserted by backend unit suites.  It
        # must not fall through as "unmapped": on 2026-10-10 the chain was edited
        # while only frontend targets ran, so a runtime NameError in
        # `project_form_structure_surfaces` broke every served form contract
        # before this route existed.
        for path in (
            "addons/smart_core/handlers/ui_contract_v2.py",
            "addons/smart_core/handlers/ui_contract_v2_projection.py",
            "addons/smart_core/core/form_structure_authority.py",
            "addons/smart_core/app_config_engine/services/assemblers/page_assembler.py",
        ):
            with self.subTest(path=path):
                targets = select_targets([path])
                self.assertIn("verify.business_config.formal_list.unit", targets)
                self.assertIn("verify.unified_page_contract.v2.assembler", targets)
                self.assertIn("verify.contract.entry_equivalence.guard", targets)
                self.assertIn("verify.form_structure_authority_unification.unit", targets)

    def test_presentation_vocabulary_change_routes_to_the_parity_guard(self) -> None:
        # The projection publishes declared presentation tokens and the renderer
        # implements them.  Editing either side (or the parity guard) must route to
        # the guard that proves every accepted token has a renderer rule; on
        # 2026-10-10 the renderer implemented none of the vocabulary while the
        # projection published it, and the region collapsed on the served contract.
        for path in (
            "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue",
            "addons/smart_core/handlers/ui_contract_v2_projection.py",
            "scripts/verify/form_container_presentation_consumption_guard.py",
        ):
            with self.subTest(path=path):
                self.assertIn(
                    "verify.form_container_presentation.guard",
                    select_targets([path]),
                )

    def test_customer_identity_boundary_change_routes_to_its_guards(self) -> None:
        # The product tree may not carry a customer identity; the governed duty
        # binding under ops_root replaces it. The customer side of that boundary
        # was last found at the frozen candidate, after the whole batch had been
        # reviewed, so editing any file that decides the boundary routes to the
        # boundary guard and the resolver's own unit target instead.
        for path in (
            "config/ops/daily_runtime_database_duties.v1.json",
            "config/ops/daily_runtime_duty_stack.env",
            "config/ops/daily_runtime_duty_stack.yml",
            "scripts/ops/daily_runtime_duty_identity.py",
            "scripts/ops/daily_runtime_database_duty.py",
            "scripts/ops/daily_runtime_tenant_topology_inventory.py",
            "scripts/ops/daily_runtime_tenant_addons_deliver.py",
            "scripts/ops/daily_runtime_tenant_recovery_contract_v1.json",
            "scripts/ops/test_daily_runtime_duty_identity.py",
            "scripts/verify/tenant_product_payload_boundary_guard.py",
        ):
            with self.subTest(path=path):
                targets = select_targets([path])
                self.assertIn("verify.tenant.product_payload_boundary", targets)
                self.assertIn("verify.daily.runtime.duty.identity.unit", targets)

    def test_planner_change_routes_to_the_planner_behaviour_lock(self) -> None:
        # The planner code, its lock and the makefile that defines the target
        # names are one contract. Without this route a renamed target turns
        # "reuse the smallest affected check" into a hard make failure.
        for path in (
            "scripts/verify/frontend_dev_incremental.py",
            "scripts/verify/test_frontend_dev_incremental.py",
            "make/frontend.mk",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    [
                        "verify.agent.resume.unit",
                        "verify.frontend.dev.incremental.unit",
                    ],
                )

    def test_governed_make_lane_change_routes_to_the_iteration_policy_guard(self) -> None:
        # The baseline iteration policy guard declares which targets each
        # governed make lane must still provide. A lane edit therefore has to be
        # validated by that guard; without this route the lane was reported as
        # an unmapped path whose L2 target could only be picked by hand.
        for path in (
            "make/runtime_ops.mk",
            "make/dev.mk",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    [
                        "verify.baseline.iteration.execution.policy",
                        "verify.frontend.standard_preview.unit",
                    ]
                    if path == "make/runtime_ops.mk"
                    else ["verify.baseline.iteration.execution.policy"],
                )
        self.assertEqual(
            select_targets(["make/ci.mk"]),
            [
                "verify.baseline.iteration.execution.policy",
                "verify.ci.workflow.contract",
            ],
        )

    def test_published_face_target_projection_routes_to_its_daily_guard(self) -> None:
        for path in (
            "addons/smart_core/delivery/edition_release_snapshot_service.py",
            "addons/smart_core/tests/test_release_preflight_target_validation.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.daily.published_face.target.unit"],
                )
        self.assertEqual(
            select_targets(["make/guards.mk"]),
            ["verify.guard.registry"],
        )
        for path in (
            "addons/smart_core/delivery/menu_service.py",
            "addons/smart_core/tests/test_delivery_menu_entry_target.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.backend.navigation_delivery.unit"],
                )

    def test_acceptance_fixture_and_browser_tools_select_owned_checks(self) -> None:
        for path in (
            "scripts/dev/frontend_standard_preview.py",
            "scripts/dev/frontend_acceptance_runtime.sh",
            "scripts/dev/frontend_acceptance_up.sh",
            "scripts/verify/frontend_menu_navigation_diagnostic.py",
            "scripts/verify/frontend_my_work_approval_browser.mjs",
            "scripts/verify/frontend_my_work_approval_runtime.py",
            "scripts/verify/frontend_my_work_approval_runtime_ids.py",
            "scripts/verify/test_frontend_release_local_entry.py",
            "scripts/verify/test_frontend_standard_preview.py",
        ):
            with self.subTest(path=path):
                self.assertIn("verify.frontend.standard_preview.unit", select_targets([path]))
        for path in (
            "addons/smart_construction_acceptance_fixture/tools/frontend_productization_fixture.py",
            "addons/smart_construction_acceptance_fixture/tests/test_business_scene_lifecycle.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.daily_dev.acceptance_fixture.unit"],
                )

    def test_primitive_adapter_guard_changes_route_to_their_owned_contract(self) -> None:
        for path in (
            "scripts/verify/frontend_primitive_adapter_guard.py",
            "scripts/verify/test_frontend_primitive_adapter_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.frontend.primitive_adapter.unit"],
                )

    def test_publish_mode_change_runs_the_publish_preflight_contract(self) -> None:
        self.assertEqual(
            select_targets(["make/codex.mk"]),
            [
                "verify.baseline.iteration.execution.policy",
                "verify.ci.path_ownership.unit",
                "verify.pr.push.unit",
            ],
        )
        self.assertEqual(
            select_targets(["scripts/verify/test_pr_publish_preflight.py"]),
            ["verify.pr.push.unit"],
        )

    def test_path_ownership_and_agent_files_route_to_their_own_checks(self) -> None:
        self.assertEqual(
            select_targets(["config/ci/path_ownership_v1.json"]),
            [
                "verify.ci.path_ownership.unit",
                "verify.ci.workflow.contract",
            ],
        )
        self.assertEqual(
            select_targets(["config/ci/risk_tiering_v1.json"]),
            [
                "verify.ci.path_ownership.unit",
                "verify.ci.workflow.contract",
            ],
        )
        self.assertEqual(
            select_targets([".agent/runs/FE-LOOP-02/run.json"]),
            ["verify.agent.ledger.unit"],
        )
        self.assertEqual(
            select_targets([".github/workflows/merge_policy_gate.yml"]),
            [
                "verify.ci.workflow.contract",
                "verify.github_actions.security",
            ],
        )

    def test_every_recommended_target_is_defined_by_a_makefile(self) -> None:
        # A recommendation that no makefile defines would break the smallest
        # affected check and push the reader back to a manual, broad run.
        makefiles = sorted((Path(__file__).resolve().parents[2] / "make").glob("*.mk"))
        self.assertTrue(makefiles)
        text = "\n".join(path.read_text(encoding="utf-8") for path in makefiles)
        targets = sorted({target for rule in RULES for target in rule.targets} | {FALLBACK_TARGET})
        self.assertTrue(targets)

        def has_executable_path(target: str, seen: set[str]) -> bool:
            if target in seen:
                return False
            seen.add(target)
            match = re.search(
                rf"(?m)^{re.escape(target)}\s*:([^\n]*)\n((?:\t[^\n]*\n)*)",
                text,
            )
            if match is None:
                return False
            if match.group(2).strip():
                return True
            dependencies = [
                dependency
                for dependency in match.group(1).split()
                if dependency not in {"guard.prod.forbid"}
            ]
            return any(has_executable_path(dependency, seen) for dependency in dependencies)

        for target in targets:
            with self.subTest(target=target):
                self.assertTrue(
                    has_executable_path(target, set()),
                    f"{target} has no executable recipe or executable dependency",
                )

    def test_run_bookkeeping_alone_is_not_an_unmapped_product_path(self) -> None:
        # Reconciling `.agent/` state carries no frontend source input: reporting
        # it as unmapped would demand a manual L2 selection with nothing to pick.
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                print_plan(
                    [
                        ".agent/active-runs.json",
                        ".agent/runs/TEST/run.json",
                    ]
                ),
                0,
            )
        payload = json.loads(output.getvalue().split("] ", 1)[1])
        self.assertEqual(payload["unmappedPaths"], [])
        self.assertFalse(payload["manualNonZeroL2Required"])

    def test_list_surface_probe_change_routes_to_its_contract_lock(self) -> None:
        # The probe and the contract-lock test that pins its assertions are one
        # contract: editing either one must run the lock, otherwise a stale
        # assertion reaches the daily lane before anyone notices.
        for path in (
            "scripts/verify/frontend_list_surface_structure_browser.mjs",
            "scripts/verify/test_frontend_list_surface_search_contract.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.frontend.list_surface_search_contract.unit"],
                )

    def test_narrative_documentation_is_not_an_unmapped_product_path(self) -> None:
        # Writing an iteration record is a documentation-only change, which the
        # recorded reuse decision says does not invalidate a unit. Reporting it as
        # unmapped demanded a manual L2 selection with nothing to select.
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                print_plan(["docs/ops/iterations/example_20261009.md"]),
                0,
            )
        payload = json.loads(output.getvalue().split("] ", 1)[1])
        self.assertEqual(payload["unmappedPaths"], [])
        self.assertFalse(payload["manualNonZeroL2Required"])

    def test_governed_contract_ledger_still_routes_over_the_docs_exemption(self) -> None:
        # `docs/` is exempt only when nothing maps it; the governed contract-basis
        # ledger stays routed to its behavioural gate.
        targets = select_targets(["docs/architecture/frontend_contract_basis_ledger.json"])
        self.assertIn("verify.frontend.contract_basis.enforce", targets)

    def test_real_unmapped_path_still_requires_manual_l2(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                print_plan(
                    [
                        ".agent/active-runs.json",
                        "addons/smart_core/models/example.py",
                    ]
                ),
                0,
            )
        payload = json.loads(output.getvalue().split("] ", 1)[1])
        self.assertEqual(payload["unmappedPaths"], ["addons/smart_core/models/example.py"])
        self.assertTrue(payload["manualNonZeroL2Required"])

    def test_template_consumer_change_recommends_primitive_adapter(self) -> None:
        targets = select_targets(
            ["frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue"]
        )
        self.assertIn("verify.frontend.primitive_adapter.unit", targets)

    def test_ui_package_theme_change_recommends_primitive_adapter(self) -> None:
        targets = select_targets(["frontend/packages/ui/src/kits/tdesign/theme.css"])
        self.assertIn("verify.frontend.primitive_adapter.unit", targets)

    def test_design_token_change_recommends_style_system_guard(self) -> None:
        for path in (
            "frontend/packages/design-tokens/tokens/pattern.json",
            "frontend/packages/design-tokens/dist/web/tokens.light.css",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.frontend.style_system.guard"],
                )

    def test_rich_text_sanitizer_inputs_select_the_browser_guard(self) -> None:
        for path in (
            "frontend/apps/web/src/utils/safeHtmlLinkTarget.ts",
            "frontend/apps/web/src/utils/sanitizeReadonlyHtml.ts",
            "frontend/apps/web/src/utils/sanitizeRestrictedHtml.ts",
        ):
            with self.subTest(path=path):
                self.assertIn("verify.frontend.rich_text.guard", select_targets([path]))

    def test_unmapped_frontend_change_fails_safe_to_typecheck(self) -> None:
        self.assertEqual(
            select_targets(["frontend/apps/web/src/new-area/NewSurface.vue"]),
            list(BASE_FRONTEND_TARGETS),
        )

    def test_single_vue_change_always_selects_lint_and_strict_typecheck(self) -> None:
        targets = select_targets([
            "frontend/apps/web/src/components/template/FormSection.vue",
        ])
        for target in BASE_FRONTEND_TARGETS:
            self.assertIn(target, targets)
        self.assertIn("verify.frontend.canonical_form_presenter.unit", targets)
        self.assertIn("verify.frontend.contract_v2_occurrence_authority.unit", targets)

    def test_single_ts_change_always_selects_lint_and_strict_typecheck(self) -> None:
        targets = select_targets(["frontend/apps/web/src/utils/money.ts"])
        self.assertEqual(targets, list(BASE_FRONTEND_TARGETS))

    def test_web_tsx_change_uses_the_same_base_targets(self) -> None:
        targets = select_targets(["frontend/apps/web/src/components/Probe.tsx"])
        self.assertEqual(targets, list(BASE_FRONTEND_TARGETS))

    def test_shared_ui_ts_tsx_and_vue_use_base_targets(self) -> None:
        for path in (
            "frontend/packages/ui/src/primitives.ts",
            "frontend/packages/ui/src/components/Probe.tsx",
            "frontend/packages/ui/src/components/SceneObjectPage.vue",
        ):
            with self.subTest(path=path):
                targets = select_targets([path])
                for target in BASE_FRONTEND_TARGETS:
                    self.assertIn(target, targets)

    def test_frontend_lint_and_typecheck_config_changes_use_base_targets(self) -> None:
        for path in (
            "frontend/apps/web/package.json",
            "frontend/apps/web/.eslintrc.cjs",
            "frontend/apps/web/tsconfig.strict.json",
            "frontend/packages/ui/package.json",
            "frontend/packages/ui/tsconfig.json",
        ):
            with self.subTest(path=path):
                targets = select_targets([path])
                for target in BASE_FRONTEND_TARGETS:
                    self.assertIn(target, targets)

    def test_mixed_frontend_and_backend_keeps_base_and_both_specialties(self) -> None:
        targets = select_targets([
            "frontend/apps/web/src/views/LoginView.vue",
            "scripts/ci/backend_test_receipt.py",
        ])
        self.assertEqual(
            targets,
            [
                "verify.ci.workflow.contract",
                "verify.frontend.auth_credential.guard",
                "verify.frontend.auth_surface.guard",
                "verify.frontend.lint.src",
                "verify.frontend.page_pattern_reference_parity.unit",
                "verify.frontend.typecheck.strict",
            ],
        )

    def test_renderer_registry_and_test_share_the_registration_locks(self) -> None:
        registry = "frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts"
        test = "frontend/apps/web/scripts/professional_component_registry_test.ts"
        self.assertEqual(
            select_targets([registry, test]),
            [
                "verify.frontend.lint.src",
                "verify.frontend.professional_component_registry.unit",
                "verify.frontend.typecheck.strict",
                "verify.semantic.registry.lint",
            ],
        )

    def test_renderer_extension_entry_gets_base_plus_registry_lock(self) -> None:
        targets = select_targets([
            "frontend/apps/web/src/extensions/industryRenderers.ts",
        ])
        self.assertEqual(
            targets,
            [
                "verify.frontend.lint.src",
                "verify.frontend.professional_component_registry.unit",
                "verify.frontend.typecheck.strict",
                "verify.semantic.registry.lint",
            ],
        )

    def test_semantic_registry_tools_keep_their_generator_and_node_locks(self) -> None:
        self.assertEqual(
            select_targets([
                "scripts/verify/semantic_registry_lint.py",
                "scripts/verify/test_semantic_registry_lint.py",
                "scripts/verify/test_node_component_registry.py",
            ]),
            [
                "verify.semantic.registry.lint",
            ],
        )

    def test_contract_make_fragment_keeps_the_generator_lock(self) -> None:
        self.assertEqual(
            select_targets(["make/contract.mk"]),
            ["verify.semantic.registry.lint"],
        )

    def test_candidate_static_proxy_paths_keep_their_proxy_unit(self) -> None:
        self.assertEqual(
            select_targets([
                "scripts/release/static_proxy_target.mjs",
                "scripts/release/release_static_server.mjs",
                "scripts/dev/local_dev_candidate_frontend.py",
                "scripts/verify/test_frontend_acceptance_runtime_profile.py",
                "scripts/verify/static_proxy_target_test.mjs",
            ]),
            ["verify.local.dev.static_proxy_target.unit"],
        )

    def test_payment_settlement_journey_keeps_local_lifecycle_contract(self) -> None:
        self.assertEqual(
            select_targets([
                "scripts/verify/local_dev_payment_settlement_component_journey.mjs",
                "scripts/verify/local_dev_payment_settlement_component_journey.sh",
                "scripts/verify/test_local_development_lifecycle.py",
            ]),
            ["verify.local.dev.payment_settlement_journey.unit"],
        )

    def test_detail_collection_guard_keeps_its_behavior_target(self) -> None:
        self.assertEqual(
            select_targets([
                "scripts/verify/frontend_professional_detail_collection_guard.py",
                "scripts/verify/test_frontend_professional_detail_collection_guard.py",
            ]),
            [
                "verify.frontend.professional_detail_collection.unit",
            ],
        )

    def test_incremental_executor_guard_change_runs_its_own_unit(self) -> None:
        for path in (
            "scripts/verify/frontend_dev_incremental.py",
            "scripts/ops/incremental_execution.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    [
                        "verify.agent.resume.unit",
                        "verify.frontend.dev.incremental.unit",
                    ],
                )

    def test_execution_policy_guard_change_runs_its_own_unit(self) -> None:
        self.assertEqual(
            select_targets([
                "scripts/verify/baseline_iteration_execution_policy_guard.py",
            ]),
            ["verify.baseline.iteration.execution.policy"],
        )

    def test_non_frontend_change_does_not_trigger_frontend_validation(self) -> None:
        self.assertEqual(select_targets(["docs/example.md"]), [])

    def test_development_selection_never_contains_candidate_work(self) -> None:
        targets = select_targets(
            [
                "frontend/apps/web/src/views/LoginView.vue",
                "frontend/apps/web/src/pages/contractForm/ContractForm.vue",
            ]
        )
        joined = " ".join(targets)
        for forbidden in ("quick", "build", "browser", "release", "fingerprint"):
            self.assertNotIn(forbidden, joined)

    def test_worktree_plan_includes_committed_dirty_and_untracked_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Codex Test"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "codex-test@example.invalid"],
                check=True,
            )
            baseline = root / "baseline.txt"
            baseline.write_text("baseline\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "baseline.txt"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "baseline"], check=True)
            baseline_sha = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
            subprocess.run(
                ["git", "-C", str(root), "update-ref", "refs/remotes/origin/main", baseline_sha],
                check=True,
            )

            committed = root / "frontend/apps/web/src/components/template/Committed.vue"
            committed.parent.mkdir(parents=True)
            committed.write_text("committed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "topic"], check=True)
            committed.write_text("dirty\n", encoding="utf-8")
            untracked = root / "frontend/packages/ui/src/new-theme.css"
            untracked.parent.mkdir(parents=True)
            untracked.write_text("untracked\n", encoding="utf-8")

            self.assertEqual(
                worktree_changed_paths(root),
                [
                    "frontend/apps/web/src/components/template/Committed.vue",
                    "frontend/packages/ui/src/new-theme.css",
                ],
            )

    def test_plan_reports_recommendations_without_running_tests(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                print_plan(["frontend/packages/ui/src/kits/tdesign/theme.css"]),
                0,
            )
        text = output.getvalue()
        self.assertIn('"status": "recommendation_only"', text)
        self.assertIn('"testsRun": false', text)
        self.assertIn("verify.frontend.primitive_adapter.unit", text)

    def test_plan_keeps_manual_l2_for_unmapped_paths_in_mixed_change(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                print_plan(
                    [
                        "frontend/packages/ui/src/kits/tdesign/theme.css",
                        "addons/smart_core/models/example.py",
                    ]
                ),
                0,
            )
        text = output.getvalue()
        self.assertIn('"manualNonZeroL2Required": true', text)
        self.assertIn('"unmappedPathCount": 1', text)
        self.assertIn('"unmappedPaths": ["addons/smart_core/models/example.py"]', text)
        self.assertIn("verify.frontend.primitive_adapter.unit", text)

    def test_plan_reports_planner_owned_targets_without_duplicate_run_registration(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                print_plan(
                    ["frontend/apps/web/src/utils/money.ts"],
                    registered_targets={"verify.frontend.typecheck.strict"},
                ),
                0,
            )
        payload = json.loads(output.getvalue().split("] ", 1)[1])
        self.assertEqual(payload["registrationMissingTargets"], ["verify.frontend.lint.src"])
        self.assertEqual(payload["registrationMode"], "planner_managed")
        self.assertTrue(payload["executionReady"])
        self.assertFalse(payload["testsRun"])
        self.assertFalse(payload["manualNonZeroL2Required"])

    def test_planner_target_set_is_not_reduced_to_explicit_run_registration(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                print_plan(
                    [
                        "frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts",
                        "frontend/apps/web/src/components/template/FormSection.vue",
                        "frontend/apps/web/src/utils/money.ts",
                    ],
                    registered_targets={"verify.frontend.expression.unit"},
                ),
                0,
            )
        payload = json.loads(output.getvalue().split("] ", 1)[1])
        self.assertTrue(payload["executionReady"])
        self.assertEqual(payload["registrationMode"], "planner_managed")
        self.assertIn("verify.frontend.lint.src", payload["registrationMissingTargets"])
        self.assertIn("verify.frontend.typecheck.strict", payload["registrationMissingTargets"])
        self.assertIn(
            "verify.frontend.professional_component_registry.unit",
            payload["registrationMissingTargets"],
        )
        self.assertFalse(payload["testsRun"])


class FrontendCoverageContractTest(unittest.TestCase):
    root = Path(__file__).resolve().parents[2]

    def target_block(self, text: str, target: str) -> str:
        match = re.search(
            rf"(?m)^{re.escape(target)}\s*:[^\n]*(?:\n\t[^\n]*)*",
            text,
        )
        self.assertIsNotNone(match, f"missing make target: {target}")
        return match.group(0)

    def test_base_targets_consume_shared_ui_checks(self) -> None:
        makefile = (self.root / "make/frontend.mk").read_text(encoding="utf-8")
        lint_header = re.search(
            r"(?m)^verify\.frontend\.lint\.src\s*:([^\n]*)",
            makefile,
        )
        typecheck_header = re.search(
            r"(?m)^verify\.frontend\.typecheck\.strict\s*:([^\n]*)",
            makefile,
        )
        self.assertIsNotNone(lint_header)
        self.assertIsNotNone(typecheck_header)
        self.assertIn("verify.frontend.ui.lint", lint_header.group(1))
        self.assertIn("verify.frontend.ui.typecheck.strict", typecheck_header.group(1))

        lint = self.target_block(makefile, "verify.frontend.ui.lint")
        self.assertIn("../../packages/ui/src", lint)
        self.assertIn("--ext .ts,.tsx,.vue", lint)
        typecheck = self.target_block(makefile, "verify.frontend.ui.typecheck.strict")
        self.assertIn("-p frontend/packages/ui/tsconfig.json", typecheck)

    def test_web_lint_script_covers_supported_typescript_suffixes(self) -> None:
        package = json.loads(
            (self.root / "frontend/apps/web/package.json").read_text(encoding="utf-8")
        )
        self.assertIn("--ext .ts,.tsx,.vue", package["scripts"]["lint:src"])

    def test_shared_ui_tsconfig_covers_supported_source_suffixes(self) -> None:
        config = json.loads(
            (self.root / "frontend/packages/ui/tsconfig.json").read_text(encoding="utf-8")
        )
        include = set(config["include"])
        self.assertIn("src/**/*.ts", include)
        self.assertIn("src/**/*.tsx", include)
        self.assertIn("src/**/*.vue", include)

    def test_planner_roots_and_suffixes_all_select_base_checks(self) -> None:
        for root in FRONTEND_SOURCE_ROOTS:
            for suffix in FRONTEND_SOURCE_SUFFIXES:
                path = f"{root}__coverage_probe{suffix}"
                with self.subTest(path=path):
                    targets = select_targets([path])
                    for target in BASE_FRONTEND_TARGETS:
                        self.assertIn(target, targets)


class IncrementalExecutionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root.joinpath("frontend/apps/web/src").mkdir(parents=True)
        self.root.joinpath("frontend/apps/web/src/NewSurface.vue").write_text(
            "<template />\n",
            encoding="utf-8",
        )
        binaries = self.root / "frontend/apps/web/node_modules/.bin"
        binaries.mkdir(parents=True)
        for tool in ("eslint", "vue-tsc", "esbuild", "node"):
            binary = binaries / tool
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            binary.chmod(0o755)
        self.root.joinpath("Makefile").write_text(
            "verify.frontend.lint.src:\n"
            "\t@printf 'lint check executed\\n'\n"
            "verify.frontend.typecheck.strict:\n"
            "\t@printf 'typecheck executed\\n'\n",
            encoding="utf-8",
        )
        self.state_patch = mock.patch(
            "scripts.verify.frontend_dev_incremental.write_state"
        )
        self.state_patch.start()
        self.addCleanup(self.state_patch.stop)

    def execute(
        self,
        *,
        registered=None,
        blocked=None,
        paths=None,
        identity=None,
    ) -> tuple[int, dict]:
        receipt_dir = self.root / f"receipt-{len(list(self.root.glob('receipt-*')))}"
        output = io.StringIO()
        with redirect_stdout(output):
            code = execute_targets(
                paths or ["frontend/apps/web/src/NewSurface.vue"],
                root=self.root,
                registered_targets=registered,
                blocked_targets=blocked,
                receipt_dir=receipt_dir,
                worktree_identity=identity or {
                    "head": "a" * 40,
                    "worktreeClean": True,
                    "authoritySha256": {"planner.py": "b" * 64},
                },
            )
        return code, json.loads((receipt_dir / "receipt.json").read_text())

    def test_execution_runs_each_required_target_and_records_logs(self) -> None:
        code, receipt = self.execute(registered=set(BASE_FRONTEND_TARGETS))
        self.assertEqual(code, 0)
        self.assertEqual(receipt["status"], "passed")
        self.assertTrue(receipt["testsRun"])
        self.assertTrue(receipt["verificationPassed"])
        self.assertEqual(
            [row["target"] for row in receipt["targetResults"]],
            list(BASE_FRONTEND_TARGETS),
        )
        for row in receipt["targetResults"]:
            self.assertEqual(row["returncode"], 0)
            self.assertEqual(len(row["logSha256"]), 64)
            self.assertTrue((self.root / row["log"]).is_file())

    def test_tsx_execution_uses_the_same_base_targets(self) -> None:
        path = "frontend/apps/web/src/NewSurface.tsx"
        self.root.joinpath(path).write_text("export const probe = true;\n", encoding="utf-8")
        code, receipt = self.execute(
            registered=set(BASE_FRONTEND_TARGETS),
            paths=[path],
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            [row["target"] for row in receipt["targetResults"]],
            list(BASE_FRONTEND_TARGETS),
        )
        self.assertTrue(receipt["verificationPassed"])

    def test_shared_ui_source_execution_includes_base_and_focused_checks(self) -> None:
        path = "frontend/packages/ui/src/components/Probe.tsx"
        self.root.joinpath(path).parent.mkdir(parents=True)
        self.root.joinpath(path).write_text("export const probe = true;\n", encoding="utf-8")
        self.root.joinpath("Makefile").write_text(
            self.root.joinpath("Makefile").read_text(encoding="utf-8")
            + "verify.frontend.primitive_adapter.unit:\n"
            "\t@printf 'primitive adapter executed\\n'\n"
            "verify.frontend.page_pattern_reference_parity.unit:\n"
            "\t@printf 'page pattern executed\\n'\n",
            encoding="utf-8",
        )
        required = set(select_targets([path]))
        code, receipt = self.execute(registered=required, paths=[path])
        self.assertEqual(code, 0)
        self.assertTrue(set(BASE_FRONTEND_TARGETS).issubset(receipt["requiredTargets"]))
        self.assertIn("verify.frontend.primitive_adapter.unit", receipt["requiredTargets"])
        self.assertTrue(receipt["verificationPassed"])

    def test_missing_run_registration_is_owned_by_the_planner(self) -> None:
        code, receipt = self.execute(registered={"verify.frontend.lint.src"})
        self.assertEqual(code, 0)
        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(receipt["registrationMode"], "planner_managed")
        self.assertEqual(
            receipt["registrationMissingTargets"],
            ["verify.frontend.typecheck.strict"],
        )
        self.assertEqual(
            [row["target"] for row in receipt["targetResults"]],
            list(BASE_FRONTEND_TARGETS),
        )
        self.assertEqual(receipt["notRunTargets"], [])
        self.assertTrue(receipt["testsRun"])
        self.assertTrue(receipt["verificationPassed"])

    def test_identical_clean_execution_reuses_verified_receipt_without_rerun(self) -> None:
        identity = {
            "head": "a" * 40,
            "worktreeClean": True,
            "authoritySha256": {"planner.py": "b" * 64},
        }
        first_code, first = self.execute(
            registered=set(BASE_FRONTEND_TARGETS),
            identity=identity,
        )
        self.assertEqual(first_code, 0)
        self.assertFalse(first["reused"])
        with mock.patch(
            "scripts.verify.frontend_dev_incremental._run_make_target",
            side_effect=AssertionError("reusable execution must not rerun targets"),
        ):
            second_code, second = self.execute(
                registered=set(BASE_FRONTEND_TARGETS),
                identity=identity,
            )
        self.assertEqual(second_code, 0)
        self.assertTrue(second["reused"])
        self.assertEqual(second["status"], "passed")
        self.assertEqual(second["reusedTargetCount"], len(BASE_FRONTEND_TARGETS))
        self.assertEqual(second["targetResults"], [])
        self.assertFalse(second["testsRun"])
        self.assertTrue(second["verificationPassed"])
        self.assertEqual(second["sourceReceipt"], "receipt-0/receipt.json")

    def test_dirty_execution_identity_never_reuses_a_clean_receipt(self) -> None:
        clean = {
            "head": "a" * 40,
            "worktreeClean": True,
            "authoritySha256": {"planner.py": "b" * 64},
        }
        dirty = {**clean, "worktreeClean": False}
        self.execute(registered=set(BASE_FRONTEND_TARGETS), identity=clean)
        code, receipt = self.execute(
            registered=set(BASE_FRONTEND_TARGETS),
            identity=dirty,
        )
        self.assertEqual(code, 0)
        self.assertFalse(receipt["reused"])
        self.assertTrue(receipt["targetResults"])

    def test_tampered_target_log_invalidates_reuse(self) -> None:
        identity = {
            "head": "a" * 40,
            "worktreeClean": True,
            "authoritySha256": {"planner.py": "b" * 64},
        }
        _, first = self.execute(
            registered=set(BASE_FRONTEND_TARGETS),
            identity=identity,
        )
        log = self.root / first["targetResults"][0]["log"]
        log.write_text("tampered\n", encoding="utf-8")
        code, second = self.execute(
            registered=set(BASE_FRONTEND_TARGETS),
            identity=identity,
        )
        self.assertEqual(code, 0)
        self.assertFalse(second["reused"])
        self.assertTrue(second["targetResults"])

    def test_unchanged_recorded_failure_blocks_instead_of_blind_retry(self) -> None:
        code, receipt = self.execute(
            registered=set(BASE_FRONTEND_TARGETS),
            blocked={"verify.frontend.typecheck.strict"},
        )
        self.assertEqual(code, 2)
        self.assertEqual(receipt["status"], "blocked")
        self.assertEqual(receipt["blockedTargets"], ["verify.frontend.typecheck.strict"])
        self.assertEqual(receipt["targetResults"], [])

    def test_missing_frontend_toolchain_blocks_before_target_execution(self) -> None:
        self.root.joinpath("frontend/apps/web/node_modules/.bin/eslint").unlink()
        code, receipt = self.execute(registered=set(BASE_FRONTEND_TARGETS))
        self.assertEqual(code, 2)
        self.assertEqual(receipt["status"], "blocked")
        self.assertEqual(
            receipt["environmentMissing"],
            ["frontend/apps/web/node_modules/.bin/eslint"],
        )
        self.assertEqual(receipt["targetResults"], [])
        self.assertEqual(receipt["notRunTargets"], list(BASE_FRONTEND_TARGETS))

    def test_no_relevant_l2_is_not_run_not_pass(self) -> None:
        code, receipt = self.execute(
            registered=set(BASE_FRONTEND_TARGETS),
            paths=["docs/record.md"],
        )
        self.assertEqual(code, 0)
        self.assertEqual(receipt["status"], "not_run")
        self.assertFalse(receipt["testsRun"])
        self.assertFalse(receipt["verificationPassed"])

    def test_pure_unmapped_source_is_blocked_with_nonzero_exit(self) -> None:
        path = "addons/smart_core/models/example.py"
        code, receipt = self.execute(
            registered=set(BASE_FRONTEND_TARGETS),
            paths=[path],
        )
        self.assertEqual(code, 2)
        self.assertEqual(receipt["status"], "blocked")
        self.assertEqual(receipt["unmappedPaths"], [path])
        self.assertEqual(receipt["requiredTargets"], [])
        self.assertEqual(receipt["targetResults"], [])
        self.assertFalse(receipt["testsRun"])
        self.assertFalse(receipt["verificationPassed"])

    def test_target_failure_is_failed_and_preserves_nonzero_exit(self) -> None:
        self.root.joinpath("Makefile").write_text(
            "verify.frontend.lint.src:\n"
            "\t@printf 'lint check executed\\n'\n"
            "verify.frontend.typecheck.strict:\n"
            "\t@exit 7\n",
            encoding="utf-8",
        )
        code, receipt = self.execute(registered=set(BASE_FRONTEND_TARGETS))
        self.assertEqual(code, 1)
        self.assertEqual(receipt["status"], "failed")
        self.assertNotEqual(receipt["targetResults"][-1]["returncode"], 0)
        self.assertEqual(receipt["notRunTargets"], [])
        self.assertFalse(receipt["verificationPassed"])

    def test_interruption_is_distinct_from_failure_and_not_pass(self) -> None:
        interrupted = {
            "target": "verify.frontend.lint.src",
            "command": ["make", "--no-print-directory", "verify.frontend.lint.src"],
            "status": "interrupted",
            "returncode": 130,
            "durationSeconds": 0.1,
            "log": "receipt/interrupted.log",
            "logSha256": "a" * 64,
        }
        with mock.patch(
            "scripts.verify.frontend_dev_incremental._run_make_target",
            return_value=interrupted,
        ):
            code, receipt = self.execute(registered=set(BASE_FRONTEND_TARGETS))
        self.assertEqual(code, 130)
        self.assertEqual(receipt["status"], "interrupted")
        self.assertEqual(receipt["executedTargetCount"], 1)
        self.assertFalse(receipt["verificationPassed"])

    def test_target_start_failure_is_blocked_not_failed(self) -> None:
        blocked = {
            "target": "verify.frontend.lint.src",
            "command": ["make", "--no-print-directory", "verify.frontend.lint.src"],
            "status": "blocked",
            "returncode": None,
            "durationSeconds": 0.1,
            "reason": "make could not start",
            "log": "receipt/blocked.log",
            "logSha256": "b" * 64,
        }
        with mock.patch(
            "scripts.verify.frontend_dev_incremental._run_make_target",
            return_value=blocked,
        ):
            code, receipt = self.execute(registered=set(BASE_FRONTEND_TARGETS))
        self.assertEqual(code, 2)
        self.assertEqual(receipt["status"], "blocked")
        self.assertEqual(receipt["notRunTargets"], ["verify.frontend.typecheck.strict"])
        self.assertFalse(receipt["verificationPassed"])


class IncrementalExecutionIdentityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.name", "Codex Test"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.email", "codex@example.invalid"],
            check=True,
        )
        self.authority = self.root / "planner.py"
        self.authority.write_text("one\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "base"], check=True)

    def test_clean_head_identity_binds_head_and_authority_bytes(self) -> None:
        identity = current_identity(self.root, (self.authority,))
        self.assertEqual(identity["head"], subprocess.check_output(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            text=True,
        ).strip())
        self.assertTrue(identity["worktreeClean"])
        self.assertEqual(len(identity["authoritySha256"]["planner.py"]), 64)

    def test_dirty_worktree_is_never_reusable(self) -> None:
        self.authority.write_text("two\n", encoding="utf-8")
        self.assertFalse(current_identity(self.root, (self.authority,))["worktreeClean"])

    def test_bookkeeping_commit_keeps_runtime_reuse_identity(self) -> None:
        before = current_identity(self.root, (self.authority,))
        (self.root / "docs").mkdir()
        (self.root / "docs/record.md").write_text("record\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "docs"], check=True)
        after = current_identity(self.root, (self.authority,))
        self.assertNotEqual(before["head"], after["head"])
        self.assertEqual(reuse_identity(before), reuse_identity(after))

    def test_runtime_source_commit_changes_reuse_identity(self) -> None:
        before = current_identity(self.root, (self.authority,))
        self.authority.write_text("two\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "source"], check=True)
        after = current_identity(self.root, (self.authority,))
        self.assertNotEqual(reuse_identity(before), reuse_identity(after))


class RunScopedPlannerTest(unittest.TestCase):
    def setUp(self):
        from scripts.verify.test_agent_run_context import RunContextTest
        self.fixture = RunContextTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_registered_run_does_not_need_origin_or_reinventory_branch_history(self):
        fixture = self.fixture
        fixture.run['baseline_sha'] = fixture.git('rev-parse', 'HEAD')
        fixture.save()
        fixture.write('source/new.py', 'change')
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(iteration_plan(fixture.root), 0)
        self.assertIn('.agent/runs/TEST/run.json', output.getvalue())
        self.assertNotIn('branch_fallback', output.getvalue())
        self.assertNotIn('source/a.py', output.getvalue())
        self.assertIn('source/new.py', output.getvalue())

    def test_receipt_advice_never_claims_tests_ran(self):
        self.fixture.receipt()
        output = io.StringIO()
        with redirect_stdout(output): iteration_plan(self.fixture.root)
        self.assertIn('reusable', output.getvalue())
        self.assertIn('"testsRun": false', output.getvalue())

    def test_reusable_target_is_not_recommended_again(self):
        self.fixture.receipt()
        output = io.StringIO()
        with redirect_stdout(output): iteration_plan(self.fixture.root)
        payload = json.loads(output.getvalue().split('] ', 1)[1])
        self.assertIn('verify.test', payload['reusedTargets'])
        self.assertNotIn('verify.test', payload['targets'])

    def test_unchanged_failure_is_blocked_not_blindly_retried(self):
        self.fixture.receipt('failed', 2)
        output = io.StringIO()
        with redirect_stdout(output): iteration_plan(self.fixture.root)
        payload = json.loads(output.getvalue().split('] ', 1)[1])
        self.assertIn('verify.test', payload['blockedTargets'])
        self.assertNotIn('verify.test', payload['targets'])

    def test_unmet_dependency_is_blocked_in_recommendations(self):
        self.fixture.second_check()
        output = io.StringIO()
        with redirect_stdout(output): iteration_plan(self.fixture.root)
        payload = json.loads(output.getvalue().split('] ', 1)[1])
        self.assertEqual(payload['recordedChecks']['second']['status'], 'blocked')
        self.assertIn('verify.test', payload['blockedTargets'])
        self.assertNotIn('verify.test', payload['targets'])

    def test_missing_registration_cannot_trigger_full_branch_inventory(self):
        from scripts.ops.agent_run_context import RunError
        (self.fixture.root / ".agent/active-runs.json").unlink()
        with self.assertRaises(RunError): iteration_plan(self.fixture.root)

    def test_invalid_registration_cannot_silently_fallback(self):
        from scripts.ops.agent_run_context import RunError
        self.fixture.run['branch'] = 'fix/other'
        self.fixture.save()
        with self.assertRaises(RunError): iteration_plan(self.fixture.root)


if __name__ == "__main__":
    unittest.main()
