# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase
from odoo.tests.common import tagged


@tagged("post_install", "-at_install", "sc_regression", "cost_fact_stock_writer")
class TestStockCostLedger(TransactionCase):

    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {"name": "Project Cost Test", "company_id": self.env.company.id}
        )
        self.wbs = self.env["construction.work.breakdown"].create({
            "name": "Root",
            "code": "WBS-001",
            "project_id": self.project.id,
        })
        self.cost_code = self.env["project.cost.code"]._get_or_create_standard_code(
            "MAT", "材料成本", "material", "材料办理确认时自动归集的默认成本科目。"
        )
        self.partner = self.env["res.partner"].create({"name": "Vendor"})
        self.product = self.env["product.product"].create({
            "name": "Test Material",
            "type": "product",
            "purchase_line_warn": "no-message",
            "standard_price": 12,
            "default_cost_code_id": self.cost_code.id,
        })
        # 取入库类型及默认库位，避免 NULL location_id
        self.picking_type = self.env["stock.picking.type"].search([("code", "=", "incoming")], limit=1)
        # 防御：确保仓库/库位存在
        if not self.picking_type:
            warehouse = self.env["stock.warehouse"].create({
                "name": "Test WH",
                "code": "TWH",
            })
            self.picking_type = warehouse.in_type_id
        self.location_src = self.picking_type.default_location_src_id
        self.location_dest = self.picking_type.default_location_dest_id
        # 若仍为空，取任意内部库位作为来源
        if not self.location_src:
            self.location_src = self.env["stock.location"].search([("usage", "=", "supplier")], limit=1)
        if self.location_src.usage != "supplier":
            self.location_src = self.env["stock.location"].search([("usage", "=", "supplier")], limit=1)
        if not self.location_dest:
            self.location_dest = self.env["stock.location"].search([("usage", "=", "internal")], limit=1)

    @tagged("post_install", "-at_install", "sc_regression", "cost_fact_stock_writer")
    def test_cost_ledger_created_on_receipt(self):
        self.env.company.write({
            "sc_cost_from_account_move": False,
            "sc_cost_from_purchase": False,
            "sc_cost_from_stock": True,
        })
        picking = self.env["stock.picking"].create({
            "name": "WH/IN/0001",
            "partner_id": self.partner.id,
            "picking_type_id": self.picking_type.id,
            "location_id": self.location_src.id,
            "location_dest_id": self.location_dest.id,
        })
        move = self.env["stock.move"].create({
            "name": self.product.name,
            "product_id": self.product.id,
            "product_uom_qty": 5,
            "product_uom": self.product.uom_id.id,
            "picking_id": picking.id,
            "location_id": self.location_src.id,
            "location_dest_id": self.location_dest.id,
            "project_id": self.project.id,
            "wbs_id": self.wbs.id,
            "cost_code_id": self.cost_code.id,
        })
        move._action_confirm()
        move._action_assign()
        move.quantity = 5
        picking.with_context(skip_immediate=True, skip_backorder=True).button_validate()
        ledger = self.env["project.cost.ledger"].search([
            ("project_id", "=", self.project.id),
            ("wbs_id", "=", self.wbs.id),
            ("cost_code_id", "=", self.cost_code.id),
        ], limit=1)
        self.assertTrue(ledger)
        self.assertEqual(ledger.source_model, "stock.move")
        self.assertEqual(ledger.source_id, move.id)
        self.assertEqual(ledger.source_line_id, move.id)
        self.assertEqual(ledger.recognition_stage, "receipt_accrual")
        self.assertEqual(ledger.reporting_treatment, "memorandum")
        picking._create_cost_ledger_from_moves()
        self.assertEqual(
            self.env["project.cost.ledger"].search_count(
                [("source_model", "=", "stock.move"), ("source_id", "=", move.id)]
            ),
            1,
        )

        return_type = self.picking_type.return_picking_type_id
        self.assertTrue(return_type)
        return_picking = self.env["stock.picking"].create({
            "name": "WH/OUT/RETURN/0001",
            "partner_id": self.partner.id,
            "picking_type_id": return_type.id,
            "location_id": self.location_dest.id,
            "location_dest_id": self.location_src.id,
        })
        return_move = self.env["stock.move"].create({
            "name": f"{self.product.name} supplier return",
            "product_id": self.product.id,
            "product_uom_qty": 2,
            "product_uom": self.product.uom_id.id,
            "picking_id": return_picking.id,
            "location_id": self.location_dest.id,
            "location_dest_id": self.location_src.id,
            "origin_returned_move_id": move.id,
        })
        self.assertEqual(return_move.project_id, self.project)
        self.assertEqual(return_move.wbs_id, self.wbs)
        self.assertEqual(return_move.cost_code_id, self.cost_code)
        return_move.quantity = 2
        return_picking._create_cost_ledger_from_moves()
        return_fact = self.env["project.cost.ledger"].search([
            ("source_model", "=", "stock.move"),
            ("source_id", "=", return_move.id),
        ])
        self.assertEqual(len(return_fact), 1)
        self.assertEqual(return_fact.qty, -2)
        self.assertEqual(return_fact.source_amount, -24)
        self.assertEqual(return_fact.recognition_stage, "receipt_accrual")
        self.assertEqual(return_fact.reporting_treatment, "memorandum")

        customer_location = self.env["stock.location"].search([("usage", "=", "customer")], limit=1)
        customer_return_picking = self.env["stock.picking"].create({
            "name": "WH/IN/CUSTOMER-RETURN/0001",
            "partner_id": self.partner.id,
            "picking_type_id": self.picking_type.id,
            "location_id": customer_location.id,
            "location_dest_id": self.location_dest.id,
        })
        customer_return = self.env["stock.move"].create({
            "name": f"{self.product.name} customer return",
            "product_id": self.product.id,
            "product_uom_qty": 1,
            "product_uom": self.product.uom_id.id,
            "picking_id": customer_return_picking.id,
            "location_id": customer_location.id,
            "location_dest_id": self.location_dest.id,
            "origin_returned_move_id": move.id,
        })
        customer_return.quantity = 1
        customer_return_picking._create_cost_ledger_from_moves()
        self.assertFalse(self.env["project.cost.ledger"].search([
            ("source_model", "=", "stock.move"),
            ("source_id", "=", customer_return.id),
        ]))
