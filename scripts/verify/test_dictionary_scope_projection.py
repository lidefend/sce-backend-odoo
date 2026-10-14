#!/usr/bin/env python3
"""Negative controls for the single dictionary scope vocabulary."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import system_init_dictionary_scope_guard as guard  # noqa: E402

projection = guard.load_projection()


class ScopeDispositionTest(unittest.TestCase):
    def test_global_is_always_the_shared_bucket(self):
        self.assertEqual(projection.projection_bucket("global", ""), projection.GLOBAL_BUCKET)
        self.assertEqual(
            projection.projection_bucket("  global  ", "ignored", ()), projection.GLOBAL_BUCKET
        )

    def test_role_uses_its_own_code_and_refuses_an_empty_reference(self):
        self.assertEqual(projection.projection_bucket("role", "pm"), "pm")
        self.assertIsNone(projection.projection_bucket("role", "   "))
        self.assertEqual(
            projection.scope_disposition("role", ""), (None, projection.DISPOSITION_MISSING_REFERENCE)
        )

    def test_company_delivers_only_for_an_authorized_company(self):
        self.assertEqual(
            projection.projection_bucket("company", "8", ["8"]), projection.GLOBAL_BUCKET
        )
        self.assertEqual(
            projection.projection_bucket("company", "8", [8]), projection.GLOBAL_BUCKET
        )
        self.assertIsNone(projection.projection_bucket("company", "8", []))
        self.assertIsNone(projection.projection_bucket("company", "9", ["8"]))
        self.assertEqual(
            projection.scope_disposition("company", "9", ["8"]),
            (None, projection.DISPOSITION_UNAUTHORIZED_COMPANY),
        )

    def test_company_without_a_reference_is_withheld_not_promoted(self):
        self.assertIsNone(projection.projection_bucket("company", "", ["8"]))
        self.assertEqual(
            projection.scope_disposition("company", None, ["8"]),
            (None, projection.DISPOSITION_MISSING_REFERENCE),
        )

    def test_unknown_scope_has_no_bucket(self):
        for scope in ("", "   ", "tenant", "industry", "GLOBAL", "Global"):
            with self.subTest(scope=scope):
                self.assertIsNone(projection.projection_bucket(scope, "8", ["8"]))
        self.assertEqual(
            projection.scope_disposition("tenant", "8", ["8"]),
            (None, projection.DISPOSITION_UNKNOWN_SCOPE),
        )

    def test_authorized_reference_normalization_matches_res_company_ids(self):
        self.assertEqual(projection.company_scope_references([3, "7", 3]), frozenset({"3", "7"}))
        self.assertEqual(projection.company_scope_references(None), frozenset())
        self.assertEqual(projection.company_scope_references([]), frozenset())

    def test_delivered_vocabulary_is_the_three_real_scopes(self):
        self.assertEqual(projection.DELIVERED_SCOPES, ("global", "company", "role"))


if __name__ == "__main__":
    unittest.main()
