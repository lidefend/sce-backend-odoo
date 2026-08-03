#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    ROOT
    / "addons/smart_construction_core/migrations/17.0.0.77/pre-migration.py"
)


def load_migration():
    spec = importlib.util.spec_from_file_location("legacy_projection_archive", MIGRATION)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load projection archive migration")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RecordingCursor:
    def __init__(self, relations):
        self.relations = dict(relations)
        self.calls = []
        self._result = None

    def execute(self, query, params=None):
        normalized = " ".join(query.split())
        self.calls.append((normalized, params))
        if "to_regclass(%s)" in normalized:
            relation = str(params[0]).removeprefix("public.")
            kind = self.relations.get(relation)
            self._result = (kind,) if kind else None
        elif normalized.startswith("ALTER TABLE"):
            source, archive = [part for part in normalized.split('"') if part.startswith("sc_")]
            self.relations[archive] = self.relations.pop(source)
            self._result = None
        else:
            self._result = None

    def fetchone(self):
        return self._result


class OptionalProjectionLegacyArchiveMigrationTest(unittest.TestCase):
    def test_physical_tables_are_archived_without_deleting_rows(self):
        module = load_migration()
        cursor = RecordingCursor(
            {
                "sc_ar_ap_project_summary": "r",
                "sc_comprehensive_cost_summary": "r",
            }
        )

        module.migrate(cursor, "17.0.0.76")

        statements = "\n".join(query for query, _params in cursor.calls)
        self.assertEqual(statements.count("ALTER TABLE"), 2)
        self.assertEqual(statements.count("COMMENT ON TABLE"), 2)
        self.assertNotIn("DROP TABLE", statements)
        self.assertNotIn("DELETE FROM", statements)
        for archive in module.LEGACY_PROJECTION_ARCHIVES.values():
            self.assertEqual(cursor.relations[archive], "r")

    def test_existing_views_are_left_in_place(self):
        module = load_migration()
        cursor = RecordingCursor(
            {source: "v" for source in module.LEGACY_PROJECTION_ARCHIVES}
        )

        module.migrate(cursor, "17.0.0.76")

        statements = "\n".join(query for query, _params in cursor.calls)
        self.assertNotIn("ALTER TABLE", statements)

    def test_existing_archive_fails_closed(self):
        module = load_migration()
        source, archive = next(iter(module.LEGACY_PROJECTION_ARCHIVES.items()))
        cursor = RecordingCursor({source: "r", archive: "r"})

        with self.assertRaisesRegex(
            RuntimeError, "LEGACY_PROJECTION_ARCHIVE_ALREADY_EXISTS"
        ):
            module.migrate(cursor, "17.0.0.76")


if __name__ == "__main__":
    unittest.main()
