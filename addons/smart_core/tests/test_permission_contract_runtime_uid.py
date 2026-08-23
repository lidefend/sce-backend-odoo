# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler


@tagged("post_install", "-at_install", "perm_runtime_uid")
class TestPermissionContractRuntimeUid(TransactionCase):
    def test_record_rule_projection_preserves_global_and_group_algebra(self):
        model = self.env["ir.model"]._get("res.partner")
        group = self.env.ref("base.group_user")
        global_rule = self.env["ir.rule"].sudo().create({
            "name": "Global partner company boundary",
            "model_id": model.id,
            "domain_force": "[('company_id', 'in', company_ids)]",
            "perm_read": True,
        })
        group_rule = self.env["ir.rule"].sudo().create({
            "name": "Grouped partner ownership boundary",
            "model_id": model.id,
            "domain_force": "[('user_id', '=', user.id)]",
            "groups": [(6, 0, [group.id])],
            "perm_read": True,
        })

        rules = self.env["app.permission.config"]._collect_record_rules("res.partner")["read"]

        self.assertEqual(rules["mode"], "GLOBAL_AND_GROUP_OR")
        self.assertIn(global_rule.id, {row["id"] for row in rules["global_clauses"]})
        self.assertIn(group_rule.id, {row["id"] for row in rules["group_clauses"]})
        global_row = next(row for row in rules["global_clauses"] if row["id"] == global_rule.id)
        self.assertFalse(global_row["domain_decoded"])
        self.assertIsNone(global_row["domain"])

    def test_page_assembler_uses_runtime_user_for_effective_permissions(self):
        company = self.env.ref("base.main_company")
        manager_group = self.env.ref("smart_construction_core.group_sc_cap_project_manager")
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "perm.runtime.project.manager",
                "login": "perm.runtime.project.manager",
                "email": "perm.runtime.project.manager@example.com",
                "company_id": company.id,
                "company_ids": [(6, 0, [company.id])],
                "groups_id": [(6, 0, [manager_group.id])],
            }
        )

        user_env = api.Environment(self.env.cr, user.id, dict(self.env.context or {}))
        su_env = api.Environment(self.env.cr, SUPERUSER_ID, dict(self.env.context or {}))
        payload = {"model": "sc.project.stage.requirement.item", "view_types": ["form"]}

        data, _versions = PageAssembler(user_env, su_env).assemble_page_contract(payload)
        effective = ((data.get("permissions") or {}).get("effective") or {}).get("rights") or {}

        self.assertTrue(effective.get("read"), effective)
        self.assertTrue(effective.get("write"), effective)
        self.assertTrue(effective.get("create"), effective)
        self.assertTrue(effective.get("unlink"), effective)

    def test_record_rule_without_xmlid_group_remains_group_scoped(self):
        model = self.env["ir.model"]._get("res.partner")
        group = self.env["res.groups"].sudo().create({"name": "No XMLID permission boundary group"})
        rule = self.env["ir.rule"].sudo().create({
            "name": "No XMLID grouped partner rule",
            "model_id": model.id,
            "domain_force": "[('id', '>', 0)]",
            "groups": [(6, 0, [group.id])],
            "perm_read": True,
        })

        rows = self.env["app.permission.config"]._collect_record_rules("res.partner")["read"]
        projected = next(row for row in rows["group_clauses"] if row["id"] == rule.id)

        self.assertFalse(projected["global"])
        self.assertEqual(projected["groups_ids"], [group.id])
        self.assertEqual(projected["groups_xmlids"], [])
