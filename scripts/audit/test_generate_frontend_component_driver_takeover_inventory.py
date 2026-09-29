from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/audit/generate_frontend_component_driver_takeover_inventory.py"
SPEC = importlib.util.spec_from_file_location("component_takeover", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ComponentDriverTakeoverInventoryTest(unittest.TestCase):
    def test_new_frontend_source_changes_inventory_input_digest(self) -> None:
        with tempfile.TemporaryDirectory(prefix=".component-takeover-test-", dir=ROOT) as raw_root:
            source_root = Path(raw_root)
            (source_root / "existing.ts").write_text("export const existing = true;\n", encoding="utf-8")
            with patch.object(MODULE, "WEB", source_root):
                before_sources = MODULE.sources()
                before_digest = MODULE.digest(before_sources)
                (source_root / "new-source.ts").write_text("export const added = true;\n", encoding="utf-8")
                after_sources = MODULE.sources()
                after_digest = MODULE.digest(after_sources)
        self.assertEqual(len(after_sources), len(before_sources) + 1)
        self.assertNotEqual(before_digest, after_digest)

    def test_catalog_is_bound_to_installed_official_version(self) -> None:
        report = MODULE.build_inventory()
        self.assertEqual(report["authority"]["lockedVersion"], "1.20.5")
        self.assertEqual(report["summary"]["officialComponents"], len(MODULE.official_components()))

    def test_all_required_drivers_are_explicitly_assessed(self) -> None:
        report = MODULE.build_inventory()
        required = {row["officialComponent"] for row in report["components"] if row["requiredForCurrentProduct"]}
        self.assertEqual(required, MODULE.REQUIRED_DRIVERS)
        self.assertTrue(all(row["status"] in {"adapter_present", "adapter_unconsumed", "bridge_only", "missing"} for row in report["components"] if row["requiredForCurrentProduct"]))

    def test_business_sources_cannot_import_tdesign_directly(self) -> None:
        report = MODULE.build_inventory()
        self.assertEqual(report["directLibraryImportBypasses"], [])

    def test_completion_rule_cannot_hide_unassessed_raw_behavior(self) -> None:
        report = MODULE.build_inventory()
        self.assertEqual(report["rawBehaviorSurfaces"], [])
        self.assertIn("unassessedRawBehaviorSurfaces=0", report["completionRule"])
        self.assertIn("adapter_unconsumed=0", report["completionRule"])

    def test_semantically_rejected_drivers_have_explicit_architecture_decisions(self) -> None:
        report = MODULE.build_inventory()
        rows = {row["officialComponent"]: row for row in report["components"]}
        for component in ("popconfirm", "switch", "time-picker", "auto-complete", "steps"):
            self.assertFalse(rows[component]["requiredForCurrentProduct"])
            self.assertNotEqual(rows[component]["requirementDecision"], "not required by current formal product semantics")
        # The two drivers below were dropped from REQUIRED_DRIVERS, so their
        # decision text is the only place the contract boundary is recorded.
        self.assertIn("ScRelationField", MODULE.NOT_REQUIRED_DECISIONS["auto-complete"])
        self.assertIn("frontend_professional_workflow_guard.py", MODULE.NOT_REQUIRED_DECISIONS["steps"])

    def test_published_completion_rule_is_evaluated_and_clean(self) -> None:
        report = MODULE.build_inventory()
        self.assertEqual(MODULE.completion_rule_failures(report), [])
        for condition in MODULE.COMPLETION_RULE_CONDITIONS:
            self.assertIn(f"{condition[0]}=0", report["completionRule"])
        self.assertIn("directLibraryImportBypasses=0", report["completionRule"])
        self.assertIn("unassessedRawBehaviorSurfaces=0", report["completionRule"])

    def test_required_driver_without_consumer_fails_the_completion_rule(self) -> None:
        # Negative case: the exact regression this gate exists for.  Re-adding a
        # required driver whose official adapter no surface consumes must fail,
        # instead of passing because the JSON merely stayed current.
        with patch.object(MODULE, "REQUIRED_DRIVERS", MODULE.REQUIRED_DRIVERS | {"steps"}):
            report = MODULE.build_inventory()
            rows = {row["officialComponent"]: row for row in report["components"]}
            self.assertEqual(rows["steps"]["status"], "adapter_unconsumed")
            failures = MODULE.completion_rule_failures(report)
        self.assertTrue(any("adapter_unconsumed" in failure for failure in failures), failures)

    def test_unassessed_takeover_is_derived_from_rows_not_hardcoded(self) -> None:
        # Negative case: a required driver that is not fully adopted and owns no
        # capability assessment must be counted, not published as zero.
        with patch.object(MODULE, "REQUIRED_DRIVERS", MODULE.REQUIRED_DRIVERS | {"steps"}):
            report = MODULE.build_inventory()
        self.assertEqual(report["summary"]["unassessedRequiredTakeovers"], 1)
        report = MODULE.build_inventory()
        self.assertEqual(report["summary"]["unassessedRequiredTakeovers"], 0)

    def test_affected_public_capabilities_and_takeovers_are_explicitly_assessed(self) -> None:
        report = MODULE.build_inventory()
        assessments = {row["officialComponent"]: row for row in report["capabilityAssessments"]}
        self.assertEqual(set(assessments), {"dialog", "drawer", "select", "date-picker", "table"})
        self.assertEqual(assessments["date-picker"]["takeover"], "none")
        for component in ("dialog", "drawer", "select", "table"):
            self.assertEqual(assessments[component]["takeover"], "retained_required")
            self.assertTrue(assessments[component]["reason"])
            self.assertTrue(assessments[component]["verification"])
        self.assertEqual(report["summary"]["unassessedRequiredTakeovers"], 0)
        self.assertIn("unassessedRequiredTakeovers=0", report["completionRule"])


if __name__ == "__main__":
    unittest.main()
