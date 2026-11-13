#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

try:
    from scripts.ci import backend_impact_plan as planner
    from scripts.ci import ci_path_ownership as ownership
    from scripts.ci.ci_risk_classifier import classify
except ImportError:
    import backend_impact_plan as planner
    import ci_path_ownership as ownership
    from ci_risk_classifier import classify


def module(deps=()):
    return {
        "depends": set(deps),
        "tests": True,
        "installable": True,
        "file_inputs": [],
        "unresolved_file_reads": [],
        "unresolved_imports": [],
        "unresolved_sql": [],
        "external_imports": [],
        "sql_reads": [],
    }


class PathOwnershipRegistryTest(unittest.TestCase):
    def category(self, path: str) -> str:
        result = ownership.classify_paths([path])
        self.assertEqual([], list(result.unknown_paths))
        return result.assignments[path]

    def test_frontend_quality_tooling_is_not_backend_quality_tooling(self):
        result = ownership.classify_paths([
            "scripts/verify/frontend_contract_basis_guard.py",
            "scripts/verify/test_frontend_contract_basis_guard.py",
        ])
        self.assertEqual(
            set(result.assignments.values()),
            {"frontend_quality_tooling"},
        )
        self.assertTrue(result.frontend_changed)
        self.assertFalse(result.backend_changed)
        self.assertFalse(result.control_plane_changed)

        ci_result = ownership.classify_paths([
            "scripts/ci/frontend_professional_extension_guard.py",
        ])
        self.assertEqual(
            ci_result.assignments["scripts/ci/frontend_professional_extension_guard.py"],
            "frontend_ci_tooling",
        )
        self.assertTrue(ci_result.frontend_changed)
        self.assertFalse(ci_result.backend_changed)
        self.assertTrue(ci_result.control_plane_changed)

    def test_non_frontend_verify_script_remains_backend_tooling(self):
        result = ownership.classify_paths([
            "scripts/verify/backend_contract_guard.py",
        ])
        self.assertEqual(result.assignments, {
            "scripts/verify/backend_contract_guard.py": "backend_quality_tooling",
        })
        self.assertTrue(result.backend_changed)
        self.assertFalse(result.backend_runtime_changed)

    def test_frontend_and_codex_makefiles_have_different_owners(self):
        result = ownership.classify_paths([
            "make/frontend.mk",
            "make/codex.mk",
            "make/frontend_professional_extensions.mk",
        ])
        self.assertEqual(result.assignments["make/frontend.mk"], "frontend_delivery_make")
        self.assertEqual(result.assignments["make/codex.mk"], "codex_control_plane")
        self.assertEqual(
            result.assignments["make/frontend_professional_extensions.mk"],
            "frontend_extension_make",
        )

    def test_agent_run_registration_and_governance_are_distinct(self):
        self.assertEqual(
            self.category(".agent/runs/FE-LOOP-02/run.json"),
            "agent_run_registration",
        )
        self.assertEqual(
            self.category(".agent/active-runs.json"),
            "agent_run_registration",
        )
        self.assertEqual(
            self.category(".agent/context.yaml"),
            "agent_governance",
        )
        self.assertEqual(
            self.category(".agent/decisions/ci-path-ownership.yaml"),
            "agent_governance",
        )

    def test_unknown_and_invalid_paths_are_visible(self):
        result = ownership.classify_paths(["unexpected/path.bin", "../escape.py"])
        self.assertEqual(result.unknown_paths, ("unexpected/path.bin",))
        self.assertEqual(len(result.invalid_paths), 1)

    def test_risk_policy_names_the_shared_ownership_registry(self):
        policy = json.loads(
            (Path(__file__).resolve().parents[2] / "config/ci/risk_tiering_v1.json").read_text()
        )
        self.assertEqual(
            policy["path_ownership_registry"],
            "config/ci/path_ownership_v1.json",
        )

    def test_known_toolchain_config_paths_have_exact_nonruntime_owners(self):
        probe = "config/frontend/probe_toolchain_registry.json"
        secrets = "config/security/secret_scan_false_positives.v1.json"
        result = ownership.classify_paths([probe, secrets])

        self.assertEqual(result.assignments[probe], "frontend_probe_toolchain_config")
        self.assertEqual(result.assignments[secrets], "security_scan_exception_config")
        self.assertEqual(result.unknown_paths, ())
        self.assertTrue(result.frontend_changed)
        self.assertFalse(result.backend_changed)
        self.assertFalse(result.backend_runtime_changed)
        self.assertTrue(result.control_plane_changed)
        self.assertEqual(
            result.category_for(probe).tool_checks,
            ("verify.local.dev.project_profile_write.unit",),
        )
        self.assertEqual(
            result.category_for(secrets).tool_checks,
            ("security.secrets.scan",),
        )

    def test_database_lifecycle_tooling_selects_backend_runtime(self):
        path = "scripts/db/create.sh"
        registry = ownership.classify_paths([path])
        risk = classify([path], event_name="pull_request")
        backend = planner.select(
            [path],
            {"kernel": module(), "bundle": module(["kernel"])},
            {"kernel": module(), "bundle": module(["kernel"])},
        )

        self.assertEqual(registry.assignments[path], "database_lifecycle_tooling")
        self.assertTrue(risk.backend_changed)
        self.assertTrue(risk.backend_runtime_changed)
        self.assertTrue(risk.orm_required)
        self.assertEqual(backend["mode"], "full")
        self.assertEqual(backend["modules"], ["bundle", "kernel"])
        self.assertIn("shared_runtime:" + path, backend["reasons"])
        self.assertIn("verify.frontend.standard_preview.unit", backend["tool_checks"])

    def test_ownership_tool_checks_name_registered_make_targets(self):
        makefiles = sorted((Path(__file__).resolve().parents[2] / "make").glob("*.mk"))
        targets_text = "\n".join(path.read_text(encoding="utf-8") for path in makefiles)
        checks = {
            target
            for category in ownership.load_registry().values()
            for target in category.tool_checks
        }
        self.assertTrue(checks)
        for target in sorted(checks):
            with self.subTest(target=target):
                self.assertIn(f"{target}:", targets_text)


