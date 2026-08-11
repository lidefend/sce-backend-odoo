#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

MIGRATION = Path(__file__).resolve().parents[2] / "addons/smart_construction_core/migrations/17.0.0.115/pre-migration.py"


def load_migration():
    spec = importlib.util.spec_from_file_location("material_inbound_p2_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeCursor:
    def __init__(self, row_count):
        self.row_count = row_count
        self.execute_count = 0

    def execute(self, query, params=None):
        self.execute_count += 1

    def fetchall(self):
        return [("legacy_visible_01",), ("legacy_acceptance_sort_id",)]

    def fetchone(self):
        return (self.row_count,)


class MaterialInboundMigrationTests(unittest.TestCase):
    def test_nonempty_history_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "MATERIAL_INBOUND_P2_HISTORY_NOT_EXTRACTED"):
            load_migration().migrate(FakeCursor(1), "17.0.0.114")

    def test_empty_history_allows_cleanup(self):
        cursor = FakeCursor(0)
        load_migration().migrate(cursor, "17.0.0.114")
        self.assertEqual(cursor.execute_count, 2)


if __name__ == "__main__":
    unittest.main()
