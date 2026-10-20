#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from . import product_configuration_capability_guard as guard


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "config/product_configuration_capability_v1.json"


class ProductConfigurationCapabilityGuardTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_declared_manifest_is_valid(self):
        self.assertEqual(guard.validate(copy.deepcopy(self.manifest)), [])

    def test_missing_configuration_card_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["configuration_cards"] = [
            row for row in manifest["configuration_cards"] if row["key"] != "system_parameters"
        ]
        self.assertTrue(any("missing configuration cards" in error for error in guard.validate(manifest)))

    def test_missing_home_block_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["login_home"]["blocks"] = [
            row for row in manifest["login_home"]["blocks"] if row["key"] != "capability_map"
        ]
        self.assertTrue(any("missing login home blocks" in error for error in guard.validate(manifest)))

    def test_duplicate_capability_key_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["capabilities"].append(copy.deepcopy(manifest["capabilities"][0]))
        self.assertTrue(any("duplicate capability key" in error for error in guard.validate(manifest)))

    def test_platform_capability_for_business_full_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        row = next(item for item in manifest["capabilities"] if item["key"] == "platform.tenant_company")
        row["audience"] = "business_full"
        self.assertTrue(any("must not be exposed to business_full" in error for error in guard.validate(manifest)))

    def test_secret_like_term_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["capabilities"][0]["description"] = "store the database password in the page"
        self.assertTrue(any("secret-like term" in error for error in guard.validate(manifest)))

    def test_raw_ir_config_parameter_entry_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        row = next(item for item in manifest["capabilities"] if item["key"] == "config.system_parameters")
        row["entry"] = "ir.config_parameter"
        self.assertTrue(any("must not expose raw ir.config_parameter" in error for error in guard.validate(manifest)))

    def test_runtime_copy_matches_product_manifest(self):
        self.assertEqual(guard.validate_runtime_copy(), [])


if __name__ == "__main__":
    unittest.main()
