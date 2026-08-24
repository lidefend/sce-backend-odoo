#!/usr/bin/env python3
"""Focused contract tests for the Phase 0 static inventory generator."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/audit/generate_frontend_professionalization_baseline.py"
SPEC = importlib.util.spec_from_file_location("phase0_inventory", MODULE_PATH)
assert SPEC and SPEC.loader
INVENTORY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INVENTORY)


class FrontendProfessionalizationBaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.files = INVENTORY.source_files(ROOT)
        cls.pages = INVENTORY.page_surface_inventory(ROOT, cls.files)
        cls.navigation = INVENTORY.navigation_inventory(ROOT, cls.files)
        cls.design = INVENTORY.design_token_inventory(ROOT, cls.files)
        cls.components = INVENTORY.component_coverage_inventory(ROOT, cls.files)

    def test_record_routes_remain_runtime_contract_authority(self) -> None:
        routes = {item["routeName"]: item for item in self.pages["routes"]}
        self.assertEqual(routes["record"]["presentationMode"], "runtime_contract_required")
        self.assertEqual(routes["model-form"]["presentationMode"], "runtime_contract_required")
        self.assertEqual(routes["record"]["renderProfile"], "readonly")
        self.assertEqual(routes["model-form"]["renderProfile"], "edit_or_create")

    def test_inventory_separates_static_and_runtime_sources(self) -> None:
        self.assertGreater(len(self.pages["declarativeActionDefinitions"]), 0)
        self.assertGreater(len(self.pages["declarativeMenuDefinitions"]), 0)
        self.assertTrue(any("cannot prove" in item for item in self.pages["limitations"]))
        self.assertEqual(
            self.navigation["canonicalRuntimeAuthority"]["declared"],
            "backend runtime navigation response / session.menuTree",
        )

    def test_design_and_component_reports_keep_missing_explicit(self) -> None:
        self.assertGreater(len(self.design["cssVariableDefinitions"]), 0)
        gaps = {item["componentKey"] for item in self.components["phase2PrimitiveGaps"]}
        self.assertIn("ScInput", gaps)
        self.assertIn("ScLoading", gaps)
        self.assertTrue(self.components["coveragePolicy"]["noSilentFallback"])

    def test_component_source_presence_is_not_readiness_or_capability(self) -> None:
        for item in self.components["declaredComponents"]:
            self.assertTrue(item["sourcePresent"])
            self.assertEqual(item["assessmentStatus"], "unassessed")
            self.assertEqual(item["semanticType"], "not_declared")
            self.assertEqual(item["supportedFieldTypes"], "not_declared")
            self.assertEqual(item["supportedPresentationModes"], "not_declared")
            self.assertEqual(item["supportedRenderProfiles"], "not_declared")
            self.assertNotIn(item["assessmentStatus"], {"ready", "readable_fallback", "fail_closed"})
        for target in self.components["phase2TargetPrimitives"]:
            self.assertEqual(target["targetState"], "planned_phase_2_adapter_api")
            self.assertTrue(target["notCurrentCapability"])
            self.assertNotIn("assessmentStatus", target)

    def test_every_report_binds_generator_inputs_and_exclusions(self) -> None:
        for report in (self.pages, self.navigation, self.design, self.components):
            self.assertEqual(report["sourceCommit"], INVENTORY.baseline_commit(ROOT))
            self.assertEqual(report["baselineScope"], "repository formal-product declarative baseline")
            self.assertRegex(report["generatorDigest"], r"^[0-9a-f]{64}$")
            self.assertRegex(report["inputDigest"], r"^[0-9a-f]{64}$")
            self.assertTrue(report["inputScopes"])
            self.assertIsInstance(report["generatedFromDirtyWorktree"], bool)
            self.assertEqual(
                report["excludedScopes"],
                [
                    "demo_addons",
                    "external customer_addons",
                    "runtime installed-module state",
                    "user-specific visibility",
                ],
            )

    def test_input_digest_changes_when_an_input_changes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "scripts/audit") as directory:
            probe = Path(directory) / "input.txt"
            probe.write_text("before\n", encoding="utf-8")
            before = INVENTORY.source_digest(ROOT, [probe])
            probe.write_text("after\n", encoding="utf-8")
            after = INVENTORY.source_digest(ROOT, [probe])
        self.assertNotEqual(before, after)


if __name__ == "__main__":
    unittest.main()
