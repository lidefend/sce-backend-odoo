# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestUmP1PaymentVisibilityContractOrm(TransactionCase):
    """Real-ORM evidence for the second document-order UM-P1 entry."""

    MODELS = ("payment.request", "sc.payment.execution")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create({"name": "UM-P1 S03 Company B"})
        base_user = cls.env.ref("base.group_user")
        finance_read = cls.env.ref("smart_construction_core.group_sc_cap_finance_read")
        finance_manager = cls.env.ref("smart_construction_core.group_sc_cap_finance_manager")

        def create_user(name, login, group):
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": name,
                    "login": login,
                    "email": f"{login}@example.invalid",
                    "company_id": cls.company_a.id,
                    "company_ids": [(6, 0, [cls.company_a.id])],
                    "groups_id": [(6, 0, [base_user.id, group.id])],
                }
            )

        cls.ordinary_user = create_user(
            "UM-P1 S03 ordinary finance reader",
            "um_p1_s03_ordinary",
            finance_read,
        )
        cls.manager_user = create_user(
            "UM-P1 S03 finance manager",
            "um_p1_s03_manager",
            finance_manager,
        )
        setup_context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company_a.id, cls.company_b.id],
            "mail_create_nosubscribe": True,
            "mail_notify_noemail": True,
            "mail_auto_subscribe_no_notify": True,
            "tracking_disable": True,
        }
        Project = cls.env["project.project"].with_context(setup_context)
        project_values = {"privacy_visibility": "followers"}
        cls.authorized_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S03 authorized project",
                "company_id": cls.company_a.id,
                "user_id": cls.ordinary_user.id,
            }
        )
        cls.unauthorized_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S03 unauthorized project",
                "company_id": cls.company_a.id,
                "user_id": cls.env.user.id,
            }
        )
        cls.cross_company_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S03 cross-company project",
                "company_id": cls.company_b.id,
                "user_id": cls.env.user.id,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "UM-P1 S03 synthetic payment partner"}
        )

        cls.records = {}
        for key, project, amount in (
            ("authorized", cls.authorized_project, 101.0),
            ("unauthorized", cls.unauthorized_project, 202.0),
            ("cross_company", cls.cross_company_project, 303.0),
        ):
            request = cls.env["payment.request"].with_context(setup_context).create(
                {
                    "type": "pay",
                    "project_id": project.id,
                    "partner_id": cls.partner.id,
                    "amount": amount,
                }
            )
            execution = cls.env["sc.payment.execution"].with_context(setup_context).create(
                {
                    "project_id": project.id,
                    "partner_id": cls.partner.id,
                    "payment_request_id": request.id,
                    "planned_amount": amount,
                    "paid_amount": amount,
                }
            )
            cls.records[key] = {
                "payment.request": request,
                "sc.payment.execution": execution,
            }

        cls.nonexistent_ids = {
            model_name: max(cls.records[key][model_name].id for key in cls.records) + 1000000
            for model_name in cls.MODELS
        }
        caller_context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company_a.id],
            "tracking_disable": True,
        }
        cls.ordinary_env = cls.env(user=cls.ordinary_user, context=caller_context)
        cls.manager_env = cls.env(user=cls.manager_user, context=caller_context)

    def test_authorized_ordinary_user_sees_only_personal_project_records(self):
        for model_name in self.MODELS:
            visible = self.ordinary_env[model_name].search(
                [
                    (
                        "id",
                        "in",
                        [self.records[key][model_name].id for key in self.records],
                    )
                ]
            )
            self.assertEqual(visible, self.records["authorized"][model_name])

    def test_unauthorized_cross_company_and_nonexistent_are_observably_equivalent(self):
        for model_name in self.MODELS:
            observations = []
            for record_id in (
                self.records["unauthorized"][model_name].id,
                self.records["cross_company"][model_name].id,
                self.nonexistent_ids[model_name],
            ):
                result = self.ordinary_env[model_name].search(
                    [("id", "=", record_id)],
                    limit=1,
                )
                observations.append((bool(result), len(result)))
            self.assertEqual(observations, [(False, 0), (False, 0), (False, 0)])

    def test_finance_manager_is_limited_by_company_not_project_membership(self):
        for model_name in self.MODELS:
            same_company = self.manager_env[model_name].search(
                [
                    (
                        "id",
                        "in",
                        [
                            self.records["authorized"][model_name].id,
                            self.records["unauthorized"][model_name].id,
                        ],
                    )
                ]
            )
            cross_company = self.manager_env[model_name].search(
                [("id", "=", self.records["cross_company"][model_name].id)],
                limit=1,
            )
            self.assertEqual(
                set(same_company.ids),
                {
                    self.records["authorized"][model_name].id,
                    self.records["unauthorized"][model_name].id,
                },
            )
            self.assertFalse(cross_company)

    def test_direct_unauthorized_reads_are_rejected(self):
        for model_name in self.MODELS:
            with self.assertRaises(AccessError):
                self.ordinary_env[model_name].browse(
                    self.records["unauthorized"][model_name].id
                ).read(["id"])

    def test_no_scope_search_keeps_personal_visibility_rules(self):
        for model_name in self.MODELS:
            visible = self.ordinary_env[model_name].search([])
            self.assertIn(self.records["authorized"][model_name], visible)
            self.assertNotIn(self.records["unauthorized"][model_name], visible)
            self.assertNotIn(self.records["cross_company"][model_name], visible)
