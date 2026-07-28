# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .test_um_p3_subcontract_cumulative_settlement_orm import (
    TestUmP3SubcontractCumulativeSettlementOrm,
)


@tagged(
    "post_install",
    "-at_install",
    "admin_vis_p3_project_record_rule_orm",
    "um_p3_core_034_subcontract_amount_orm",
)
class TestUmP3SubcontractCumulativeAmountOrm(
    TestUmP3SubcontractCumulativeSettlementOrm
):
    """Tax-included amount limits in authoritative contract currency."""

    def _amount_contract(self, label, limit):
        contract = self.contract_a.copy(
            {
                "subject": f"UM-P3 CORE-034 {label}",
                "line_ids": [(5, 0, 0)],
            }
        )
        self.env["construction.contract.line"].create(
            {
                "contract_id": contract.id,
                "qty_contract": 1.0,
                "price_contract": limit / 1.03,
            }
        )
        self.assertEqual(contract.amount_total, limit)
        return contract

    def _amount_register(self, label, contract, amount, activate=True):
        register = self.env["sc.subcontract.register"].create(
            {
                "contract_id": contract.id,
                "subcontract_scope": f"UM-P3 CORE-034 {label}",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "work_scope": f"UM-P3 CORE-034 {label}",
                            "contract_qty": 1000.0,
                            "unit_name": "项",
                            "registered_amount": amount,
                        },
                    )
                ],
            }
        )
        if activate:
            register.action_register()
        return register

    def _amount_settlement(self, label, register, amount):
        settlement = self._settlement(
            f"core-034-{label}",
            [register.line_ids],
            quantities=[1.0],
        )
        settlement.line_ids.write(
            {"unit_price": amount, "tax_rate": 0.0}
        )
        return settlement

    def test_register_single_and_cumulative_contract_limits(self):
        below_contract = self._amount_contract("register-below", 100.0)
        below = self._amount_register(
            "register-below", below_contract, 99.99
        )
        self.assertEqual(below.state, "active")

        exact_contract = self._amount_contract("register-exact", 100.0)
        exact = self._amount_register(
            "register-exact", exact_contract, 100.0
        )
        self.assertEqual(exact.state, "active")

        over_contract = self._amount_contract("register-over", 100.0)
        over = self._amount_register(
            "register-over", over_contract, 100.01, activate=False
        )
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            over.action_register()
        self.assertEqual(over.state, "draft")

        cumulative_contract = self._amount_contract(
            "register-cumulative", 100.0
        )
        self._amount_register(
            "register-cumulative-first", cumulative_contract, 60.0
        )
        second = self._amount_register(
            "register-cumulative-second",
            cumulative_contract,
            40.0,
        )
        self.assertEqual(second.state, "active")
        third = self._amount_register(
            "register-cumulative-over",
            cumulative_contract,
            0.01,
            activate=False,
        )
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            third.action_register()

    def test_draft_and_cancelled_registers_release_capacity(self):
        contract = self._amount_contract("register-state", 100.0)
        active = self._amount_register("register-active", contract, 60.0)
        pending = self._amount_register(
            "register-pending", contract, 50.0, activate=False
        )
        self.assertEqual(pending.state, "draft")
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            pending.action_register()
        active.action_cancel()
        pending.action_register()
        self.assertEqual(pending.state, "active")

    def test_settlement_single_and_cumulative_limits(self):
        contract = self._amount_contract("settlement-limit", 100.0)
        register = self._amount_register(
            "settlement-register", contract, 100.0
        )
        below = self._confirm(
            self._amount_settlement("settlement-below", register, 40.0)
        )
        exact = self._confirm(
            self._amount_settlement("settlement-exact", register, 60.0)
        )
        self.assertEqual((below.state, exact.state), ("confirmed", "confirmed"))
        over = self._amount_settlement(
            "settlement-over", register, 0.01
        )
        over.action_submit()
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            over.action_confirm()

    def test_effective_write_contract_limit_and_atomic_commands(self):
        contract = self._amount_contract("effective-write", 100.0)
        register = self._amount_register(
            "effective-write-register", contract, 100.0
        )
        settlement = self._confirm(
            self._amount_settlement("effective-write", register, 90.0)
        )
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            settlement.line_ids.write({"unit_price": 101.0})
        self.assertEqual(settlement.amount_total, 90.0)

        contract_line = contract.line_ids
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            contract_line.write({"price_contract": 80.0 / 1.03})
        self.assertEqual(contract.amount_total, 100.0)

        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            settlement.write(
                {
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "register_line_id": register.line_ids.id,
                                "work_scope": "UM-P3 CORE-034 atomic",
                                "qty": 1.0,
                                "unit_name": "项",
                                "unit_price": 11.0,
                                "tax_rate": 0.0,
                            },
                        )
                    ]
                }
            )
        self.assertEqual(len(settlement.line_ids), 1)

        lower_contract = self._amount_contract("lower-limit", 50.0)
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            register.write({"contract_id": lower_contract.id})
        self.assertEqual(register.contract_id, contract)

    def test_cross_currency_effective_transition_is_rejected(self):
        other_currency = self.env["res.currency"].search(
            [("id", "!=", self.company_a.currency_id.id)], limit=1
        )
        self.assertTrue(other_currency)
        contract = self._amount_contract("currency", 100.0)
        register = self._amount_register(
            "currency", contract, 50.0, activate=False
        )
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            register.write({"currency_id": other_currency.id})
        self.assertEqual(register.currency_id, contract.currency_id)

    def test_explicit_register_amount_relation_without_history_inference(self):
        contract = self._amount_contract("explicit-relation", 1000.0)
        register = self._amount_register(
            "explicit-relation", contract, 50.0
        )
        over = self._amount_settlement(
            "explicit-register-over", register, 50.01
        )
        over.action_submit()
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            over.action_confirm()

        unrelated = self._settlement(
            "core-034-unrelated-no-inference", quantities=[1.0]
        )
        self._confirm(unrelated)
        self.assertFalse(unrelated.contract_id)
        self.assertFalse(unrelated.line_ids.register_line_id)
