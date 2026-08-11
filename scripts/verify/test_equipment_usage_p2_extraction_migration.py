#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

MIGRATION = Path(__file__).resolve().parents[2] / "addons/smart_construction_core/migrations/17.0.0.120/pre-migration.py"


def load_migration():
    spec = importlib.util.spec_from_file_location("equipment_usage_p2_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeCursor:
    def __init__(self, count): self.count = count
    def execute(self, query, params=None): return None
    def fetchall(self): return [("legacy_visible_01",), ("former_supplier_name",)]
    def fetchone(self): return (self.count,)


class EquipmentUsageP2MigrationTests(unittest.TestCase):
    def test_nonempty_history_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "EQUIPMENT_USAGE_P2_HISTORY_NOT_EXTRACTED"):
            load_migration().migrate(FakeCursor(1), "17.0.0.119")

    def test_empty_history_allows_cleanup(self):
        load_migration().migrate(FakeCursor(0), "17.0.0.119")


if __name__ == "__main__": unittest.main()
