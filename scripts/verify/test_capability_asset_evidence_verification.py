#!/usr/bin/env python3
"""Offline tests for CAP-02D-02-R1 evidence verification."""
from __future__ import annotations

import unittest

from scripts.verify import capability_asset_evidence_verification as ev


class EvidenceVerificationTests(unittest.TestCase):
    def test_unreconciled_provider_is_flagged(self):
        catalog = [
            {"capability_key": "a.enter", "layer": "atomic", "disposition": "defer",
             "providers": [{"provider_type": "unknown", "provider_ref": "",
                            "pending_reason": "provider not yet reconciled"}]},
            {"capability_key": "b.open", "layer": "atomic", "disposition": "defer",
             "providers": [{"provider_type": "odoo_action", "provider_ref": "x.action_b"}]},
        ]
        scenes = [{"scene_key": "s1", "primary_capabilities": ["b.open"]}]
        runtime = {
            "model_ownership": {"items": []},
            "actions": {"items": [{"xmlid": "x.action_b"}]},
            "intent_handlers": {"items": []},
        }
        report = ev.verify(catalog, scenes, set(), runtime)
        verdicts = {r["capability_key"]: r["verdict"]
                    for r in report["A_provider_only_evidence"]}
        self.assertEqual(verdicts["a.enter"], "provider_unreconciled")
        self.assertEqual(verdicts["b.open"], "contract_candidate")


if __name__ == "__main__":
    unittest.main()
