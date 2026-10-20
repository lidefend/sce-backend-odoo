#!/usr/bin/env python3
from __future__ import annotations

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core.handlers.product_system_parameter_change import (
    ProductSystemParameterPublishHandler,
    ProductSystemParameterRollbackHandler,
)


@tagged("post_install", "-at_install", "sc_gate", "product_system_parameter_change")
class TestProductSystemParameterChange(TransactionCase):
    def _publish(self, parameter_key, proposed_value):
        handler = ProductSystemParameterPublishHandler(self.env)
        return handler.handle(
            {
                "parameter_key": parameter_key,
                "proposed_value": proposed_value,
                "change_reason": "test",
            }
        )

    def _rollback(self, change_id):
        handler = ProductSystemParameterRollbackHandler(self.env)
        return handler.handle({"change_id": change_id})

    def test_publish_writes_company_authority_and_records_snapshot(self):
        self.env.company.write(
            {
                "sc_cost_from_account_move": True,
                "sc_cost_from_purchase": False,
                "sc_cost_from_stock": False,
            }
        )
        result = self._publish("cost_ledger_source", "purchase_order")
        self.assertTrue(result["ok"])
        self.assertFalse(self.env.company.sc_cost_from_account_move)
        self.assertTrue(self.env.company.sc_cost_from_purchase)
        self.assertFalse(self.env.company.sc_cost_from_stock)
        change = self.env["sc.product.system.parameter.change"].browse(result["data"]["change"]["id"])
        self.assertEqual(change.state, "published")
        self.assertEqual(change.previous_value, "account_move")
        self.assertEqual(change.parameter_key, "cost_ledger_source")

    def test_rollback_restores_previous_value(self):
        self.env.company.write(
            {
                "sc_cost_from_account_move": True,
                "sc_cost_from_purchase": False,
                "sc_cost_from_stock": False,
            }
        )
        published = self._publish("cost_ledger_source", "stock_move")
        self.assertTrue(published["ok"])
        change_id = published["data"]["change"]["id"]
        result = self._rollback(change_id)
        self.assertTrue(result["ok"])
        self.assertTrue(self.env.company.sc_cost_from_account_move)
        self.assertFalse(self.env.company.sc_cost_from_stock)
        change = self.env["sc.product.system.parameter.change"].browse(change_id)
        self.assertEqual(change.state, "rolled_back")
        self.assertEqual(result["data"]["restored_value"], "account_move")

    def test_publish_rejects_value_outside_allowed_set(self):
        self.env.company.write(
            {
                "sc_cost_from_account_move": True,
                "sc_cost_from_purchase": False,
                "sc_cost_from_stock": False,
            }
        )
        result = self._publish("cost_ledger_source", "not-a-source")
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"]["reason_code"], "VALUE_NOT_ALLOWED")
        self.assertTrue(self.env.company.sc_cost_from_account_move)
        self.assertEqual(self.env["sc.product.system.parameter.change"].search_count([]), 0)

    def test_publish_rejects_planned_parameter(self):
        result = self._publish("tax_rate", 0.13)
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"]["reason_code"], "NOT_IMPLEMENTED")

    def test_rollback_rejects_non_published_change(self):
        change = self.env["sc.product.system.parameter.change"].sudo().create(
            {
                "parameter_key": "cost_ledger_source",
                "proposed_value": "disabled",
                "previous_value": "account_move",
                "state": "draft",
                "company_id": self.env.company.id,
            }
        )
        result = self._rollback(change.id)
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"]["reason_code"], "CHANGE_NOT_ROLLBACKABLE")
