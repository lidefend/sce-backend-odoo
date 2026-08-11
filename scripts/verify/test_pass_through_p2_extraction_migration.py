#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

MIGRATION = Path(__file__).resolve().parents[2] / "addons/smart_construction_core/migrations/17.0.0.116/pre-migration.py"


def load_migration():
    spec = importlib.util.spec_from_file_location("pass_through_p2_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeCursor:
    def __init__(self, row_counts):
        self.row_counts = iter(row_counts)
        self.current_count = 0

    def execute(self, query, params=None):
        if "SELECT COUNT" in query:
            self.current_count = next(self.row_counts)

    def fetchall(self):
        return [("legacy_visible_01",)]

    def fetchone(self):
        return (self.current_count,)


class PassThroughP2MigrationTests(unittest.TestCase):
    def test_any_nonempty_table_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "PASS_THROUGH_P2_HISTORY_NOT_EXTRACTED"):
            load_migration().migrate(FakeCursor([0, 2]), "17.0.0.115")

    def test_all_empty_tables_allow_cleanup(self):
        load_migration().migrate(FakeCursor([0, 0, 0, 0]), "17.0.0.115")


if __name__ == "__main__":
    unittest.main()
