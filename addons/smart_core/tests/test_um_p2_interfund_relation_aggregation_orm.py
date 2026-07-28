# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestUmP2InterfundRelationAggregationOrm(TransactionCase):
    """Real-ORM evidence for account, project and counterparty aggregation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create(
            {"name": "UM-P2 S03 company B"}
        )
        base_user = cls.env.ref("base.group_user")
        finance_user = cls.env.ref(
            "smart_construction_core.group_sc_role_finance_user"
        )
        cls.caller = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "UM-P2 S03 finance user",
                "login": "um_p2_s03_finance_user",
                "email": "um_p2_s03@example.invalid",
                "company_id": cls.company_a.id,
                "company_ids": [(6, 0, [cls.company_a.id])],
                "groups_id": [(6, 0, [base_user.id, finance_user.id])],
            }
        )
        cls.context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company_a.id, cls.company_b.id],
            "mail_create_nosubscribe": True,
            "mail_notify_noemail": True,
            "mail_auto_subscribe_no_notify": True,
            "tracking_disable": True,
        }
        Project = cls.env["project.project"].with_context(cls.context)
        cls.project_a1 = Project.create(
            {
                "name": "UM-P2 S03 project A1",
                "company_id": cls.company_a.id,
                "privacy_visibility": "followers",
                "user_id": cls.caller.id,
            }
        )
        cls.project_a2 = Project.create(
            {
                "name": "UM-P2 S03 project A2",
                "company_id": cls.company_a.id,
                "privacy_visibility": "followers",
                "user_id": cls.caller.id,
            }
        )
        cls.project_b = Project.create(
            {
                "name": "UM-P2 S03 project B",
                "company_id": cls.company_b.id,
                "privacy_visibility": "followers",
                "user_id": cls.env.user.id,
            }
        )
        Account = cls.env["sc.fund.account"].with_context(cls.context)
        cls.account_a1 = Account.create(
            {
                "name": "UM-P2 S03 project A1 account",
                "company_id": cls.company_a.id,
                "project_id": cls.project_a1.id,
            }
        )
        cls.account_a2 = Account.create(
            {
                "name": "UM-P2 S03 project A2 account",
                "company_id": cls.company_a.id,
                "project_id": cls.project_a2.id,
            }
        )
        cls.account_a1_secondary = Account.create(
            {
                "name": "UM-P2 S03 second A1 account",
                "company_id": cls.company_a.id,
                "project_id": cls.project_a1.id,
            }
        )
        cls.company_account_a = Account.create(
            {
                "name": "UM-P2 S03 company A account",
                "company_id": cls.company_a.id,
            }
        )
        cls.account_b = Account.create(
            {
                "name": "UM-P2 S03 company B account",
                "company_id": cls.company_b.id,
                "project_id": cls.project_b.id,
            }
        )
        cls.mismatched_account = Account.create(
            {
                "name": "UM-P2 S03 mismatched project account",
                "company_id": cls.company_a.id,
                "project_id": cls.project_b.id,
            }
        )
        caller_context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company_a.id],
            "tracking_disable": True,
        }
        cls.caller_env = cls.env(user=cls.caller, context=caller_context)

    def _transfer(self, source, target, label):
        return self.caller_env["sc.fund.account.operation"].create(
            {
                "name": f"UM-P2 S03 {label}",
                "operation_type": "transfer_between",
                "company_id": self.company_a.id,
                "project_id": source.project_id.id or target.project_id.id,
                "source_account_id": source.id,
                "target_account_id": target.id,
                "amount": 10,
                "operation_reason": label,
            }
        )

    def _fact(self, operation):
        return self.env["sc.interfund.movement.fact"].search(
            [
                ("source_model", "=", operation._name),
                ("source_res_id", "=", operation.id),
            ],
            limit=1,
        )

    def test_project_to_project_uses_account_endpoint_projects(self):
        operation = self._transfer(
            self.account_a1,
            self.account_a2,
            "project to project",
        )
        fact = self._fact(operation)
        self.assertEqual(fact.source_account_id, self.account_a1)
        self.assertEqual(fact.target_account_id, self.account_a2)
        self.assertEqual(fact.source_project_id, self.project_a1)
        self.assertEqual(fact.target_project_id, self.project_a2)
        self.assertEqual(fact.movement_type, "project_to_project_transfer")
        self.assertFalse(fact.partner_id)
        self.assertFalse(fact.partner_name)

    def test_project_company_and_internal_counterparties_are_deterministic(self):
        project_company = self._fact(
            self._transfer(
                self.account_a1,
                self.company_account_a,
                "project to company",
            )
        )
        company_project = self._fact(
            self._transfer(
                self.company_account_a,
                self.account_a1,
                "company to project",
            )
        )
        internal = self._fact(
            self._transfer(
                self.account_a1,
                self.account_a1_secondary,
                "same project",
            )
        )
        self.assertEqual(project_company.movement_type, "project_to_company_transfer")
        self.assertEqual(company_project.movement_type, "company_to_project_transfer")
        self.assertEqual(internal.movement_type, "same_project_account_transfer")

    def test_cross_company_and_nonexistent_accounts_are_equivalent(self):
        nonexistent_id = max(
            self.account_a1.id,
            self.account_a2.id,
            self.account_b.id,
        ) + 1000000
        observations = []
        for target_id in (self.account_b.id, nonexistent_id):
            with self.assertRaises(AccessError) as raised:
                self.caller_env["sc.fund.account.operation"].create(
                    {
                        "operation_type": "transfer_between",
                        "company_id": self.company_a.id,
                        "source_account_id": self.account_a1.id,
                        "target_account_id": target_id,
                        "amount": 10,
                        "operation_reason": "hidden or absent",
                    }
                )
            observations.append((type(raised.exception), str(raised.exception)))
        self.assertEqual(observations[0], observations[1])

    def test_account_project_and_account_company_must_share_one_company(self):
        with self.assertRaises(AccessError):
            self._transfer(
                self.account_a1,
                self.mismatched_account,
                "mismatched project company",
            )

    def test_write_revalidates_changed_account_endpoint(self):
        operation = self._transfer(
            self.account_a1,
            self.account_a2,
            "write endpoint",
        )
        with self.assertRaises(AccessError):
            operation.write({"target_account_id": self.account_b.id})
        self.assertEqual(operation.target_account_id, self.account_a2)


if __name__ == "__main__":
    import unittest

    unittest.main()
