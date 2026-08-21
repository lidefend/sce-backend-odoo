# -*- coding: utf-8 -*-
import importlib.util
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


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

    def test_projection_source_token_changes_with_runtime_source_fingerprint(self):
        class FakeModel:
            _fields = {"write_date": object()}

            def sudo(self):
                return self

            def with_context(self, **_kwargs):
                return self

            def search(self, _domain, **_kwargs):
                return SimpleNamespace(id=1, write_date="2026-08-21 00:00:00", latest_version="")

        class FakeEnv:
            def __init__(self):
                self.user = SimpleNamespace(id=7)
                self._model = FakeModel()

            def __contains__(self, _model_code):
                return True

            def __getitem__(self, _model_code):
                return self._model

        env = FakeEnv()
        base = {"SC_SOURCE_REVISION": "a" * 40, "SC_SOURCE_FINGERPRINT": "b" * 64}
        with patch.dict(os.environ, base, clear=False):
            first = TARGET.build_projection_source_token(env, model_name="x.record")
        with patch.dict(os.environ, {**base, "SC_SOURCE_FINGERPRINT": "c" * 64}, clear=False):
            second = TARGET.build_projection_source_token(env, model_name="x.record")

        self.assertTrue(first)
        self.assertTrue(second)
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
