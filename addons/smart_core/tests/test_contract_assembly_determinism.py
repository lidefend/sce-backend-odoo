# -*- coding: utf-8 -*-
"""Contract assembly kernel determinism: same frozen input, same output.

The precondition for any reproducible baseline is that the three authoritative
entry points project identical output for identical input. Each test runs the
same entry point twice on frozen fixtures and compares canonical JSON.
"""
import json

from odoo.tests.common import TransactionCase, tagged


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


@tagged("post_install", "-at_install", "contract_assembly_determinism")
class TestContractAssemblyDeterminism(TransactionCase):
    def test_model_config_is_deterministic_given_frozen_snapshot(self):
        snapshot = {
            "x_locked_note": {
                "type": "char",
                "string": "Locked note",
                "required": False,
                "readonly": True,
                "help": "",
            },
            "name": {"type": "char", "string": "Name", "required": True, "readonly": False, "help": ""},
        }
        first = self.env["app.model.config"].with_context(
            contract_projection_readonly=True,
        )._generate_from_ir_model("res.partner", fields_get_snapshot=snapshot)
        second = self.env["app.model.config"].with_context(
            contract_projection_readonly=True,
        )._generate_from_ir_model("res.partner", fields_get_snapshot=snapshot)
        self.assertEqual(_canonical(first.fields_def), _canonical(second.fields_def))

    def test_view_config_is_deterministic_given_frozen_view_data(self):
        view = self.env["ir.ui.view"].sudo().create({
            "name": "contract assembly determinism partner form",
            "model": "res.partner",
            "type": "form",
            "arch": (
                "<form><sheet><group>"
                '<field name="active" invisible="1"/>'
                '<field name="name"/>'
                '<field name="phone" readonly="not active"/>'
                "</group></sheet></form>"
            ),
        })
        view_data = self.env["res.partner"].sudo().get_view(
            view_id=view.id,
            view_type="form",
        )
        first = self.env["app.view.config"].with_context(
            contract_view_id=view.id,
            contract_projection_readonly=True,
        )._generate_from_fields_view_get("res.partner", "form", view_data=view_data)
        second = self.env["app.view.config"].with_context(
            contract_view_id=view.id,
            contract_projection_readonly=True,
        )._generate_from_fields_view_get("res.partner", "form", view_data=view_data)
        self.assertEqual(_canonical(first.arch_parsed), _canonical(second.arch_parsed))

    def test_permission_config_is_deterministic_given_explicit_rules(self):
        model = self.env["ir.model"]._get("res.partner")
        group = self.env.ref("base.group_user")
        self.env["ir.rule"].sudo().create({
            "name": "Contract assembly determinism partner rule",
            "model_id": model.id,
            "domain_force": "[('company_id', 'in', company_ids)]",
            "perm_read": True,
            "groups": [(6, 0, [group.id])],
        })
        first = self.env["app.permission.config"]._collect_record_rules("res.partner")
        second = self.env["app.permission.config"]._collect_record_rules("res.partner")
        self.assertEqual(_canonical(first), _canonical(second))
