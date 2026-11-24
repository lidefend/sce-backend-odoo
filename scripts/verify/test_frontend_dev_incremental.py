from __future__ import annotations

import hashlib
import io
import json
import re
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
    FRONTEND_SOURCE_TARGETS,
    FRONTEND_SOURCE_SUFFIXES,
    RULES,
    CHANNEL_ALL,
    CHANNEL_BACKEND,
    CHANNEL_FRONTEND,
    channel_target_class,
    channel_target_sets,
    execute_targets,
    implicitly_registered_offline_targets,
    iteration_scope,
    iteration_plan,
    print_plan,
    remote_integration_targets,
    remote_scope_projection,
    reusable_execution_results,
    reusable_execution_targets,
    select_targets,
    select_channel_targets,
    select_iteration_targets,
    target_layers,
    validation_exclusion_targets,
    worktree_changed_paths,
)
from scripts.ops.incremental_execution import current_identity, reuse_identity
from scripts.ops.incremental_execution import committed_runtime_tree_sha256
from scripts.verify import frontend_dev_incremental as incremental
from scripts.verify.frontend_style_system_guard import (
    RECORD_RUNTIME_SIZE_LIMITS,
    SIZE_LIMITS,
)

ROOT = Path(__file__).resolve().parents[2]


class FrontendDevelopmentIncrementalTest(unittest.TestCase):
    def test_channel_targets_partition_without_losing_shared_or_union_members(self):
        targets = {
            "verify.frontend.lint.src",
            "verify.frontend.typecheck.strict",
            "verify.smart_construction_core.changed_tests.orm",
            "verify.smart_core.close_02.module_baseline",
            "verify.unified_page_contract.v2",
            "verify.frontend.contract_v2_occurrence_authority.unit",
            "verify.agent.resume.unit",
        }
        partition = channel_target_sets(targets)
        self.assertEqual(
            set(partition["backend"]) | set(partition["frontend"]),
            targets,
        )
        self.assertEqual(
            partition["shared"],
            [
                "verify.agent.resume.unit",
                "verify.frontend.contract_v2_occurrence_authority.unit",
                "verify.unified_page_contract.v2",
            ],
        )
        self.assertEqual(
            partition["frontendOnly"],
            ["verify.frontend.lint.src", "verify.frontend.typecheck.strict"],
        )
        self.assertEqual(
            partition["backendOnly"],
            [
                "verify.smart_construction_core.changed_tests.orm",
                "verify.smart_core.close_02.module_baseline",
            ],
        )
        self.assertEqual(
            select_channel_targets(targets, CHANNEL_ALL),
            sorted(targets),
        )

    def test_channel_classification_keeps_contract_and_governance_shared(self):
        self.assertEqual(
            channel_target_class("verify.frontend.contract_v2_occurrence_authority.unit"),
            "shared",
        )
        self.assertEqual(
            channel_target_class("verify.agent.resume.unit"),
            "shared",
        )
        self.assertEqual(
            channel_target_class("verify.frontend.lint.src"),
            CHANNEL_FRONTEND,
        )
        self.assertEqual(
            channel_target_class("verify.smart_construction_core.changed_tests.orm"),
            CHANNEL_BACKEND,
        )

    def test_shared_contract_path_is_visible_to_both_channels(self):
        paths = ["frontend/apps/web/src/app/contracts/v2/schema.ts"]
        targets = select_iteration_targets(paths)
        partition = channel_target_sets(targets, paths=paths)
        self.assertIn("verify.frontend.lint.src", partition["backend"])
        self.assertIn("verify.frontend.typecheck.strict", partition["backend"])
        self.assertTrue(partition["sharedContract"])
        self.assertTrue(set(partition["sharedContract"]) <= set(partition["frontend"]))

    def test_lane_coverage_is_selected_only_for_verification_surface_changes(self):
        demo_paths = [
            "demo_addons/smart_construction_demo/data/demo/wutao_full_product_user.xml",
            "demo_addons/smart_construction_demo/seed/steps/step_demo_users.py",
        ]
        for path in demo_paths:
            with self.subTest(path=path):
                self.assertNotIn(
                    "audit.verification.lane_coverage.check",
                    select_iteration_targets([path]),
                )

        for path in (
            "make/ci.mk",
            ".github/workflows/professional_quality_gate.yml",
            "scripts/audit/verification_lane_dispositions.json",
            "scripts/verify/registry.yaml",
            "scripts/verify/frontend_dev_incremental.py",
            "scripts/ops/local_quick_evidence.py",
            "docs/audit/guard_registry/guard_registry.json",
        ):
            with self.subTest(path=path):
                self.assertIn(
                    "audit.verification.lane_coverage.check",
                    select_iteration_targets([path]),
                )

    def test_backend_and_frontend_channels_keep_deferred_module_baseline(self):
        targets = select_iteration_targets([
            "addons/smart_core/handlers/business_config_change_set.py",
        ])
        backend = set(select_channel_targets(targets, CHANNEL_BACKEND))
        frontend = set(select_channel_targets(targets, CHANNEL_FRONTEND))
        self.assertIn("verify.smart_core.close_02.module_baseline", backend)
        self.assertEqual(frontend, set())
        self.assertEqual(
            remote_integration_targets(backend),
            {"verify.smart_core.close_02.module_baseline"},
        )

    def test_real_backend_frontend_and_mixed_paths_select_expected_channels(self):
        backend_path = "addons/smart_core/handlers/business_config_change_set.py"
        frontend_path = "frontend/apps/web/src/views/ActionView.vue"
        backend_targets = select_iteration_targets([backend_path])
        frontend_targets = select_iteration_targets([frontend_path])
        self.assertTrue(select_channel_targets(backend_targets, CHANNEL_BACKEND))
        self.assertFalse(select_channel_targets(backend_targets, CHANNEL_FRONTEND))
        self.assertTrue(select_channel_targets(frontend_targets, CHANNEL_FRONTEND))
        self.assertFalse(select_channel_targets(frontend_targets, CHANNEL_BACKEND))
        mixed = select_iteration_targets([backend_path, frontend_path])
        mixed_partition = channel_target_sets(
            mixed,
            paths=[backend_path, frontend_path],
        )
        self.assertTrue(mixed_partition["backendOnly"])
        self.assertTrue(mixed_partition["frontendOnly"])
        self.assertEqual(
            set(mixed_partition["backend"]) | set(mixed_partition["frontend"]),
            set(mixed),
        )

    def test_remote_scope_projection_records_each_exact_head_responsibility(self):
        cases = {
            "addons/smart_core/handlers/business_config_change_set.py": {
                "backendSuiteRequired": True,
                "backendSeedModules": ["smart_core"],
                "frontendReleaseGateRequired": False,
                "controlPlaneChanged": False,
            },
            "addons/smart_core/tests/test_authentication_compatibility.py": {
                "backendSuiteRequired": True,
                "backendSeedModules": ["smart_core"],
                "frontendReleaseGateRequired": False,
                "controlPlaneChanged": False,
            },
            "frontend/apps/web/src/views/ActionView.vue": {
                "backendSuiteRequired": False,
                "backendSeedModules": [],
                "frontendReleaseGateRequired": True,
                "controlPlaneChanged": False,
            },
            "frontend/apps/web/src/app/contracts/v2/schema.ts": {
                "backendSuiteRequired": False,
                "backendSeedModules": [],
                "frontendReleaseGateRequired": True,
                "controlPlaneChanged": False,
            },
            "make/ci.mk": {
                "backendSuiteRequired": False,
                "backendSeedModules": [],
                "frontendReleaseGateRequired": False,
                "controlPlaneChanged": True,
            },
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                scope = remote_scope_projection([path])
                for key, value in expected.items():
                    self.assertEqual(value, scope[key])
                self.assertEqual(
                    "exact_head_remote_planners",
                    scope["authority"],
                )

        unknown = remote_scope_projection(["unexpected/runtime/loader.py"])
        self.assertTrue(unknown["backendSuiteRequired"])
        self.assertEqual(
            ["unexpected/runtime/loader.py"],
            unknown["unknownPaths"],
        )

    def test_covering_reusable_check_satisfies_its_selected_subcheck(self):
        checks = {
            "lane_coverage": {
                "target": "verify.verification.lane_coverage",
                "status": "reusable",
                "source_receipt": ".runtime/EXAMPLE/lane_coverage.json",
                "source_log": ".runtime/lane_coverage.log",
                "source_log_sha256": "a" * 64,
            },
        }
        required = {"audit.verification.lane_coverage.check"}
        reusable, covered_by = reusable_execution_targets(required, checks)
        self.assertEqual(required, reusable)
        self.assertEqual(
            {
                "audit.verification.lane_coverage.check":
                    "verify.verification.lane_coverage",
            },
            covered_by,
        )
        row = reusable_execution_results(
            checks,
            reusable,
            covered_by,
        )["audit.verification.lane_coverage.check"]
        self.assertEqual(
            "audit.verification.lane_coverage.check",
            row["target"],
        )
        self.assertIn(
            "verify.verification.lane_coverage",
            row["reuseReason"],
        )

    def test_plan_does_not_execute_a_subcheck_covered_by_a_reusable_check(self):
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan(
                ["make/ci.mk"],
                checks={
                    "lane_coverage": {
                        "target": "verify.verification.lane_coverage",
                        "status": "reusable",
                    },
                },
            )
        payload = json.loads(output.getvalue().split("] ", 1)[1])
        subcheck = "audit.verification.lane_coverage.check"
        self.assertIn(subcheck, payload["reusedTargets"])
        self.assertNotIn(subcheck, payload["targets"])
        self.assertNotIn(subcheck, payload["registrationMissingTargets"])
        self.assertEqual(
            "verify.verification.lane_coverage",
            payload["reusedTargetCoverage"][subcheck],
        )

    def test_local_channels_and_remote_exact_scope_use_the_same_path_facts(self):
        from scripts.ci import backend_impact_plan

        graph = {
            "smart_core": {
                "depends": set(),
                "tests": True,
                "installable": True,
            },
            "smart_construction_core": {
                "depends": {"smart_core"},
                "tests": True,
                "installable": True,
            },
        }
        production = "addons/smart_core/handlers/business_config_change_set.py"
        production_targets = select_iteration_targets([production])
        production_partition = channel_target_sets(
            production_targets,
            paths=[production],
        )
        production_remote = backend_impact_plan.select(
            [production],
            graph,
            graph,
        )
        self.assertTrue(production_partition["backend"])
        self.assertFalse(production_partition["frontend"])
        self.assertEqual(
            ["smart_construction_core", "smart_core"],
            production_remote["modules"],
        )
        self.assertEqual(
            {"verify.smart_core.close_02.module_baseline"},
            remote_integration_targets(production_partition["backend"]),
        )

        test_only = (
            "addons/smart_core/tests/"
            "test_authentication_compatibility.py"
        )
        test_targets = select_iteration_targets([test_only])
        test_partition = channel_target_sets(test_targets, paths=[test_only])
        test_remote = backend_impact_plan.select([test_only], graph, graph)
        self.assertEqual(
            ["verify.changed_tests.orm"],
            test_partition["backend"],
        )
        self.assertEqual([], test_partition["frontend"])
        self.assertEqual(
            ["smart_construction_core", "smart_core"],
            test_remote["modules"],
        )
        self.assertEqual(
            set(),
            remote_integration_targets(test_partition["backend"]),
        )
        test_scope = remote_scope_projection([test_only])
        self.assertTrue(test_scope["backendSuiteRequired"])
        self.assertEqual(["smart_core"], test_scope["backendSeedModules"])

        frontend = "frontend/apps/web/src/views/ActionView.vue"
        frontend_targets = select_iteration_targets([frontend])
        frontend_partition = channel_target_sets(
            frontend_targets,
            paths=[frontend],
        )
        self.assertEqual([], frontend_partition["backend"])
        self.assertTrue(frontend_partition["frontend"])
        self.assertEqual(
            [],
            backend_impact_plan.select([frontend], graph, graph)["modules"],
        )
        self.assertTrue(
            remote_scope_projection([frontend])[
                "frontendReleaseGateRequired"
            ]
        )

        contract = "frontend/apps/web/src/app/contracts/v2/schema.ts"
        contract_targets = select_iteration_targets([contract])
        contract_partition = channel_target_sets(
            contract_targets,
            paths=[contract],
        )
        self.assertTrue(contract_partition["backend"])
        self.assertTrue(contract_partition["frontend"])
        self.assertTrue(contract_partition["sharedContract"])
        self.assertEqual(
            [],
            backend_impact_plan.select([contract], graph, graph)["modules"],
        )

        control = "make/ci.mk"
        control_targets = select_iteration_targets([control])
        control_partition = channel_target_sets(control_targets, paths=[control])
        control_remote = backend_impact_plan.select([control], graph, graph)
        self.assertEqual([], control_remote["modules"])
        self.assertEqual(
            [
                "verify.baseline.iteration.execution.policy",
                "verify.ci.workflow.contract",
            ],
            control_remote["tool_checks"],
        )
        self.assertNotIn("verify.ci.workflow.contract", control_targets)
        self.assertEqual(
            set(control_targets),
            set(control_partition["backend"]) | set(control_partition["frontend"]),
        )

    def test_remote_entries_preserve_exact_head_scope_and_owner_execution(self):
        professional = (
            ROOT / ".github/workflows/professional_quality_gate.yml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            '--base "${BASE_SHA}"',
            professional,
        )
        self.assertIn(
            '--head "${CHECKOUT_SHA}"',
            professional,
        )
        self.assertIn(
            "scope_mode: ${{ (needs.professional_authorization.outputs."
            "candidate_requested == 'true' || needs.professional_authorization.outputs."
            "backend_tooling_changed == 'true') && 'full' || 'focused' }}",
            professional,
        )
        self.assertIn("make ${TOOL_CHECKS}", professional)
        self.assertIn(
            'test "${TOOL_CHECKS_RAN}" = true',
            professional,
        )

        backend_suite = (
            ROOT / ".github/workflows/backend_test_suite.yml"
        ).read_text(encoding="utf-8")
        for fragment in (
            'test "$(git rev-parse HEAD)" = "${HEAD_SHA}"',
            '--frozen-plan "${RUNNER_TEMP}/frozen-plan/backend-plan.json"',
            '--plan-sha256 "${PLAN_SHA256}"',
            '--shard "${SHARD_INDEX}"',
            '--module "${module}" --selectors',
        ):
            self.assertIn(fragment, backend_suite)

        frontend = (
            ROOT / ".github/workflows/frontend_release_gate.yml"
        ).read_text(encoding="utf-8")
        for fragment in (
            "ref: ${{ env.CHECKOUT_SHA }}",
            'test "$(git rev-parse HEAD)" = "${CHECKOUT_SHA}"',
            "Resolve effective frontend lane",
            "pnpm -C frontend/apps/web lint:src",
            "pnpm -C frontend/apps/web typecheck:strict",
            "pnpm -C frontend/apps/web test",
        ):
            self.assertIn(fragment, frontend)

    def test_backend_handoff_receipt_is_channel_and_run_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / ".runtime/frontend-dev-validation/executions/one/verify.unified_page_contract.v2.log"
            log.parent.mkdir(parents=True)
            log.write_text("contract ok\n")
            identity = {
                "head": "a" * 40,
                "runtimeTreeSha256": "b" * 64,
                "authoritySha256": {"authority.py": "c" * 64},
                "worktreeClean": False,
            }
            receipt = {
                "status": "passed",
                "verificationPassed": True,
                "channel": CHANNEL_BACKEND,
                "runId": "RUN",
                "identity": identity,
                "requiredTargets": ["verify.unified_page_contract.v2"],
                "targetResults": [{
                    "target": "verify.unified_page_contract.v2",
                    "status": "passed",
                    "returncode": 0,
                    "log": str(log.relative_to(root)),
                    "logSha256": hashlib.sha256(log.read_bytes()).hexdigest(),
                }],
                "notRunTargets": [],
            }
            path = log.parent / "receipt.json"
            path.write_text(json.dumps(receipt))
            found, _, rows = incremental.resumable_receipt_results(
                root,
                [],
                ["verify.unified_page_contract.v2"],
                identity=identity,
                channel=CHANNEL_BACKEND,
                run_id="RUN",
            )
            self.assertEqual(found, path)
            self.assertIn("verify.unified_page_contract.v2", rows)
            self.assertTrue(
                incremental.channel_receipt_complete_pass(
                    found,
                    {"verify.unified_page_contract.v2"},
                )
            )
            self.assertEqual(
                incremental.resumable_receipt_results(
                    root,
                    [],
                    ["verify.unified_page_contract.v2"],
                    identity=identity,
                    channel=CHANNEL_FRONTEND,
                    run_id="RUN",
                )[0],
                None,
            )
            receipt["status"] = "failed"
            receipt["verificationPassed"] = False
            path.write_text(json.dumps(receipt))
            self.assertFalse(
                incremental.channel_receipt_complete_pass(
                    path,
                    {"verify.unified_page_contract.v2"},
                )
            )

    def test_frontend_shared_contract_targets_block_without_backend_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_path = root / ".runtime/state.json"
            receipt_dir = root / ".runtime/one"
            identity = {
                "head": "a" * 40,
                "tree": "d" * 40,
                "runtimeTreeSha256": "b" * 64,
                "authoritySha256": {"authority.py": "c" * 64},
                "worktreeClean": False,
            }
            with mock.patch.object(incremental, "STATE_PATH", state_path), \
                    mock.patch.object(incremental, "_run_make_target") as run:
                status = execute_targets(
                    ["frontend/apps/web/src/app/contracts/v2/schema.ts"],
                    root=root,
                    channel=CHANNEL_FRONTEND,
                    run_id="RUN",
                    worktree_identity=identity,
                    receipt_dir=receipt_dir,
                )
            self.assertEqual(status, 2)
            run.assert_not_called()
            receipt = json.loads((receipt_dir / "receipt.json").read_text())
            self.assertEqual(receipt["channelHandoffStatus"], "missing")
            self.assertIn("backend contract handoff", receipt["reason"])
            self.assertEqual(
                incremental.resumable_receipt_results(
                    root,
                    [],
                    ["verify.unified_page_contract.v2"],
                    identity=identity,
                    channel=CHANNEL_BACKEND,
                    run_id="OTHER",
                )[0],
                None,
            )

    def test_industry_business_model_02_paths_route_to_batch_checks(self):
        paths = (
            "addons/smart_construction_core/handlers/my_work_summary.py",
            "addons/smart_construction_core/models/core/boq.py",
            "addons/smart_construction_core/models/core/plan_management.py",
            "addons/smart_construction_core/models/core/project_core.py",
            "addons/smart_construction_core/models/core/settlement.py",
            "addons/smart_construction_core/services/project_dashboard_builders/project_progress_builder.py",
            "addons/smart_construction_core/services/project_execution_builders/project_execution_tasks_builder.py",
            "addons/smart_construction_core/views/core/plan_management_views.xml",
            "addons/smart_construction_core/wizard/project_task_from_boq_wizard.py",
            "scripts/e2e/e2e_boq_to_wbs_task_preflight.py",
            "scripts/verify/industry_business_model_02_data_audit.py",
        )
        for path in paths:
            with self.subTest(path=path):
                targets = set(select_targets([path]))
                self.assertIn("verify.industry_business_model_02.orm", targets)
                self.assertIn("verify.industry_business_model_02.data_audit", targets)

    def test_backend_workflow_contract_does_not_select_http_samples(self):
        targets = set(select_targets([
            "addons/smart_construction_core/models/core/project_core.py",
            "addons/smart_construction_core/tests/test_workflow_contract_backend.py",
        ]))
        self.assertIn("verify.workflow_contract.be_close_01.orm", targets)
        self.assertNotIn("verify.workflow_contract.be_close_01.samples", targets)

        probe_targets = set(select_targets([
            "scripts/verify/be_close_01_workflow_contract_http_probe.py",
        ]))
        self.assertIn("verify.workflow_contract.be_close_01.samples", probe_targets)

    def test_baseline_debt_routes_are_owning_module_checks(self):
        cases = {
            "addons/smart_core/core/view_orchestrator.py": "verify.smart_core.close_02.module_baseline",
            "addons/smart_core/tests/test_tenant_extension_storage.py": "verify.smart_core.close_02.module_baseline",
            "addons/smart_construction_core/tests/test_source_bounded_data_space_rules.py": "verify.smart_construction_core.module_baseline",
            "addons/smart_construction_core/views/menu_business_taxonomy.xml": "verify.smart_construction_core.module_baseline",
            "addons/smart_construction_scene/tests/test_source_bounded_scene_rules.py": "verify.smart_construction_scene.module_baseline",
        }
        for path, target in cases.items():
            with self.subTest(path=path):
                self.assertIn(target, select_targets([path]))
        self.assertEqual(
            select_targets(["addons/smart_core/tests/test_unknown_new_family.py"]),
            [],
        )

    def test_test_only_module_changes_select_changed_classes_not_full_baseline(self):
        targets = select_iteration_targets([
            "addons/smart_construction_core/tests/test_context_workspace_native_lowcode.py",
            "addons/smart_construction_core/tests/test_native_advisory_draft.py",
        ])
        self.assertIn(
            "verify.changed_tests.orm",
            targets,
        )
        self.assertNotIn(
            "verify.smart_construction_core.module_baseline",
            targets,
        )
        overlapping = select_iteration_targets([
            "addons/smart_construction_core/tests/test_context_workspace_native_lowcode.py",
            "addons/smart_construction_core/tests/test_tender_award_fact.py",
        ])
        self.assertIn("verify.changed_tests.orm", overlapping)
        self.assertNotIn("verify.tender_award_fact.orm", overlapping)
        self.assertEqual(
            select_iteration_targets([
                "addons/smart_construction_acceptance_fixture/tests/test_business_scene_lifecycle.py"
            ]),
            [
                "verify.changed_tests.orm",
                "verify.daily_dev.acceptance_fixture.unit",
            ],
        )

    def test_production_change_keeps_owning_module_baseline(self):
        targets = select_iteration_targets([
            "addons/smart_core/handlers/business_config_change_set.py",
            "addons/smart_core/tests/test_business_config_change_set.py",
        ])
        self.assertIn("verify.smart_core.close_02.module_baseline", targets)
        self.assertNotIn("verify.changed_tests.orm", targets)

    def test_full_module_baselines_are_deferred_to_remote_integration(self):
        self.assertEqual(
            remote_integration_targets({
                "verify.smart_core.close_02.module_baseline",
                "verify.smart_construction_core.module_baseline",
                "verify.changed_tests.orm",
                "verify.changed.odoo.tests.unit",
            }),
            {
                "verify.smart_core.close_02.module_baseline",
                "verify.smart_construction_core.module_baseline",
            },
        )

    def test_implicit_registration_is_limited_to_pure_target_families(self):
        targets = {
            "verify.alpha.unit",
            "verify.beta.guard",
            "verify.gamma.assembler",
            "verify.delta.contract",
            "verify.epsilon.coverage",
            "verify.zeta.lane_coverage",
            "verify.zeta.policy",
            "verify.eta.orm",
            "verify.theta.browser",
            "verify.iota",
        }
        self.assertEqual(
            implicitly_registered_offline_targets(targets),
            {
                "verify.alpha.unit",
                "verify.beta.guard",
                "verify.gamma.assembler",
                "verify.delta.contract",
                "verify.epsilon.coverage",
                "verify.zeta.lane_coverage",
                "verify.zeta.policy",
            },
        )

    def test_explicit_validation_exclusions_remove_only_declared_targets(self):
        excluded = "verify.product_center.policy.orm"
        self.assertEqual(
            validation_exclusion_targets({
                "validation_exclusions": {"targets": [excluded]},
            }),
            {excluded},
        )
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan(
                [
                    "addons/smart_construction_core/models/support/product_policy_sync.py"
                ],
                excluded_targets={excluded},
            )
        payload = json.loads(output.getvalue().split("] ", 1)[1])
        self.assertNotIn(excluded, payload["requiredTargets"])
        self.assertEqual(payload["excludedTargets"], [excluded])
        with self.assertRaises(incremental.RunError):
            validation_exclusion_targets({
                "validation_exclusions": {"targets": ["not-a-verify-target"]},
            })

    def test_shared_release_assertions_are_required_before_merge(self):
        makefile = (ROOT / "make/frontend.mk").read_text()
        def prerequisites(target):
            return " ".join(re.findall(r"^" + re.escape(target) + r":(.*)$", makefile, re.M)).split()
        # The full-source scan must not depend on recognizing a new filename.
        self.assertIn("verify.frontend.localized_display.unit", prerequisites("verify.frontend.systemic.convergence.static"))
        self.assertIn("verify.frontend.localized_display.unit", prerequisites("verify.frontend.pr.unit"))
        self.assertIn("verify.frontend.contract_reason_dialog.browser", prerequisites("verify.frontend.pr.unit"))
        self.assertIn(
            "verify.frontend.systemic.convergence.static",
            select_targets(["frontend/apps/web/src/new-area/NewSurface.vue"]),
        )
        ci = (ROOT / "make/ci.mk").read_text()
        for target in (
            "ci.local.iteration",
            "ci.local.backend.iteration",
            "ci.local.frontend.iteration",
        ):
            dependency_line = re.search(
                r"^" + re.escape(target) + r":(.*)$",
                ci,
                re.M,
            )
            self.assertIsNotNone(dependency_line)
            self.assertNotIn(
                "verify.frontend.systemic.convergence.static",
                dependency_line.group(1),
            )

    def test_incremental_targets_enable_database_template_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "target.log"
            completed = subprocess.CompletedProcess(
                ["make", "verify.node_component_validation.unit"],
                0,
                stdout="ok\n",
                stderr="",
            )
            with mock.patch.dict(
                incremental.os.environ,
                {"LOCAL_TEST_TEMPLATE_MODULE": ""},
            ), mock.patch.object(
                incremental.subprocess,
                "run",
                return_value=completed,
            ) as run:
                result = incremental._run_make_target(
                    "verify.node_component_validation.unit",
                    Path(directory),
                    log_path,
                )
        self.assertEqual(result["status"], "passed")
        self.assertEqual(run.call_args.kwargs["env"]["LOCAL_TEST_REUSE_DATABASE"], "1")
        self.assertEqual(
            run.call_args.kwargs["env"]["LOCAL_TEST_TEMPLATE_MODULE"],
            "smart_construction_bundle",
        )

    def test_incremental_targets_allow_a_declared_superset_template(self):
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "target.log"
            completed = subprocess.CompletedProcess(
                ["make", "verify.node_component_validation.unit"],
                0,
                stdout="ok\n",
                stderr="",
            )
            with mock.patch.dict(
                incremental.os.environ,
                {
                    "LOCAL_TEST_TEMPLATE_MODULE":
                        "smart_construction_acceptance_fixture",
                },
            ), mock.patch.object(
                incremental.subprocess,
                "run",
                return_value=completed,
            ) as run:
                incremental._run_make_target(
                    "verify.node_component_validation.unit",
                    Path(directory),
                    log_path,
                )
        self.assertEqual(
            run.call_args.kwargs["env"]["LOCAL_TEST_TEMPLATE_MODULE"],
            "smart_construction_acceptance_fixture",
        )

    def test_performance_consumption_regressions_have_executable_owners(self):
        for path, owner in [
            ("addons/smart_core/core/system_init_extension_fact_merger.py", "verify.backend.navigation_delivery.unit"),
            ("addons/smart_core/tests/test_system_init_extension_fact_merger.py", "verify.backend.navigation_delivery.unit"),
            ("frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue", "verify.frontend.professional_relation_field.unit"),
            ("frontend/apps/web/scripts/readonly_block_component_test.mjs", "verify.frontend.professional_relation_field.unit"),
        ]:
            with self.subTest(path=path):
                self.assertIn(owner, select_targets([path]))

    def test_branch_cleanup_paths_keep_their_worktree_guard(self):
        for path in (
            "scripts/ops/branch_cleanup_safe.sh",
            "scripts/ops/test_safe_worktree_cleanup.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.workspace.worktree.guard"],
                )

    def test_demo_module_paths_select_demo_lifecycle_contracts(self) -> None:
        demo_targets = [
            "verify.demo.lifecycle.unit",
            "verify.demo.scenario_step.unit",
        ]
        for path in (
            "demo_addons/smart_construction_demo/README.md",
            "demo_addons/smart_construction_demo/data/base/20_projects.xml",
            "demo_addons/smart_construction_demo/models/project_demo_cockpit_seed.py",
            "demo_addons/smart_construction_demo/seed/registry.py",
            "demo_addons/smart_construction_demo/seed/steps/step_demo_business_chain.py",
            "demo_addons/smart_construction_demo/tests/test_demo_supplemental_flows.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(select_targets([path]), demo_targets)
        self.assertEqual(
            select_targets([
                "demo_addons/smart_construction_demo/tests/test_demo_golden_chain.py"
            ]),
            demo_targets + ["verify.local.dev.golden_chain.orm"],
        )

    def test_demo_role_scope_inputs_select_their_existing_owner(self) -> None:
        for path in (
            "scripts/verify/demo_usage_foundation_role_scope_manifest.json",
            "scripts/verify/demo_usage_foundation_role_scope_probe.py",
            "scripts/verify/test_demo_usage_foundation_role_scope_probe.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.demo.usage_foundation_role_scope.unit"],
                )

    def test_bundle_system_product_release_inputs_select_their_owner(self) -> None:
        for path in (
            "addons/smart_construction_bundle/migrations/0.1.2/post-migrate.py",
            "addons/smart_construction_bundle/tests/__init__.py",
            "addons/smart_construction_bundle/tests/test_system_product_release.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    [
                        "verify.extension.lifecycle.orm",
                        "verify.smart_construction_bundle.system_product_baseline.orm",
                    ],
                )

    def test_semantic_registry_declarations_keep_generator_and_lint(self) -> None:
        self.assertEqual(
            select_targets([
                "contracts/registry/component.yaml",
                "contracts/registry/registry.schema.json",
            ]),
            [
                "verify.frontend.professional_component_registry.unit",
                "verify.semantic.registry.lint",
            ],
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

    def test_presentation_targets_select_the_acceptance_semantics_lock(self) -> None:
        for path in (
            "config/acceptance/frontend_presentation_targets.v1.json",
            "scripts/verify/frontend_product_page_header_browser.mjs",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.frontend.presentation.lane.unit"],
                )

    def test_formal_project_views_select_the_product_structure_lock(self) -> None:
        for path in (
            "addons/smart_construction_core/views/core/project_views.xml",
            "addons/smart_construction_core/views/core/project_overview_views.xml",
            "scripts/verify/test_product_view_structure_contract.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.product_view_structure.contract.unit"],
                )

    def test_backend_contract_instance_selects_list_surface_receipt(self) -> None:
        self.assertEqual(
            select_targets(["config/acceptance/backend_contract_instance_v1.json"]),
            ["verify.frontend.acceptance.environment.guard"],
        )

    def test_daily_contract_instance_selects_daily_declaration_tests(self) -> None:
        self.assertEqual(
            select_targets(["config/acceptance/backend_contract_instance_daily_v1.json"]),
            ["verify.daily_dev.acceptance_fixture.unit"],
        )

    def test_page_block_action_inputs_select_p0c_owners(self) -> None:
        self.assertEqual(
            select_targets([
                "addons/smart_core/core/action_target_schema.py"
            ]),
            [
                "verify.frontend.page_contract_boundary.guard",
                "verify.p0_contract_producer.p0c.unit",
                "verify.page_contract.action_schema_semantics.guard",
            ],
        )
        self.assertEqual(
            select_targets([
                "addons/smart_core/core/page_block_action_contract.py"
            ]),
            [
                "verify.p0_contract_producer.p0a.backend_unit",
                "verify.p0_contract_producer.p0a.money",
                "verify.p0_contract_producer.p0a.unit",
                "verify.p0_contract_producer.p0c.orm",
                "verify.p0_contract_producer.p0c.unit",
            ],
        )
        self.assertEqual(
            select_targets([
                "frontend/apps/web/src/app/pageOrchestration.ts"
            ]),
            [
                "verify.frontend.lint.src",
                "verify.frontend.systemic.convergence.static",
                "verify.frontend.typecheck.strict",
                "verify.p0_contract_producer.p0c.unit",
            ],
        )
        self.assertEqual(
            select_targets([
                "frontend/apps/web/src/app/runtime/actionViewContractActionRuntime.ts"
            ]),
            [
                "verify.execute_button.authority.unit",
                "verify.frontend.lint.src",
                "verify.frontend.systemic.convergence.static",
                "verify.frontend.typecheck.strict",
                "verify.p0_c_fix01.action_id.orm",
                "verify.p0_c_fix01.action_id.unit",
                "verify.p0_contract_producer.p0c.orm",
                "verify.p0_contract_producer.p0c.unit",
            ],
        )
        self.assertEqual(
            select_targets([
                "scripts/verify/action_view_contract_action_runtime_smoke.js"
            ]),
            ["verify.action_view_runtime_smoke.behavior"],
        )
    def test_contract_consumer_declaration_changes_select_their_owners(self) -> None:
        cases = {
            "addons/smart_construction_core/tests/test_tender_award_fact.py": [
                "verify.tender_award_fact.orm",
            ],
            "addons/smart_core/handlers/route_authority_validate.py": [
                "verify.execute_button.authority.unit",
                "verify.product.entry_publication.unit",
            ],
            "scripts/verify/acceptance_contract_receipt_test.mjs": [
                "verify.frontend.list_surface_search_contract.unit",
            ],
            "scripts/verify/daily_demo_contract_api_acceptance.py": [
                "verify.daily.demo.contract.api.unit",
            ],
            "scripts/verify/daily_demo_runtime_performance.py": [
                "verify.local.dev.runtime.performance.unit",
            ],
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(select_targets([path]), expected)

    def test_expression_feedback_and_responsive_inputs_route_to_owning_units(self) -> None:
        self.assertEqual(
            select_targets(["frontend/apps/web/src/app/routeFailure.ts"]),
            [
                "verify.frontend.lint.src",
                "verify.frontend.product_page_header.unit",
                "verify.frontend.systemic.convergence.static",
                "verify.frontend.typecheck.strict",
                "verify.nav.pro01r.route_authority.unit",
            ],
        )
        self.assertEqual(
            select_targets(["frontend/apps/web/src/app/relationReadRouteAuthority.ts"]),
            [
                "verify.frontend.lint.src",
                "verify.frontend.record_form_return.unit",
                "verify.frontend.systemic.convergence.static",
                "verify.frontend.typecheck.strict",
            ],
        )
        self.assertIn(
            "verify.frontend.action_view_selection_feedback.unit",
            select_targets(["frontend/apps/web/src/app/runtime/actionViewSelectionExportRuntime.ts"]),
        )
        self.assertEqual(
            set(select_targets(["frontend/apps/web/src/components/product-page-header/ProductPageHeader.vue"])),
            {
                "verify.frontend.lint.src",
                "verify.frontend.product_page_header.unit",
                "verify.frontend.systemic.convergence.static",
                "verify.frontend.typecheck.strict",
            },
        )
        self.assertEqual(
            set(select_targets(["frontend/apps/web/src/views/SceneContractBlockGridView.vue"])),
            {
                "verify.frontend.lint.src",
                "verify.frontend.product_page_header.unit",
                "verify.frontend.systemic.convergence.static",
                "verify.frontend.typecheck.strict",
            },
        )

    def test_acceptance_runtime_tooling_routes_to_its_owning_unit(self) -> None:
        for path in (
            "scripts/dev/backend_acceptance_up.sh",
            "scripts/verify/test_acceptance_artifact.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.acceptance.artifact.unit"],
                )
        for path in (
            "scripts/dev/frontend_acceptance_baseline_rebuild.sh",
            "scripts/verify/test_frontend_acceptance_baseline_rebuild.py",
            "scripts/verify/test_frontend_acceptance_carrier_discard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.acceptance.runtime.tooling.unit"],
                )

    def test_candidate_runtime_identity_tools_select_their_unit(self) -> None:
        for path in (
            "scripts/dev/candidate_runtime_identity.py",
            "scripts/verify/test_candidate_runtime_identity.py",
            "scripts/verify/test_frontend_acceptance_candidate_guards.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.candidate.profile.unit"],
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

    def test_quick_receipt_verifier_inputs_select_the_joint_consistency_unit(self) -> None:
        for path in (
            "scripts/ops/local_quick_evidence.py",
            "scripts/ops/test_local_quick_evidence.py",
            "scripts/verify/test_local_quick_evidence.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.branch.governance.consistency"],
                )
        for path in (
            "scripts/ops/quick_input_scope.py",
            "scripts/ops/test_quick_input_scope.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.quick.input_scope.unit"],
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

    def test_rendering_evidence_inputs_select_their_registered_units(self) -> None:
        cases = {
            "scripts/audit/generate_frontend_rendering_detail_inventory.py": "verify.frontend.rendering_detail_state.unit",
            "scripts/audit/generate_frontend_visual_projection_inventory.py": "verify.frontend.rendering_detail_state.unit",
            "scripts/verify/frontend_rendering_detail_state_guard.py": "verify.frontend.rendering_detail_state.unit",
            "frontend/apps/web/scripts/view_type_render_coverage_probe.ts": "verify.frontend.view_type_render_coverage.guard",
            "scripts/verify/frontend_project_domain_rollout.py": "verify.frontend.project_domain_rollout.unit",
            "scripts/verify/frontend_state_dashboard_browser.mjs": "verify.frontend.state_dashboard.unit",
            "scripts/audit/generate_frontend_professionalization_baseline.py": "verify.frontend.style_system.guard",
            "scripts/verify/test_design_token_system.py": "verify.frontend.style_system.guard",
        }
        for path, target in cases.items():
            with self.subTest(path=path):
                self.assertIn(target, select_targets([path]))

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

    def test_navigation_contract_compiler_selects_navigation_and_boundary(self) -> None:
        for path in (
            "addons/smart_core/delivery/navigation_contract_compiler.py",
            "addons/smart_core/handlers/system_init.py",
            "addons/smart_core/tests/test_navigation_contract_compiler.py",
            "addons/smart_core/tests/test_system_init_final_route_authority_static.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    [
                        "verify.backend.navigation_delivery.unit",
                        "verify.scenario.center_projection.guard",
                        "verify.system_init.menu_boundary.guard",
                    ] if path != "addons/smart_core/handlers/system_init.py" else [
                        "verify.backend.navigation_delivery.unit",
                        "verify.platform.duty.contract.unit",
                        "verify.scenario.center_projection.guard",
                        "verify.system_init.menu_boundary.guard",
                    ],
                )

    def test_platform_duty_dependencies_select_contract(self) -> None:
        for path in (
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
        ):
            with self.subTest(path=path):
                self.assertIn("verify.platform.duty.contract.unit", select_targets([path]))

    def test_startup_smoke_selects_real_lifecycle_orm(self) -> None:
        self.assertEqual(select_targets(["addons/smart_core/tests/test_intent_smoke.py"]), [
            "verify.smart_core.intent_smoke.orm",
        ])

    def test_runtime_capability_catalog_selects_its_projection_unit(self) -> None:
        for path in (
            "addons/smart_core/delivery/runtime_capability_catalog.py",
            "addons/smart_core/tests/test_runtime_capability_catalog.py",
            "addons/smart_core/tests/test_backend_semantic_copy_supply.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.runtime_capability_catalog.unit"],
                )
        self.assertEqual(
            select_targets([
                "addons/smart_core/delivery/product_policy_catalog_sync_service.py"
            ]),
            [
                "verify.capability.identity_boundary.unit",
                "verify.runtime_capability_catalog.unit",
            ],
        )

    def test_platform_capability_explorer_selects_its_readonly_unit(self) -> None:
        for path in (
            "addons/smart_core/delivery/platform_capability_explorer.py",
            "addons/smart_core/delivery/platform_catalog_action_contract.py",
            "addons/smart_core/handlers/platform_capability_explorer.py",
            "addons/smart_core/tests/test_platform_capability_explorer.py",
            "addons/smart_construction_core/services/platform_capability_explorer_contributions.py",
            "addons/smart_construction_core/tests/test_platform_capability_explorer_contributions.py",
            "scripts/verify/platform_capability_explorer_runtime_probe.py",
            "scripts/verify/test_platform_capability_explorer_runtime_probe.py",
            "scripts/ops/odoo_shell_exec.sh",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.platform.capability_explorer.unit"],
                )
        self.assertEqual(
            select_targets([
                "addons/smart_construction_core/services/product_menu_source.py"
            ]),
            [
                "verify.capability.identity_boundary.unit",
                "verify.platform.capability_explorer.unit",
                "verify.product_center.policy.unit",
            ],
        )

    def test_admin_close_management_surfaces_select_their_owning_families(self) -> None:
        for path in (
            "addons/smart_core/delivery/platform_management_action_contract.py",
            "addons/smart_core/delivery/release_operator_contract_registry.py",
            "addons/smart_core/delivery/release_operator_surface_service.py",
            "addons/smart_core/tests/test_release_operator_surface_copy_backend.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.admin_close_01.backend.unit"],
                )
        self.assertEqual(
            select_targets([
                "addons/smart_core/delivery/release_operator_read_model_service.py"
            ]),
            [
                "verify.admin_close_01.backend.unit",
                "verify.product_center.policy.unit",
            ],
        )
        for path in (
            "addons/smart_construction_scene/handlers/scenario_activation.py",
            "addons/smart_construction_scene/services/tenant_scene_activation.py",
            "addons/smart_construction_scene/services/scenario_activation_catalog.py",
            "addons/smart_construction_scene/tests/test_admin_close_01_platform_to_enterprise.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    [
                        "verify.admin_close_01.runtime.orm",
                        "verify.daily.permission_truth.capability.orm",
                        "verify.navigation.publication_consumers.unit",
                    ],
                )

    def test_native_scene_inventory_selects_its_evidence_unit(self) -> None:
        for path in (
            "scripts/audit/native_scene_inventory.py",
            "scripts/audit/test_native_scene_inventory.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.native_scene.inventory.unit"],
                )

    def test_docs_link_tooling_selects_docs_links(self) -> None:
        for path in (
            "scripts/verify/docs_links.py",
            "scripts/verify/test_docs_links.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.docs.links"],
                )

    def test_platform_capability_explorer_frontend_selects_its_consumer_unit(self) -> None:
        for path in (
            "frontend/apps/web/src/api/platformCapabilityExplorer.ts",
            "frontend/apps/web/src/app/platformCapabilityExplorerPresentation.ts",
            "frontend/apps/web/src/app/platformCapabilityExplorerRequestGate.ts",
            "frontend/apps/web/src/views/PlatformCapabilityExplorerView.vue",
            "frontend/apps/web/src/app/adminRouteAccess.ts",
            "frontend/apps/web/scripts/admin_route_access_test.ts",
            "frontend/apps/web/scripts/platform_capability_explorer_test.ts",
            "frontend/apps/web/scripts/platform_capability_explorer_browser.mjs",
            "frontend/apps/web/scripts/platform_capability_explorer_browser_support.mjs",
            "frontend/apps/web/scripts/platform_capability_explorer_browser_support_test.mjs",
        ):
            with self.subTest(path=path):
                expected = (
                    [
                        "verify.frontend.lint.src",
                        "verify.frontend.platform_capability_explorer.unit",
                        "verify.frontend.systemic.convergence.static",
                        "verify.frontend.typecheck.strict",
                    ]
                    if path.startswith("frontend/apps/web/src/")
                    else ["verify.frontend.platform_capability_explorer.unit"]
                )
                self.assertEqual(
                    select_targets([path]),
                    expected,
                )

    def test_page_contract_builder_selects_contract_boundary_gates(self) -> None:
        self.assertEqual(
            select_targets(["addons/smart_core/core/page_contracts_builder.py"]),
            [
                "verify.frontend.page_contract_boundary.guard",
                "verify.p0_contract_producer.p0c.unit",
                "verify.page_contract.action_schema_semantics.guard",
            ],
        )
        self.assertEqual(
            select_targets(["scripts/verify/frontend_page_contract_boundary_guard.py"]),
            ["verify.frontend.page_contract_boundary.guard"],
        )

    def test_decision_authority_artifacts_select_their_unit(self) -> None:
        for path in (
            "scripts/verify/frontend_decision_authority.py",
            "scripts/verify/frontend_decision_authority_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.frontend.decision_authority.unit"],
                )

    def test_scene_shell_compiler_selects_its_navigation_unit(self) -> None:
        for path in (
            "addons/smart_core/delivery/scene_shell_compiler.py",
            "addons/smart_core/tests/test_scene_shell_compiler.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.scene.shell_compiler.unit"],
                )

    def test_scene_shell_frontend_contract_selects_its_consumer_unit(self) -> None:
        self.assertEqual(
            select_targets(["frontend/apps/web/src/app/resolvers/sceneRegistry.ts"]),
            [
                "verify.frontend.lint.src",
                "verify.frontend.scene_shell_contract.unit",
                "verify.frontend.systemic.convergence.static",
                "verify.frontend.typecheck.strict",
            ],
        )
        self.assertEqual(
            select_targets(["frontend/apps/web/scripts/scene_shell_contract_test.ts"]),
            ["verify.frontend.scene_shell_contract.unit"],
        )

    def test_enterprise_configuration_consumer_tool_selects_its_unit_guard(self) -> None:
        for path in (
            "scripts/verify/local_dev_enterprise_configuration_consumer.mjs",
            "scripts/verify/local_dev_enterprise_configuration_consumer.sh",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.local.dev.enterprise_configuration.consumer.unit"],
                )
        makefile = (ROOT / "make/dev.mk").read_text(encoding="utf-8")
        wrapper = makefile.split(
            "verify.local.dev.enterprise_configuration.consumer:", 1
        )[1].split("\n\n", 1)[0]
        runner = makefile.split(
            "verify.local.dev.enterprise_configuration.consumer.run:", 1
        )[1].split("\n\n", 1)[0]
        self.assertIn("local_dev_write_lease.sh", wrapper)
        self.assertIn("local.dev.write_lease.require", runner)
        self.assertIn("C02_RUNTIME_CANDIDATE_SHA", runner)
        self.assertIn("TEST_TOOL_GIT_HEAD", runner)
        self.assertIn('SCENARIO_ONLY="$(C02_SCENARIO_ONLY)"', runner)
        script = (
            ROOT / "scripts/verify/local_dev_enterprise_configuration_consumer.mjs"
        ).read_text(encoding="utf-8")
        self.assertIn("process.env.C02_SCENARIO_ONLY", script)
        self.assertIn("scenario_only", script)

    def test_menu_metadata_batch_selects_its_executable_suite(self) -> None:
        self.assertEqual(select_targets(['scripts/verify/test_menu_metadata_batch.py']),
                         ['verify.product.menu.metadata_batch.unit'])
        self.assertIn('verify.product.menu.metadata_batch.unit',
                      select_targets(['addons/smart_core/delivery/menu_service.py']))

    def test_scenario_center_composition_selects_center_and_navigation_guards(self) -> None:
        self.assertEqual(
            select_targets([
                "addons/smart_construction_core/models/support/product_scenario.py"
            ]),
            [
                "verify.daily.permission_truth.capability.orm",
                "verify.navigation.publication_consumers.unit",
                "verify.product_center.policy.orm",
                "verify.product_center.policy.unit",
                "verify.scenario.center_projection.guard",
            ],
        )
        for path in (
            "addons/smart_construction_core/services/scenario_surface_projection.py",
            "scripts/verify/scenario_center_projection_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    [
                        "verify.navigation.publication_consumers.unit",
                        "verify.scenario.center_projection.guard",
                    ],
                )

    def test_moved_industry_orm_selects_both_owning_module_baselines(self):
        self.assertEqual(select_targets([
            "addons/smart_core/tests/test_um_p3_material_settlement_purchase_authority_orm.py",
            "addons/smart_construction_core/tests/test_um_p3_material_settlement_purchase_authority_orm.py",
        ]), ["verify.smart_construction_core.module_baseline", "verify.smart_core.close_02.module_baseline"])

    def test_scenario_center_migration_and_view_select_orm_and_center_guards(self) -> None:
        for path in (
            "addons/smart_construction_core/__manifest__.py",
            "addons/smart_construction_core/migrations/17.0.0.179/post-migrate.py",
            "addons/smart_construction_core/views/support/product_scenario_views.xml",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    sorted([
                        "verify.daily.permission_truth.capability.orm",
                        "verify.scenario.center_projection.guard",
                    ] + (["verify.extension.lifecycle.orm", "verify.smart_construction_core.module_baseline"]
                         if path.endswith("__manifest__.py") else [])),
                )

    def test_backend_collection_inputs_select_only_offline_workflow_checks(self) -> None:
        for path in (
            "scripts/ci/backend_impact_plan.py",
            "scripts/ci/test_backend_impact_plan.py",
            "scripts/ci/backend_suite_plan.py",
            "scripts/ci/test_backend_suite_plan.py",
            "scripts/ci/backend_changed_test_coverage.py",
            "scripts/ci/test_backend_changed_test_coverage.py",
            "scripts/ci/backend_test_receipt.py",
            "scripts/ci/test_backend_test_receipt.py",
            "scripts/verify/backend_contract_fact_readback_probe.py",
            "scripts/verify/test_backend_contract_fact_readback_probe.py",
            "scripts/test/test.sh",
            "scripts/ci/enforce_complexity_baseline_lock.py",
            "scripts/ci/test_complexity_baseline_report.py",
            "docs/engineering_convergence/complexity_baseline_lock.json",
            "scripts/test/dependency_baseline.py",
            "scripts/test/test_dependency_baseline.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(select_targets([path]), ["verify.ci.workflow.contract"])
        for path in (
            "scripts/ci/backend_iteration_lanes.py",
            "scripts/ci/test_backend_iteration_lanes.py",
            "scripts/ci/test_backend_test_suite_dispatch_contract.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(select_targets([path]), [
                    "verify.backend_iteration_lanes.unit",
                    "verify.ci.workflow.contract",
                ])

    def test_build_and_test_isolation_select_existing_tool_owners(self):
        self.assertEqual(select_targets(["Dockerfile"]), ["verify.ci.workflow.contract"])
        self.assertEqual(select_targets(["docker-compose.test-isolation.yml"]), [
            "verify.ci.workflow.contract", "verify.local.development_lifecycle.unit",
        ])

    def test_backend_workflow_selects_security_before_final_delivery(self) -> None:
        self.assertEqual(select_targets([".github/workflows/backend_test_suite.yml"]), [
            "verify.ci.workflow.contract", "verify.github_actions.security",
        ])

    def test_frontend_cleanup_selects_workflow_contract(self) -> None:
        self.assertEqual(
            select_targets(["scripts/ci/self_hosted_runner_cleanup.sh"]),
            ["verify.ci.workflow.contract"],
        )

    def test_required_pr_workflows_select_contract_and_security_checks(self) -> None:
        for path in (
            ".github/workflows/frontend_release_gate.yml",
            ".github/workflows/merge_policy_gate.yml",
            ".github/workflows/professional_quality_gate.yml",
            ".github/workflows/public_guard.yml",
            ".github/workflows/release_candidate_gate.yml",
            "scripts/ci/scheduled_validation.py",
            "scripts/ci/select_authoritative_workflow_run.py",
            "scripts/ci/test_select_authoritative_workflow_run.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(select_targets([path]), [
                    "verify.ci.scheduled_gates",
                    "verify.ci.workflow.contract",
                ])

    def test_release_condition_inputs_select_ci_and_scheduled_contracts(self) -> None:
        for path in (
            "scripts/ci/release_condition.py",
            "scripts/ci/test_release_condition.py",
            "scripts/ci/test_release_candidate_gate.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(select_targets([path]), [
                    "verify.ci.scheduled_gates",
                    "verify.ci.workflow.contract",
                ])

    def test_acceptance_login_route_inputs_select_scheduled_gates(self) -> None:
        for path in (
            "scripts/verify/frontend_release_ci_guard.py",
            "scripts/verify/test_frontend_release_ci_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(select_targets([path]), ["verify.ci.scheduled_gates"])
        self.assertEqual(
            select_targets(["scripts/dev/frontend_acceptance_operation_entry.sh"]),
            ["verify.ci.scheduled_gates", "verify.frontend.standard_preview.unit"],
        )

    def test_main_full_release_dispatch_selects_its_unit_and_scheduled_gate(self) -> None:
        for path in (
            "scripts/ci/main_full_release_dispatch.py",
            "scripts/ci/test_main_full_release_dispatch.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.ci.scheduled_gates"],
                )

    def test_current_static_guard_consumers_select_their_owning_checks(self) -> None:
        page_header_paths = (
            "scripts/verify/frontend_product_page_header_guard.py",
            "scripts/verify/test_frontend_product_page_header_guard.py",
        )
        for path in page_header_paths:
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.frontend.product_page_header.unit"],
                )
        for path in (
            "frontend/apps/web/src/router/index.ts",
            "frontend/apps/web/src/views/MyWorkView.vue",
        ):
            with self.subTest(path=path):
                self.assertIn(
                    "verify.frontend.product_page_header.unit",
                    select_targets([path]),
                )
                self.assertIn("verify.frontend.lint.src", select_targets([path]))
                self.assertIn("verify.frontend.typecheck.strict", select_targets([path]))

        for route_path in (
            "frontend/apps/web/src/pages/ContractFormRoute.vue",
            "frontend/apps/web/src/pages/contractFormRouteLoader.ts",
        ):
            with self.subTest(route_path=route_path):
                self.assertIn("verify.frontend.delivery_hardening.guard", select_targets([route_path]))
                self.assertIn("verify.frontend.startup_performance.unit", select_targets([route_path]))

        delivery_paths = (
            "scripts/verify/frontend_delivery_hardening_guard.py",
            "scripts/verify/test_frontend_delivery_hardening_guard.py",
        )
        for path in delivery_paths:
            with self.subTest(path=path):
                self.assertIn(
                    "verify.frontend.delivery_hardening.guard",
                    select_targets([path]),
                )
        for path in (
            "frontend/apps/web/src/App.vue",
            "frontend/apps/web/src/app/activityPageCacheIdentity.ts",
        ):
            with self.subTest(path=path):
                self.assertIn(
                    "verify.frontend.delivery_hardening.guard",
                    select_targets([path]),
                )
                self.assertIn("verify.frontend.lint.src", select_targets([path]))
                self.assertIn("verify.frontend.typecheck.strict", select_targets([path]))

        self.assertEqual(
            select_targets(["scripts/verify/unified_page_contract_v2_assembler_guard.py"]),
            ["verify.unified_page_contract.v2.assembler"],
        )
        self.assertIn(
            "verify.unified_page_contract.v2.assembler",
            select_targets(["addons/smart_core/core/unified_page_contract_v2_assembler.py"]),
        )
        self.assertEqual(
            select_targets(["scripts/test/frontend_acceptance_db_ensure.sh"]),
            ["verify.frontend.acceptance.db_preparation.unit"],
        )
        self.assertEqual(
            select_targets(["scripts/db/create.sh"]),
            ["verify.frontend.acceptance.db_preparation.unit"],
        )

    def test_test_coverage_registry_audit_selects_its_executable_check(self) -> None:
        for path in (
            "scripts/verify/test_coverage_registry.yaml",
            "scripts/verify/test_test_coverage_registry_audit.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.test.coverage.registry"],
                )

    def test_native_action_view_set_paths_select_their_runtime_and_contract_l2(self) -> None:
        expected = {
            "verify.native_action.view_set.unit",
            "verify.native_action.view_set.orm",
            "verify.unified_page_contract.v2.assembler",
            "verify.contract.entry_equivalence.guard",
        }
        for path in (
            "addons/smart_core/core/native_action_view_set.py",
            "addons/smart_core/app_config_engine/services/resolvers/action_resolver.py",
            "addons/smart_core/handlers/ui_contract_preview.py",
            "addons/smart_core/tests/test_native_action_view_set_integration.py",
            "scripts/verify/test_native_action_view_set.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(set(select_targets([path])), expected)

    def test_native_action_search_view_paths_select_their_runtime_and_contract_l2(self) -> None:
        expected = {
            "verify.native_action.search_view.unit",
            "verify.native_action.search_view.orm",
            "verify.unified_page_contract.v2.assembler",
            "verify.contract.entry_equivalence.guard",
        }
        for path in (
            "addons/smart_core/core/native_action_search_view.py",
            "addons/smart_core/app_config_engine/models/app_search_config.py",
            "addons/smart_core/app_config_engine/models/app_view_config.py",
            "addons/smart_core/tests/test_native_action_search_view_integration.py",
            "scripts/verify/test_native_action_search_view.py",
        ):
            with self.subTest(path=path):
                self.assertLessEqual(expected, set(select_targets([path])))

    def test_native_action_contract_paths_select_atomic_backend_and_frontend_l2(self) -> None:
        backend_expected = {
            "verify.native_action.contract.unit",
            "verify.native_action.contract.orm",
            "verify.unified_page_contract.v2.assembler",
        }
        for path in (
            "addons/smart_core/core/native_action_contract.py",
            "addons/smart_core/app_config_engine/utils/payload.py",
            "addons/smart_core/handlers/ui_contract.py",
            "addons/smart_core/tests/test_native_action_contract_integration.py",
            "scripts/verify/test_native_action_contract.py",
        ):
            with self.subTest(path=path):
                self.assertLessEqual(backend_expected, set(select_targets([path])))
        for path in (
            "frontend/apps/web/src/app/contracts/actionViewSurfaceContract.ts",
            "frontend/apps/web/src/app/action_runtime/useActionViewModeRuntime.ts",
            "frontend/apps/web/scripts/collection_view_semantics_test.ts",
        ):
            with self.subTest(path=path):
                targets = set(select_targets([path]))
                self.assertIn("verify.frontend.contract_record_action_state.unit", targets)
                self.assertIn("verify.frontend.collection_view_semantics.unit", targets)
        self.assertEqual(
            select_targets(["scripts/verify/backend_contract_lifecycle_authority_guard.py"]),
            ["verify.backend.contract_lifecycle.authority"],
        )
        self.assertEqual(
            select_targets(["scripts/verify/unified_page_contract_v2_intent_guard.py"]),
            ["verify.unified_page_contract.v2.intent"],
        )

    def test_native_occurrence_paths_select_producer_and_decoder_gates(self) -> None:
        expected = {
            "verify.native_occurrence.contract.unit",
            "verify.native_occurrence.contract.orm",
            "verify.unified_page_contract.v2.assembler",
        }
        for path in (
            "addons/smart_core/core/native_view_occurrence.py",
            "addons/smart_core/tests/test_native_occurrence_contract_integration.py",
            "scripts/verify/test_native_occurrence_contract.py",
        ):
            with self.subTest(path=path):
                self.assertLessEqual(expected, set(select_targets([path])))

    def test_contract_retirement_manifest_selects_zero_residue_guard(self) -> None:
        self.assertEqual(
            select_targets(["config/contract/page_contract_v1_retirement_manifest.json"]),
            ["verify.contract.page_v1_zero_residue.guard"],
        )
        self.assertEqual(
            select_targets(["scripts/verify/web_contract_v2_frontend_architecture_guard.py"]),
            ["verify.unified_page_contract.v2.web_architecture"],
        )

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
                "verify.frontend.contract_record_action_state.unit",
                "verify.frontend.lint.src",
                "verify.frontend.systemic.convergence.static",
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
                    [
                        "verify.backend.contract_lifecycle.authority",
                        "verify.frontend.contract_v2_render_authority.unit",
                        "verify.unified_page_contract.v2.schema",
                    ],
                )
        for path in (
            "scripts/verify/contract_v2_render_authority_matrix.py",
            "docs/frontend_productization/rendering-detail/contract-v2-render-authority-matrix-v1.json",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.frontend.contract_v2_render_authority.unit"],
                )
        self.assertEqual(
            select_targets(["scripts/verify/frontend_contract_record_action_state.test.mjs"]),
            ["verify.frontend.contract_record_action_state.unit"],
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
                    ["verify.daily.permission_truth.capability.orm", "verify.extension.lifecycle.orm",
                     "verify.smart_construction_core.module_baseline"]
                    if path.endswith("__init__.py") else ["verify.daily.permission_truth.capability.orm"],
                )
        self.assertEqual(
            select_targets(["addons/smart_core/utils/extension_hooks.py"]),
            [
                "verify.daily.permission_truth.capability.orm",
                "verify.extension.hook_authority.orm",
                "verify.extension.hook_contracts.unit",
                "verify.extension.hook_resolver.unit",
                "verify.extension.native_alignment.orm",
            ],
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
                "verify.product_center.policy.orm",
                "verify.product_center.policy.unit",
                "verify.scenario.center_projection.guard",
            ],
        )
        self.assertEqual(
            select_targets([
                "addons/smart_construction_scene/tests/test_company_route_scope_cache.py",
            ]),
            ["verify.scene.company_route_scope_cache.orm"],
        )
        self.assertEqual(
            select_targets([
                "addons/smart_construction_core/data/product_menu_source.json",
            ]),
            [
                "verify.frontend.navigation_policy.unit",
                "verify.frontend.role_surface_exposure_declaration.guard",
                "verify.role_surface.landing.contract.unit",
                "verify.workflow_action_semantics.guard",
            ],
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
            [
                "repository.clean_history.scan",
                "security.personal_data_scan",
                "verify.repository.clean_history.unit",
            ],
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
            [
                "verify.extension.consumers.unit",
                "verify.intent_group.authorization.unit",
            ],
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
            "addons/smart_core/delivery/capability_service.py",
            "addons/smart_construction_core/services/product_capability_admission.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.capability.identity_boundary.unit"],
                )
        self.assertEqual(
            select_targets([
                "addons/smart_construction_core/services/product_menu_source.py"
            ]),
            [
                "verify.capability.identity_boundary.unit",
                "verify.platform.capability_explorer.unit",
                "verify.product_center.policy.unit",
            ],
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
                "verify.smart_construction_core.module_baseline",
            ],
        )
        self.assertEqual(
            select_targets([
                "addons/smart_construction_core/data/formal_business_product_menu_policy_v1.json"
            ]),
            [
                "verify.frontend.navigation_policy.unit",
                "verify.frontend.role_surface_exposure_declaration.guard",
                "verify.product.menu.contract_v1.guard",
                "verify.product_center.policy.unit",
                "verify.role_surface.landing.contract.unit",
                "verify.workflow_action_semantics.guard",
            ],
        )

    def test_operation_entry_paths_select_navigation_and_role_surface(self) -> None:
        for path in (
            "addons/smart_construction_core/security/sc_role_entry_groups.xml",
            "addons/smart_construction_core/tests/test_business_category_entry_policy.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    [
                        "verify.frontend.navigation_shell.unit",
                        "verify.role_surface.landing.contract.unit",
                    ],
                )

    def test_administration_wave_paths_select_their_release_guard(self) -> None:
        for path in (
            "addons/smart_construction_core/views/menu_product_administration_wave1.xml",
            "scripts/verify/product_administration_center_wave1_guard.py",
            "scripts/verify/test_product_administration_center_wave1_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.product.administration_center.wave1.guard"],
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

    def test_collection_aggregate_guard_inputs_select_their_own_unit(self) -> None:
        for path in (
            "scripts/verify/frontend_collection_aggregate_footer_guard.py",
            "scripts/verify/test_frontend_collection_aggregate_footer_guard.py",
        ):
            self.assertEqual(
                select_targets([path]),
                ["verify.frontend.collection_aggregate_footer.unit"],
            )

    def test_backend_mapping_does_not_mask_unknown_frontend_input(self) -> None:
        paths = ["scripts/ci/backend_test_receipt.py",
                 "frontend/apps/web/src/newFeature.ts"]
        expected = sorted({
            "verify.ci.workflow.contract",
            FALLBACK_TARGET,
            *FRONTEND_SOURCE_TARGETS,
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
                "verify.frontend.systemic.convergence.static",
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
                    "verify.frontend.systemic.convergence.static",
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
        for path in (
            "frontend/apps/web/src/components/MenuTree.vue",
            "frontend/apps/web/src/components/product-shell/ProductSideNavigation.vue",
        ):
            with self.subTest(path=path):
                self.assertIn(
                    "verify.frontend.navigation_shell.unit",
                    select_targets([path]),
                )

    def test_scene_route_change_recommends_scene_entry_contract(self) -> None:
        # The scene runtime is cached by <KeepAlive> and its route ownership rule
        # must be re-verified whenever the view or the rule module changes.
        for path in (
            "frontend/apps/web/src/views/SceneView.vue",
            "frontend/apps/web/src/app/sceneEntryContract.ts",
        ):
            expected = [
                "verify.frontend.lint.src",
                "verify.frontend.navigation_shell.unit",
                "verify.frontend.scene_entry_contract.unit",
                "verify.frontend.systemic.convergence.static",
                "verify.frontend.typecheck.strict",
            ]
            if path.endswith("/SceneView.vue"):
                expected.insert(2, "verify.frontend.product_page_header.unit")
            self.assertEqual(
                select_targets([path]),
                expected,
            )
        self.assertEqual(
            select_targets([
                "addons/smart_core/tests/test_scene_provider_target_identity_merge.py",
            ]),
            [
                "verify.frontend.navigation_shell.unit",
                "verify.frontend.scene_entry_contract.unit",
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

    def test_change_impact_inventory_inputs_route_to_their_audit_unit(self) -> None:
        for path in (
            "scripts/audit/generate_change_impact_verification_inventory.py",
            "scripts/audit/test_generate_change_impact_verification_inventory.py",
            "make/help.mk",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    [
                        "verify.change_impact.acceptance",
                        "verify.change_impact.verification.unit",
                    ],
                )

    def test_change_impact_planner_inputs_route_to_the_planner_unit(self) -> None:
        for path in (
            "scripts/ops/change_impact_planner.py",
            "scripts/ops/change_impact_graph.py",
            "scripts/ops/change_impact_evidence.py",
            "scripts/ops/change_impact_acceptance.py",
            "scripts/ops/test_change_impact_planner.py",
            "scripts/ops/test_change_impact_graph.py",
            "scripts/ops/test_change_impact_evidence.py",
            "scripts/ops/typescript_change_facts.mjs",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    [
                        "verify.change_impact.acceptance",
                        "verify.change_impact.plan.unit",
                    ],
                )

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
            "addons/smart_core/core/native_view_projection.py",
            "addons/smart_core/core/unified_page_contract_v2_modifier_dependencies.py",
            "addons/smart_core/app_config_engine/models/app_view_config.py",
            "addons/smart_core/app_config_engine/services/assemblers/page_assembler.py",
            "addons/smart_core/tests/test_odoo_native_alignment_boundaries.py",
        ):
            with self.subTest(path=path):
                targets = select_targets([path])
                self.assertIn("verify.business_config.formal_list.unit", targets)
                self.assertIn("verify.unified_page_contract.v2.assembler", targets)
                self.assertIn("verify.contract.entry_equivalence.guard", targets)
                self.assertIn("verify.form_structure_authority_unification.unit", targets)

    def test_native_role_and_personnel_changes_select_their_orm_owners(self) -> None:
        self.assertEqual(
            select_targets(["addons/smart_core/security/group_assignment.py"]),
            [
                "verify.runtime_user_management.orm",
                "verify.system.permission_role.assignment.unit",
            ],
        )
        self.assertEqual(
            select_targets([
                "addons/smart_construction_core/tests/test_runtime_user_management.py",
            ]),
            ["verify.runtime_user_management.orm"],
        )
        self.assertEqual(
            select_targets(["addons/smart_construction_core/tests/test_product_job.py"]),
            ["verify.product_job.orm"],
        )

    def test_low_code_workbench_context_paths_select_behavior_owners(self) -> None:
        workbench_paths = (
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
        )
        for path in workbench_paths:
            with self.subTest(path=path):
                targets = set(select_targets([path]))
                self.assertIn("verify.business_config.unit", targets)
                self.assertFalse(any(".orm" in target for target in targets))

        approval_targets = set(select_targets([
            "frontend/apps/web/src/views/businessConfigSurface/useBusinessConfigApprovalEditor.ts",
            "frontend/apps/web/scripts/business_config_approval_target_test.mjs",
        ]))
        self.assertEqual(
            approval_targets,
            {
                "verify.business_config.approval_targets.unit",
                *FRONTEND_SOURCE_TARGETS,
            },
        )
        shared_context_targets = set(select_targets([
            "frontend/apps/web/src/app/contextEpoch.ts",
        ]))
        self.assertIn("verify.business_config.unit", shared_context_targets)
        self.assertIn("verify.business_config.approval_targets.unit", shared_context_targets)

    def test_enterprise_readiness_contract_routes_to_navigation_consumers(self) -> None:
        for path in (
            "addons/smart_construction_scene/services/enterprise_readiness_diagnosis.py",
            "addons/smart_construction_core/tests/test_enterprise_setup_native_contracts.py",
            "addons/smart_construction_scene/tests/test_enterprise_readiness_contract.py",
        ):
            with self.subTest(path=path):
                targets = set(select_targets([path]))
                self.assertIn("verify.navigation.publication_consumers.unit", targets)
                self.assertFalse(any(".orm" in target for target in targets))

    def test_controlled_feedback_chain_routes_to_unit_and_orm_owners(self) -> None:
        for path in (
            "addons/smart_core/core/native_advisory.py",
            "addons/smart_core/core/draft_feedback.py",
            "addons/smart_core/core/node_component_validation.py",
            "addons/smart_core/tests/test_native_advisory.py",
            "addons/smart_core/tests/test_node_component_validation.py",
            "addons/smart_construction_core/tests/test_conditioned_processing_feedback.py",
            "addons/smart_construction_core/tests/test_company_project_refund_feedback.py",
        ):
            with self.subTest(path=path):
                targets = select_targets([path])
                self.assertIn("verify.native_advisory.unit", targets)
                self.assertIn("verify.node_component_validation.unit", targets)
                self.assertIn(
                    "verify.local.dev.conditioned.feedback.orm",
                    targets,
                )

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
                    ["verify.frontend.dev.incremental.unit"],
                )

    def test_agent_run_context_change_routes_to_its_own_unit(self) -> None:
        for path in (
            "scripts/ops/agent_run_context.py",
            "scripts/verify/test_agent_run_context.py",
            "scripts/ops/generated_evidence_paths.py",
        ):
            with self.subTest(path=path):
                self.assertIn(
                    "verify.agent.resume.unit",
                    select_targets([path]),
                )

    def test_scenario_composition_paths_keep_their_responsibility_targets(self) -> None:
        expected = {
            "addons/smart_construction_core/migrations/17.0.0.182/post-migrate.py": [
                "verify.capability.identity_boundary.orm",
            ],
            "addons/smart_construction_core/migrations/17.0.0.183/post-migrate.py": [
                "verify.smart_construction_core.close_03.preview_promotion.orm",
            ],
            "addons/smart_construction_core/tests/test_locked_menu_policy_initialization.py": [
                "verify.capability.identity_boundary.orm",
                "verify.product_center.policy.orm",
                "verify.product_center.policy.unit",
                "verify.smart_construction_core.close_03.preview_promotion.orm",
            ],
            "addons/smart_construction_core/services/contract_governance_overrides.py": [
                "verify.intake_autosave.contract.unit",
                "verify.project_intake.contract_governance.unit",
            ],
            "addons/smart_construction_core/tests/test_project_intake_contract_governance.py": [
                "verify.intake_autosave.contract.unit",
                "verify.project_intake.contract_governance.unit",
            ],
            "addons/smart_construction_core/tests/test_project_initiation_native_lowcode.py": [
                "verify.project_intake.contract_governance.unit",
            ],
            "scripts/verify/close_03_intake_autosave_samples.mjs": [
                "verify.backend.close_03.intake_autosave.samples",
            ],
            "scripts/verify/close_03_intake_autosave_samples_validate.py": [
                "verify.backend.close_03.intake_autosave.samples",
            ],
            "scripts/verify/close_03_project_intake_browser.mjs": [
                "verify.intake_autosave.contract.unit",
            ],
            "scripts/verify/local_dev_native_projection_audit.py": [
                "verify.local.dev.native_projection.audit.unit",
            ],
            "scripts/verify/product_menu_contract_v1_guard.py": [
                "verify.product.menu.contract_v1.guard",
            ],
            "scripts/verify/test_product_menu_contract_v1_guard.py": [
                "verify.product.menu.contract_v1.guard",
            ],
            "addons/smart_construction_core/views/menu_product_navigation_v2.xml": [
                "verify.product.menu.runtime_closeout.guard",
            ],
            "config/ops/local-platform-empty-addons/.gitkeep": [
                "verify.local.development_lifecycle.unit",
            ],
            "config/product_menu_release_manifest_v2.json": [
                "verify.product.menu.contract_v1.guard",
                "verify.product.primary_center.baseline.guard",
            ],
            "scripts/verify/product_menu_release_manifest_v2_guard.py": [
                "verify.product.menu.contract_v1.guard",
                "verify.product.primary_center.baseline.guard",
            ],
            "scripts/verify/product_primary_center_baseline_guard.py": [
                "verify.product.primary_center.baseline.guard",
            ],
            "scripts/verify/product_primary_center_candidate_guard.py": [
                "verify.product.primary_center.candidate.guard",
            ],
            "scripts/verify/scenario_seed_runtime_readback.py": [
                "verify.nav01.native_authority.unit",
            ],
            "config/product_scenario_organization_v1.json": [
                "verify.product.scenario.organization.unit",
            ],
            "scripts/audit/build_scenario_product_organization.py": [
                "verify.product.scenario.organization.unit",
            ],
            "scripts/audit/test_build_scenario_product_organization.py": [
                "verify.product.scenario.organization.unit",
            ],
            "scripts/ops/test_promote_product_ten_center_policy.py": [
                "verify.product.menu.contract_v1.guard",
            ],
            "addons/smart_construction_acceptance_fixture/tests/test_scenario_navigation_maintenance.py": [
                "verify.daily_dev.acceptance_fixture.unit",
            ],
            "addons/smart_construction_core/data/product_scenario_seed.xml": [
                "verify.daily.permission_truth.capability.orm",
                "verify.navigation.publication_consumers.unit",
                "verify.scenario.center_projection.guard",
            ],
            "addons/smart_construction_core/data/scenario_product_surface.json": [
                "verify.daily.permission_truth.capability.orm",
                "verify.navigation.publication_consumers.unit",
                "verify.scenario.center_projection.guard",
            ],
            "addons/smart_construction_core/migrations/17.0.0.180/pre-migrate.py": [
                "verify.daily.permission_truth.capability.orm",
                "verify.navigation.publication_consumers.unit",
                "verify.scenario.center_projection.guard",
                "verify.smart_construction_core.migration_compatibility.orm",
            ],
            "addons/smart_construction_core/migrations/17.0.0.181/pre-migrate.py": [
                "verify.daily.permission_truth.capability.orm",
                "verify.navigation.publication_consumers.unit",
                "verify.scenario.center_projection.guard",
                "verify.smart_construction_core.migration_compatibility.orm",
            ],
            "addons/smart_construction_core/tests/test_scenario_direct_entry_initialization.py": [
                "verify.daily.permission_truth.capability.orm",
                "verify.navigation.publication_consumers.unit",
                "verify.scenario.center_projection.guard",
                "verify.smart_construction_core.migration_compatibility.orm",
            ],
            "addons/smart_construction_core/security/sc_capability_groups.xml": [
                "verify.frontend.navigation_policy.unit",
                "verify.frontend.role_surface_exposure_declaration.guard",
                "verify.role_surface.landing.contract.unit",
                "verify.workflow_action_semantics.guard",
            ],
            "addons/smart_construction_core/core_extension_actor_roles.py": [
                "verify.frontend.navigation_policy.unit",
                "verify.frontend.role_surface_exposure_declaration.guard",
                "verify.role_surface.landing.contract.unit",
                "verify.workflow_action_semantics.guard",
            ],
            "addons/smart_construction_scene/services/business_scene_enablement.py": [
                "verify.daily.permission_truth.capability.orm",
                "verify.navigation.publication_consumers.unit",
                "verify.scenario.center_projection.guard",
            ],
            "addons/smart_core/core/navigation_entry_target.py": [
                "verify.backend.navigation_delivery.unit",
                "verify.scenario.center_projection.guard",
                "verify.system_init.menu_boundary.guard",
            ],
            "addons/smart_core/tests/test_entry_publication_authority.py": [
                "verify.product.entry_publication.unit",
            ],
            "addons/smart_core/tests/test_platform_admin_duty_contract.py": [
                "verify.platform.duty.contract.unit",
            ],
            "addons/smart_construction_scene/tests/test_scene_registry_yaml_asset_merge.py": [
                "verify.navigation.publication_consumers.unit",
            ],
            "config/product_menu_contract_v1.json": [
                "verify.product.menu.contract_v1.guard",
                "verify.product_center.policy.unit",
            ],
            "scripts/verify/scene_fact_data_boundary_guard.py": [
                "verify.navigation.publication_consumers.unit",
                "verify.scenario.center_projection.guard",
            ],
        }
        for path, targets in expected.items():
            with self.subTest(path=path):
                self.assertEqual(select_targets([path]), targets)

    def test_project_evidence_summary_routes_only_to_dashboard_contract(self) -> None:
        for path in (
            "addons/smart_construction_core/services/__init__.py",
            "addons/smart_construction_core/services/project_dashboard_service.py",
            "addons/smart_construction_core/services/project_evidence_summary_service.py",
            "addons/smart_construction_core/tests/__init__.py",
            "addons/smart_construction_core/tests/test_project_evidence_summary_service.py",
            "scripts/verify/project_management_contract_guard.py",
            "scripts/verify/project_dashboard_assembly_guard.py",
            "scripts/verify/project_dashboard_block_schema_guard.py",
            "scripts/verify/project_dashboard_metric_semantics_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.project.dashboard.contract"],
                )
        for path in (
            "scripts/verify/project_dashboard_contract_snapshot_export.py",
            "scripts/verify/project_dashboard_snapshot_freshness_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.project.dashboard.snapshot"],
                )

    def test_release_probe_change_selects_the_fixture_consumer(self) -> None:
        self.assertCountEqual(
            select_targets(["scripts/ops/dev_acceptance_release_probe.py"]),
            [
                "verify.daily_dev.acceptance_fixture.unit",
                "verify.frontend.acceptance.environment.guard",
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
                "verify.frontend.dev.incremental.unit",
            ],
        )
        self.assertEqual(
            select_targets(["scripts/verify/frontend_static_release_audit.py"]),
            ["verify.ci.workflow.contract"],
        )

    def test_published_face_target_projection_routes_to_its_daily_guard(self) -> None:
        for path in (
            "addons/smart_core/delivery/edition_release_snapshot_service.py",
            "addons/smart_core/tests/test_release_preflight_target_validation.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    [
                        "verify.daily.published_face.target.unit",
                        *(
                            ["verify.product_center.policy.unit"]
                            if path.endswith("edition_release_snapshot_service.py")
                            else []
                        ),
                    ],
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
                    ["verify.backend.navigation_delivery.unit", *(["verify.product.menu.metadata_batch.unit"] if path.endswith("/menu_service.py") else []), "verify.workspace.entry_authority.orm"],
                )

    def test_native_scene_identity_test_selects_navigation_checks(self):
        self.assertEqual(select_targets(["addons/smart_core/tests/test_navigation_entry_target.py"]), [
            "verify.backend.navigation_delivery.unit", "verify.scenario.center_projection.guard",
            "verify.system_init.menu_boundary.guard",
        ])

    def test_startup_payload_projection_selects_navigation_checks(self):
        for path in ("addons/smart_core/core/system_init_payload_builder.py", "addons/smart_core/tests/test_system_init_payload_builder_semantics.py"):
            self.assertEqual(select_targets([path]), ["verify.backend.navigation_delivery.unit", "verify.scenario.center_projection.guard", "verify.system_init.menu_boundary.guard"])

    def test_workspace_authority_tests_select_their_orm(self):
        for path in (
            "addons/smart_construction_bundle/tests/test_workspace_role_routes.py",
            "addons/smart_construction_bundle/tests/test_company_project_refund_workspace.py",
            "addons/smart_construction_bundle/tests/test_current_account_workspace.py",
            "addons/smart_construction_bundle/tests/test_team_loan_deduction_workspace.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(select_targets([path]), ["verify.workspace.entry_authority.orm"])

    def test_acceptance_fixture_and_browser_tools_select_owned_checks(self) -> None:
        self.assertEqual(
            select_targets(["scripts/verify/frontend_my_work_approval_guard.py"]),
            ["verify.frontend.my_work_approval.guard"],
        )
        for path in (
            "scripts/dev/frontend_cached_dependencies_restore.sh",
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

    def test_delivery_scan_and_policy_tools_select_owned_checks(self) -> None:
        for path in (
            "scripts/ci/secret_scan.py",
            "scripts/ci/personal_data_scan.py",
            "scripts/ci/trusted_scan_scope.py",
            "scripts/ci/test_trusted_scan_scope.py",
            "scripts/verify/repository_clean_history_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.trusted_scan.unit"],
                )
        for path in (
            "scripts/verify/construction_core_extension_policy_maps_split_guard.py",
            "scripts/verify/test_construction_core_extension_policy_maps_split_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.construction.policy_maps.unit"],
                )
        self.assertEqual(
            select_targets([
                "scripts/verify/construction_core_extension_capability_rows_split_guard.py",
            ]),
            ["verify.contract.architecture.suite"],
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
                "verify.pr.review.unit",
            ],
        )
        self.assertEqual(
            select_targets(["scripts/verify/test_pr_publish_preflight.py"]),
            ["verify.pr.push.unit"],
        )
        self.assertEqual(
            select_targets(["scripts/ops/pr_review_submit.py"]),
            ["verify.pr.review.unit"],
        )
        self.assertEqual(
            select_targets(["scripts/ops/test_pr_review_submit.py"]),
            ["verify.pr.review.unit"],
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
                "verify.ci.scheduled_gates",
                "verify.ci.workflow.contract",
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

    def test_collection_row_and_optional_column_guards_route_to_their_owned_units(self) -> None:
        for path in (
            "scripts/verify/frontend_collection_row_cell_guard.py",
            "scripts/verify/test_frontend_collection_row_cell_guard.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.frontend.collection_row_cell.unit"],
                )
        self.assertEqual(
            select_targets(["scripts/verify/frontend_list_optional_columns_contract_test.ts"]),
            ["verify.frontend.list_optional_columns.unit"],
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
            list(FRONTEND_SOURCE_TARGETS),
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
        self.assertEqual(targets, list(FRONTEND_SOURCE_TARGETS))

    def test_web_tsx_change_uses_the_same_base_targets(self) -> None:
        targets = select_targets(["frontend/apps/web/src/components/Probe.tsx"])
        self.assertEqual(targets, list(FRONTEND_SOURCE_TARGETS))

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
                "verify.frontend.systemic.convergence.static",
                "verify.frontend.typecheck.strict",
            ],
        )

    def test_renderer_registry_and_test_share_the_registration_locks(self) -> None:
        registry = "frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts"
        test = "frontend/apps/web/scripts/professional_component_registry_test.ts"
        self.assertEqual(
            select_targets(["contracts/registry/component.yaml", registry, test]),
            [
                "verify.frontend.lint.src",
                "verify.frontend.professional_component_registry.unit",
                "verify.frontend.systemic.convergence.static",
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
                "verify.frontend.systemic.convergence.static",
                "verify.frontend.typecheck.strict",
                "verify.semantic.registry.lint",
            ],
        )

    def test_native_widget_sources_select_provenance_and_registry_checks(self) -> None:
        self.assertEqual(
            select_targets(["addons/smart_core/core/native_widget_profile.py"]),
            [
                "verify.native_widget.provenance.unit",
                "verify.semantic.registry.lint",
                "verify.unified_page_contract.v2.assembler",
            ],
        )

    def test_native_field_descriptor_selects_producer_and_registry_checks(self) -> None:
        self.assertEqual(
            select_targets([
                "addons/smart_core/utils/native_field_descriptor.py",
                "addons/smart_core/tests/test_native_view_parser_surfaces.py",
            ]),
            [
                "verify.frontend.collection_view_semantics.unit",
                "verify.native_widget.provenance.unit",
                "verify.semantic.registry.lint",
                "verify.unified_page_contract.v2.assembler",
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

    def test_construction_semantic_declarations_keep_the_registry_lint(self) -> None:
        self.assertEqual(
            select_targets([
                "addons/smart_construction_core/core_extension_contract_normalizers.py",
                "scripts/verify/test_construction_semantic_declarations.py",
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
            ]),
            ["verify.local.dev.payment_settlement_journey.unit"],
        )

    def test_local_test_database_reuse_keeps_lifecycle_unit(self) -> None:
        self.assertEqual(
            select_targets(["scripts/dev/local_test_runner.py"]),
            [
                "verify.local.development_lifecycle.unit",
                "verify.orm.guard.self_test",
            ],
        )
        for path in (
            "scripts/verify/test_local_test_runner.py",
            "scripts/verify/test_local_development_lifecycle.py",
            "scripts/dev/local_platform_control.py",
            "scripts/dev/local_platform_release_apply.py",
            "scripts/verify/test_local_platform_control.py",
            "config/ops/local_platform_control.v1.json",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.local.development_lifecycle.unit"],
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
                    ["verify.frontend.dev.incremental.unit"],
                )

    def test_generated_evidence_registry_routes_to_both_consumers(self) -> None:
        self.assertEqual(
            select_targets(["scripts/ops/generated_evidence_paths.py"]),
            [
                "verify.agent.resume.unit",
                "verify.workspace.branch.sync-main",
            ],
        )

    def test_published_branch_sync_inputs_route_to_their_unit(self) -> None:
        for path in (
            "scripts/ops/gitee_published_branch_sync.py",
            "scripts/ops/github_published_branch_sync.py",
            "scripts/ops/test_gitee_published_branch_sync.py",
            "scripts/ops/test_github_published_branch_sync.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(
                    select_targets([path]),
                    ["verify.workspace.branch.sync-github.unit"],
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
        self.assertEqual(
            payload["registrationMissingTargets"],
            [
                "verify.frontend.lint.src",
                "verify.frontend.systemic.convergence.static",
            ],
        )
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

    def test_precommit_generated_refresh_routes_to_lane_coverage(self) -> None:
        self.assertEqual(
            select_targets(["scripts/ops/pre-commit_refresh_generated.sh"]),
            ["verify.verification.lane_coverage"],
        )


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
                    for target in FRONTEND_SOURCE_TARGETS:
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
            "verify.frontend.systemic.convergence.static:\n"
            "\t@printf 'systemic static executed\\n'\n"
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
        reusable=None,
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
                reusable_targets=reusable,
                reusable_results={
                    target: self.reusable_result(target)
                    for target in (reusable or set())
                },
                receipt_dir=receipt_dir,
                worktree_identity=identity or {
                    "head": "a" * 40,
                    "worktreeClean": True,
                    "authoritySha256": {"planner.py": "b" * 64},
                },
            )
        return code, json.loads((receipt_dir / "receipt.json").read_text())

    def reusable_result(self, target: str) -> dict:
        log = self.root / ".runtime" / "reused" / f"{target}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(f"{target}:reused\n", encoding="utf-8")
        return {
            "target": target,
            "status": "passed",
            "returncode": 0,
            "durationSeconds": 0.0,
            "log": log.relative_to(self.root).as_posix(),
            "logSha256": hashlib.sha256(log.read_bytes()).hexdigest(),
            "reusedFrom": ".runtime/agent-runs/TEST/unit.json",
            "reuseReason": "test fixture",
        }

    def test_execution_runs_each_required_target_and_records_logs(self) -> None:
        code, receipt = self.execute(registered=set(FRONTEND_SOURCE_TARGETS))
        self.assertEqual(code, 0)
        self.assertEqual(receipt["status"], "passed")
        self.assertTrue(receipt["testsRun"])
        self.assertTrue(receipt["verificationPassed"])
        self.assertEqual(
            [row["target"] for row in receipt["targetResults"]],
            list(FRONTEND_SOURCE_TARGETS),
        )
        for row in receipt["targetResults"]:
            self.assertEqual(row["returncode"], 0)
            self.assertEqual(len(row["logSha256"]), 64)
            self.assertTrue((self.root / row["log"]).is_file())

    def test_reusable_check_targets_are_not_executed(self) -> None:
        code, receipt = self.execute(
            registered=set(FRONTEND_SOURCE_TARGETS),
            reusable={FRONTEND_SOURCE_TARGETS[0]},
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            [row["target"] for row in receipt["targetResults"]],
            list(FRONTEND_SOURCE_TARGETS),
        )
        self.assertEqual(
            receipt["targetOrder"],
            list(FRONTEND_SOURCE_TARGETS),
        )
        self.assertEqual(
            receipt["executionTargetOrder"],
            list(FRONTEND_SOURCE_TARGETS[1:]),
        )
        self.assertTrue(receipt["targetResults"][0]["reusedFrom"])
        self.assertNotIn("reusedFrom", receipt["targetResults"][1])
        self.assertEqual(receipt["requiredTargets"], list(FRONTEND_SOURCE_TARGETS))
        self.assertEqual(receipt["reusedTargets"], [FRONTEND_SOURCE_TARGETS[0]])
        self.assertEqual(receipt["reusedTargetCount"], 1)
        self.assertEqual(receipt["executedTargetCount"], 2)
        self.assertTrue(receipt["verificationPassed"])

    def test_reusable_check_results_require_materialized_log_evidence(self) -> None:
        checks = {
            "complete": {
                "target": "verify.example",
                "status": "reusable",
                "test_count": 2,
                "source_receipt": ".runtime/agent-runs/TEST/example.json",
                "source_log": ".runtime/example.log",
                "source_log_sha256": "a" * 64,
            },
            "incomplete": {
                "target": "verify.missing",
                "status": "reusable",
                "test_count": 1,
            },
        }
        self.assertEqual(
            set(incremental.reusable_check_results(checks)),
            {"verify.example"},
        )

    def test_all_reusable_check_targets_pass_without_running_make(self) -> None:
        with mock.patch(
            "scripts.verify.frontend_dev_incremental._run_make_target",
            side_effect=AssertionError("reusable checks must not rerun"),
        ):
            code, receipt = self.execute(
                registered=set(FRONTEND_SOURCE_TARGETS),
                reusable=set(FRONTEND_SOURCE_TARGETS),
            )
        self.assertEqual(code, 0)
        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(
            [row["target"] for row in receipt["targetResults"]],
            list(FRONTEND_SOURCE_TARGETS),
        )
        self.assertTrue(
            all(row.get("reusedFrom") for row in receipt["targetResults"])
        )
        self.assertEqual(receipt["reusedTargets"], list(FRONTEND_SOURCE_TARGETS))
        self.assertFalse(receipt["testsRun"])
        self.assertEqual(receipt["executedTargetCount"], 0)
        self.assertTrue(receipt["verificationPassed"])

    def test_mixed_execution_receipt_reuses_completely_on_identical_rerun(self) -> None:
        identity = {
            "head": "a" * 40,
            "tree": "c" * 40,
            "worktreeClean": True,
            "runtimeTreeSha256": "d" * 64,
            "authoritySha256": {"planner.py": "b" * 64},
        }
        first_code, first = self.execute(
            registered=set(FRONTEND_SOURCE_TARGETS),
            reusable={FRONTEND_SOURCE_TARGETS[0]},
            identity=identity,
        )
        self.assertEqual(first_code, 0)
        self.assertEqual(
            [row["target"] for row in first["targetResults"]],
            list(FRONTEND_SOURCE_TARGETS),
        )
        self.assertEqual(first["executedTargetCount"], 2)
        self.assertEqual(first["reusedTargetCount"], 1)

        with mock.patch(
            "scripts.verify.frontend_dev_incremental._run_make_target",
            side_effect=AssertionError("complete mixed receipt must be reusable"),
        ):
            second_code, second = self.execute(
                registered=set(FRONTEND_SOURCE_TARGETS),
                identity=identity,
            )
        self.assertEqual(second_code, 0)
        self.assertTrue(second["reused"])
        self.assertEqual(second["executedTargetCount"], 0)
        self.assertEqual(second["reusedTargetCount"], len(FRONTEND_SOURCE_TARGETS))
        self.assertEqual(second["targetResults"], [])

    def test_tsx_execution_uses_the_same_base_targets(self) -> None:
        path = "frontend/apps/web/src/NewSurface.tsx"
        self.root.joinpath(path).write_text("export const probe = true;\n", encoding="utf-8")
        code, receipt = self.execute(
            registered=set(FRONTEND_SOURCE_TARGETS),
            paths=[path],
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            [row["target"] for row in receipt["targetResults"]],
            list(FRONTEND_SOURCE_TARGETS),
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
        self.assertTrue(set(FRONTEND_SOURCE_TARGETS).issubset(receipt["requiredTargets"]))
        self.assertIn("verify.frontend.primitive_adapter.unit", receipt["requiredTargets"])
        self.assertTrue(receipt["verificationPassed"])

    def test_missing_run_registration_is_owned_by_the_planner(self) -> None:
        code, receipt = self.execute(registered={"verify.frontend.lint.src"})
        self.assertEqual(code, 0)
        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(receipt["registrationMode"], "planner_managed")
        self.assertEqual(
            receipt["registrationMissingTargets"],
            [
                "verify.frontend.systemic.convergence.static",
                "verify.frontend.typecheck.strict",
            ],
        )
        self.assertEqual(
            [row["target"] for row in receipt["targetResults"]],
            list(FRONTEND_SOURCE_TARGETS),
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
            registered=set(FRONTEND_SOURCE_TARGETS),
            identity=identity,
        )
        self.assertEqual(first_code, 0)
        self.assertFalse(first["reused"])
        with mock.patch(
            "scripts.verify.frontend_dev_incremental._run_make_target",
            side_effect=AssertionError("reusable execution must not rerun targets"),
        ):
            second_code, second = self.execute(
                registered=set(FRONTEND_SOURCE_TARGETS),
                identity=identity,
            )
        self.assertEqual(second_code, 0)
        self.assertTrue(second["reused"])
        self.assertEqual(second["status"], "passed")
        self.assertEqual(second["reusedTargetCount"], len(FRONTEND_SOURCE_TARGETS))
        self.assertEqual(second["targetResults"], [])
        self.assertFalse(second["testsRun"])
        self.assertTrue(second["verificationPassed"])
        self.assertEqual(second["sourceReceipt"], "receipt-0/receipt.json")

    def test_equivalent_dirty_and_clean_identity_reuses_verified_receipt(self) -> None:
        clean = {
            "head": "a" * 40,
            "worktreeClean": True,
            "runtimeTreeSha256": "c" * 64,
            "authoritySha256": {"planner.py": "b" * 64},
        }
        dirty = {**clean, "worktreeClean": False}
        first_code, first = self.execute(
            registered=set(FRONTEND_SOURCE_TARGETS),
            identity=dirty,
        )
        self.assertEqual(first_code, 0)
        self.assertFalse(first["reused"])
        code, receipt = self.execute(
            registered=set(FRONTEND_SOURCE_TARGETS),
            identity=clean,
        )
        self.assertEqual(code, 0)
        self.assertTrue(receipt["reused"])
        self.assertEqual(receipt["targetResults"], [])
        self.assertEqual(receipt["sourceReceipt"], "receipt-0/receipt.json")

    def test_changed_runtime_tree_does_not_reuse_verified_receipt(self) -> None:
        identity = {
            "head": "a" * 40,
            "worktreeClean": True,
            "runtimeTreeSha256": "c" * 64,
            "authoritySha256": {"planner.py": "b" * 64},
        }
        self.execute(registered=set(FRONTEND_SOURCE_TARGETS), identity=identity)
        code, receipt = self.execute(
            registered=set(FRONTEND_SOURCE_TARGETS),
            identity={**identity, "runtimeTreeSha256": "d" * 64},
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
            registered=set(FRONTEND_SOURCE_TARGETS),
            identity=identity,
        )
        log = self.root / first["targetResults"][0]["log"]
        log.write_text("tampered\n", encoding="utf-8")
        code, second = self.execute(
            registered=set(FRONTEND_SOURCE_TARGETS),
            identity=identity,
        )
        self.assertEqual(code, 0)
        self.assertFalse(second["reused"])
        self.assertTrue(second["targetResults"])

    def test_unchanged_recorded_failure_blocks_instead_of_blind_retry(self) -> None:
        code, receipt = self.execute(
            registered=set(FRONTEND_SOURCE_TARGETS),
            blocked={"verify.frontend.typecheck.strict"},
        )
        self.assertEqual(code, 2)
        self.assertEqual(receipt["status"], "blocked")
        self.assertEqual(receipt["blockedTargets"], ["verify.frontend.typecheck.strict"])
        self.assertEqual(receipt["targetResults"], [])

    def test_missing_frontend_toolchain_blocks_before_target_execution(self) -> None:
        self.root.joinpath("frontend/apps/web/node_modules/.bin/eslint").unlink()
        code, receipt = self.execute(registered=set(FRONTEND_SOURCE_TARGETS))
        self.assertEqual(code, 2)
        self.assertEqual(receipt["status"], "blocked")
        self.assertEqual(
            receipt["environmentMissing"],
            ["frontend/apps/web/node_modules/.bin/eslint"],
        )
        self.assertEqual(receipt["targetResults"], [])
        self.assertEqual(receipt["notRunTargets"], list(FRONTEND_SOURCE_TARGETS))

    def test_no_relevant_l2_is_not_run_not_pass(self) -> None:
        code, receipt = self.execute(
            registered=set(FRONTEND_SOURCE_TARGETS),
            paths=["docs/record.md"],
        )
        self.assertEqual(code, 0)
        self.assertEqual(receipt["status"], "not_run")
        self.assertFalse(receipt["testsRun"])
        self.assertFalse(receipt["verificationPassed"])

    def test_pure_unmapped_source_is_blocked_with_nonzero_exit(self) -> None:
        path = "addons/smart_core/models/example.py"
        code, receipt = self.execute(
            registered=set(FRONTEND_SOURCE_TARGETS),
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
            "verify.frontend.systemic.convergence.static:\n"
            "\t@printf 'systemic static executed\\n'\n"
            "verify.frontend.typecheck.strict:\n"
            "\t@exit 7\n",
            encoding="utf-8",
        )
        code, receipt = self.execute(registered=set(FRONTEND_SOURCE_TARGETS))
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
            code, receipt = self.execute(registered=set(FRONTEND_SOURCE_TARGETS))
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
            code, receipt = self.execute(registered=set(FRONTEND_SOURCE_TARGETS))
        self.assertEqual(code, 2)
        self.assertEqual(receipt["status"], "blocked")
        self.assertEqual(
            receipt["notRunTargets"],
            ["verify.frontend.systemic.convergence.static", "verify.frontend.typecheck.strict"],
        )
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

    def test_committed_runtime_digest_matches_clean_worktree(self) -> None:
        head = subprocess.check_output(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            text=True,
        ).strip()
        identity = current_identity(self.root, (self.authority,))
        self.assertEqual(
            identity["runtimeTreeSha256"],
            committed_runtime_tree_sha256(self.root, head),
        )

    def test_dirty_worktree_hashes_current_runtime_bytes(self) -> None:
        clean = current_identity(self.root, (self.authority,))
        self.authority.write_text("two\n", encoding="utf-8")
        dirty = current_identity(self.root, (self.authority,))
        self.assertFalse(dirty["worktreeClean"])
        self.assertNotEqual(clean["runtimeTreeSha256"], dirty["runtimeTreeSha256"])

    def test_committing_equivalent_dirty_runtime_keeps_reuse_identity(self) -> None:
        self.authority.write_text("two\n", encoding="utf-8")
        dirty = current_identity(self.root, (self.authority,))
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "source"], check=True)
        clean = current_identity(self.root, (self.authority,))
        self.assertTrue(clean["worktreeClean"])
        self.assertNotEqual(dirty["head"], clean["head"])
        self.assertEqual(reuse_identity(dirty), reuse_identity(clean))

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


class InterruptedExecutionResumeTest(unittest.TestCase):
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
        source = self.root / "frontend/apps/web/src/NewSurface.vue"
        source.parent.mkdir(parents=True)
        source.write_text("<template />\n", encoding="utf-8")
        safe_sync = self.root / "scripts/ops/safe_branch_sync_main.py"
        safe_sync.parent.mkdir(parents=True)
        safe_sync.write_text("VERSION = 1\n", encoding="utf-8")
        self.root.joinpath(".gitignore").write_text(".runtime/\n", encoding="utf-8")
        binaries = self.root / "frontend/apps/web/node_modules/.bin"
        binaries.mkdir(parents=True)
        for tool in ("eslint", "vue-tsc", "esbuild"):
            binary = binaries / tool
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            binary.chmod(0o755)
        self.root.joinpath("Makefile").write_text(
            "verify.frontend.lint.src:\n"
            "\t@printf 'lint check executed\\n'\n"
            "verify.frontend.systemic.convergence.static:\n"
            "\t@printf 'systemic static executed\\n'\n"
            "verify.frontend.typecheck.strict:\n"
            "\t@printf 'typecheck executed\\n'\n"
            "verify.workspace.branch.sync-main:\n"
            "\t@printf 'sync check executed\\n'\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "base"], check=True)
        self.state_patch = mock.patch(
            "scripts.verify.frontend_dev_incremental.write_state"
        )
        self.state_patch.start()
        self.addCleanup(self.state_patch.stop)
        self.paths = [
            "frontend/apps/web/src/NewSurface.vue",
            "scripts/ops/safe_branch_sync_main.py",
        ]

    def _execute(
        self,
        directory: str,
        *,
        interrupted: bool,
        failed_target: str | None = None,
        non_reusable_targets: set[str] | None = None,
    ) -> dict:
        calls = []

        def run_target(target: str, root: Path, log_path: Path) -> dict:
            calls.append(target)
            if failed_target and target == failed_target:
                status = "failed"
            elif interrupted and target == "verify.workspace.branch.sync-main":
                status = "interrupted"
            else:
                status = "passed"
            log_path.write_text(f"{target}:{status}\n", encoding="utf-8")
            return {
                "target": target,
                "command": ["make", "--no-print-directory", target],
                "status": status,
                "returncode": 0 if status == "passed" else (1 if status == "failed" else 130),
                "durationSeconds": 0.1,
                "log": str(log_path),
                "logSha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
            }

        with mock.patch(
            "scripts.verify.frontend_dev_incremental._run_make_target",
            side_effect=run_target,
        ):
            code = execute_targets(
                self.paths,
                root=self.root,
                non_reusable_targets=non_reusable_targets,
                registered_targets={
                    "verify.frontend.lint.src",
                    "verify.frontend.typecheck.strict",
                    "verify.workspace.branch.sync-main",
                },
                receipt_dir=self.root
                / ".runtime/frontend-dev-validation/executions"
                / directory,
                worktree_identity=incremental.current_execution_identity(self.root),
            )
        receipt = json.loads(
            (
                self.root
                / ".runtime/frontend-dev-validation/executions"
                / directory
                / "receipt.json"
            ).read_text(encoding="utf-8")
        )
        receipt["_code"] = code
        receipt["_calls"] = calls
        return receipt

    def test_interrupted_prefix_is_resumed_and_changed_target_is_rechecked(self) -> None:
        first = self._execute("first", interrupted=True)
        self.assertEqual(first["_code"], 130)
        self.assertEqual(first["status"], "interrupted")

        safe_sync = self.root / "scripts/ops/safe_branch_sync_main.py"
        safe_sync.write_text("VERSION = 2\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "tool"], check=True)

        second = self._execute("second", interrupted=False)
        self.assertEqual(second["_code"], 0)
        self.assertEqual(second["status"], "passed")
        self.assertEqual(second["_calls"], ["verify.workspace.branch.sync-main"])
        self.assertEqual(second["executedTargetCount"], 1)
        self.assertEqual(second["reusedTargetCount"], 3)
        self.assertEqual(
            second["sourceReceipt"],
            ".runtime/frontend-dev-validation/executions/first/receipt.json",
        )
        self.assertTrue(
            all(
                row.get("reusedFrom") == second["sourceReceipt"]
                for row in second["targetResults"]
                if row["target"] != "verify.workspace.branch.sync-main"
            )
        )

    def test_dirty_non_runtime_path_does_not_block_same_head_resume(self) -> None:
        first = self._execute("first", interrupted=True)
        self.assertEqual(first["_code"], 130)
        docs = self.root / "docs/notes.md"
        docs.parent.mkdir(parents=True)
        docs.write_text("uncommitted bookkeeping\n", encoding="utf-8")

        receipt, head, rows = incremental.resumable_receipt_results(
            self.root,
            self.paths,
            ["verify.frontend.lint.src"],
        )

        self.assertEqual(
            receipt,
            self.root
            / ".runtime/frontend-dev-validation/executions/first/receipt.json",
        )
        self.assertEqual(head, first["identity"]["head"])
        self.assertEqual(set(rows), {"verify.frontend.lint.src"})

    def test_dirty_candidate_same_identity_resumes_passed_prefix(self) -> None:
        source = self.root / "frontend/apps/web/src/NewSurface.vue"
        source.write_text("<template><main /></template>\n", encoding="utf-8")
        safe_sync = self.root / "scripts/ops/safe_branch_sync_main.py"
        safe_sync.write_text("VERSION = 2\n", encoding="utf-8")
        self.assertFalse(current_identity(self.root)["worktreeClean"])

        first = self._execute("first", interrupted=True)
        self.assertEqual(first["_code"], 130)
        second = self._execute("second", interrupted=False)

        self.assertEqual(second["_code"], 0)
        self.assertEqual(second["_calls"], ["verify.workspace.branch.sync-main"])
        self.assertEqual(second["executedTargetCount"], 1)
        self.assertEqual(second["reusedTargetCount"], 3)
        self.assertEqual(
            second["sourceReceipt"],
            ".runtime/frontend-dev-validation/executions/first/receipt.json",
        )

    def test_changed_runtime_tree_blocks_same_head_resume(self) -> None:
        self._execute("first", interrupted=True)
        source = self.root / "frontend/apps/web/src/NewSurface.vue"
        source.write_text("<template><div /></template>\n", encoding="utf-8")

        receipt, _, rows = incremental.resumable_receipt_results(
            self.root,
            self.paths,
            ["verify.frontend.lint.src"],
        )

        self.assertIsNone(receipt)
        self.assertEqual(rows, {})

    def test_reverted_dirty_fix_cannot_survive_unrelated_commit(self) -> None:
        source = self.root / "frontend/apps/web/src/NewSurface.vue"
        original = source.read_text()
        source.write_text("<template><main /></template>\n")
        first = self._execute("first", interrupted=True)
        self.assertFalse(first["identity"]["worktreeClean"])
        source.write_text(original)
        self.root.joinpath("note.md").write_text("unrelated documentation\n")
        subprocess.run(["git", "-C", str(self.root), "add", "note.md"], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "note"], check=True)
        second = self._execute("second", interrupted=False)
        self.assertEqual(second["_code"], 0)
        self.assertIn("verify.frontend.lint.src", second["_calls"])
        self.assertIn("verify.frontend.typecheck.strict", second["_calls"])
        self.assertEqual(second["reusedTargetCount"], 0)

    def test_clean_commit_of_same_runtime_identity_resumes_passed_prefix(self) -> None:
        source = self.root / "frontend/apps/web/src/NewSurface.vue"
        source.write_text("<template><main /></template>\n", encoding="utf-8")
        first = self._execute("first", interrupted=True)
        self.assertEqual(first["_code"], 130)

        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-qm", "candidate"],
            check=True,
        )
        second = self._execute("second", interrupted=False)

        self.assertEqual(second["_code"], 0)
        self.assertEqual(second["_calls"], ["verify.workspace.branch.sync-main"])
        self.assertEqual(second["reusedTargetCount"], 3)

    def test_changed_verifier_authority_blocks_resume(self) -> None:
        self._execute("first", interrupted=True)
        authority = self.root / "make/frontend.mk"
        authority.parent.mkdir(parents=True)
        authority.write_text("# changed resume authority\n", encoding="utf-8")

        receipt, _, rows = incremental.resumable_receipt_results(
            self.root,
            self.paths,
            ["verify.frontend.lint.src"],
        )

        self.assertIsNone(receipt)
        self.assertEqual(rows, {})

    def test_non_ancestor_receipt_head_blocks_resume(self) -> None:
        self._execute("first", interrupted=True)
        source = self.root / "frontend/apps/web/src/NewSurface.vue"
        source.write_text("<template><div /></template>\n", encoding="utf-8")
        with mock.patch.object(incremental, "_is_ancestor", return_value=False):
            receipt, _, rows = incremental.resumable_receipt_results(
                self.root,
                self.paths,
                ["verify.frontend.lint.src"],
            )

        self.assertIsNone(receipt)
        self.assertEqual(rows, {})

    def test_rewritten_commit_with_same_runtime_identity_resumes(self) -> None:
        first = self._execute("first", interrupted=True)
        self.assertEqual(first["_code"], 130)
        environment = dict(
            incremental.os.environ,
            GIT_COMMITTER_DATE="2030-01-01T00:00:00+0000",
        )
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "--amend", "--no-edit", "--allow-empty"],
            check=True,
            env=environment,
        )

        receipt, _, rows = incremental.resumable_receipt_results(
            self.root,
            self.paths,
            ["verify.frontend.lint.src"],
        )

        self.assertIsNotNone(receipt)
        self.assertEqual(set(rows), {"verify.frontend.lint.src"})

    def test_complete_pass_is_preferred_over_newer_interrupted_receipt(self) -> None:
        complete = self._execute("complete", interrupted=False)
        self.assertEqual(complete["_code"], 0)

        safe_sync = self.root / "scripts/ops/safe_branch_sync_main.py"
        safe_sync.write_text("VERSION = 2\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-qm", "tool"],
            check=True,
        )
        interrupted = self._execute("interrupted", interrupted=True)
        self.assertEqual(interrupted["_code"], 130)

        receipt, head, rows = incremental.resumable_receipt_results(
            self.root,
            self.paths,
            ["verify.frontend.lint.src"],
        )
        self.assertEqual(
            receipt,
            self.root
            / ".runtime/frontend-dev-validation/executions/complete/receipt.json",
        )
        self.assertEqual(head, complete["identity"]["head"])
        self.assertEqual(set(rows), {"verify.frontend.lint.src"})

    def test_passed_receipt_reuses_unaffected_targets_after_source_change(self) -> None:
        first = self._execute("first", interrupted=False)
        self.assertEqual(first["_code"], 0)
        self.assertEqual(first["status"], "passed")

        safe_sync = self.root / "scripts/ops/safe_branch_sync_main.py"
        safe_sync.write_text("VERSION = 2\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "tool"], check=True)

        second = self._execute("second", interrupted=False)
        self.assertEqual(second["_code"], 0)
        self.assertEqual(second["status"], "passed")
        self.assertEqual(second["_calls"], ["verify.workspace.branch.sync-main"])
        self.assertEqual(second["executedTargetCount"], 1)
        self.assertEqual(second["reusedTargetCount"], 3)
        self.assertEqual(
            second["sourceReceipt"],
            ".runtime/frontend-dev-validation/executions/first/receipt.json",
        )

    def test_new_unrelated_target_does_not_rerun_passed_business_targets(self) -> None:
        self.paths = ["frontend/apps/web/src/NewSurface.vue"]
        first = self._execute("first", interrupted=False)
        self.assertEqual(first["_code"], 0)
        self.paths.append("scripts/ops/safe_branch_sync_main.py")
        second = self._execute("second", interrupted=False)
        self.assertEqual(second["_code"], 0)
        self.assertEqual(second["_calls"], ["verify.workspace.branch.sync-main"])
        self.assertEqual(second["reusedTargetCount"], 3)

    def test_declared_stale_input_cannot_be_overridden_by_aggregate(self) -> None:
        self._execute("first", interrupted=False)
        target = "verify.workspace.branch.sync-main"
        second = self._execute("second", interrupted=False, non_reusable_targets={target})
        self.assertEqual(second["_code"], 0)
        self.assertEqual(second["_calls"], [target])
        self.assertEqual(second["reusedTargetCount"], 3)

    def test_remaining_target_subset_reuses_only_verified_source_rows(self) -> None:
        self._execute("first", interrupted=False)
        target = "verify.frontend.typecheck.strict"
        receipt, _, rows = incremental.resumable_receipt_results(
            self.root, self.paths + ["docs/new-note.md"], [target],
        )
        self.assertIsNotNone(receipt)
        self.assertEqual([target], list(rows))
        source = json.loads(receipt.read_text())
        row = next(row for row in source["targetResults"] if row["target"] == target)
        (self.root / row["log"]).write_text("tampered\n")
        self.assertEqual({}, incremental.resumable_receipt_results(
            self.root, self.paths, [target],
        )[2])

    def test_failed_receipt_reuses_only_verified_passed_targets(self) -> None:
        first = self._execute(
            "first",
            interrupted=False,
            failed_target="verify.workspace.branch.sync-main",
        )
        self.assertEqual(first["_code"], 1)
        self.assertEqual(first["status"], "failed")

        second = self._execute("second", interrupted=False)
        self.assertEqual(second["_code"], 0)
        self.assertEqual(second["_calls"], ["verify.workspace.branch.sync-main"])
        self.assertEqual(second["reusedTargetCount"], 3)


class RunScopedPlannerTest(unittest.TestCase):
    def setUp(self):
        from scripts.verify.test_agent_run_context import RunContextTest
        self.fixture = RunContextTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def _install_checkpoint_authority(self) -> None:
        for path in incremental.CHECKPOINT_AUTHORITY_PATHS:
            self.fixture.write(path, (ROOT / path).read_text(encoding="utf-8"))

    def _write_checkpoint_receipt(
        self,
        head: str,
        changed_paths: list[str],
        *,
        baseline_sha: str,
        baseline_kind: str = "run_baseline",
        mutate=None,
    ) -> Path:
        fixture = self.fixture
        targets = select_targets(changed_paths)
        folder = fixture.root / ".runtime/frontend-dev-validation/executions" / f"checkpoint-{head[:8]}"
        folder.mkdir(parents=True, exist_ok=True)
        result_rows = []
        for index, target in enumerate(targets):
            log = folder / f"{index}-{target}.log"
            log.write_text(f"{target}:passed\n", encoding="utf-8")
            result_rows.append({
                "target": target,
                "status": "passed",
                "returncode": 0,
                "log": str(log),
                "logSha256": hashlib.sha256(log.read_bytes()).hexdigest(),
            })
        receipt = {
            "schemaVersion": 1,
            "mode": "development_incremental_execution",
            "status": "passed",
            "verificationPassed": True,
            "testsRun": True,
            "identity": {
                "head": head,
                "tree": fixture.git("rev-parse", f"{head}^{{tree}}"),
                "worktreeClean": True,
                "runtimeTreeSha256": committed_runtime_tree_sha256(fixture.root, head),
                "authoritySha256": {
                    path: hashlib.sha256(incremental._historical_blob(fixture.root, head, path)).hexdigest()
                    for path in incremental.CHECKPOINT_AUTHORITY_PATHS
                },
            },
            "changedPaths": changed_paths,
            "requiredTargets": targets,
            "targetOrder": targets,
            "targetResults": result_rows,
            "notRunTargets": [],
            "iterationBaselineSha": baseline_sha,
            "iterationBaselineKind": baseline_kind,
        }
        if mutate is not None:
            mutate(receipt)
        path = folder / "receipt.json"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        return path

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

    def test_verified_ancestor_receipt_becomes_incremental_checkpoint(self):
        fixture = self.fixture
        self._install_checkpoint_authority()
        checkpoint_path = 'frontend/apps/web/src/Checkpoint.vue'
        latest_path = 'frontend/apps/web/src/Latest.vue'
        fixture.write(checkpoint_path, 'checkpoint')
        fixture.git('add', '.')
        fixture.git('commit', '-qm', 'checkpoint')
        checkpoint = fixture.git('rev-parse', 'HEAD')
        checkpoint_paths = fixture.git(
            'diff', '--name-only', fixture.run['baseline_sha'], checkpoint
        ).splitlines()
        self._write_checkpoint_receipt(
            checkpoint,
            checkpoint_paths,
            baseline_sha=fixture.run['baseline_sha'],
            mutate=lambda receipt: receipt['targetResults'][0].update({
                'reusedFrom': '.runtime/agent-runs/TEST/source.json',
                'reuseReason': 'verified source row',
            }),
        )
        fixture.write(latest_path, 'latest')
        fixture.git('add', '.')
        fixture.git('commit', '-qm', 'latest')

        resolved_checkpoint, kind, paths = iteration_scope(fixture.root, fixture.run)
        self.assertEqual(resolved_checkpoint, checkpoint)
        self.assertEqual(kind, 'verified_incremental_receipt')
        self.assertEqual(paths, [latest_path])

        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(iteration_plan(fixture.root), 0)
        payload = json.loads(output.getvalue().split('] ', 1)[1])
        self.assertEqual(payload['iterationBaselineSha'], checkpoint)
        self.assertEqual(payload['iterationBaselineKind'], 'verified_incremental_receipt')
        self.assertEqual(payload['changedPathCount'], 1)

    def test_incomplete_checkpoint_receipts_fall_back_to_run_baseline(self):
        fixture = self.fixture
        self._install_checkpoint_authority()
        checkpoint_path = 'frontend/apps/web/src/Checkpoint.vue'
        latest_path = 'frontend/apps/web/src/Latest.vue'
        fixture.write(checkpoint_path, 'checkpoint')
        fixture.git('add', '.')
        fixture.git('commit', '-qm', 'checkpoint')
        checkpoint = fixture.git('rev-parse', 'HEAD')
        checkpoint_paths = fixture.git(
            'diff', '--name-only', fixture.run['baseline_sha'], checkpoint
        ).splitlines()
        fixture.write(latest_path, 'latest')
        fixture.git('add', '.')
        fixture.git('commit', '-qm', 'latest')

        def assert_fallback(label: str, mutate) -> None:
            receipt_path = self._write_checkpoint_receipt(
                checkpoint,
                checkpoint_paths,
                baseline_sha=fixture.run['baseline_sha'],
                mutate=mutate,
            )
            resolved, kind, _ = iteration_scope(fixture.root, fixture.run)
            self.assertEqual(resolved, fixture.run['baseline_sha'], label)
            self.assertEqual(kind, 'run_baseline', label)
            receipt_path.unlink()

        assert_fallback('empty targetResults', lambda receipt: receipt.update({
            'targetResults': [],
        }))
        assert_fallback('missing target result', lambda receipt: receipt.update({
            'targetResults': receipt['targetResults'][1:],
        }))
        assert_fallback('forged pass result', lambda receipt: receipt['targetResults'][0].update({
            'status': 'failed',
            'returncode': 1,
        }))
        assert_fallback('open not-run closure', lambda receipt: receipt.update({
            'notRunTargets': list(receipt['requiredTargets']),
        }))
        assert_fallback('replaced runtime digest', lambda receipt: receipt['identity'].update({
            'runtimeTreeSha256': 'f' * 64,
        }))
        assert_fallback('replaced authority digest', lambda receipt: receipt['identity'][
            'authoritySha256'
        ].update({
            'make/frontend.mk': 'f' * 64,
        }))

    def test_broken_checkpoint_source_chain_falls_back_to_run_baseline(self):
        fixture = self.fixture
        self._install_checkpoint_authority()
        checkpoint_path = 'frontend/apps/web/src/Checkpoint.vue'
        latest_path = 'frontend/apps/web/src/Latest.vue'
        unreceipted_parent = fixture.git('rev-parse', 'HEAD')
        fixture.write(checkpoint_path, 'checkpoint')
        fixture.git('add', '.')
        fixture.git('commit', '-qm', 'checkpoint')
        checkpoint = fixture.git('rev-parse', 'HEAD')
        checkpoint_paths = fixture.git(
            'diff', '--name-only', unreceipted_parent, checkpoint
        ).splitlines()
        self._write_checkpoint_receipt(
            checkpoint,
            checkpoint_paths,
            baseline_sha=unreceipted_parent,
            baseline_kind='verified_incremental_receipt',
        )
        fixture.write(latest_path, 'latest')
        fixture.git('add', '.')
        fixture.git('commit', '-qm', 'latest')
        resolved, kind, _ = iteration_scope(fixture.root, fixture.run)
        self.assertEqual(resolved, fixture.run['baseline_sha'])
        self.assertEqual(kind, 'run_baseline')

    def test_historical_target_mapping_mismatch_falls_back_to_run_baseline(self):
        fixture = self.fixture
        self._install_checkpoint_authority()
        mapping_path = 'scripts/verify/frontend_dev_incremental.py'
        fixture.write(
            mapping_path,
            fixture.root.joinpath(mapping_path).read_text(encoding='utf-8')
            + (
                '\n_original_select_targets = select_targets\n'
                'def select_targets(paths):\n'
                '    return [target for target in _original_select_targets(paths) '
                'if target != "verify.frontend.typecheck.strict"]\n'
            ),
        )
        fixture.write('frontend/apps/web/src/Checkpoint.vue', 'checkpoint')
        fixture.git('add', '.')
        fixture.git('commit', '-qm', 'checkpoint with changed mapping')
        checkpoint = fixture.git('rev-parse', 'HEAD')
        checkpoint_paths = fixture.git(
            'diff', '--name-only', fixture.run['baseline_sha'], checkpoint
        ).splitlines()
        self._write_checkpoint_receipt(
            checkpoint,
            checkpoint_paths,
            baseline_sha=fixture.run['baseline_sha'],
        )
        fixture.write('frontend/apps/web/src/Latest.vue', 'latest')
        fixture.git('add', '.')
        fixture.git('commit', '-qm', 'latest')
        resolved, kind, _ = iteration_scope(fixture.root, fixture.run)
        self.assertEqual(resolved, fixture.run['baseline_sha'])
        self.assertEqual(kind, 'run_baseline')

    def test_unverified_receipt_falls_back_to_run_baseline(self):
        fixture = self.fixture
        receipt_path = (
            fixture.root
            / '.runtime/frontend-dev-validation/executions/unverified/receipt.json'
        )
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps({
            'status': 'failed',
            'verificationPassed': False,
            'identity': {'head': fixture.git('rev-parse', 'HEAD'), 'worktreeClean': True},
        }), encoding='utf-8')
        checkpoint, kind, _ = iteration_scope(fixture.root, fixture.run)
        self.assertEqual(checkpoint, fixture.run['baseline_sha'])
        self.assertEqual(kind, 'run_baseline')

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

    def test_worktree_execution_passes_reusable_checks_to_the_executor(self):
        fixture = self.fixture
        with (
            mock.patch.object(
                incremental,
                "resolve_run",
                return_value=(".agent/runs/TEST/run.json", fixture.run),
            ),
            mock.patch.object(
                incremental,
                "iteration_scope",
                return_value=(fixture.run["baseline_sha"], "run_baseline", ["source/a.py"]),
            ),
            mock.patch.object(incremental, "select_targets", return_value=["verify.test"]),
            mock.patch.object(
                incremental,
                "check_states",
                return_value={
                    "unit": {
                        "target": "verify.test",
                        "status": "reusable",
                        "test_count": 2,
                        "source_receipt": ".runtime/agent-runs/TEST/unit.json",
                        "source_log": ".runtime/check.log",
                        "source_log_sha256": "a" * 64,
                    },
                },
            ),
            mock.patch.object(incremental, "execute_targets", return_value=0) as execute,
        ):
            self.assertEqual(incremental.execute_worktree(fixture.root), 0)
        self.assertEqual(execute.call_args.kwargs["reusable_targets"], {"verify.test"})
        self.assertEqual(
            execute.call_args.kwargs["reusable_results"]["verify.test"]["log"],
            ".runtime/check.log",
        )

    def test_worktree_execution_auto_registers_only_offline_affected_targets(self):
        fixture = self.fixture
        with (
            mock.patch.object(
                incremental,
                "resolve_run",
                return_value=(".agent/runs/TEST/run.json", fixture.run),
            ),
            mock.patch.object(
                incremental,
                "iteration_scope",
                return_value=(fixture.run["baseline_sha"], "run_baseline", ["source/a.py"]),
            ),
            mock.patch.object(
                incremental,
                "select_targets",
                return_value=["verify.alpha.unit", "verify.beta.orm"],
            ),
            mock.patch.object(incremental, "check_states", return_value={}),
            mock.patch.object(incremental, "execute_targets", return_value=0) as execute,
        ):
            self.assertEqual(incremental.execute_worktree(fixture.root), 0)

        self.assertEqual(
            execute.call_args.kwargs["registered_targets"],
            {"verify.alpha.unit", "verify.test"},
        )
        self.assertEqual(
            execute.call_args.kwargs["non_reusable_targets"],
            {"verify.beta.orm"},
        )

    def test_missing_runtime_receipt_cannot_borrow_aggregate_success(self):
        fixture = self.fixture
        for kind in ("runtime", None, "offline", "unregistered"):
            with self.subTest(kind=kind):
                check = {"target": "verify.test"}
                if kind is not None:
                    check["kind"] = kind
                run = {**fixture.run, "checks": {} if kind == "unregistered" else {"unit": check}}
                with (
                    mock.patch.object(incremental, "resolve_run", return_value=("run.json", run)),
                    mock.patch.object(incremental, "iteration_scope", return_value=(
                        fixture.run["baseline_sha"], "run_baseline", ["source/a.py"])),
                    mock.patch.object(incremental, "select_targets", return_value=["verify.test"]),
                    mock.patch.object(incremental, "check_states", return_value=(
                        {} if kind == "unregistered" else {
                            "unit": {"target": "verify.test", "status": "not_run"}})),
                    mock.patch.object(incremental, "execute_targets", return_value=0) as execute,
                ):
                    self.assertEqual(incremental.execute_worktree(fixture.root), 0)
                self.assertEqual(
                    set() if kind == "offline" else {"verify.test"},
                    execute.call_args.kwargs["non_reusable_targets"],
                )

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

    def test_identity_architecture_inputs_select_their_owner(self):
        self.assertEqual(
            select_targets([
                "scripts/verify/identity_architecture_audit_guard.py"
            ]),
            ["verify.identity.architecture.audit.unit"],
        )

    def test_mixed_targets_report_backend_frontend_and_governance_layers(self):
        self.assertEqual(
            target_layers([
                "verify.frontend.typecheck.strict",
                "verify.daily.permission_truth.capability.orm",
                "verify.identity.architecture.audit.unit",
            ]),
            ["frontend", "backend", "governance"],
        )

    def test_plan_reports_execution_layers_and_neutral_entrypoint(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                print_plan([
                    "frontend/apps/web/src/NewSurface.tsx",
                    "addons/smart_construction_scene/__manifest__.py",
                    "scripts/verify/identity_architecture_audit_guard.py",
                ]),
                0,
            )
        label, raw_payload = output.getvalue().split("] ", 1)
        payload = json.loads(raw_payload)
        self.assertEqual(label, "[local.incremental.plan")
        self.assertEqual(
            payload["requiredLayers"],
            ["frontend", "backend", "governance"],
        )
        self.assertEqual(
            payload["executionLayers"],
            ["frontend", "backend", "governance"],
        )


if __name__ == "__main__":
    unittest.main()
