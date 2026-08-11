#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

from python_http_smoke_utils import build_intent_url, with_database_query


class ContractProbeRoutingTest(unittest.TestCase):
    def test_build_intent_url_binds_database(self) -> None:
        self.assertEqual(
            build_intent_url("http://127.0.0.1:18131", "sc_product_center"),
            "http://127.0.0.1:18131/api/v1/intent?db=sc_product_center",
        )

    def test_database_query_replaces_stale_value_and_preserves_context(self) -> None:
        self.assertEqual(
            with_database_query("https://example.test/api/v1/intent?lang=zh_CN&db=old", "tenant_a"),
            "https://example.test/api/v1/intent?lang=zh_CN&db=tenant_a",
        )

    def test_empty_database_does_not_invent_routing_context(self) -> None:
        self.assertEqual(
            with_database_query("https://example.test/api/v1/intent", ""),
            "https://example.test/api/v1/intent",
        )

    def test_scene_snapshot_uses_canonical_multi_database_probe_auth(self) -> None:
        source = (Path(__file__).resolve().parent / "scene_registry_asset_snapshot_guard.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("build_intent_url(base_url, db_name)", source)
        self.assertIn("obtain_runtime_probe_token(intent_url, db_name)", source)
        self.assertIn('"X-Odoo-DB": db_name', source)
        self.assertNotIn('"intent": "login"', source)


if __name__ == "__main__":
    unittest.main()
