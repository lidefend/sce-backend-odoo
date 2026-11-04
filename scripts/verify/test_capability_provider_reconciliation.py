#!/usr/bin/env python3
"""Offline tests for CAP-02D-03 provider reconciliation."""
from __future__ import annotations

import unittest

from scripts.verify import capability_provider_reconciliation as rec


class ProviderReconciliationTests(unittest.TestCase):
    def test_intent_match_is_provider_verified_and_unknown_is_no_provider(self):
        catalog = [
            {"capability_key": "a.enter", "layer": "atomic", "disposition": "defer", "providers": []},
            {"capability_key": "b.enter", "layer": "atomic", "disposition": "defer", "providers": []},
            {"capability_key": "governance.x", "layer": "atomic", "disposition": "defer", "providers": []},
        ]
        scenes = [{"scene_key": "s1", "primary_capabilities": ["a.enter"]}]
        runtime = {
            "intent_handlers": {"items": [{"intent": "b.enter", "handler": "BHandler",
                                           "registered": True, "module": "m"}]},
        }
        report = rec.reconcile(catalog, scenes, set(), runtime)
        by_key = {r["capability_key"]: r for r in report["items"]}
        self.assertEqual(by_key["b.enter"]["disposition"], "provider_verified")
        self.assertEqual(by_key["b.enter"]["provider_source"], "sce_handler_registry")
        self.assertEqual(by_key["a.enter"]["disposition"], "unresolved")
        self.assertEqual(by_key["governance.x"]["disposition"], "platform_mechanism")


if __name__ == "__main__":
    unittest.main()
