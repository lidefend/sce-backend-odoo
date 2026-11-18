#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/audit/generate_frontend_contract_business_journey_research.py"
SPEC = importlib.util.spec_from_file_location("contract_business_journey_research", MODULE_PATH)
assert SPEC and SPEC.loader
RESEARCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESEARCH)


class ContractBusinessJourneyResearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = RESEARCH.build_report()
        cls.entries = cls.report["businessEntries"]
        cls.facets = {row["id"]: row for row in cls.report["contractFacets"]}

    def test_formal_entry_join_is_complete_and_unique(self) -> None:
        self.assertEqual(len(self.entries), 91)
        self.assertEqual(len({row["menu_xmlid"] for row in self.entries}), 91)
        self.assertTrue(all(row["menu_xmlid"] and row["closure_boundary"] for row in self.entries))

    def test_source_and_research_closure_classes_are_distinct(self) -> None:
        summary = self.report["summary"]
        self.assertEqual(summary["sourceStatusCounts"], {"passed": 88, "pending": 3})
        self.assertEqual(
            summary["closureLevelCounts"],
            {
                "declared_empty_read_only": 64,
                "full_declared_scope": 4,
                "pending": 3,
                "read_detail_only": 16,
                "surface_only": 3,
                "write_create_partial": 1,
            },
        )
        self.assertEqual(summary["browserWriteCount"], 5)
        self.assertEqual(summary["browserWorkflowCount"], 3)
        self.assertEqual(summary["attachmentChainCount"], 1)
        self.assertEqual(summary["coreOrmSmokeDeclaredCount"], 12)
        self.assertEqual(summary["coreOrmSmokeMatchedEntryCount"], 4)
        self.assertEqual(summary["coreOrmSmokeUnmatchedEntryCount"], 8)

    def test_historical_evidence_is_not_rebound_to_current_baseline(self) -> None:
        self.assertEqual(self.report["summary"]["currentBaselineReboundCount"], 0)
        self.assertTrue(all(not row["current_baseline_rebound"] for row in self.entries))

    def test_contract_findings_bind_consumer_and_owner(self) -> None:
        self.assertGreaterEqual(len(self.facets), 40)
        for required in (
            "search-panel",
            "intake-autosave",
            "workflow-contract-schema",
            "runtime-control-plane",
            "runtime-validation-rules",
            "renderer-registry-fallbacks",
        ):
            self.assertIn(required, self.facets)
            self.assertTrue(self.facets[required]["nextActionOwner"])
            self.assertTrue(self.facets[required]["finding"])
        self.assertEqual(self.facets["search-panel"]["frontendConsumers"], [])
        self.assertEqual(self.facets["intake-autosave"]["verdict"], "consumption_defect")
        self.assertEqual(self.facets["workflow-contract-schema"]["verdict"], "expression_gap")

    def test_workflow_runtime_shape_exposes_untyped_keys(self) -> None:
        audit = self.report["workflowContractSchema"]
        self.assertTrue(audit["additionalProperties"])
        self.assertEqual(audit["typedProperties"], ["submissionRequirements"])
        self.assertIn("availableActions", audit["runtimePropertiesWithoutTypedShape"])
        self.assertIn("transitions", audit["runtimePropertiesWithoutTypedShape"])

    def test_ux_and_capability_matrix_evidence_boundaries_are_explicit(self) -> None:
        ux = self.report["userExperienceCoverage"]
        self.assertEqual(ux["journeyCount"], 12)
        self.assertEqual(ux["browserEvidenceJourneyCount"], 8)
        self.assertEqual(
            ux["withoutBrowserEvidenceJourneyIds"],
            ["UX-J005", "UX-J007", "UX-J008", "UX-J012"],
        )
        self.assertFalse(ux["roleJourneyAuditRegisteredInMake"])
        capability = self.report["capabilityMatrixMeasurement"]
        self.assertEqual(capability["renderedRowsWithSearchZero"], 81)
        self.assertEqual(capability["verdict"], "validation_tool_defect")

    def test_registered_facet_targets_are_real(self) -> None:
        make_text = RESEARCH.registered_make_text()
        targets = {
            target
            for row in self.report["contractFacets"]
            for target in row["registeredTargets"]
        }
        self.assertTrue(targets)
        self.assertFalse(sorted(target for target in targets if target not in make_text))

    def test_generated_outputs_are_reproducible(self) -> None:
        payload, business_csv, _ = RESEARCH.render_outputs()
        self.assertTrue(payload.endswith("\n"))
        self.assertTrue(business_csv.startswith("menu_xmlid,label,domain,model,action_xmlid,"))
        self.assertEqual(payload, RESEARCH.render_outputs()[0])
        self.assertEqual(business_csv, RESEARCH.render_outputs()[1])


if __name__ == "__main__":
    unittest.main()
