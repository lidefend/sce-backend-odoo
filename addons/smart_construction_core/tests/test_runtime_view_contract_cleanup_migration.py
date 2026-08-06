# -*- coding: utf-8 -*-
import importlib.util
import json
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "17.0.0.83"
    / "post-migration.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "smart_construction_core_17_0_0_83_post",
        MIGRATION_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("post_install", "-at_install", "runtime_view_contract")
class TestRuntimeViewContractCleanupMigration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.migration = _load_migration()
        cls.Contract = cls.env["ui.business.config.contract"].sudo().with_context(active_test=False)
        cls.view = cls.env["ir.ui.view"].create({
            "name": "runtime.cleanup.partner.tree",
            "model": "res.partner",
            "type": "tree",
            "arch": "<tree><field name='name' string='单位名称'/><field name='email' string='邮箱'/></tree>",
        })
        cls.action = cls.env["ir.actions.act_window"].create({
            "name": "Runtime cleanup partners",
            "res_model": "res.partner",
            "view_mode": "tree,form",
            "view_id": cls.view.id,
        })

    def _payload(self, columns):
        return {"view_orchestration": {"views": {"tree": {"columns": columns}}}}

    def _sql_publish(self, record, payload):
        self.env.cr.execute(
            "UPDATE ui_business_config_contract "
            "SET active=true, status='published', contract_json=%s WHERE id=%s",
            [json.dumps(payload, ensure_ascii=False), record.id],
        )
        self.env.invalidate_all()
        return self.Contract.browse(record.id)

    def _protected_fingerprint(self):
        models = (
            "project.project",
            "ir.attachment",
            "mail.message",
            "ir.rule",
            "ir.model.access",
            "sc.user.view.preference",
        )
        return {
            model: (self.env[model].sudo().search_count([]) if model in self.env else None)
            for model in models
        }

    def test_invalid_historical_contract_is_retired_atomically_and_idempotently(self):
        valid = self.Contract.create({
            "name": "runtime.cleanup.valid.survivor",
            "model": "res.partner",
            "view_type": "tree",
            "action_id": self.action.id,
            "status": "published",
            "contract_json": self._payload([
                {"name": "name", "label": "单位名称"},
                {"name": "email", "label": "邮箱"},
            ]),
        })
        invalid = self.Contract.create({
            "name": "runtime.cleanup.historical.fixture",
            "model": "res.partner",
            "view_type": "tree",
            "action_id": self.action.id,
            "active": False,
            "status": "draft",
            "contract_json": self._payload([{"name": "name", "label": "单位名称"}]),
        })
        invalid = self._sql_publish(invalid, self._payload([
            {"name": "name", "label": "单位名称"},
            {"name": "uc_formal_migration_fixture", "label": "历史过渡字段"},
        ]))
        self.env["ir.config_parameter"].sudo().set_param(self.migration.SNAPSHOT_KEY, "")
        protected_before = self._protected_fingerprint()

        self.migration.migrate(self.env.cr, "17.0.0.82")

        self.assertTrue(valid.active)
        self.assertFalse(invalid.active)
        self.assertEqual(protected_before, self._protected_fingerprint())
        snapshot_text = self.env["ir.config_parameter"].sudo().get_param(self.migration.SNAPSHOT_KEY)
        snapshot = json.loads(snapshot_text)
        self.assertEqual(snapshot["before"]["invalid_contracts"], 1)
        self.assertEqual(snapshot["after"]["retired_contracts"], 1)
        classification = snapshot["before"]["classifications"][0]
        self.assertEqual(classification["model"], "res.partner")
        self.assertIn("historical_stale_alias", classification["reason_codes"])
        self.assertIn("runtime_unknown_columns", classification["reason_codes"])
        self.assertIn("uc_formal_migration_fixture", classification["fields"])

        self.migration.migrate(self.env.cr, "17.0.0.83")
        self.assertEqual(
            snapshot_text,
            self.env["ir.config_parameter"].sudo().get_param(self.migration.SNAPSHOT_KEY),
        )
        self.assertTrue(valid.active)
        self.assertFalse(invalid.active)
        self.assertEqual(protected_before, self._protected_fingerprint())
