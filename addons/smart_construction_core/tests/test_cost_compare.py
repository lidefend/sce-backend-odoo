# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase
from odoo.tests.common import tagged


@tagged("post_install", "-at_install", "sc_regression", "cost", "cost_fact_projection_v2")
class TestProjectCostCompare(TransactionCase):

    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {"name": "Compare Project", "company_id": self.env.company.id}
        )
        self.cost_code = self.env["project.cost.code"].create({
            "name": "材料费",
            "code": "CF-COMPARE-MAT",
            "type": "material",
        })
        self.wbs = self.env["construction.work.breakdown"].create({
            "name": "桥梁结构",
            "code": "WBS-001",
            "project_id": self.project.id,
        })
        budget = self.env["project.budget"].create({
            "name": "Budget",
            "project_id": self.project.id,
        })
        line = self.env["project.budget.boq.line"].create({
            "budget_id": budget.id,
            "name": "Line",
            "wbs_id": self.wbs.id,
            "qty_bidded": 10,
            "price_bidded": 100,
        })
        self.env["project.budget.cost.alloc"].create({
            "project_id": self.project.id,
            "budget_boq_line_id": line.id,
            "cost_code_id": self.cost_code.id,
            "currency_id": budget.currency_id.id,
            "amount_budget": 1000,
        })
        ledger = self.env["project.cost.ledger"].create({
            "project_id": self.project.id,
            "cost_code_id": self.cost_code.id,
            "wbs_id": self.wbs.id,
            "currency_id": budget.currency_id.id,
            "date": "2025-01-15",
            "amount": 800,
        })
        self.assertEqual(ledger.recognition_state, "active")
        self.assertEqual(ledger.reporting_treatment, "manual_actual")
        self.env.flush_all()

    @tagged("post_install", "-at_install", "sc_regression", "cost")
    def test_compare_view_records(self):
        records = self.env["project.cost.compare"].search([
            ("project_id", "=", self.project.id),
            ("cost_code_id", "=", self.cost_code.id),
            ("wbs_id", "=", self.wbs.id),
        ])
        self.assertTrue(records)
        rec = records[0]
        self.assertEqual(rec.budget_amount, 1000)
        self.assertEqual(rec.actual_amount, 800)
        self.assertEqual(rec.period, "2025-01")

    @tagged("post_install", "-at_install", "sc_regression", "cost")
    def test_cost_ledger_flow_label_readable(self):
        ledger = self.env["project.cost.ledger"]._upsert_generated_cost_rows([{
            "project_id": self.project.id,
            "cost_code_id": self.cost_code.id,
            "wbs_id": self.wbs.id,
            "date": "2025-01-20",
            "source_amount": 10,
            "source_currency_id": self.project.company_id.currency_id.id,
            "source_model": "stock.move",
            "source_id": 1001,
            "source_line_id": 1001,
        }])

        self.assertEqual(ledger.read(["cost_flow_label"])[0]["cost_flow_label"], "入库成本")
