#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SERVICE_PATH = (
    ROOT
    / "addons/smart_construction_core/services/product_system_parameter_catalog.py"
)
MANIFEST_PATH = ROOT / "config/product_system_parameter_catalog_v1.json"
MODULE_MANIFEST_PATH = (
    ROOT
    / "addons/smart_construction_core/data/product_system_parameter_catalog_v1.json"
)


def _load_service():
    spec = importlib.util.spec_from_file_location(
        "product_system_parameter_catalog_service", SERVICE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


service = _load_service()


class ProductSystemParameterCatalogServiceTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_catalog_projects_categories_parameters_and_guardrails(self):
        catalog = service.build_catalog(self.manifest)
        self.assertEqual(len(catalog["categories"]), 6)
        self.assertEqual(len(catalog["parameters"]), 13)
        self.assertIn("no_raw_ir_config_parameter_in_user_entry", catalog["guardrails"])

    def test_planned_parameter_is_not_available(self):
        catalog = service.build_catalog(self.manifest)
        row = next(item for item in catalog["parameters"] if item["key"] == "tax_rate")
        self.assertFalse(row["available"])
        self.assertEqual(row["status"], "planned")

    def test_backed_parameter_is_available(self):
        catalog = service.build_catalog(self.manifest)
        row = next(item for item in catalog["parameters"] if item["key"] == "cost_ledger_source")
        self.assertTrue(row["available"])
        self.assertEqual(row["status"], "available")

    def test_preview_accepts_allowed_selection_value(self):
        result = service.impact_preview(self.manifest, "cost_ledger_source", "stock_move")
        self.assertTrue(result["ok"])
        self.assertTrue(result["change_set_required"])
        self.assertTrue(result["audit_required"])
        self.assertTrue(result["rollback_required"])
        self.assertEqual(result["impact"]["risk_level"], "medium")

    def test_preview_rejects_value_outside_allowed_set(self):
        result = service.impact_preview(self.manifest, "cost_ledger_source", "not-a-source")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "value_not_allowed")

    def test_preview_rejects_planned_parameter(self):
        result = service.impact_preview(self.manifest, "tax_rate", 0.13)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "not_implemented")

    def test_preview_rejects_unknown_parameter(self):
        result = service.impact_preview(self.manifest, "does_not_exist", "x")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "unknown_parameter")

    def test_number_parameter_value_is_range_checked(self):
        manifest = {
            "parameters": [
                {
                    "key": "tax_rate",
                    "type": "number",
                    "status": "available",
                    "min": 0,
                    "max": 1,
                    "allowed_values": [],
                    "impact": {"surfaces": ["财务"], "summary": "税率影响"},
                }
            ]
        }
        ok = service.impact_preview(manifest, "tax_rate", 0.13)
        over = service.impact_preview(manifest, "tax_rate", 1.5)
        self.assertTrue(ok["ok"])
        self.assertFalse(over["ok"])
        self.assertEqual(over["reason"], "value_not_allowed")

    def test_runtime_manifest_copy_matches_product_catalog(self):
        self.assertEqual(
            MODULE_MANIFEST_PATH.read_bytes(),
            MANIFEST_PATH.read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
