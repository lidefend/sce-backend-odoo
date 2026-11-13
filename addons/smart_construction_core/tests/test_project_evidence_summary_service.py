# -*- coding: utf-8 -*-
from odoo import api
from odoo.tests.common import tagged

from .business_case import BusinessTransactionCase
from ..services.project_dashboard_service import ProjectDashboardService


@tagged(
    "post_install",
    "-at_install",
    "sc_gate",
    "project_evidence_summary",
)
class TestProjectEvidenceSummaryService(BusinessTransactionCase):
    approval_models = ("payment.request",)

    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {
                "name": "Evidence Summary Project",
                "company_id": self.env.company.id,
                "user_id": self.env.user.id,
            }
        )
        self.partner = self.env["res.partner"].create(
            {
                "name": "Evidence Summary Payee",
                "supplier_rank": 1,
                "sc_account_name": "Evidence Summary Payee",
                "sc_bank_name": "Evidence Summary Bank",
                "sc_bank_account": "EVIDENCE-SUMMARY-ACCOUNT",
            }
        )
        self.contract = self.env["construction.contract"].create(
            {
                "subject": "Evidence Summary Expense Contract",
                "type": "in",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_payment_method_text": "按批准金额付款",
            }
        )
        cost_code = self.env["project.cost.code"].create(
            {
                "name": "Evidence Summary Material",
                "code": "EVIDENCE-SUMMARY-MATERIAL",
                "type": "material",
            }
        )
        self.env["project.cost.ledger"].create(
            {
                "project_id": self.project.id,
                "cost_code_id": cost_code.id,
                "currency_id": self.project.company_id.currency_id.id,
                "date": "2026-11-13",
                "amount": 800.0,
            }
        )
        settlement = self.env["sc.settlement.order"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
                "settlement_type": "out",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Evidence Summary Settlement",
                            "qty": 1.0,
                            "price_unit": 400000.0,
                        },
                    )
                ],
            }
        )
        settlement._write_lifecycle("approve")

        request = self.env["payment.request"].create(
            {
                "type": "pay",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
                "amount": 160000.0,
            }
        )
        self.env.cr.execute(
            """
            UPDATE payment_request
               SET state = 'approved',
                   validation_status = 'validated'
             WHERE id = %s
            """,
            (request.id,),
        )
        request.invalidate_recordset(["state", "validation_status"])
        execution = self.env["sc.payment.execution"].create(
            {
                "payment_request_id": request.id,
                "payment_account_name": "Evidence Summary Operating Account",
                "payment_bank_name": "Evidence Summary Bank",
                "payment_account_no": "EVIDENCE-SUMMARY-PAYMENT",
                "payment_method": "bank_transfer",
            }
        )
        self.env.cr.execute(
            """
            UPDATE sc_payment_execution
               SET state = 'confirmed',
                   validation_status = 'validated'
             WHERE id = %s
            """,
            (execution.id,),
        )
        execution.invalidate_recordset(["state", "validation_status"])
        execution.action_paid()
        self.ledger = self.env["payment.ledger"].search(
            [
                ("payment_request_id", "=", request.id),
                ("state", "=", "posted"),
            ],
            limit=1,
        )
        self.assertTrue(self.ledger)

    def test_formal_dashboard_uses_posted_ledger_and_traceable_sources(self):
        service = self.env["sc.evidence.summary.service"]
        summary = service.summary_for_project(self.project)

        self.assertEqual(summary["pay_total"], 160000.0)
        self.assertEqual(summary["pay_done_total"], 160000.0)
        self.assertEqual(summary["pay_done_count"], 1)
        self.assertEqual(summary["payment_count"], 1)
        self.assertEqual(summary["payment_request_count"], 1)
        self.assertEqual(summary["cost_total"], 800.0)
        self.assertEqual(summary["cost_count"], 1)
        self.assertEqual(summary["settlement_total"], 400000.0)
        self.assertEqual(summary["settlement_count"], 1)
        self.assertEqual(summary["evidence_count"], 3)
        self.assertIn(
            "payment.ledger#%s" % self.ledger.id,
            summary["evidence_refs"],
        )
        self.assertEqual(
            set(summary["source_status"].values()),
            {"ready"},
        )

        payload = ProjectDashboardService(self.env).project_payload(self.project)
        self.assertEqual(float(payload["payment_executed_total"]), 160000.0)
        self.assertEqual(int(payload["payment_executed_record_count"]), 1)
        self.assertEqual(float(payload["cost_total"]), 800.0)
        self.assertIn(
            "payment.ledger#%s" % self.ledger.id,
            payload["evidence_refs"],
        )

    def test_approved_request_amount_is_not_reported_as_paid(self):
        unpaid_request = self.env["payment.request"].create(
            {
                "type": "pay",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
                "amount": 5000.0,
            }
        )
        self.env.cr.execute(
            """
            UPDATE payment_request
               SET state = 'approved',
                   validation_status = 'validated'
             WHERE id = %s
            """,
            (unpaid_request.id,),
        )
        unpaid_request.invalidate_recordset(["state", "validation_status"])
        partial_request = self.env["payment.request"].create(
            {
                "type": "pay",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
                "amount": 200.0,
            }
        )
        self.env.cr.execute(
            """
            UPDATE payment_request
               SET state = 'approved',
                   validation_status = 'validated'
             WHERE id = %s
            """,
            (partial_request.id,),
        )
        partial_request.invalidate_recordset(["state", "validation_status"])
        partial_ledger = partial_request._ensure_payment_ledger(amount=50.0)
        cost_ledger = self.env["project.cost.ledger"].search(
            [("project_id", "=", self.project.id)],
            limit=1,
        )
        cost_ledger.write({"amount": 162000.0})

        summary = self.env[
            "sc.evidence.summary.service"
        ].summary_for_project(self.project)
        self.assertEqual(summary["payment_request_total"], 165200.0)
        self.assertEqual(summary["payment_request_count"], 3)
        self.assertEqual(summary["pay_total"], 160050.0)
        self.assertEqual(summary["pay_done_total"], 160050.0)
        self.assertEqual(summary["pay_done_count"], 2)
        self.assertIn(
            "payment.ledger#%s" % partial_ledger.id,
            summary["evidence_refs"],
        )

        payload = ProjectDashboardService(self.env).project_payload(self.project)
        self.assertEqual(float(payload["payment_total"]), 160050.0)
        self.assertEqual(
            float(payload["payment_executed_total"]),
            160050.0,
        )
        metrics = ProjectDashboardService(
            self.env
        ).build_metrics_explain(self.project)
        payment_metric = next(
            row for row in metrics if row.get("key") == "payment"
        )
        self.assertEqual(payment_metric["status"], "normal")
        self.assertEqual(payment_metric["explain"], "付款与成本关系正常。")

    def test_unresolved_legacy_ledger_is_not_counted_as_paid(self):
        self.env.cr.execute(
            """
            UPDATE payment_ledger
               SET normalization_state = 'legacy_unresolved_identity'
             WHERE id = %s
            """,
            (self.ledger.id,),
        )
        self.ledger.invalidate_recordset(["normalization_state"])
        summary = self.env[
            "sc.evidence.summary.service"
        ].summary_for_project(self.project)

        self.assertEqual(summary["pay_total"], 0.0)
        self.assertEqual(summary["pay_done_total"], 0.0)
        self.assertEqual(summary["pay_done_count"], 0)
        self.assertNotIn(
            "payment.ledger#%s" % self.ledger.id,
            summary["evidence_refs"],
        )
        self.assertEqual(summary["source_status"]["payment.ledger"], "ready")

    def test_project_member_without_finance_groups_gets_no_source_leak(self):
        restricted_user = self.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "Evidence Summary Restricted Member",
                "login": "evidence_summary_restricted_member",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.project.write({"user_id": restricted_user.id})
        restricted_env = api.Environment(
            self.env.cr,
            restricted_user.id,
            {
                **self.env.context,
                "allowed_company_ids": [self.project.company_id.id],
            },
        )
        restricted_project = restricted_env["project.project"].browse(self.project.id)
        summary = restricted_env[
            "sc.evidence.summary.service"
        ].summary_for_project(restricted_project)

        self.assertEqual(summary["pay_total"], 0.0)
        self.assertEqual(summary["pay_done_total"], 0.0)
        self.assertEqual(summary["cost_total"], 0.0)
        self.assertEqual(summary["settlement_total"], 0.0)
        self.assertEqual(summary["evidence_count"], 0)
        self.assertEqual(summary["evidence_refs"], [])
        self.assertEqual(
            summary["source_status"],
            {
                "payment.request": "forbidden",
                "payment.ledger": "forbidden",
                "project.cost.ledger": "forbidden",
                "sc.settlement.order": "forbidden",
            },
        )
