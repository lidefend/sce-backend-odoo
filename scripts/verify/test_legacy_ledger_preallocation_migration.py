"""Execute migration DML on real relational rows; adapt PostgreSQL DDL only."""
import importlib.util
import sqlite3
import ast
import xml.etree.ElementTree as ET
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "migration", ROOT / "addons/smart_construction_core/migrations/17.0.0.169/pre-migration.py"
)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


class Cursor:
    def __init__(self, db):
        self.db = db
        self.result = None

    def execute(self, sql):
        if "to_regclass" in sql:
            table = sql.split("public.")[1].split("'")[0]
            exists = self.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            self.result = (exists[0] if exists else None,)
        elif sql.startswith("LOCK TABLE"):
            pass  # PostgreSQL lock behavior is covered by the restored-db rehearsal.
        elif sql.startswith("ALTER TABLE"):
            columns = [row[1] for row in self.db.execute("PRAGMA table_info(payment_ledger)")]
            if "normalization_state" not in columns:
                self.db.execute("ALTER TABLE payment_ledger ADD COLUMN normalization_state varchar")
        else:
            self.db.execute(sql)

    def fetchone(self):
        return self.result


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.cr = Cursor(self.db)

    def create_ledger(self, classified=False):
        self.db.execute("CREATE TABLE payment_ledger(id integer, amount numeric, company_id integer)")
        self.db.execute("INSERT INTO payment_ledger VALUES (1, 123.45, NULL)")
        if classified:
            self.db.execute("ALTER TABLE payment_ledger ADD COLUMN normalization_state varchar")

    def run_migration(self):
        MIGRATION.migrate(self.cr, "17.0.0.132")

    def test_old_schema_without_allocation_preserves_history(self):
        self.create_ledger()
        self.run_migration()
        self.assertEqual(self.db.execute("SELECT * FROM payment_ledger").fetchall(),
                         [(1, 123.45, None, "legacy_unresolved_identity")])

    def test_existing_classifications_are_preserved(self):
        self.create_ledger(True)
        for i, state in enumerate(("normalized", "legacy_observed_identity", "legacy_unresolved_identity"), 2):
            self.db.execute("INSERT INTO payment_ledger VALUES (?, 50, 7, ?)", (i, state))
        before = self.db.execute("SELECT * FROM payment_ledger WHERE id > 1").fetchall()
        self.run_migration()
        self.assertEqual(before, self.db.execute("SELECT * FROM payment_ledger WHERE id > 1").fetchall())
        self.assertEqual(self.db.execute("SELECT normalization_state FROM payment_ledger WHERE id=1").fetchone()[0],
                         "legacy_unresolved_identity")

    def test_idempotent(self):
        self.create_ledger()
        self.run_migration()
        first = self.db.execute("SELECT * FROM payment_ledger").fetchall()
        self.run_migration()
        self.assertEqual(first, self.db.execute("SELECT * FROM payment_ledger").fetchall())

    def test_funding_replay_runs_after_parent_classification(self):
        self.create_ledger()
        seen = []
        def replay(cr, version):
            self.assertIs(cr, self.cr)
            seen.append(self.db.execute("SELECT normalization_state FROM payment_ledger").fetchone()[0])
        with patch.object(MIGRATION.runpy, "run_path", return_value={"migrate": replay}) as loader:
            self.run_migration()
            self.assertTrue(loader.call_args.args[0].endswith("17.0.0.156/pre-migration.py"))
        self.assertEqual(seen, ["legacy_unresolved_identity"])

    def test_retired_contracts_leave_publication_before_validation(self):
        path = ROOT / "addons/smart_construction_core/data/view_orchestration_form_section_contract_data.xml"
        root = ET.parse(path).getroot()
        retirements = []
        for function in root.iter("function"):
            if function.get("model") != "ui.business.config.contract" or function.get("name") != "write":
                continue
            values = function.findall("value")
            if len(values) != 2:
                continue
            vals = ast.literal_eval(values[1].get("eval"))
            if vals.get("active") is False:
                retirements.append(vals)
                self.assertEqual(vals, {"active": False, "status": "draft"})
        self.assertGreaterEqual(len(retirements), 2)

    def test_no_parent_table_is_noop(self):
        self.run_migration()
        self.assertEqual(self.db.execute("SELECT name FROM sqlite_master").fetchall(), [])

    def test_child_table_does_not_change_parent_classification(self):
        self.create_ledger()
        self.db.execute("CREATE TABLE payment_ledger_allocation(id integer)")
        self.db.execute("INSERT INTO payment_ledger_allocation VALUES (9)")
        self.run_migration()
        self.assertEqual(self.db.execute("SELECT * FROM payment_ledger_allocation").fetchall(), [(9,)])
        self.assertEqual(self.db.execute("SELECT normalization_state FROM payment_ledger").fetchone()[0],
                         "legacy_unresolved_identity")


if __name__ == "__main__":
    unittest.main()
