# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "site_variation")
class TestProjectSiteVariationEntry(TransactionCase):
    def _user(self, login, group_xmlid):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@invalid.local",
                "groups_id": [
                    (
                        6,
                        0,
                        [self.env.ref("base.group_user").id, self.env.ref(group_xmlid).id],
                    )
                ],
            }
        )

    def test_project_entry_reuses_settlement_fact_and_preserves_write_capability(self):
        project_user = self._user(
            "site_variation_project_user",
            "smart_construction_core.group_sc_cap_project_user",
        )
        settlement_user = self._user(
            "site_variation_settlement_user",
            "smart_construction_core.group_sc_cap_settlement_user",
        )
        project = self.env["project.project"].create({"name": "签证入口测试项目"})
        adjustment = self.env["sc.settlement.adjustment"].create(
            {
                "project_id": project.id,
                "item_name": "现场签证测试",
                "amount": 100,
            }
        )

        self.assertEqual(
            adjustment.with_user(project_user).read(["item_name"])[0]["item_name"],
            "现场签证测试",
        )
        with self.assertRaises(AccessError):
            adjustment.with_user(project_user).write({"note": "项目用户不得绕过结算能力写入"})

        adjustment.with_user(settlement_user).write({"note": "结算经办可办理"})
        self.assertEqual(adjustment.note, "结算经办可办理")

        action = self.env.ref(
            "smart_construction_core.action_sc_product_site_variation_v1"
        )
        self.assertEqual(action.res_model, "sc.settlement.adjustment")
        self.assertIn("search_default_group_project", action.context)
        self.assertIn("sc_project_context_entry", action.context)
