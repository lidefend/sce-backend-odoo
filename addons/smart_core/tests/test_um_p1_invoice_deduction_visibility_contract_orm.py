# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestUmP1InvoiceDeductionVisibilityContractOrm(TransactionCase):
    """Real-ORM evidence for company-shared finance ledger visibility."""

    MODELS = ("sc.invoice.registration", "sc.tax.deduction.registration")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create({"name": "UM-P1 S04 Company B"})
        base_user = cls.env.ref("base.group_user")
        finance_user = cls.env.ref("smart_construction_core.group_sc_role_finance_user")
        finance_manager = cls.env.ref(
            "smart_construction_core.group_sc_role_finance_manager"
        )
        business_initiator = cls.env.ref(
            "smart_construction_core.group_sc_cap_business_initiator"
        )

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

        cls.finance_user = create_user(
            "UM-P1 S04 finance user",
            "um_p1_s04_finance_user",
            finance_user,
        )
        cls.finance_manager = create_user(
            "UM-P1 S04 finance manager",
            "um_p1_s04_finance_manager",
            finance_manager,
        )
        cls.non_finance_user = create_user(
            "UM-P1 S04 business initiator",
            "um_p1_s04_business_initiator",
            business_initiator,
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
                "name": "UM-P1 S04 authorized company A project",
                "company_id": cls.company_a.id,
                "user_id": cls.finance_user.id,
            }
        )
        cls.shared_company_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S04 shared company A project",
                "company_id": cls.company_a.id,
                "user_id": cls.env.user.id,
            }
        )
        cls.cross_company_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S04 company B project",
                "company_id": cls.company_b.id,
                "user_id": cls.env.user.id,
            }
        )

        cls.records = {}
        for key, project in (
            ("authorized", cls.authorized_project),
            ("shared_company", cls.shared_company_project),
            ("cross_company", cls.cross_company_project),
        ):
            cls.records[key] = {}
            for model_name in cls.MODELS:
                cls.records[key][model_name] = (
                    cls.env[model_name]
                    .with_context(setup_context)
                    .create(
                        {
                            "name": f"UM-P1 S04 {key} {model_name}",
                            "project_id": project.id,
                        }
                    )
                )

        cls.nonexistent_ids = {
            model_name: max(
                cls.records[key][model_name].id for key in cls.records
            )
            + 1000000
            for model_name in cls.MODELS
        }
        caller_context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company_a.id],
            "tracking_disable": True,
        }
        cls.finance_env = cls.env(user=cls.finance_user, context=caller_context)
        cls.manager_env = cls.env(user=cls.finance_manager, context=caller_context)
        cls.non_finance_env = cls.env(
            user=cls.non_finance_user,
            context=caller_context,
        )

    def test_finance_user_reads_shared_company_ledgers_not_cross_company(self):
        for model_name in self.MODELS:
            visible = self.finance_env[model_name].search(
                [
                    (
                        "id",
                        "in",
                        [self.records[key][model_name].id for key in self.records],
                    )
                ]
            )
            self.assertEqual(
                set(visible.ids),
                {
                    self.records["authorized"][model_name].id,
                    self.records["shared_company"][model_name].id,
                },
            )

    def test_finance_user_can_create_and_write_only_caller_visible_projects(self):
        for model_name in self.MODELS:
            created = self.finance_env[model_name].create(
                {
                    "name": f"UM-P1 S04 finance create {model_name}",
                    "project_id": self.authorized_project.id,
                }
            )
            self.assertEqual(created.company_id, self.company_a)
            created.write({"project_id": self.authorized_project.id})
            with self.assertRaises(AccessError):
                created.write({"project_id": self.cross_company_project.id})

    def test_non_finance_business_initiator_acl_does_not_open_ledger(self):
        for model_name in self.MODELS:
            self.assertFalse(
                self.non_finance_env[model_name].search(
                    [("id", "=", self.records["authorized"][model_name].id)],
                    limit=1,
                )
            )
            with self.assertRaises(AccessError):
                self.non_finance_env[model_name].browse(
                    self.records["authorized"][model_name].id
                ).read(["id"])

    def test_cross_company_context_cannot_be_forged(self):
        forged_context = {
            **self.finance_env.context,
            "allowed_company_ids": [self.company_b.id],
        }
        with self.assertRaises(AccessError):
            self.env(user=self.finance_user, context=forged_context).companies

    def test_manager_can_delete_same_company_but_not_cross_company(self):
        for model_name in self.MODELS:
            disposable = self.env[model_name].create(
                {
                    "name": f"UM-P1 S04 manager delete {model_name}",
                    "project_id": self.authorized_project.id,
                }
            )
            self.manager_env[model_name].browse(disposable.id).unlink()
            self.assertFalse(self.env[model_name].browse(disposable.id).exists())
            with self.assertRaises(AccessError):
                self.manager_env[model_name].browse(
                    self.records["cross_company"][model_name].id
                ).unlink()

    def test_unauthorized_and_nonexistent_searches_are_equivalent(self):
        for model_name in self.MODELS:
            observations = []
            for record_id in (
                self.records["cross_company"][model_name].id,
                self.nonexistent_ids[model_name],
            ):
                result = self.finance_env[model_name].search(
                    [("id", "=", record_id)],
                    limit=1,
                )
                observations.append((bool(result), len(result)))
            self.assertEqual(observations, [(False, 0), (False, 0)])

    def test_direct_cross_company_reads_are_rejected(self):
        for model_name in self.MODELS:
            with self.assertRaises(AccessError):
                self.finance_env[model_name].browse(
                    self.records["cross_company"][model_name].id
                ).read(["id"])

    def test_no_scope_search_does_not_fall_back_to_all_companies(self):
        for model_name in self.MODELS:
            visible = self.finance_env[model_name].search([])
            self.assertIn(self.records["authorized"][model_name], visible)
            self.assertIn(self.records["shared_company"][model_name], visible)
            self.assertNotIn(self.records["cross_company"][model_name], visible)

    def test_superuser_administrator_contract_is_unchanged(self):
        for model_name in self.MODELS:
            visible = self.env[model_name].search(
                [
                    (
                        "id",
                        "in",
                        [self.records[key][model_name].id for key in self.records],
                    )
                ]
            )
            self.assertEqual(
                set(visible.ids),
                {self.records[key][model_name].id for key in self.records},
            )
