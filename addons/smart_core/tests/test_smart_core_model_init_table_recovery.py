# -*- coding: utf-8 -*-
"""P1 regression: a model overriding ``init()`` must still create its table.

``Registry.check_tables_exist`` recreates a missing table by calling only
``model.init()`` and never ``_auto_init()``.  A model whose ``init()`` only adds
extra indexes therefore leaves the table missing and the module upgrade dies
with ``UndefinedTable``.  These tests drop the real tables inside the test
transaction and re-enter the governed recovery entry, so the schema -- columns
and foreign keys included -- must come back before teardown rolls the drop back.
"""

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import SQL, table_exists

from ..core import model_table_recovery

RECOVERY_TEST_TAG = "model_init_table_recovery"

RECOVERED_MODELS = (
    "sc.contract.slo.observation",
    "sc.idempotency.record",
)


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

    def _assert_index(self, table, indexname):
        self.env.cr.execute(
            "SELECT 1 FROM pg_indexes WHERE tablename = %s AND indexname = %s",
            (table, indexname),
        )
        self.assertTrue(self.env.cr.fetchone(), "missing index %s" % indexname)

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

        self._assert_foreign_key(
            "sc_contract_slo_observation", "company_id", "res_company", "id"
        )
        self._assert_foreign_key(
            "sc_idempotency_record", "company_id", "res_company", "id"
        )
        self._assert_foreign_key(
            "sc_idempotency_record", "actor_uid", "res_users", "id"
        )
        self._assert_index(
            "sc_contract_slo_observation", "sc_contract_slo_observation_version_time"
        )
        self._assert_index(
            "sc_idempotency_record", "sc_idempotency_record_key_unique"
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
