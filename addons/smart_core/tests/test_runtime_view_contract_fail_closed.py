# -*- coding: utf-8 -*-
import json

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "smart_core", "runtime_view_contract")
class TestRuntimeViewContractFailClosed(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.view = cls.env["ir.ui.view"].create({
            "name": "runtime.contract.partner.tree",
            "model": "res.partner",
            "type": "tree",
            "arch": "<tree><field name='name' string='单位名称'/><field name='email' string='邮箱'/></tree>",
        })
        cls.action = cls.env["ir.actions.act_window"].create({
            "name": "Runtime contract partners",
            "res_model": "res.partner",
            "view_mode": "tree,form",
            "view_id": cls.view.id,
        })
        cls.Contract = cls.env["ui.business.config.contract"].sudo().with_context(active_test=False)

    def _payload(self, columns):
        return {"view_orchestration": {"views": {"tree": {"columns": columns}}}}

    def _sql_publish(self, record, payload):
        self.env.cr.execute(
            "UPDATE ui_business_config_contract SET active=true, status=%s, contract_json=%s WHERE id=%s",
            ["published", json.dumps(payload, ensure_ascii=False), record.id],
        )
        self.env.invalidate_all()
        return self.Contract.browse(record.id)

    def test_valid_action_subset_is_effective(self):
        record = self.Contract.create({
            "name": "runtime.contract.valid.subset",
            "model": "res.partner",
            "view_type": "tree",
            "action_id": self.action.id,
            "status": "published",
            "contract_json": self._payload([
                {"name": "name", "label": "单位名称"},
                {"name": "email", "label": "邮箱"},
            ]),
        })
        effective = self.Contract._effective_view_orchestration_contracts(
            "res.partner", view_type="tree", action_id=self.action.id,
        )
        self.assertIn(record.id, [row.id for row in effective])

    def test_unknown_or_transition_alias_is_rejected_atomically(self):
        record = self.Contract.create({
            "name": "runtime.contract.invalid.alias",
            "model": "res.partner",
            "view_type": "tree",
            "action_id": self.action.id,
            "active": False,
            "status": "draft",
            "contract_json": self._payload([{"name": "name", "label": "单位名称"}]),
        })
        record = self._sql_publish(record, self._payload([
            {"name": "name", "label": "单位名称"},
            {"name": "p1_visible_negative", "label": "过渡字段"},
        ]))
        validation = record._runtime_contract_validation(
            record, requested_view_type="tree", action_id=self.action.id, model_name="res.partner",
        )
        self.assertIn("historical_stale_alias", validation["reason_codes"])
        self.assertIn("runtime_unknown_columns", validation["reason_codes"])
        effective = self.Contract._effective_view_orchestration_contracts(
            "res.partner", view_type="tree", action_id=self.action.id,
        )
        self.assertNotIn(record.id, [row.id for row in effective])

    def test_known_nonmember_cannot_be_published_or_partially_applied(self):
        with self.assertRaises(ValidationError):
            self.Contract.create({
                "name": "runtime.contract.invalid.nonmember",
                "model": "res.partner",
                "view_type": "tree",
                "action_id": self.action.id,
                "status": "published",
                "contract_json": self._payload([
                    {"name": "name", "label": "单位名称"},
                    {"name": "phone", "label": "电话"},
                ]),
            })

    def test_global_contract_is_revalidated_for_each_action_authority(self):
        alternate_view = self.env["ir.ui.view"].create({
            "name": "runtime.contract.partner.alternate.tree",
            "model": "res.partner",
            "type": "tree",
            "arch": "<tree><field name='name' string='单位名称'/></tree>",
        })
        alternate_action = self.env["ir.actions.act_window"].create({
            "name": "Runtime contract alternate partners",
            "res_model": "res.partner",
            "view_mode": "tree,form",
            "view_id": alternate_view.id,
        })
        record = self.Contract.create({
            "name": "runtime.contract.global.action.revalidation",
            "model": "res.partner",
            "view_type": "tree",
            "status": "published",
            "contract_json": self._payload([
                {"name": "name", "label": "单位名称"},
                {"name": "email", "label": "邮箱"},
            ]),
        })
        accepted = self.Contract._effective_view_orchestration_contracts(
            "res.partner", view_type="tree", action_id=self.action.id,
        )
        rejected = self.Contract._effective_view_orchestration_contracts(
            "res.partner", view_type="tree", action_id=alternate_action.id,
        )
        self.assertIn(record.id, [row.id for row in accepted])
        self.assertNotIn(record.id, [row.id for row in rejected])
