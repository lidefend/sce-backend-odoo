#!/usr/bin/env python3
"""Offline tests for CAP-02C-04 D4 module change impact report."""
from __future__ import annotations

import unittest

from scripts.verify import module_change_impact_report as d4


def _propagation(**overrides):
    base = {
        "impacted_capabilities": [],
        "impacted_contracts": [],
        "impacted_product_scenes": [],
        "unresolved": [],
        "has_unresolved_impact": False,
    }
    base.update(overrides)
    return base


class RiskTests(unittest.TestCase):
    def test_comment_only_change_is_low_and_source_only(self):
        report = d4.build_report(
            {"module": "smart_construction_core", "source": "sce",
             "change_type": "comment_only", "fact_source": "repository"},
            [],
            _propagation(),
        )
        self.assertTrue(report["technical_assets"]["source_only_change"])
        self.assertEqual(report["risk"], "Low")
        self.assertTrue(any("无业务影响" in r for r in report["recommendations"]))

    def test_removed_action_provider_is_critical(self):
        prop = _propagation(impacted_capabilities=[{
            "capability_key": "project.list.open", "providers": [
                {"module": "smart_construction_core", "provider_refs": []},
            ], "contract": True, "scenes": ["project.list"], "product_scenes": ["project.list"],
        }])
        self.assertEqual(d4.classify_risk(prop), "Critical")

    def test_missing_contract_is_unresolved(self):
        prop = _propagation(has_unresolved_impact=True, unresolved=[
            {"subject": "cap.x", "reason": "contract_missing"},
        ])
        self.assertEqual(d4.classify_risk(prop), "Unresolved")

    def test_scene_impact_is_medium(self):
        prop = _propagation(impacted_capabilities=[{
            "capability_key": "project.list.open", "providers": [
                {"module": "m", "provider_refs": ["ref"]},
            ], "contract": True, "scenes": ["project.list"], "product_scenes": ["project.list"],
        }])
        self.assertEqual(d4.classify_risk(prop), "Medium")

    def test_recommendations_derived_from_actual_counts(self):
        prop = _propagation(
            impacted_capabilities=[
                {"capability_key": f"c{i}", "providers": [{"module": "m", "provider_refs": ["r"]}],
                 "contract": True, "scenes": ["s"], "product_scenes": ["s"]}
                for i in range(3)
            ],
            impacted_contracts=[{"capability_key": "c0"} for _ in range(2)],
            impacted_product_scenes=[{"capability_key": "c0", "scenes": ["s"]}],
        )
        report = d4.build_report({"module": "m", "source": "sce", "change_type": "x",
                                  "fact_source": "runtime_registry"}, [], prop)
        self.assertTrue(any("3 项受影响能力" in r for r in report["recommendations"]))
        self.assertTrue(any("2 项验收契约" in r for r in report["recommendations"]))
        self.assertTrue(any("1 个产品场景" in r for r in report["recommendations"]))

    def test_impact_summary_splits_confirmed_and_unresolved(self):
        prop = _propagation(
            impacted_capabilities=[
                {"capability_key": "c_confirmed", "providers": [{"module": "m", "provider_refs": ["r"]}],
                 "contract": True, "scenes": ["s"], "product_scenes": ["s"]},
                {"capability_key": "c_unresolved", "providers": [{"module": "m", "provider_refs": ["r"]}],
                 "contract": False, "scenes": [], "product_scenes": []},
            ],
            impacted_contracts=[{"capability_key": "c_confirmed"}],
            unresolved=[{"subject": "c_unresolved", "reason": "contract_missing"}],
            has_unresolved_impact=True,
            association_coverage={"repository_coverage": True,
                                  "runtime_coverage": False,
                                  "associations_complete": False},
        )
        report = d4.build_report({"module": "m", "source": "sce", "change_type": "x",
                                  "fact_source": "runtime_registry"}, [], prop)
        summary = report["impact_summary"]
        self.assertEqual([c["capability_key"] for c in summary["confirmed_capabilities"]],
                         ["c_confirmed"])
        self.assertEqual([c["capability_key"] for c in summary["unresolved_capabilities"]],
                         ["c_unresolved"])
        self.assertEqual(len(summary["unresolved_contracts"]), 1)
        self.assertFalse(summary["association_coverage"]["associations_complete"])

    def test_content_unresolved_is_never_low(self):
        prop = _propagation()
        technical = [{"fact_identity": "x:1", "change": "changed",
                      "semantics": {"content_unresolved": True, "reason": "no semantic schema"}}]
        report = d4.build_report({"module": "m", "source": "sce", "change_type": "x",
                                  "fact_source": "repository"}, technical, prop)
        self.assertEqual(report["risk"], "Unresolved")


if __name__ == "__main__":
    unittest.main()
