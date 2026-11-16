from __future__ import annotations

import copy
import unittest

from scripts.ops import change_impact_evidence as evidence
from scripts.ops import change_impact_planner as planner


def contract_plan() -> dict:
    items = [
        {
            "path": "frontend/apps/web/src/app/contracts/v2/schema.ts",
            "before": "export function decode(value: unknown) { return value }\n",
            "after": "export function decode(value: unknown) { return value ?? {} }\n",
            "ts_facts": {
                "before": {
                    "ok": True,
                    "symbols": [
                        {"name": "decode", "kind": "function", "start_line": 1, "end_line": 1}
                    ],
                    "fields": [],
                    "imports": [],
                    "import_bindings": [],
                    "assertion_calls": [],
                    "dynamic_dependency_possible": False,
                },
                "after": {
                    "ok": True,
                    "symbols": [
                        {"name": "decode", "kind": "function", "start_line": 1, "end_line": 1}
                    ],
                    "fields": [],
                    "imports": [],
                    "import_bindings": [],
                    "assertion_calls": [],
                    "dynamic_dependency_possible": False,
                },
            },
        }
    ]
    return planner.analyze_change_set(items, base="a" * 40, head="b" * 40)


def receipts_for(plan: dict) -> dict:
    receipts = {}
    for decision in plan["decisions"]:
        receipts[decision["check_id"]] = {
            "status": "passed",
            "input_fingerprint": decision["input_fingerprint"],
            "assertion_closure": True,
            "environment_identity": plan["environment_identity"],
            "evidence_authority": "exact_run",
            "evidence_sha256": "c" * 64,
        }
    return receipts


def baseline_for(plan: dict, receipts: dict) -> dict:
    return evidence.build_baseline(
        plan,
        receipts=receipts,
        source_head="d" * 40,
        source_tree="e" * 40,
        merged_main_head="f" * 40,
        independent_review="approved",
        remote_checks="passed",
        main_tree_equivalent=True,
    )


class BaselineEvidenceTests(unittest.TestCase):
    def test_baseline_requires_current_bound_receipts(self) -> None:
        plan = contract_plan()
        with self.assertRaises(evidence.BaselineError):
            baseline_for(plan, {})

    def test_baseline_promotes_only_complete_reviewed_tree_equivalent_proof(self) -> None:
        plan = contract_plan()
        receipts = receipts_for(plan)
        baseline = baseline_for(plan, receipts)
        self.assertTrue(baseline["promotion"]["eligible"])
        self.assertEqual(baseline["coverage"]["blocked"], 0)

    def test_stale_input_or_environment_receipt_is_rejected(self) -> None:
        plan = contract_plan()
        receipts = receipts_for(plan)
        stale = copy.deepcopy(receipts)
        next(iter(stale.values()))["input_fingerprint"] = "0" * 64
        with self.assertRaises(evidence.BaselineError):
            baseline_for(plan, stale)
        wrong_environment = copy.deepcopy(receipts)
        next(iter(wrong_environment.values()))["environment_identity"] = {
            "profile": "other",
            "database": "other",
            "artifact": "other",
        }
        with self.assertRaises(evidence.BaselineError):
            baseline_for(plan, wrong_environment)

    def test_missing_receipt_blocks_coordination(self) -> None:
        plan = contract_plan()
        baseline = baseline_for(plan, receipts_for(plan))
        result = evidence.coordinate(plan, baseline, receipts={})
        self.assertFalse(result["ready_for_existing_gates"])
        self.assertTrue(result["coverage"]["missing"])

    def test_zero_delta_reuses_baseline_without_product_execution(self) -> None:
        plan = contract_plan()
        baseline = baseline_for(plan, receipts_for(plan))
        zero = planner.analyze_change_set([], base="a" * 40, head="b" * 40)
        result = evidence.coordinate(zero, baseline, receipts={})
        self.assertTrue(result["ready_for_existing_gates"])
        self.assertEqual(result["product_checks_executed"], 0)
        self.assertTrue(result["coverage"]["baseline_reused"])

    def test_tampered_baseline_is_rejected(self) -> None:
        plan = contract_plan()
        baseline = baseline_for(plan, receipts_for(plan))
        baseline["proofs"][0]["assertion_set_sha256"] = "0" * 64
        with self.assertRaises(evidence.BaselineError):
            evidence.validate_baseline(baseline)


if __name__ == "__main__":
    unittest.main()