class FiveCiScenarioTest(unittest.TestCase):
    def setUp(self):
        self.graph = {
            "kernel": module(),
            "bundle": module(["kernel"]),
            "unrelated": module(),
        }

    def classify(self, *paths: str):
        return classify(paths, event_name="pull_request")

    def plan(self, *paths: str):
        return planner.select(list(paths), self.graph, self.graph)

    def test_pure_frontend_runs_frontend_scope_without_backend_or_orm(self):
        path = "frontend/apps/web/src/pages/ProjectList.vue"
        risk = self.classify(path)
        backend = self.plan(path)
        self.assertEqual(risk.lane, "STANDARD")
        self.assertEqual(risk.frontend_mode, "standard")
        self.assertTrue(risk.frontend_changed)
        self.assertFalse(risk.backend_changed)
        self.assertFalse(risk.control_plane_changed)
        self.assertFalse(risk.backend_runtime_changed)
        self.assertFalse(risk.orm_required)
        self.assertEqual(backend["modules"], [])
        self.assertEqual(backend["tool_checks"], [])
        self.assertEqual(backend["scope_status"], "NOT_APPLICABLE")

    def test_pure_frontend_quality_tooling_stays_frontend_standard(self):
        path = "scripts/verify/frontend_contract_basis_guard.py"
        risk = self.classify(path)
        backend = self.plan(path)
        self.assertEqual(risk.lane, "STANDARD")
        self.assertTrue(risk.frontend_changed)
        self.assertFalse(risk.backend_changed)
        self.assertFalse(risk.backend_runtime_changed)
        self.assertFalse(risk.control_plane_changed)
        self.assertEqual(risk.professional_mode, "standard_frontend")
        self.assertEqual(backend["modules"], [])
        self.assertIn("verify.frontend.dev.incremental.unit", backend["tool_checks"])
        self.assertEqual(backend["scope_status"], "NOT_APPLICABLE")

    def test_backend_quality_tooling_is_governance_without_runtime(self):
        path = "scripts/verify/backend_contract_guard.py"
        risk = self.classify(path)
        backend = self.plan(path)
        self.assertEqual(risk.lane, "STANDARD")
        self.assertFalse(risk.frontend_changed)
        self.assertTrue(risk.backend_changed)
        self.assertFalse(risk.backend_runtime_changed)
        self.assertFalse(risk.control_plane_changed)
        self.assertEqual(risk.professional_mode, "governance")
        self.assertFalse(risk.orm_required)
        self.assertEqual(backend["modules"], [])
        self.assertEqual(backend["scope_status"], "NOT_APPLICABLE")

    def test_pure_backend_runs_only_selected_module_closure(self):
        path = "addons/bundle/models/record.py"
        risk = self.classify(path)
        backend = self.plan(path)
        self.assertEqual(risk.lane, "STANDARD")
        self.assertFalse(risk.frontend_changed)
        self.assertTrue(risk.backend_changed)
        self.assertTrue(risk.backend_runtime_changed)
        self.assertFalse(risk.control_plane_changed)
        self.assertTrue(risk.orm_required)
        self.assertEqual(backend["modules"], ["bundle"])
        self.assertEqual(backend["mode"], "incremental")

    def test_mixed_change_keeps_frontend_and_backend_mandatory_scopes(self):
        frontend = "frontend/apps/web/src/pages/ProjectList.vue"
        backend_path = "addons/bundle/models/record.py"
        risk = self.classify(frontend, backend_path)
        backend = self.plan(frontend, backend_path)
        self.assertEqual(risk.lane, "STANDARD")
        self.assertTrue(risk.frontend_changed)
        self.assertTrue(risk.backend_changed)
        self.assertTrue(risk.backend_runtime_changed)
        self.assertFalse(risk.control_plane_changed)
        self.assertTrue(risk.orm_required)
        self.assertEqual(backend["modules"], ["bundle"])
        self.assertEqual(backend["mode"], "incremental")

    def test_pure_ci_tooling_is_control_plane_not_backend_business(self):
        path = "scripts/ci/backend_impact_plan.py"
        risk = self.classify(path)
        backend = self.plan(path)
        self.assertEqual(risk.lane, "HIGH_RISK")
        self.assertEqual(risk.professional_mode, "full")
        self.assertFalse(risk.frontend_changed)
        self.assertFalse(risk.backend_changed)
        self.assertTrue(risk.control_plane_changed)
        self.assertFalse(risk.backend_runtime_changed)
        self.assertFalse(risk.orm_required)
        self.assertEqual(backend["modules"], [])
        self.assertIn("verify.ci.workflow.contract", backend["tool_checks"])
        self.assertEqual(backend["scope_status"], "NOT_APPLICABLE")

    def test_release_and_security_control_plane_do_not_trigger_module_suite(self):
        paths = [
            ".github/workflows/frontend_release_gate.yml",
            "scripts/release/publish.py",
            "scripts/verify/github_actions_security_guard.py",
        ]
        risk = self.classify(*paths)
        backend = self.plan(*paths)
        self.assertEqual(risk.lane, "HIGH_RISK")
        self.assertFalse(risk.frontend_changed)
        self.assertFalse(risk.backend_changed)
        self.assertTrue(risk.control_plane_changed)
        self.assertFalse(risk.backend_runtime_changed)
        self.assertFalse(risk.orm_required)
        self.assertEqual(risk.frontend_mode, "full")
        self.assertEqual(backend["modules"], [])
        self.assertIn("verify.ci.scheduled_gates", backend["tool_checks"])
        self.assertIn("verify.github_actions.security", backend["tool_checks"])
        self.assertEqual(backend["scope_status"], "NOT_APPLICABLE")

    def test_unknown_path_still_fails_closed(self):
        path = "unexpected/new-surface.bin"
        risk = self.classify(path)
        backend = self.plan(path)
        self.assertEqual(risk.lane, "HIGH_RISK")
        self.assertIn("unknown_path_fail_closed", risk.reasons)
        self.assertTrue(risk.orm_required)
        self.assertEqual(backend["mode"], "full")
        self.assertEqual(backend["modules"], sorted(self.graph))
        self.assertIn("unknown_impact:" + path, backend["reasons"])

    def test_frontend_and_codex_makefiles_trigger_different_checks(self):
        frontend_risk = self.classify("make/frontend.mk")
        codex_risk = self.classify("make/codex.mk")
        frontend_plan = self.plan("make/frontend.mk")
        codex_plan = self.plan("make/codex.mk")
        self.assertTrue(frontend_risk.frontend_changed)
        self.assertFalse(frontend_risk.backend_changed)
        self.assertFalse(frontend_risk.control_plane_changed)
        self.assertTrue(frontend_risk.frontend_full_required)
        self.assertFalse(codex_risk.frontend_changed)
        self.assertFalse(codex_risk.backend_changed)
        self.assertTrue(codex_risk.control_plane_changed)
        self.assertIn("verify.frontend.dev.incremental.unit", frontend_plan["tool_checks"])
        self.assertIn("verify.baseline.iteration.execution.policy", frontend_plan["tool_checks"])
        self.assertNotIn("verify.pr.push.unit", frontend_plan["tool_checks"])
        self.assertIn("verify.pr.push.unit", codex_plan["tool_checks"])
        self.assertNotIn("verify.frontend.dev.incremental.unit", codex_plan["tool_checks"])

    def test_agent_registration_is_fast_but_governance_is_control_plane_high_risk(self):
        registration = self.classify(".agent/runs/FE-LOOP-02/run.json")
        governance = self.classify(".agent/context.yaml")
        self.assertEqual(registration.lane, "FAST")
        self.assertTrue(registration.control_plane_changed)
        self.assertFalse(registration.backend_changed)
        self.assertFalse(registration.orm_required)
        self.assertEqual(governance.lane, "HIGH_RISK")
        self.assertTrue(governance.control_plane_changed)
        self.assertFalse(governance.backend_changed)
        self.assertFalse(governance.orm_required)
        self.assertIn(
            "verify.agent.ledger.unit",
            self.plan(".agent/runs/FE-LOOP-02/run.json")["tool_checks"],
        )

    def test_known_880_tooling_paths_do_not_expand_to_backend_or_orm(self):
        paths = [
            ".agent/active-runs.json",
            ".agent/goals/DELIVERED-ENTRY-COVERAGE-PROJECT-SAVE-20261113.yaml",
            ".agent/runs/DELIVERED-ENTRY-COVERAGE-PROJECT-SAVE-20261113/run.json",
            "config/frontend/probe_toolchain_registry.json",
            "config/security/secret_scan_false_positives.v1.json",
            "docs/engineering_convergence/complexity_budget_report.md",
            "docs/engineering_convergence/split_plan_queue.md",
            "docs/engineering_convergence/test_inventory.csv",
            "docs/engineering_convergence/test_inventory_summary.md",
            "docs/ops/iterations/delivered_entry_coverage_project_save_20261113.md",
            "make/dev.mk",
            "make/frontend.mk",
            "scripts/ops/dev_acceptance_release_probe.py",
            "scripts/verify/business_entry_matrix_browser.mjs",
            "scripts/verify/business_entry_matrix_incremental.py",
            "scripts/verify/business_entry_matrix_model.mjs",
            "scripts/verify/business_entry_matrix_overlay.json",
            "scripts/verify/business_entry_matrix_reuse_identity.test.mjs",
            "scripts/verify/business_entry_matrix_runtime_route.test.mjs",
            "scripts/verify/business_entry_matrix_scope.mjs",
            "scripts/verify/business_entry_negative_closures.mjs",
            "scripts/verify/frontend_dev_incremental.py",
            "scripts/verify/local_dev_project_profile_write_browser.mjs",
            "scripts/verify/local_dev_project_profile_write_contract.mjs",
            "scripts/verify/local_dev_project_profile_write_contract.test.mjs",
            "scripts/verify/released_navigation_target.mjs",
            "scripts/verify/test_business_entry_matrix_incremental.py",
            "scripts/verify/test_daily_acceptance_fixture_lane.py",
            "scripts/verify/test_dev_acceptance_release_identity.py",
            "scripts/verify/test_frontend_dev_incremental.py",
            "scripts/verify/test_local_dev_project_profile_write_fixture.py",
        ]
        registry = ownership.classify_paths(paths)
        risk = self.classify(*paths)
        backend = self.plan(*paths)

        self.assertEqual(registry.unknown_paths, ())
        self.assertFalse(risk.backend_runtime_changed)
        self.assertFalse(risk.orm_required)
        self.assertEqual(backend["mode"], "incremental")
        self.assertEqual(backend["modules"], [])
        self.assertEqual(backend["scope_status"], "NOT_APPLICABLE")
        self.assertEqual(backend["reasons"], [])
        self.assertIn("verify.local.dev.project_profile_write.unit", backend["tool_checks"])
        self.assertIn("security.secrets.scan", backend["tool_checks"])
        self.assertEqual(risk.managed_orm_required, False)
        self.assertEqual(risk.outputs()["payment_orm_required"], "false")


if __name__ == "__main__":
    unittest.main()
