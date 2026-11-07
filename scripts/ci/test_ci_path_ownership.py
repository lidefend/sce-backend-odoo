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


if __name__ == "__main__":
    unittest.main()
