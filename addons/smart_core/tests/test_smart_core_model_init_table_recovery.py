# -*- coding: utf-8 -*-
"""P1 regression: a model overriding ``init()`` must still create its table.

``Registry.check_tables_exist`` recreates a missing table by calling only
``model.init()`` and never ``_auto_init()``.  A model whose ``init()`` only adds
extra indexes therefore leaves the table missing and the module upgrade dies
with ``UndefinedTable``.  These tests drop the real tables inside the test
transaction and re-enter the governed recovery entry, so the schema -- columns,
foreign keys and declared indexes included -- must come back before teardown
rolls the drop back.

Root cause 2 is locked separately: ``Registry.is_an_ordinary_table`` answers from
a process-wide ``pg_class`` snapshot, so a snapshot taken while a table was
missing makes the recovery path silently skip that table's foreign keys unless
the helper discards it before rebuilding.
"""

import ast
import os

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import SQL, table_exists

from ..core import model_table_recovery

RECOVERY_TEST_TAG = "model_init_table_recovery"

RECOVERED_MODELS = (
    "sc.contract.slo.observation",
    "sc.idempotency.record",
)

# Every Many2one column the two tables must end up carrying: the ORM-managed
# create_uid/write_uid/company_id plus sc.idempotency.record.actor_uid.
EXPECTED_FOREIGN_KEYS = (
    ("sc_contract_slo_observation", "company_id", "res_company", "id"),
    ("sc_contract_slo_observation", "create_uid", "res_users", "id"),
    ("sc_contract_slo_observation", "write_uid", "res_users", "id"),
    ("sc_idempotency_record", "actor_uid", "res_users", "id"),
    ("sc_idempotency_record", "company_id", "res_company", "id"),
    ("sc_idempotency_record", "create_uid", "res_users", "id"),
    ("sc_idempotency_record", "write_uid", "res_users", "id"),
)

# Both declared composite indexes plus the partial unique arbitration index.
EXPECTED_INDEXES = (
    ("sc_contract_slo_observation", "sc_contract_slo_observation_version_time"),
    ("sc_contract_slo_observation", "sc_contract_slo_observation_identity_time"),
    ("sc_idempotency_record", "sc_idempotency_record_key_unique"),
)

MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models"
)


def _iter_init_overrides(path):
    """Yield ``(class_name, function_node)`` for every ``init()`` override."""
    with open(path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=path)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "init":
                yield node.name, item


