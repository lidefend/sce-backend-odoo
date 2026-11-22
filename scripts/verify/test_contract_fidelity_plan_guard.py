#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/verify/contract_fidelity_plan_guard.py"
SPEC = importlib.util.spec_from_file_location("contract_fidelity_plan_guard", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ContractFidelityPlanGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.matrix = json.loads((ROOT / MODULE.MATRIX_PATH).read_text(encoding="utf-8"))
        self.plan = json.loads((ROOT / MODULE.PLAN_PATH).read_text(encoding="utf-8"))
        self.guard = json.loads((ROOT / MODULE.GUARD_PATH).read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self) -> None:
        for relative, content in (
            (MODULE.MATRIX_PATH, self.matrix),
            (MODULE.PLAN_PATH, self.plan),
            (MODULE.GUARD_PATH, self.guard),
        ):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")

    def errors(self) -> list[str]:
        self.write()
        return MODULE.check(self.root)

    def assert_error(self, fragment: str) -> None:
        errors = self.errors()
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_repository_plan_is_consistent(self) -> None:
        self.assertEqual(MODULE.check(ROOT), [])

    def test_synthetic_baseline_is_clean(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_missing_not_verified_cell_is_detected(self) -> None:
        self.plan["not_verified_cells"].pop()
        self.assert_error("NOT_VERIFIED matrix mismatch")

    def test_my_work_attachment_responsibility_drift_is_detected(self) -> None:
        for cell in self.plan["not_verified_cells"]:
            if cell["id"] == "NV-11":
                cell["gap_probe"] = "CFG-GAP-03"
        self.assert_error("NV-11: gap_probe must be CFG-GAP-04")

    def test_dialog_duration_responsibility_drift_is_detected(self) -> None:
        for cell in self.plan["not_verified_cells"]:
            if cell["id"] == "NV-15":
                cell["gap_probe"] = "CFG-GAP-03"
        self.assert_error("NV-15: gap_probe must be CFG-GAP-07")

    def test_gap_blocks_must_match_cell_ownership(self) -> None:
        for probe in self.plan["contract_gap_probes"]:
            if probe["id"] == "CFG-GAP-03":
                probe["blocks"].append("NV-11")
        self.assert_error("CFG-GAP-03: NV blocks mismatch")

    def test_missing_gap_dependency_edge_is_detected(self) -> None:
        self.plan["dependency_edges"] = [
            edge for edge in self.plan["dependency_edges"]
            if edge["id"] != "DEP-GAP-04-TRANSPORT"
        ]
        self.assert_error("without a matching dependency edge")

    def test_contract_gap_branch_must_redirect_to_p0(self) -> None:
        edge = next(
            edge for edge in self.plan["dependency_edges"]
            if edge.get("kind") == "contract_gate"
        )
        edge["branches"]["contract_gap"] = "unlock"
        self.assert_error("contract_gate branches must be exact")

    def test_first_batch_must_remain_independent(self) -> None:
        self.plan["batches"][0]["depends_on"] = ["CFG-GAP-01"]
        self.assert_error("FCF-02-1 must remain independently startable")

    def test_numeric_clamp_guard_is_required(self) -> None:
        for rule in self.guard["rules"]:
            if rule["id"] == "CFG-003":
                rule["negative_cases"] = ["value looks out of range"]
        self.assert_error("CFG-003 must explicitly cover")

    def test_page_block_feedback_guard_is_required(self) -> None:
        self.guard["rules"] = [rule for rule in self.guard["rules"] if rule["id"] != "CFG-011"]
        self.assert_error("guard rules must be exactly CFG-001..011")

    def test_semantic_carrier_requirement_is_required(self) -> None:
        self.guard["semantic_carrier_requirements"].pop()
        self.assert_error("semantic carrier requirements must be exactly CARRIER-01..06")


if __name__ == "__main__":
    unittest.main()
