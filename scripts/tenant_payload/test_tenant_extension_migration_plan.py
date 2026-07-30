#!/usr/bin/env python3

import unittest

from tenant_extension_migration_plan import validate


class TestTenantExtensionMigrationPlan(unittest.TestCase):
    def test_valid_plan_is_dry_run(self):
        report = validate(
            {
                "entries": [
                    {
                        "company_scope": "fixture-a",
                        "model": "fixture.model",
                        "extension_key": "site_reference",
                        "data_type": "char",
                        "owner_confirmed": True,
                    }
                ]
            }
        )
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["mode"], "dry-run")
        self.assertEqual(report["old_columns_deleted"], 0)

    def test_unknown_owner_fails_closed(self):
        report = validate(
            {
                "entries": [
                    {
                        "company_scope": "",
                        "model": "fixture.model",
                        "extension_key": "site_reference",
                        "data_type": "char",
                        "owner_confirmed": False,
                    }
                ]
            }
        )
        reasons = {row["reason_code"] for row in report["errors"]}
        self.assertEqual(report["result"], "BLOCKED")
        self.assertIn("OWNER_IDENTITY_REQUIRED", reasons)
        self.assertIn("OWNER_NOT_CONFIRMED", reasons)

    def test_old_column_drop_is_rejected(self):
        report = validate(
            {
                "entries": [
                    {
                        "company_scope": "fixture-a",
                        "model": "fixture.model",
                        "extension_key": "site_reference",
                        "data_type": "char",
                        "owner_confirmed": True,
                        "drop_old_column": True,
                    }
                ]
            }
        )
        self.assertIn(
            "OLD_COLUMN_DROP_FORBIDDEN",
            {row["reason_code"] for row in report["errors"]},
        )


if __name__ == "__main__":
    unittest.main()
