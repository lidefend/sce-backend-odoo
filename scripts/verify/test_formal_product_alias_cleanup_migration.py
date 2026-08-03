#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    ROOT
    / "addons/smart_construction_core/migrations/17.0.0.76/pre-migration.py"
)


class RecordingCursor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def execute(self, query: str, params: tuple[str, ...]) -> None:
        self.calls.append((" ".join(query.split()), params))


def load_migration():
    spec = importlib.util.spec_from_file_location("field_alias_cleanup", MIGRATION)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load cleanup migration")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FormalProductAliasCleanupMigrationTest(unittest.TestCase):
    def test_cleanup_is_metadata_only_and_covers_both_obsolete_prefixes(self):
        cursor = RecordingCursor()
        load_migration().migrate(cursor, "17.0.0.75")

        self.assertEqual(len(cursor.calls), 3)
        statements = "\n".join(query for query, _params in cursor.calls)
        self.assertIn("WITH RECURSIVE obsolete_view_ids", statements)
        self.assertIn("child.inherit_id = parent.id", statements)
        self.assertIn("model = 'ir.ui.view'", statements)
        self.assertIn("DELETE FROM ir_ui_view", statements)
        self.assertIn("DELETE FROM ir_model_data", statements)
        self.assertIn("DELETE FROM ir_model_fields", statements)
        self.assertNotIn("UPDATE ", statements)
        self.assertNotIn("ALTER TABLE", statements)
        self.assertNotIn("DROP ", statements)
        self.assertNotIn("construction_contract", statements)
        params = [value for _query, values in cursor.calls for value in values]
        self.assertIn("p1_visible_%", params)
        self.assertIn("uc_formal_%", params)


if __name__ == "__main__":
    unittest.main()
