#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    ROOT
    / "addons"
    / "smart_construction_core"
    / "migrations"
    / "17.0.0.114"
    / "pre-migration.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("material_rfq_p2_extraction_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeCursor:
    def __init__(self, *, row_count: int):
        self.row_count = row_count
        self.execute_count = 0

    def execute(self, query, params=None):
        self.execute_count += 1

    def fetchall(self):
        return [("legacy_visible_01",), ("legacy_acceptance_sort_id",)]

    def fetchone(self):
        return (self.row_count,)


class MaterialRfqP2ExtractionMigrationTests(unittest.TestCase):
    def test_nonempty_customer_history_fails_closed(self):
        migration = _load_migration()
        with self.assertRaisesRegex(RuntimeError, "MATERIAL_RFQ_P2_HISTORY_NOT_EXTRACTED"):
            migration.migrate(FakeCursor(row_count=2), "17.0.0.113")

    def test_empty_customer_history_allows_schema_cleanup(self):
        migration = _load_migration()
        cursor = FakeCursor(row_count=0)
        migration.migrate(cursor, "17.0.0.113")
        self.assertEqual(cursor.execute_count, 2)


if __name__ == "__main__":
    unittest.main()
