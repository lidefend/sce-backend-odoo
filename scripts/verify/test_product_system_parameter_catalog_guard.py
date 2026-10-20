#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from . import product_system_parameter_catalog_guard as guard


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "config/product_system_parameter_catalog_v1.json"


class ProductSystemParameterCatalogGuardTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_declared_catalog_is_valid(self):
        self.assertEqual(guard.validate(copy.deepcopy(self.manifest)), [])

    def test_missing_category_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["categories"] = [
            row for row in manifest["categories"] if row["key"] != "integration"
        ]
        self.assertTrue(any("missing categories" in error for error in guard.validate(manifest)))

    def test_selection_default_outside_allowed_values_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        row = next(item for item in manifest["parameters"] if item["key"] == "cost_ledger_source")
        row["allowed_values"] = ["purchase_order", "stock_move"]
        self.assertTrue(any("default not in allowed_values" in error for error in guard.validate(manifest)))

    def test_duplicate_parameter_key_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["parameters"].append(copy.deepcopy(manifest["parameters"][0]))
        self.assertTrue(any("duplicate parameter key" in error for error in guard.validate(manifest)))

    def test_secret_like_term_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["parameters"][0]["description"] = "store the database password here"
        self.assertTrue(any("secret-like term" in error for error in guard.validate(manifest)))

    def test_raw_ir_config_parameter_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["parameters"][0]["authority"] = "ir.config_parameter"
        self.assertTrue(any("raw ir.config_parameter" in error for error in guard.validate(manifest)))

    def test_missing_required_guardrail_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["guardrails"] = [
            item for item in manifest["guardrails"] if item != "change_set_required_for_mutation"
        ]
        self.assertTrue(any("missing guardrails" in error for error in guard.validate(manifest)))

    def test_runtime_copy_matches_product_catalog(self):
        self.assertEqual(
            (ROOT / "addons/smart_construction_core/data/product_system_parameter_catalog_v1.json").read_bytes(),
            MANIFEST.read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
