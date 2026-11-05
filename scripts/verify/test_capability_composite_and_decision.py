#!/usr/bin/env python3
"""Offline tests for CAP-02D-04 batch 3/4 composite + decision matrix."""
from __future__ import annotations

import unittest

from scripts.verify import capability_composite_and_decision as cd


class CompositeAndDecisionTests(unittest.TestCase):
    def test_composite_and_decision_verdicts(self):
        catalog = [
            {"capability_key": "a.manage", "layer": "composite", "dependencies": ["a.list"]},
            {"capability_key": "a.list", "layer": "atomic", "dependencies": []},
            {"capability_key": "b.manage", "layer": "composite", "dependencies": []},
        ]
        runtime = {"model_ownership": {"items": [{"model": "sc.quality.issue"}]}}
        report = cd.build(catalog, set(), runtime)
        comp = {r["capability_key"]: r["verdict"] for r in report["composite_convergence"]}
        self.assertEqual(comp["a.manage"], "composite_entry")
        self.assertEqual(comp["b.manage"], "unresolved")
        dec = {r["capability_key"]: r["verdict"] for r in report["no_provider_decisions"]}
        self.assertEqual(dec["quality.issue.list"], "retain")
        self.assertEqual(dec["safety.issue.list"], "confirm")


if __name__ == "__main__":
    unittest.main()
