#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    ROOT
    / "addons/smart_construction_core/migrations/17.0.0.130/pre-migration.py"
)


class RecordingCursor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def execute(self, query: str, params: tuple[str, ...]) -> None:
        self.calls.append((" ".join(query.split()), params))


def load_migration():
    spec = importlib.util.spec_from_file_location("retired_p1_view_cleanup", MIGRATION)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load retired P1 view cleanup migration")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RetiredP1AliasViewCleanupMigrationTest(unittest.TestCase):
    def test_cleanup_is_metadata_only_and_uses_xmlid_namespace(self):
        cursor = RecordingCursor()
        load_migration().migrate(cursor, "17.0.0.75")

        self.assertEqual(len(cursor.calls), 1)
        statement, params = cursor.calls[0]
        self.assertIn("WITH RECURSIVE retired_view_ids", statement)
        self.assertIn("data.module = 'smart_construction_core'", statement)
        self.assertIn("data.model = 'ir.ui.view'", statement)
        self.assertIn("child.inherit_id = parent.id", statement)
        self.assertIn("DELETE FROM ir_model_data", statement)
        self.assertIn("DELETE FROM ir_ui_view", statement)
        self.assertNotIn("arch_db", statement)
        self.assertNotIn("UPDATE ", statement)
        self.assertNotIn("ALTER TABLE", statement)
        self.assertNotIn("DROP ", statement)
        self.assertEqual(params, ("view_p1_daily_business_visible_%",))


if __name__ == "__main__":
    unittest.main()
