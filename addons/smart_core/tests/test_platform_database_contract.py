# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


TARGET_PATH = Path(__file__).resolve().parents[1] / "core/platform_database_contract.py"
SPEC = importlib.util.spec_from_file_location("platform_database_contract", TARGET_PATH)
assert SPEC and SPEC.loader
TARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGET)


class _Params:
    def __init__(self, value):
        self.value = value

    def sudo(self):
        return self

    def get_param(self, key, default=""):
        self.key = key
        return self.value if self.value is not None else default


class _Env:
    def __init__(self, database, configured):
        self.cr = SimpleNamespace(dbname=database)
        self.params = _Params(configured)

    def __getitem__(self, key):
        if key != "ir.config_parameter":
            raise KeyError(key)
        return self.params


class PlatformDatabaseContractTests(unittest.TestCase):
    def test_production_requires_explicit_platform_database(self):
        with patch.dict(os.environ, {"SC_ENVIRONMENT": "production"}, clear=False):
            with self.assertRaisesRegex(TARGET.PlatformDatabaseContractError, "PLATFORM_RELEASE_DB_REQUIRED"):
                TARGET.resolve_platform_database(_Env("sc_production", ""))

    def test_production_rejects_cross_database_target(self):
        with patch.dict(os.environ, {"SC_ENVIRONMENT": "production"}, clear=False):
            with self.assertRaisesRegex(TARGET.PlatformDatabaseContractError, "MUST_MATCH_CURRENT"):
                TARGET.resolve_platform_database(_Env("sc_production", "sc_platform_core"))

    def test_production_accepts_explicit_colocation(self):
        with patch.dict(os.environ, {"SC_ENVIRONMENT": "production"}, clear=False):
            self.assertEqual(
                TARGET.resolve_platform_database(_Env("sc_production", "sc_production")),
                "sc_production",
            )

    def test_nonproduction_missing_value_colocates_without_guessing(self):
        with patch.dict(os.environ, {"SC_ENVIRONMENT": "test"}, clear=False):
            self.assertEqual(TARGET.resolve_platform_database(_Env("sc_demo", "")), "sc_demo")

    def test_nonproduction_explicit_dual_database_is_recognized(self):
        with patch.dict(os.environ, {"SC_ENVIRONMENT": "test"}, clear=False):
            self.assertEqual(
                TARGET.resolve_platform_database(_Env("sc_demo", "sc_platform_core")),
                "sc_platform_core",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
