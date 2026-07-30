#!/usr/bin/env python3

import csv
import tempfile
import unittest
from pathlib import Path

from legacy_custom_column_retirement import evaluate, load_inventory, rollback_ddl


class TestLegacyCustomColumnRetirement(unittest.TestCase):
    def _inventory(self, *, nonempty_record_count="0"):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "inventory.csv"
        columns = [
            "database_table",
            "model",
            "column_name",
            "field_type",
            "sql_type",
            "nullable",
            "default",
            "index",
            "constraint",
            "nonempty_record_count",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerow(
                {
                    "database_table": "fixture_record",
                    "model": "fixture.record",
                    "column_name": "x_custom_field",
                    "field_type": "char",
                    "sql_type": "varchar",
                    "nullable": "true",
                    "default": "NONE",
                    "index": "false",
                    "constraint": "NONE",
                    "nonempty_record_count": nonempty_record_count,
                }
            )
        return load_inventory(path)

    def _probe(self, **overrides):
        row = {
            "database_table": "fixture_record",
            "column_name": "x_custom_field",
            "effective_value_count": 0,
            "database_view_reference_count": 0,
            "odoo_view_reference_count": 0,
            "business_logic_reference_count": 0,
            "external_contract_reference_count": 0,
            "module_recreation_source_count": 0,
            "installation_dependency": False,
            "upgrade_dependency": False,
            "rollback_ddl_ready": True,
            "isolated_drop_rehearsal": "PASS",
            "registry_after_drop": "PASS",
            "upgrade_after_drop": "PASS",
            "rollback_ddl_verification": "PASS",
        }
        row.update(overrides)
        return {"columns": [row]}

    def test_complete_zero_reference_evidence_is_ready(self):
        rows = evaluate(self._inventory(), self._probe())
        self.assertEqual(rows[0]["status"], "READY_FOR_CONTROLLED_DROP")

    def test_reference_fails_closed(self):
        rows = evaluate(
            self._inventory(),
            self._probe(odoo_view_reference_count=1),
        )
        self.assertEqual(rows[0]["status"], "DEFER_REFERENCE_REMEDIATION")

    def test_missing_probe_fails_closed(self):
        rows = evaluate(self._inventory(), {"columns": []})
        self.assertEqual(rows[0]["status"], "BLOCKED_INCOMPLETE_EVIDENCE")

    def test_nonempty_value_requires_verified_restricted_archive(self):
        rows = evaluate(self._inventory(nonempty_record_count="1"), self._probe())
        self.assertEqual(rows[0]["status"], "BLOCKED_INCOMPLETE_EVIDENCE")
        self.assertIn(
            "NONEMPTY_VALUE_NOT_SAFELY_ARCHIVED",
            rows[0]["reason_codes"],
        )

    def test_verified_restricted_archive_allows_controlled_drop(self):
        probe = self._probe(
            selected_disposition="ARCHIVE_AS_UNRESOLVED_AUDIT_VALUE",
            unresolved_archive_verified=True,
            value_reconciliation="PASS",
            ordinary_user_discovery=0,
            formal_contract_publication=0,
        )
        rows = evaluate(self._inventory(nonempty_record_count="1"), probe)
        self.assertEqual(
            rows[0]["status"],
            "READY_FOR_CONTROLLED_DROP_AFTER_ARCHIVE",
        )

    def test_rollback_ddl_preserves_shape(self):
        ddl = rollback_ddl(self._inventory())
        self.assertIn(
            'ALTER TABLE "fixture_record" ADD COLUMN "x_custom_field" character varying;',
            ddl,
        )


if __name__ == "__main__":
    unittest.main()
