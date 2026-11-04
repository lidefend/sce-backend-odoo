#!/usr/bin/env python3
"""Offline tests for CAP-02D-01 read-only reconciliation."""
from __future__ import annotations

import unittest

from scripts.verify import capability_asset_reconciliation as rec


class ReconciliationTests(unittest.TestCase):
    def test_count_by_source(self):
        items = {
            "a": {"source": "odoo_native"},
            "b": {"source": "odoo_native"},
            "c": {"source": "sce_custom"},
            "d": {},
        }
        self.assertEqual(rec._count_by_source(items),
                         {"odoo_native": 2, "sce_custom": 1, "unknown": 1})

    def test_reconcile_produces_five_sections(self):
        index = {
            "module_sources": {
                "smart_construction_core": {"source": "sce_custom", "capability_count": 3},
            },
            "reverse_index": {
                "smart_construction_core": [
                    {"capability_key": "project.list.open", "provider_type": "odoo_action",
                     "provider_ref": "smart_construction_core.action_sc_project_list"},
                ],
            },
            "mechanism_impact": {},
        }
        runtime = {
            "modules": {"items": {"smart_construction_core": {"state": "installed",
                                                               "installed_version": "17.0.0.172"}}},
        }
        report = rec.reconcile(index, runtime)
        self.assertEqual(set(report.keys()),
                         {"schema", "A_module_inventory", "B_module_provider_matrix",
                          "C_capability_contract", "D_scene_product_diff", "E_priority"})
        self.assertIn("project.list.open", report["C_capability_contract"])
        self.assertIn("smart_construction_core", report["B_module_provider_matrix"])


if __name__ == "__main__":
    unittest.main()
