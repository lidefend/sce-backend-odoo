#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "addons/smart_core/app_config_engine/models/app_nav_config.py"
IDENTITY_SOURCE = ROOT / "addons/smart_core/core/system_init_identity_payload.py"
SYSTEM_INIT_SOURCE = ROOT / "addons/smart_core/handlers/system_init.py"


class AppNavConfigCompanyCacheTest(unittest.TestCase):
    def test_inactive_unique_dimension_is_discovered_and_reactivated(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count("with_context(active_test=False).search("), 3)
        self.assertIn("if cfg and cfg.is_active and not self._menu_metadata_changed_since(cfg):", source)
        self.assertIn("'is_active': True", source)
        self.assertIn("if hash_changed or not cfg.is_active:", source)

    def test_concurrent_create_reuses_authoritative_dimension(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("except IntegrityError:", source)
        self.assertIn("Menu config concurrent create resolved", source)

    def test_system_init_identity_uses_effective_request_company(self):
        identity_source = IDENTITY_SOURCE.read_text(encoding="utf-8")
        system_init_source = SYSTEM_INIT_SOURCE.read_text(encoding="utf-8")
        self.assertIn("company=None", identity_source)
        self.assertIn('"allowed_company_ids": normalized_allowed', identity_source)
        self.assertIn("company=env.company", system_init_source)
        self.assertIn('env.context.get("allowed_company_ids")', system_init_source)


if __name__ == "__main__":
    unittest.main()
