from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_change_impact_verification_inventory as inventory


class ChangeImpactVerificationInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = inventory.build_inventory()

    def test_workflow_inventory_contains_every_checked_in_workflow(self) -> None:
        workflows = {
            path.name
            for path in (inventory.ROOT / ".github/workflows").glob("*.yml")
        }
        seen = {row["workflow"].split("/")[-1] for row in self.data["workflow_jobs"]}
        self.assertEqual(seen, workflows)

    def test_gate_boundaries_have_all_eight_answers(self) -> None:
        required = {
            "what_it_verifies",
            "what_triggers_it",
            "what_it_actually_executes",
            "services_and_database_dependencies",
            "defects_it_can_detect",
            "what_it_can_prove",
            "what_it_cannot_prove",
            "duplicate_or_overlap",
        }
        self.assertTrue(self.data["make_targets"])
        self.assertTrue(self.data["gate_scripts"])
        for item in [*self.data["make_targets"], *self.data["gate_scripts"]]:
            self.assertEqual(set(item["boundary_answers"]), required, item["id"])

    def test_make_inventory_contains_real_rules_not_variable_shapes(self) -> None:
        identifiers = {item["entrypoint"].removeprefix("make ") for item in self.data["make_targets"]}
        for invalid in (":=", "DB_NAME", "ACCEPTANCE_BASE_URL"):
            self.assertNotIn(invalid, identifiers)
        self.assertGreater(
            self.data["surface_summary"]["anchor_parser_non_target_nodes"], 0
        )
        self.assertLess(
            self.data["surface_summary"]["normalized_anchor_targets"],
            self.data["surface_summary"]["anchor_union_targets"],
        )

    def test_gate_scripts_declare_execution_mode_and_role(self) -> None:
        for item in self.data["gate_scripts"]:
            self.assertIn(
                item["execution_role"],
                {
                    "test",
                    "guard_or_probe",
                    "tool_or_orchestrator",
                    "implementation_or_fixture",
                },
            )
            self.assertTrue(item["execution_modes"])

    def test_surface_is_non_empty_and_debt_is_visible(self) -> None:
        summary = self.data["surface_summary"]
        self.assertGreater(summary["anchor_union_targets"], 200)
        self.assertGreater(summary["targets_unreached_from_anchor"], 1000)
        self.assertGreater(len(summary["targets_zero_reference"]), 0)
        self.assertGreater(len(summary["targets_missing_asset"]), 0)

    def test_contract_decoder_path_currently_requests_presentation_evidence(self) -> None:
        row = next(
            item
            for item in self.data["classification_probes"]
            if item["path"] == "frontend/apps/web/src/app/contracts/v2/schema.ts"
        )
        self.assertEqual(row["acceptance_rule"], "frontend-contract-form-consumer")
        self.assertIn("frontend_presentation", row["evidence_suites"])

    def test_renderer_registry_path_currently_lacks_presentation_evidence(self) -> None:
        row = next(
            item
            for item in self.data["classification_probes"]
            if item["path"].endswith(
                "/app/presentation/professionalComponentRegistry.ts"
            )
        )
        self.assertEqual(row["acceptance_rule"], "frontend-runtime")
        self.assertEqual(row["evidence_suites"], [])

    def test_manual_long_tail_is_not_reported_as_gate_enforced(self) -> None:
        lifecycle = {row["path"]: row["lifecycle"] for row in self.data["script_lifecycle"]}
        gate_scripts = {row["path"] for row in self.data["gate_scripts"]}
        for path, state in lifecycle.items():
            if path not in gate_scripts:
                self.assertNotEqual(state, "gate_enforced")

    def test_execution_graph_keeps_workflow_and_script_boundaries(self) -> None:
        graph = inventory.build_execution_graph(self.data)
        kinds = {node["kind"] for node in graph["nodes"]}
        relations = {edge["relation"] for edge in graph["edges"]}
        self.assertIn("workflow_job", kinds)
        self.assertIn("make_target", kinds)
        self.assertIn("executable_check", kinds)
        self.assertIn("contains_job", relations)
        self.assertIn("invokes_make", relations)
        self.assertIn("executes_script", relations)


if __name__ == "__main__":
    unittest.main()
