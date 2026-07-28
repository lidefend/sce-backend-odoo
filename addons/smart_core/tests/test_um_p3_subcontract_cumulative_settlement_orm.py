# -*- coding: utf-8 -*-
import threading

import odoo
from odoo import SUPERUSER_ID, api
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from .test_um_p3_subcontract_register_settlement_authority_orm import (
    TestUmP3SubcontractRegisterSettlementAuthorityOrm,
)


@tagged("post_install", "-at_install", "um_p3_s06_subcontract_cumulative_orm")
class TestUmP3SubcontractCumulativeSettlementOrm(
    TestUmP3SubcontractRegisterSettlementAuthorityOrm
):
    """Real-ORM proof for the approved registered-quantity hard limit."""

    @staticmethod
    def _confirm(settlement):
        settlement.action_submit()
        settlement.action_confirm()
        return settlement

    def test_partial_split_exact_and_over_limit(self):
        register = self._new_register(
            "s06-split-register", self.contract_a, quantity=10.0
        )
        source = register.line_ids
        first = self._confirm(
            self._settlement(
                "s06-split-first", [source], quantities=[4.0]
            )
        )
        second = self._confirm(
            self._settlement(
                "s06-split-second", [source], quantities=[6.0]
            )
        )
        self.assertEqual(first.state, "confirmed")
        self.assertEqual(second.state, "confirmed")

        over = self._settlement(
            "s06-split-over", [source], quantities=[0.01]
        )
        over.action_submit()
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            over.action_confirm()
        self.assertEqual(over.state, "submitted")

    def test_same_settlement_and_multiple_settlements_cannot_overrun(self):
        register = self._new_register(
            "s06-multi-line-register", self.contract_a, quantity=10.0
        )
        source = register.line_ids
        same_settlement = self._settlement(
            "s06-same-settlement",
            [source, source],
            quantities=[6.0, 5.0],
        )
        same_settlement.action_submit()
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            same_settlement.action_confirm()

        first = self._confirm(
            self._settlement(
                "s06-multi-first", [source], quantities=[6.0]
            )
        )
        second = self._settlement(
            "s06-multi-second", [source], quantities=[5.0]
        )
        second.action_submit()
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            second.action_confirm()
        self.assertEqual(first.state, "confirmed")

    def test_draft_submitted_and_cancel_are_excluded_until_confirmed(self):
        register = self._new_register(
            "s06-state-register", self.contract_a, quantity=10.0
        )
        source = register.line_ids
        pending = self._settlement(
            "s06-pending", [source], quantities=[100.0]
        )
        pending.action_submit()
        self.assertEqual(pending.state, "submitted")
        pending.action_cancel()
        self.assertEqual(pending.state, "cancel")

        effective = self._confirm(
            self._settlement(
                "s06-effective", [source], quantities=[10.0]
            )
        )
        self.assertEqual(effective.state, "confirmed")

        pending.action_reset_draft()
        pending.action_submit()
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            pending.action_confirm()

    def test_effective_quantity_relation_and_register_capacity_writes_recheck(self):
        first_register = self._new_register(
            "s06-write-first", self.contract_a, quantity=10.0
        )
        second_register = self._new_register(
            "s06-write-second", self.contract_a, quantity=5.0
        )
        settlement = self._confirm(
            self._settlement(
                "s06-effective-write",
                [first_register.line_ids],
                quantities=[8.0],
            )
        )
        line = settlement.line_ids
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            line.write({"qty": 11.0})
        self.assertEqual(line.qty, 8.0)

        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            line.write({"register_line_id": second_register.line_ids.id})
        self.assertEqual(line.register_line_id, first_register.line_ids)

        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            first_register.line_ids.write({"contract_qty": 7.0})
        self.assertEqual(first_register.line_ids.contract_qty, 10.0)

    def test_one2many_generic_crud_and_batch_paths_recheck(self):
        register = self._new_register(
            "s06-command-register", self.contract_a, quantity=10.0
        )
        source = register.line_ids
        settlement = self._confirm(
            self._settlement(
                "s06-command", [source], quantities=[6.0]
            )
        )
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            settlement.write(
                {
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "register_line_id": source.id,
                                "work_scope": "UM-P3 S06 command overrun",
                                "qty": 5.0,
                                "unit_name": "项",
                                "unit_price": 100.0,
                            },
                        )
                    ]
                }
            )

        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            settlement.line_ids.with_context(import_file=True).write(
                {"qty": 11.0}
            )
        with self.env.cr.savepoint(), self.assertRaises(UserError):
            settlement.line_ids.unlink()

    def test_unit_compatibility_and_precision_boundary(self):
        exact_register = self._new_register(
            "s06-precision-register", self.contract_a, quantity=0.3
        )
        source = exact_register.line_ids
        self._confirm(
            self._settlement(
                "s06-precision-first", [source], quantities=[0.1]
            )
        )
        self._confirm(
            self._settlement(
                "s06-precision-second", [source], quantities=[0.2]
            )
        )

        for label, register_unit, settlement_unit in (
            ("missing-register-unit", False, "项"),
            ("missing-settlement-unit", "项", False),
            ("incompatible-unit", "项", "米"),
        ):
            register = self._new_register(
                f"s06-{label}", self.contract_a, quantity=10.0
            )
            register.line_ids.write({"unit_name": register_unit})
            settlement = self._settlement(
                f"s06-{label}",
                [register.line_ids],
                quantities=[1.0],
            )
            settlement.line_ids.write({"unit_name": settlement_unit})
            settlement.action_submit()
            with self.env.cr.savepoint(), self.assertRaises(
                ValidationError
            ):
                settlement.action_confirm()

    def test_zero_negative_and_approved_amount_policy_boundaries(self):
        register = self._new_register(
            "s06-amount-register", self.contract_a, quantity=1.0
        )
        register.line_ids.write({"registered_amount": 1.0})
        amount_over_register = self._settlement(
            "s06-amount-nonblocking",
            [register.line_ids],
            quantities=[1.0],
        )
        amount_over_register.line_ids.write(
            {"unit_price": 1000000.0, "tax_rate": 13.0}
        )
        amount_over_register.action_submit()
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            amount_over_register.action_confirm()
        self.assertEqual(amount_over_register.state, "submitted")
        self.assertNotIn(
            "remaining_amount",
            self.env["sc.subcontract.register.line"]._fields,
        )

        for quantity in (0.0, -1.0):
            with self.env.cr.savepoint(), self.assertRaises(
                ValidationError
            ):
                self._settlement(
                    f"s06-invalid-{quantity}",
                    quantities=[quantity],
                )

    def test_unrelated_and_explicit_historical_relations_are_not_inferred(self):
        unrelated = self._settlement(
            "s06-unrelated", quantities=[1.0]
        )
        self._confirm(unrelated)
        self.assertFalse(unrelated.line_ids.register_line_id)
        self.assertFalse(unrelated.register_id)

        register = self._new_register(
            "s06-explicit-history", self.contract_a, quantity=2.0
        )
        explicit = self._confirm(
            self._settlement(
                "s06-explicit-history",
                [register.line_ids],
                quantities=[2.0],
            )
        )
        later = self._settlement(
            "s06-explicit-history-over",
            [register.line_ids],
            quantities=[0.01],
        )
        later.action_submit()
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            later.action_confirm()
        self.assertEqual(explicit.state, "confirmed")

    def test_concurrent_confirmations_serialize_on_register_line(self):
        database = self.env.cr.dbname
        registry = odoo.registry(database)
        with registry.cursor() as cursor:
            env = api.Environment(
                cursor,
                SUPERUSER_ID,
                {"tracking_disable": True},
            )
            company = env.ref("base.main_company")
            project = env["project.project"].create(
                {
                    "name": "UM-P3 S06 concurrent project",
                    "code": "UM-P3-S06-CONCURRENT",
                    "company_id": company.id,
                    "privacy_visibility": "followers",
                    "user_id": env.user.id,
                }
            )
            partner = env["res.partner"].create(
                {"name": "UM-P3 S06 concurrent subcontractor"}
            )
            tax_group = env["account.tax.group"].search(
                [("company_id", "=", company.id)], limit=1
            )
            if not tax_group:
                tax_group = env["account.tax.group"].create(
                    {
                        "name": "UM-P3 S06 concurrent tax group",
                        "company_id": company.id,
                    }
                )
            tax = env["account.tax"].search(
                [
                    ("name", "=", "UM-P3 S06 concurrent 3%"),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            )
            if not tax:
                tax = env["account.tax"].create(
                    {
                        "name": "UM-P3 S06 concurrent 3%",
                        "amount": 3.0,
                        "amount_type": "percent",
                        "type_tax_use": "purchase",
                        "price_include": False,
                        "company_id": company.id,
                        "tax_group_id": tax_group.id,
                        "country_id": (
                            company.country_id or env.ref("base.cn")
                        ).id,
                    }
                )
            contract = env["construction.contract"].create(
                {
                    "subject": "UM-P3 S06 concurrent contract",
                    "type": "in",
                    "project_id": project.id,
                    "partner_id": partner.id,
                    "company_id": company.id,
                    "currency_id": company.currency_id.id,
                    "tax_id": tax.id,
                }
            )
            env["construction.contract.line"].create(
                {
                    "contract_id": contract.id,
                    "qty_contract": 1.0,
                    "price_contract": 1000000.0,
                }
            )
            register = env["sc.subcontract.register"].create(
                {
                    "contract_id": contract.id,
                    "subcontract_scope": "UM-P3 S06 concurrent scope",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "work_scope": (
                                    "UM-P3 S06 concurrent register line"
                                ),
                                "contract_qty": 10.0,
                                "unit_name": "项",
                                "registered_amount": 1000.0,
                            },
                        )
                    ],
                }
            )
            register.action_register()
            settlement_ids = []
            for index in range(2):
                settlement = env["sc.subcontract.settlement"].create(
                    {
                        "name": f"UM-P3 S06 concurrent {index}",
                        "project_id": project.id,
                        "subcontractor_id": partner.id,
                        "line_ids": [
                            (
                                0,
                                0,
                                {
                                    "register_line_id": register.line_ids.id,
                                    "work_scope": (
                                        f"UM-P3 S06 concurrent line {index}"
                                    ),
                                    "qty": 6.0,
                                    "unit_name": "项",
                                    "unit_price": 100.0,
                                },
                            )
                        ],
                    }
                )
                settlement.action_submit()
                settlement_ids.append(settlement.id)
            cursor.commit()

        barrier = threading.Barrier(2)
        result_lock = threading.Lock()
        outcomes = []

        def confirm(settlement_id):
            outcome = "unexpected"
            with registry.cursor() as cursor:
                env = api.Environment(
                    cursor,
                    SUPERUSER_ID,
                    {"tracking_disable": True},
                )
                settlement = env["sc.subcontract.settlement"].search(
                    [("id", "=", settlement_id)], limit=1
                )
                try:
                    barrier.wait(timeout=15)
                    settlement.action_confirm()
                    cursor.commit()
                    outcome = "confirmed"
                except ValidationError:
                    cursor.rollback()
                    outcome = "over_limit_rejected"
            with result_lock:
                outcomes.append(outcome)

        threads = [
            threading.Thread(target=confirm, args=(settlement_id,))
            for settlement_id in settlement_ids
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(
            sorted(outcomes),
            ["confirmed", "over_limit_rejected"],
        )
