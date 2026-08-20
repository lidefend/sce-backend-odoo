# -*- coding: utf-8 -*-
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "utils" / "load_contract_response_cache.py"
SPEC = importlib.util.spec_from_file_location("load_contract_response_cache_under_test", MODULE_PATH)
TARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGET)
LoadContractResponseCache = TARGET.LoadContractResponseCache


class TestLoadContractResponseCache(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.cache = LoadContractResponseCache(
            max_entries=2,
            ttl_seconds=5,
            clock=lambda: self.now,
        )

    def test_hit_returns_isolated_copy(self):
        response = {"status": "success", "data": {"views": ["form"]}}
        self.cache.put("user-page", "source-v1", response)

        first = self.cache.get("user-page", "source-v1")
        first["data"]["views"].append("tree")

        self.assertEqual(
            self.cache.get("user-page", "source-v1")["data"]["views"],
            ["form"],
        )

    def test_source_change_invalidates_entry(self):
        self.cache.put("user-page", "source-v1", {"status": "success"})

        self.assertIsNone(self.cache.get("user-page", "source-v2"))
        self.assertIsNone(self.cache.get("user-page", "source-v1"))

    def test_ttl_expiry_invalidates_entry(self):
        self.cache.put("user-page", "source-v1", {"status": "success"})
        self.now += 5.01

        self.assertIsNone(self.cache.get("user-page", "source-v1"))

    def test_capacity_evicts_least_recently_used_entry(self):
        self.cache.put("page-a", "source", {"page": "a"})
        self.cache.put("page-b", "source", {"page": "b"})
        self.assertEqual(self.cache.get("page-a", "source")["page"], "a")

        self.cache.put("page-c", "source", {"page": "c"})

        self.assertIsNone(self.cache.get("page-b", "source"))
        self.assertEqual(self.cache.get("page-a", "source")["page"], "a")
        self.assertEqual(self.cache.get("page-c", "source")["page"], "c")


if __name__ == "__main__":
    unittest.main()