@tagged("post_install", "-at_install", "smart_core", RECOVERY_TEST_TAG)
class TestModelInitTableRecovery(TransactionCase):
    """Missing-table recovery has to rebuild columns, not only indexes."""

    def _drop_table(self, model):
        self.env.cr.execute(
            SQL("DROP TABLE IF EXISTS %s CASCADE", SQL.identifier(model._table))
        )

    def _assert_foreign_key(self, table, column, ref_table, ref_column):
        self.env.cr.execute(
            """
            SELECT c2.relname, a2.attname
              FROM pg_constraint AS fk
              JOIN pg_class AS c1 ON fk.conrelid = c1.oid
              JOIN pg_class AS c2 ON fk.confrelid = c2.oid
              JOIN pg_attribute AS a1 ON a1.attrelid = c1.oid AND fk.conkey[1] = a1.attnum
              JOIN pg_attribute AS a2 ON a2.attrelid = c2.oid AND fk.confkey[1] = a2.attnum
             WHERE fk.contype = 'f' AND c1.relname = %s AND a1.attname = %s
            """,
            (table, column),
        )
        rows = self.env.cr.fetchall()
        self.assertIn(
            (ref_table, ref_column),
            rows,
            "missing foreign key %s.%s -> %s.%s" % (table, column, ref_table, ref_column),
        )

    def _foreign_key_count(self, table):
        self.env.cr.execute(
            """
            SELECT count(*)
              FROM pg_constraint AS fk
              JOIN pg_class AS c1 ON fk.conrelid = c1.oid
             WHERE fk.contype = 'f' AND c1.relname = %s
            """,
            (table,),
        )
        return self.env.cr.fetchone()[0]

    def _assert_index(self, table, indexname):
        self.env.cr.execute(
            "SELECT 1 FROM pg_indexes WHERE tablename = %s AND indexname = %s",
            (table, indexname),
        )
        self.assertTrue(self.env.cr.fetchone(), "missing index %s" % indexname)

    def _assert_recovered_schema(self):
        for table, column, ref_table, ref_column in EXPECTED_FOREIGN_KEYS:
            self._assert_foreign_key(table, column, ref_table, ref_column)
        for table, indexname in EXPECTED_INDEXES:
            self._assert_index(table, indexname)

    def test_registry_recovers_missing_tables(self):
        models = [self.env[name] for name in RECOVERED_MODELS]

        # Negative baseline first: every table really is present before injection,
        # so a later failure can only come from the dropped-table path.
        for model in models:
            self.assertTrue(table_exists(self.env.cr, model._table), model._table)

        for model in models:
            self._drop_table(model)
            self.assertFalse(
                table_exists(self.env.cr, model._table),
                "injection failed for %s" % model._table,
            )

        # The governed recovery entry that used to crash must now heal the schema.
        self.env.registry.check_tables_exist(self.env.cr)

        for model in models:
            self.assertTrue(table_exists(self.env.cr, model._table), model._table)

        self._assert_recovered_schema()
        recovered_fks = sum(self._foreign_key_count(model._table) for model in models)
        self.assertEqual(
            recovered_fks,
            len(EXPECTED_FOREIGN_KEYS),
            "recovered tables carry an unexpected foreign-key set",
        )

        # The recovered table must be usable by the ORM, not only present in SQL.
        record = self.env["sc.idempotency.record"].create(
            {
                "name": "model_init_table_recovery",
                "idempotency_key": "model-init-table-recovery",
                "idempotency_fingerprint": "regression",
            }
        )
        self.assertTrue(record.id)
        self.env.cr.execute(
            "SELECT id FROM sc_idempotency_record WHERE id = %s", (record.id,)
        )
        self.assertEqual(self.env.cr.fetchone(), (record.id,))

    def test_ensure_table_on_init_is_noop_for_existing_table(self):
        model = self.env["sc.idempotency.record"]
        self.assertTrue(table_exists(self.env.cr, model._table))
        # A present table must take the untouched path: no recreation, no error.
        self.assertFalse(model_table_recovery.ensure_table_on_init(model))
        self.assertIsNone(model.init())
        self.assertTrue(table_exists(self.env.cr, model._table))

    def test_recovery_survives_stale_ordinary_tables_snapshot(self):
        """Root cause 2: the registry caches a ``pg_class`` snapshot.

        The snapshot below is taken *after* the tables are dropped, so it says
        they are missing.  If ``ensure_table_on_init`` ever stops discarding it,
        ``Many2one.update_db_foreign_key`` answers from the stale set and the
        foreign keys are silently skipped -- this test then fails.
        """
        models = [self.env[name] for name in RECOVERED_MODELS]
        registry = self.env.registry

        for model in models:
            self._drop_table(model)

        registry._ordinary_tables = None
        # Take the snapshot now, while both tables are absent from it.
        registry.is_an_ordinary_table(models[0])
        self.assertNotIn(models[0]._table, registry._ordinary_tables)

        try:
            registry.check_tables_exist(self.env.cr)
            for model in models:
                self.assertTrue(table_exists(self.env.cr, model._table), model._table)
            self._assert_recovered_schema()
        finally:
            # Never leak a test-injected snapshot into sibling tests.
            registry._ordinary_tables = None

    def test_every_smart_core_init_override_calls_recovery(self):
        """Static guard for the opt-in convention (silent-regression risk).

        ``ensure_table_on_init`` only acts when a model calls it, so a future
        smart_core model that overrides ``init()`` without calling the helper
        would quietly reintroduce root cause 1.  Every ``init()`` override in
        this package must call it.
        """
        offenders = []
        overrides = 0
        for filename in sorted(os.listdir(MODELS_DIR)):
            if not filename.endswith(".py"):
                continue
            path = os.path.join(MODELS_DIR, filename)
            for class_name, func in _iter_init_overrides(path):
                overrides += 1
                calls_helper = any(
                    isinstance(node, ast.Call)
                    and (
                        (
                            isinstance(node.func, ast.Attribute)
                            and node.func.attr == "ensure_table_on_init"
                        )
                        or (
                            isinstance(node.func, ast.Name)
                            and node.func.id == "ensure_table_on_init"
                        )
                    )
                    for node in ast.walk(func)
                )
                if not calls_helper:
                    offenders.append("%s:%s.%s" % (filename, class_name, func.name))

        self.assertGreater(overrides, 0, "static scan matched no init() override")
        self.assertEqual(
            offenders,
            [],
            "smart_core init() overrides must call ensure_table_on_init: %s" % offenders,
        )
