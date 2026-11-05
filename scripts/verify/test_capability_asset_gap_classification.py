#!/usr/bin/env python3
"""Offline tests for CAP-02D-02 capability asset gap classification."""
from __future__ import annotations

import unittest

from scripts.verify import capability_asset_gap_classification as cls


class GapClassificationTests(unittest.TestCase):
    def test_composite_platform_and_deferred_classification(self):
        catalog = [
            {"capability_key": "a.composite.manage", "layer": "composite", "disposition": "keep",
             "dependencies": ["x"], "compatibility_aliases": []},
            {"capability_key": "governance.openability", "layer": "atomic", "disposition": "defer",
             "dependencies": [], "compatibility_aliases": []},
            {"capability_key": "b.enter", "layer": "atomic", "disposition": "defer",
             "dependencies": [], "compatibility_aliases": []},
        ]
        scenes = [{"scene_key": "s1", "primary_capabilities": ["legacy.old"]}]
        report = cls.classify(catalog, scenes, set())
        verdicts = {r["capability_key"]: r["verdict"]
                    for r in report["A_workflow_A_31_provider_only"]}
        self.assertEqual(verdicts["a.composite.manage"], "composite")
        self.assertEqual(verdicts["governance.openability"], "platform_mechanism")
        self.assertEqual(verdicts["b.enter"], "unresolved")
        self.assertEqual(report["C_recommended_contract_candidates"], [])

    def test_scene_only_identity_migration(self):
        catalog = [{"capability_key": "a.new", "layer": "atomic", "disposition": "keep",
                    "dependencies": [], "compatibility_aliases": ["a.old"]}]
        scenes = [{"scene_key": "s1", "primary_capabilities": ["a.old"]}]
        report = cls.classify(catalog, scenes, set())
        b = report["B_workflow_B_25_scene_only"]
        self.assertEqual(b[0]["scene_capability"], "a.old")
        self.assertEqual(b[0]["verdict"], "identity_migration")


if __name__ == "__main__":
    unittest.main()
