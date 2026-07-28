# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.core.project_context import business_scope_meta
from odoo.addons.smart_core.handlers.api_data import ApiDataHandler


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestAdminVisP3ProjectRecordRuleOrm(TransactionCase):
    """Real-ORM acceptance for caller-scoped project strategy lookup."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        base_user = cls.env.ref("base.group_user")
        project_read = cls.env.ref("smart_construction_core.group_sc_cap_project_read")
        cls.ordinary_user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "ADMIN_VIS_P3 ordinary project reader",
                "login": "admin_vis_p3_project_reader",
                "email": "admin_vis_p3_project_reader@example.invalid",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "groups_id": [(6, 0, [base_user.id, project_read.id])],
            }
        )
        project_context = dict(
            cls.env.context,
            allowed_company_ids=[cls.company.id],
            mail_create_nosubscribe=True,
            mail_notify_noemail=True,
            mail_auto_subscribe_no_notify=True,
            tracking_disable=True,
        )
        Project = cls.env["project.project"].with_context(project_context)
        common_values = {
            "company_id": cls.company.id,
            "privacy_visibility": "followers",
        }
        cls.authorized_project = Project.create(
            {
                **common_values,
                "name": "ADMIN_VIS_P3 authorized project",
                "user_id": cls.ordinary_user.id,
                "operation_strategy": "direct",
            }
        )
        cls.unauthorized_direct_project = Project.create(
            {
                **common_values,
                "name": "ADMIN_VIS_P3 unauthorized direct project",
                "user_id": cls.env.user.id,
                "operation_strategy": "direct",
            }
        )
        cls.unauthorized_joint_project = Project.create(
            {
                **common_values,
                "name": "ADMIN_VIS_P3 unauthorized joint project",
                "user_id": cls.env.user.id,
                "operation_strategy": "joint",
            }
        )
        cls.nonexistent_project_id = max(
            cls.authorized_project.id,
            cls.unauthorized_direct_project.id,
            cls.unauthorized_joint_project.id,
        ) + 1000000
        cls.caller_env = cls.env(
            user=cls.ordinary_user,
            context={
                **cls.env.context,
                "allowed_company_ids": [cls.company.id],
                "tracking_disable": True,
            },
        )
        cls.caller_project_model = cls.caller_env["project.project"]
        cls.caller_scope_model = cls.caller_env["project.task"]
        cls.contract_tax_group = cls.env["account.tax.group"].search(
            [("name", "=", "合同税率")],
            limit=1,
        )
        if not cls.contract_tax_group:
            cls.contract_tax_group = cls.env["account.tax.group"].create(
                {"name": "合同税率"}
            )

    def _scope_meta(self, project_id, operation_strategy):
        return business_scope_meta(
            self.caller_scope_model,
            {
                "company_id": self.company.id,
                "project_id": project_id,
                "operation_strategy": operation_strategy,
            },
            applied_domain=[],
        )

    def _denial_observation(self, project_id):
        with self.assertRaises(AccessError) as caught:
            self._scope_meta(project_id, "direct")
        return type(caught.exception), str(caught.exception)

    def _account_tax_quick_create_vals(self):
        return {
            "name": "ADMIN_VIS_P3 contract tax",
            "type_tax_use": "none",
            "amount_type": "percent",
            "amount": 3.0,
            "price_include": False,
            "tax_group_id": self.contract_tax_group.id,
        }

    def _authorize_account_tax_then_policy(self, project_id, operation_strategy):
        params = {
            "company_id": self.company.id,
            "project_id": project_id,
            "operation_strategy": operation_strategy,
        }
        handler = ApiDataHandler(self.caller_env)
        context = handler._request_context(params)
        caller_model, meta = handler._authorize_account_tax_create_scope(
            params,
            context,
        )
        policy = handler._create_execution_policy(
            "account.tax",
            self._account_tax_quick_create_vals(),
            context,
            params,
        )
        return caller_model, meta, policy

    def test_authorized_project_metadata_contract(self):
        self.assertFalse(self.ordinary_user.has_group("base.group_system"))
        self.assertTrue(self.caller_project_model.check_access_rights("read"))
        visible = self.caller_project_model.search(
            [("id", "=", self.authorized_project.id)],
            limit=1,
        )
        self.assertEqual(visible, self.authorized_project)

        meta = self._scope_meta(self.authorized_project.id, "direct")

        self.assertEqual(meta["project_id"], self.authorized_project.id)
        self.assertEqual(meta["record_context_id"], self.authorized_project.id)
        self.assertEqual(meta["operation_strategy"], "direct")
        self.assertEqual(meta["project_operation_strategy"], "direct")
        self.assertIs(meta["project_operation_strategy_mismatch"], False)
        self.assertIs(type(meta["project_id"]), int)
        self.assertIs(type(meta["operation_strategy"]), str)
        self.assertIs(type(meta["project_operation_strategy"]), str)

    def test_unauthorized_strategy_variation_and_nonexistent_are_equivalent(self):
        for project in (
            self.unauthorized_direct_project,
            self.unauthorized_joint_project,
        ):
            self.assertTrue(self.env["project.project"].browse(project.id).exists())
            self.assertFalse(
                self.caller_project_model.search([("id", "=", project.id)], limit=1)
            )

        direct_denial = self._denial_observation(self.unauthorized_direct_project.id)
        joint_denial = self._denial_observation(self.unauthorized_joint_project.id)
        nonexistent_denial = self._denial_observation(self.nonexistent_project_id)

        self.assertEqual(direct_denial, joint_denial)
        self.assertEqual(direct_denial, nonexistent_denial)
        self.assertEqual(direct_denial[1], "当前项目不存在或无权访问")

    def test_authorized_strategy_mismatch_is_preserved(self):
        meta = self._scope_meta(self.authorized_project.id, "joint")

        self.assertEqual(meta["operation_strategy"], "joint")
        self.assertEqual(meta["project_operation_strategy"], "direct")
        self.assertIs(meta["project_operation_strategy_mismatch"], True)

    def test_no_project_fallback_contract_is_preserved(self):
        meta = business_scope_meta(
            self.caller_scope_model,
            {
                "company_id": self.company.id,
                "project_id": 0,
                "operation_strategy": "",
            },
            applied_domain=[],
        )

        self.assertIsNone(meta["project_id"])
        self.assertIsNone(meta["record_context_id"])
        self.assertEqual(meta["operation_strategy"], "")
        self.assertEqual(meta["project_operation_strategy"], "")
        self.assertIs(meta["project_operation_strategy_mismatch"], False)

    def test_account_tax_policy_sudo_is_only_selected_after_authorized_scope(self):
        caller_model, meta, policy = self._authorize_account_tax_then_policy(
            self.authorized_project.id,
            "direct",
        )

        self.assertEqual(caller_model.env.uid, self.ordinary_user.id)
        self.assertFalse(caller_model.env.su)
        self.assertEqual(meta["project_id"], self.authorized_project.id)
        self.assertEqual(meta["project_operation_strategy"], "direct")
        self.assertFalse(meta["project_operation_strategy_mismatch"])
        self.assertTrue(policy["allowed"])
        self.assertTrue(policy["sudo"])
        self.assertTrue(caller_model.sudo().env.su)

    def test_account_tax_unauthorized_and_nonexistent_stop_before_policy(self):
        observations = []
        for project_id in (
            self.unauthorized_direct_project.id,
            self.unauthorized_joint_project.id,
            self.nonexistent_project_id,
        ):
            with self.assertRaises(AccessError) as caught:
                self._authorize_account_tax_then_policy(project_id, "direct")
            observations.append((type(caught.exception), str(caught.exception)))

        self.assertEqual(observations[0], observations[1])
        self.assertEqual(observations[0], observations[2])
        self.assertEqual(observations[0][1], "当前项目不存在或无权访问")
