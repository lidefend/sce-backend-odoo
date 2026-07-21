# -*- coding: utf-8 -*-
import importlib.util
import unittest
from pathlib import Path


def _load_boundary():
    root = Path(__file__).resolve().parents[1]
    path = root / "core" / "database_request_boundary.py"
    spec = importlib.util.spec_from_file_location("smart_core_database_request_boundary_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestLockedDatabaseParameterEnforcement(unittest.TestCase):
    def setUp(self):
        self.boundary = _load_boundary()

    def normalize(self, params, *, trusted_lock=True, effective_db="sc_production"):
        return self.boundary.normalize_database_params(
            params,
            effective_db=effective_db,
            trusted_lock=trusted_lock,
        )

    def assert_locked(self, source):
        params, target = self.normalize(source)
        self.assertEqual(target, "sc_production")
        self.assertEqual(params.get("db"), "sc_production")
        if "database" in params:
            self.assertEqual(params["database"], "sc_production")

    def test_locked_missing_database_uses_effective_database(self):
        self.assert_locked({"scene": "web"})

    def test_locked_matching_db_uses_effective_database(self):
        self.assert_locked({"db": "sc_production"})

    def test_locked_matching_database_alias_uses_effective_database(self):
        self.assert_locked({"database": "sc_production"})

    def test_locked_old_db_cannot_override_effective_database(self):
        self.assert_locked({"db": "sc_prod"})

    def test_locked_unknown_db_cannot_override_effective_database(self):
        self.assert_locked({"db": "r8_missing_database"})

    def test_locked_database_alias_cannot_override_effective_database(self):
        self.assert_locked({"database": "sc_prod"})

    def test_locked_unknown_database_alias_cannot_override_effective_database(self):
        self.assert_locked({"database": "r8_missing_database"})

    def test_locked_conflicting_database_fields_are_consistent(self):
        self.assert_locked({"db": "sc_prod", "database": "r8_missing_database"})

    def test_locked_null_database_values_are_replaced(self):
        self.assert_locked({"db": None, "database": None})

    def test_locked_empty_database_values_are_replaced(self):
        self.assert_locked({"db": "", "database": ""})

    def test_locked_non_string_database_values_are_replaced(self):
        for value in ([], {}, 7):
            with self.subTest(value=value):
                self.assert_locked({"db": value, "database": value})

    def test_locked_effective_database_is_not_hardcoded(self):
        params, target = self.normalize(
            {"db": "sc_production"},
            effective_db="tenant_locked_by_proxy",
        )
        self.assertEqual(target, "tenant_locked_by_proxy")
        self.assertEqual(params["db"], "tenant_locked_by_proxy")

    def test_normalization_does_not_mutate_request_input(self):
        source = {"db": "sc_prod", "nested": {"keep": True}}
        params, _target = self.normalize(source)
        self.assertEqual(source["db"], "sc_prod")
        self.assertIsNot(params, source)
        self.assertEqual(params["nested"], {"keep": True})

    def test_unlocked_legal_database_selection_is_preserved(self):
        params, target = self.normalize(
            {"db": "tenant_a"},
            trusted_lock=False,
            effective_db="tenant_a",
        )
        self.assertEqual(params["db"], "tenant_a")
        self.assertEqual(target, "tenant_a")

    def test_untrusted_lock_claim_does_not_gain_override_semantics(self):
        params, target = self.normalize(
            {"db": "tenant_a"},
            trusted_lock=False,
            effective_db="client_claimed_lock",
        )
        self.assertEqual(params["db"], "tenant_a")
        self.assertEqual(target, "tenant_a")


if __name__ == "__main__":
    unittest.main()
