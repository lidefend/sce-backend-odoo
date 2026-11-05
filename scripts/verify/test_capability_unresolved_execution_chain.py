#!/usr/bin/env python3
"""Offline tests for CAP-02D-04 batch-2 execution-chain verification."""
from __future__ import annotations

import unittest

from scripts.verify import capability_unresolved_execution_chain as chain


class UnresolvedExecutionChainTests(unittest.TestCase):
    def test_verdicts_use_model_and_co_reference_evidence(self):
        runtime = {"model_ownership": {"items": [
            {"model": "project.risk"}, {"model": "project.funding.baseline"},
        ]}}
        scenes = [
            {"scene_key": "s1", "primary_capabilities": ["project.risk.list", "project.list.open"]},
            {"scene_key": "s2", "primary_capabilities": ["analytics.lifecycle.monitor",
                                                          "project.lifecycle.transition"]},
            {"scene_key": "s3", "primary_capabilities": ["finance.exception.monitor"]},
        ]
        acceptance = {"project.list.open", "project.lifecycle.transition"}
        report = chain.verify(runtime, scenes, acceptance)
        by_key = {r["capability_key"]: r["verdict"] for r in report["items"]}
        self.assertEqual(by_key["project.risk.list"], "composite_member")
        self.assertEqual(by_key["finance.plan.funding"], "provider_found")
        self.assertEqual(by_key["analytics.lifecycle.monitor"], "absorbed_by_existing")
        self.assertEqual(by_key["finance.exception.monitor"], "unresolved")


if __name__ == "__main__":
    unittest.main()
