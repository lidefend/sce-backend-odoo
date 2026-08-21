#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPORTER_PATH = ROOT / "scripts/contract/export_catalogs.py"
SPEC = importlib.util.spec_from_file_location("contract_export_catalogs", EXPORTER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load catalog exporter: {EXPORTER_PATH}")
EXPORTER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXPORTER
SPEC.loader.exec_module(EXPORTER)


class ContractCatalogPathTest(unittest.TestCase):
    def test_small_mapping_keeps_explicit_contract_keys(self):
        paths = EXPORTER.dotted_paths({"status": {"code": "ready", "label": "Ready"}})

        self.assertEqual(paths, {"status", "status.code", "status.label"})

    def test_large_dynamic_mapping_uses_stable_wildcard_shape(self):
        payload = {
            "fields": {
                f"field_{index}": {"type": "char", "required": index % 2 == 0}
                for index in range(EXPORTER.MAX_EXPLICIT_MAPPING_KEYS + 1)
            }
        }

        paths = EXPORTER.dotted_paths(payload)

        self.assertIn("fields", paths)
        self.assertIn("fields.*", paths)
        self.assertIn("fields.*.type", paths)
        self.assertIn("fields.*.required", paths)
        self.assertFalse(any("field_" in path for path in paths))

    def test_large_mapping_collects_the_union_of_value_shapes(self):
        rows = {
            f"entry_{index}": ({"allowed": True} if index % 2 else {"reason": {"code": "ok"}})
            for index in range(EXPORTER.MAX_EXPLICIT_MAPPING_KEYS + 1)
        }

        paths = EXPORTER.dotted_paths({"policies": rows})

        self.assertIn("policies.*.allowed", paths)
        self.assertIn("policies.*.reason.code", paths)


if __name__ == "__main__":
    unittest.main()
