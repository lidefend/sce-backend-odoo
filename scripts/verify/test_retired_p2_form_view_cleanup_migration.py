#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    ROOT
    / "addons/smart_construction_core/migrations/17.0.0.127/pre-migration.py"
)
PRODUCT_SOURCE = ROOT / "addons/smart_construction_core"


class RecordingCursor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[list[str]]]] = []

    def execute(self, query: str, params: list[list[str]]) -> None:
        self.calls.append((" ".join(query.split()), params))


def load_migration():
    spec = importlib.util.spec_from_file_location("retired_p2_view_cleanup", MIGRATION)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load retired P2 view cleanup migration")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RetiredP2FormViewCleanupMigrationTest(unittest.TestCase):
    def test_cleanup_is_exact_metadata_only_and_recursive(self):
        cursor = RecordingCursor()
        module = load_migration()
        module.migrate(cursor, "17.0.0.126")

        self.assertEqual(len(cursor.calls), 1)
        statement, params = cursor.calls[0]
        self.assertIn("WITH RECURSIVE retired_view_ids", statement)
        self.assertIn("child.inherit_id = parent.id", statement)
        self.assertIn("data.module = 'smart_construction_core'", statement)
        self.assertIn("DELETE FROM ir_model_data", statement)
        self.assertIn("DELETE FROM ir_ui_view", statement)
        self.assertNotIn("UPDATE ", statement)
        self.assertNotIn("ALTER TABLE", statement)
        self.assertNotIn("DROP ", statement)
        self.assertEqual(params, [list(module.RETIRED_P2_FORM_VIEW_XMLIDS)])
        self.assertEqual(len(module.RETIRED_P2_FORM_VIEW_XMLIDS), 21)

    def test_retired_xmlids_are_not_redeclared_by_the_product_module(self):
        module = load_migration()
        declarations = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in PRODUCT_SOURCE.rglob("*.xml")
        )
        for xmlid in module.RETIRED_P2_FORM_VIEW_XMLIDS:
            self.assertNotIn(f'id="{xmlid}"', declarations)


if __name__ == "__main__":
    unittest.main()
