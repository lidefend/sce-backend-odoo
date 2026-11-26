# -*- coding: utf-8 -*-
from odoo.addons.smart_core.tests.platform_company_test_support import license_multi_company
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged

from . import test_um_p3_fund_plan_actual_event_allocation_orm as base_cases


@tagged(
    "post_install",
    "-at_install",
    "admin_vis_p3_project_record_rule_orm",
    "um_p3_core_020_payment_ledger_permission_orm",
)
class TestUmP3PaymentLedgerRequestPermissionOrm(
    base_cases.TestUmP3FundPlanActualEventAllocationOrm
):
    """Finance-manager payment ledgers inherit request company authority."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        license_multi_company(cls.env, cls.company_a)
        base_user = cls.env.ref("base.group_user")
        finance_manager = cls.env.ref(
            "smart_construction_core.group_sc_cap_finance_manager"
        )
        cls.manager = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "UM-P3 CORE-020 finance manager",
                "login": "um_p3_core_020_manager",
                "email": "um_p3_core_020@example.invalid",
                "company_id": cls.company_a.id,
                "company_ids": [
                    (6, 0, [cls.company_a.id, cls.company_b.id])
                ],
                "groups_id": [
                    (6, 0, [base_user.id, finance_manager.id])
                ],
            }
        )
        cls.manager_a = cls._manager_env([cls.company_a.id])
        cls.manager_b = cls._manager_env([cls.company_b.id])
        cls.manager_ab = cls._manager_env(
            [cls.company_a.id, cls.company_b.id]
        )

    @classmethod
    def _manager_env(cls, company_ids):
        return cls.env(
            user=cls.manager,
            context={
                **cls.env.context,
                "allowed_company_ids": company_ids,
                "tracking_disable": True,
            },
        )

    def _visible_event_ids(self, env):
        governed_ids = [
            self.event_a1.id,
            self.event_a2.id,
            self.event_a_other.id,
            self.hidden_event.id,
            self.event_b.id,
        ]
        return set(
            env["payment.ledger"].search(
                [("id", "in", governed_ids)]
            ).ids
        )

    def _create_ledger(self, env, request):
        return env["payment.ledger"].with_context(
            allow_payment_ledger_create=True,
            payment_soft_gate=True,
        ).create(
            {
                "payment_request_id": request.id,
                "amount": request.amount,
            }
        )

    def test_a_b_and_multi_company_search_and_count(self):
        a_ids = self._visible_event_ids(self.manager_a)
        self.assertIn(self.event_a1.id, a_ids)
        self.assertIn(self.event_a2.id, a_ids)
        self.assertNotIn(self.event_b.id, a_ids)

        b_ids = self._visible_event_ids(self.manager_b)
        self.assertEqual(b_ids, {self.event_b.id})

        ab_ids = self._visible_event_ids(self.manager_ab)
        self.assertEqual(
            ab_ids,
            {
                self.event_a1.id,
                self.event_a2.id,
                self.event_a_other.id,
                self.hidden_event.id,
                self.event_b.id,
            },
        )
        self.assertEqual(
            self.manager_a["payment.ledger"].search_count(
                [("id", "in", [self.event_a1.id, self.event_b.id])]
            ),
            1,
        )
        self.assertEqual(
            self.manager_ab["payment.ledger"].search_count(
                [("id", "in", [self.event_a1.id, self.event_b.id])]
            ),
            2,
        )

    def test_direct_read_mixed_batch_and_display_name_do_not_leak(self):
        Ledger = self.manager_a["payment.ledger"]
        visible = Ledger.search(
            [("id", "in", [self.event_a1.id, self.event_b.id])]
        )
        self.assertEqual(visible.ids, [self.event_a1.id])
        self.assertTrue(visible.mapped("display_name"))
        self.assertEqual(
            visible.read(["payment_request_id", "amount"])[0]["id"],
            self.event_a1.id,
        )
        with self.env.cr.savepoint(), self.assertRaises(AccessError):
            Ledger.browse(self.event_b.id).read(
                ["payment_request_id", "amount"]
            )
        with self.env.cr.savepoint(), self.assertRaises(AccessError):
            Ledger.browse(self.event_b.id).mapped("amount")

    def test_unauthorized_and_nonexistent_ids_are_search_equivalent(self):
        Ledger = self.manager_a["payment.ledger"]
        observations = []
        for record_id in (
            self.event_b.id,
            self.event_b.id + 1000000,
        ):
            record = Ledger.search([("id", "=", record_id)], limit=1)
            observations.append(
                (
                    bool(record),
                    len(record),
                    Ledger.search_count([("id", "=", record_id)]),
                )
            )
        self.assertEqual(
            observations,
            [(False, 0, 0), (False, 0, 0)],
        )

    def test_allowed_company_switch_has_no_stale_visibility(self):
        self.assertIn(
            self.event_a1.id,
            self._visible_event_ids(self.manager_a),
        )
        self.assertNotIn(
            self.event_a1.id,
            self._visible_event_ids(self.manager_b),
        )
        self.assertIn(
            self.event_b.id,
            self._visible_event_ids(self.manager_b),
        )
        self.assertNotIn(
            self.event_b.id,
            self._visible_event_ids(self.manager_a),
        )

    def test_finance_manager_cannot_mutate_immutable_cash_facts(self):
        # Company-scoped read authority never grants direct cash-fact writes.
        for env in (self.manager_a, self.manager_b):
            for ledger in (self.event_a1, self.event_b):
                before = ledger.read(["amount", "state", "note"])
                with self.subTest(company=env.company.id, ledger=ledger.id):
                    with self.env.cr.savepoint(), self.assertRaises(AccessError):
                        self._create_ledger(env, ledger.payment_request_id)
                    with self.env.cr.savepoint(), self.assertRaises(AccessError):
                        ledger.with_env(env).write({"note": "direct mutation"})
                    with self.env.cr.savepoint(), self.assertRaisesRegex(UserError, "不允许删除"):
                        ledger.with_env(env).unlink()
                    ledger.invalidate_recordset()
                    self.assertEqual(ledger.read(["amount", "state", "note"]), before)

    def test_payment_request_company_rule_remains_authoritative(self):
        self.assertTrue(
            self.manager_a["payment.request"].search(
                [("id", "=", self.request_a1.id)],
                limit=1,
            )
        )
        self.assertFalse(
            self.manager_a["payment.request"].search(
                [("id", "=", self.request_b.id)],
                limit=1,
            )
        )
        self.assertTrue(
            self.manager_b["payment.request"].search(
                [("id", "=", self.request_b.id)],
                limit=1,
            )
        )
