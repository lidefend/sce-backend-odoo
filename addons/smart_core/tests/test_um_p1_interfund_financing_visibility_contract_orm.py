# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestUmP1InterfundFinancingVisibilityContractOrm(TransactionCase):
    """Real-ORM evidence for company-scoped fund and financing ledgers."""

    MODELS = ("sc.fund.account.operation", "sc.financing.loan")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create({"name": "UM-P1 S05 Company B"})
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
            "UM-P1 S05 finance user",
            "um_p1_s05_finance_user",
            finance_user,
        )
        cls.finance_manager = create_user(
            "UM-P1 S05 finance manager",
            "um_p1_s05_finance_manager",
            finance_manager,
        )
        cls.non_finance_user = create_user(
            "UM-P1 S05 business initiator",
            "um_p1_s05_business_initiator",
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
        cls.project_a = Project.create(
            {
                **project_values,
                "name": "UM-P1 S05 Company A project",
                "company_id": cls.company_a.id,
                "user_id": cls.finance_user.id,
            }
        )
        cls.shared_project_a = Project.create(
            {
                **project_values,
                "name": "UM-P1 S05 shared Company A project",
                "company_id": cls.company_a.id,
                "user_id": cls.env.user.id,
            }
        )
        cls.secondary_visible_project_a = Project.create(
            {
                **project_values,
                "name": "UM-P1 S05 secondary caller-visible Company A project",
                "company_id": cls.company_a.id,
                "user_id": cls.finance_user.id,
            }
        )
        cls.project_b = Project.create(
            {
                **project_values,
                "name": "UM-P1 S05 Company B project",
                "company_id": cls.company_b.id,
                "user_id": cls.env.user.id,
            }
        )
        cls.account_a = cls.env["sc.fund.account"].with_context(
            setup_context
        ).create(
            {
                "name": "UM-P1 S05 Company A account",
                "company_id": cls.company_a.id,
            }
        )
        cls.account_b = cls.env["sc.fund.account"].with_context(
            setup_context
        ).create(
            {
                "name": "UM-P1 S05 Company B account",
                "company_id": cls.company_b.id,
            }
        )

        cls.records = {
            "company_a": {
                "sc.fund.account.operation": cls._create_fund_operation(
                    cls.env,
                    cls.company_a,
                    cls.account_a,
                    project=cls.project_a,
                    label="company A",
                ),
                "sc.financing.loan": cls._create_financing_loan(
                    cls.env,
                    cls.project_a,
                    label="company A",
                ),
            },
            "shared_company_a": {
                "sc.fund.account.operation": cls._create_fund_operation(
                    cls.env,
                    cls.company_a,
                    cls.account_a,
                    project=False,
                    label="shared company A no project",
                ),
                "sc.financing.loan": cls._create_financing_loan(
                    cls.env,
                    cls.shared_project_a,
                    label="shared company A",
                ),
            },
            "company_b": {
                "sc.fund.account.operation": cls._create_fund_operation(
                    cls.env,
                    cls.company_b,
                    cls.account_b,
                    project=cls.project_b,
                    label="company B",
                ),
                "sc.financing.loan": cls._create_financing_loan(
                    cls.env,
                    cls.project_b,
                    label="company B",
                ),
            },
        }
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

    @classmethod
    def _create_fund_operation(
        cls,
        env,
        company,
        account,
        *,
        project,
        label,
    ):
        values = {
            "name": f"UM-P1 S05 {label} fund operation",
            "operation_type": "balance_adjustment",
            "company_id": company.id,
            "fund_account_id": account.id,
            "before_balance": 0,
            "after_balance": 1,
            "operation_reason": label,
        }
        if project:
            values["project_id"] = project.id
        return env["sc.fund.account.operation"].create(values)

    @classmethod
    def _create_financing_loan(cls, env, project, *, label):
        return env["sc.financing.loan"].create(
            {
                "name": f"UM-P1 S05 {label} financing loan",
                "project_id": project.id,
                "amount": 1,
            }
        )

    def test_finance_user_reads_all_allowed_company_records_only(self):
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
                    self.records["company_a"][model_name].id,
                    self.records["shared_company_a"][model_name].id,
                },
            )

    def test_finance_user_creates_and_writes_only_allowed_company_records(self):
        fund_operation = self._create_fund_operation(
            self.finance_env,
            self.company_a,
            self.account_a,
            project=False,
            label="finance create without project",
        )
        self.assertFalse(fund_operation.project_id)
        fund_operation.write({"project_id": self.project_a.id})
        with self.assertRaises(AccessError):
            fund_operation.write({"project_id": self.project_b.id})
        with self.assertRaises(AccessError):
            self._create_fund_operation(
                self.finance_env,
                self.company_b,
                self.account_b,
                project=False,
                label="forged cross company",
            )

        financing_loan = self._create_financing_loan(
            self.finance_env,
            self.project_a,
            label="finance create",
        )
        financing_loan.write({"project_id": self.secondary_visible_project_a.id})
        with self.assertRaises(AccessError):
            financing_loan.write({"project_id": self.project_b.id})
        with self.assertRaises(AccessError):
            self._create_financing_loan(
                self.finance_env,
                self.project_b,
                label="forged cross company",
            )

    def test_fund_project_and_company_must_match(self):
        with self.assertRaises(AccessError):
            self._create_fund_operation(
                self.finance_env,
                self.company_a,
                self.account_a,
                project=self.project_b,
                label="mismatched project company",
            )

    def test_non_finance_acl_does_not_open_company_ledgers(self):
        for model_name in self.MODELS:
            record = self.records["company_a"][model_name]
            self.assertFalse(
                self.non_finance_env[model_name].search(
                    [("id", "=", record.id)],
                    limit=1,
                )
            )
            with self.assertRaises(AccessError):
                self.non_finance_env[model_name].browse(record.id).read(["id"])

    def test_allowed_company_context_cannot_be_forged(self):
        forged_context = {
            **self.finance_env.context,
            "allowed_company_ids": [self.company_b.id],
        }
        with self.assertRaises(AccessError):
            self.env(user=self.finance_user, context=forged_context).companies

    def test_manager_delete_respects_company_boundary(self):
        disposable = {
            "sc.fund.account.operation": self._create_fund_operation(
                self.env,
                self.company_a,
                self.account_a,
                project=False,
                label="manager delete",
            ),
            "sc.financing.loan": self._create_financing_loan(
                self.env,
                self.project_a,
                label="manager delete",
            ),
        }
        for model_name, record in disposable.items():
            self.manager_env[model_name].browse(record.id).unlink()
            self.assertFalse(self.env[model_name].browse(record.id).exists())
            with self.assertRaises(AccessError):
                self.manager_env[model_name].browse(
                    self.records["company_b"][model_name].id
                ).unlink()

    def test_direct_read_and_search_hide_cross_company_records(self):
        for model_name in self.MODELS:
            cross_company_id = self.records["company_b"][model_name].id
            with self.assertRaises(AccessError):
                self.finance_env[model_name].browse(cross_company_id).read(["id"])
            observations = []
            for record_id in (cross_company_id, self.nonexistent_ids[model_name]):
                result = self.finance_env[model_name].search(
                    [("id", "=", record_id)],
                    limit=1,
                )
                observations.append((bool(result), len(result)))
            self.assertEqual(observations, [(False, 0), (False, 0)])

    def test_no_scope_search_does_not_fall_back_to_all_companies(self):
        for model_name in self.MODELS:
            visible = self.finance_env[model_name].search([])
            self.assertIn(self.records["company_a"][model_name], visible)
            self.assertIn(self.records["shared_company_a"][model_name], visible)
            self.assertNotIn(self.records["company_b"][model_name], visible)

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
