# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "project_salary_product")
class TestProjectSalaryProduct(TransactionCase):
    def _user(self, login, group_xmlid):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": "%s@invalid.local" % login,
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(group_xmlid).id,
                        ],
                    )
                ],
            }
        )

    def test_calculation_and_payment_are_distinct_and_payment_is_conserved(self):
        project_user = self._user(
            "project_salary_user",
            "smart_construction_core.group_sc_cap_project_user",
        )
        project_manager = self._user(
            "project_salary_manager",
            "smart_construction_core.group_sc_cap_project_manager",
        )
        project = self.env["project.project"].create(
            {
                "name": "项目薪资测试项目",
                "user_id": project_user.id,
                "operation_strategy": "direct",
            }
        )
        with self.assertRaises(UserError):
            self.env["sc.hr.payroll.document"].with_context(
                default_fact_type="salary_registration"
            ).with_user(project_user).create(
                {
                    "project_id": project.id,
                    "employee_name": "绕过状态测试人员",
                    "state": "done",
                }
            )
        payroll = self.env["sc.hr.payroll.document"].with_context(
            default_fact_type="salary_registration"
        ).with_user(project_user).create(
            {
                "project_id": project.id,
                "employee_name": "测试项目人员",
                "period_year": 2026,
                "period_month": 8,
                "gross_amount": 1200,
                "deduction_amount": 200,
                "net_salary": 1000,
            }
        )
        self.assertIn("建议补充所属部门", payroll.processing_advisory)
        self.assertIn("建议上传薪资核算依据", payroll.processing_advisory)
        payroll.action_submit()
        with self.assertRaises(UserError):
            payroll.action_done()
        payroll.with_user(project_manager).action_done()
        self.assertEqual(payroll.state, "done")

        with self.assertRaises(UserError):
            payroll.with_user(project_manager).write({"state": "cancel"})
        with self.assertRaises(UserError):
            payroll.with_user(project_manager).write({"net_salary": 900})

        with self.assertRaises(UserError):
            payroll.with_user(project_manager).write({"paid_amount": 100})
        with self.assertRaises(AccessError):
            self.env["sc.hr.salary.payment"].with_user(project_user).create(
                {
                    "payroll_document_id": payroll.id,
                    "payment_amount": 1,
                }
            )
        with self.assertRaises(UserError):
            self.env["sc.hr.salary.payment"].with_user(project_manager).create(
                {
                    "payroll_document_id": payroll.id,
                    "payment_amount": 1,
                    "state": "confirmed",
                }
            )

        payment = self.env["sc.hr.salary.payment"].with_user(project_manager).create(
            {
                "payroll_document_id": payroll.id,
                "payment_amount": 600,
            }
        )
        self.assertIn("建议补充支付凭证号", payment.processing_advisory)
        payment.action_submit()
        with self.assertRaises(UserError):
            payment.write({"payment_amount": 500})
        with self.assertRaises(UserError):
            payment.write({"state": "confirmed"})
        payment.action_confirm()
        self.assertEqual(payment.state, "confirmed")
        self.assertEqual(payroll.paid_amount, 600)
        self.assertEqual(payroll.unpaid_amount, 400)
        self.assertEqual(payroll.payment_state, "partial")

        excessive = self.env["sc.hr.salary.payment"].with_user(project_manager).create(
            {
                "payroll_document_id": payroll.id,
                "payment_amount": 500,
            }
        )
        excessive.action_submit()
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            excessive.action_confirm()
        self.assertEqual(payroll.paid_amount, 600)

        payment.action_cancel()
        self.assertEqual(payroll.paid_amount, 0)
        self.assertEqual(payroll.payment_state, "unpaid")

        calculation_action = self.env.ref(
            "smart_construction_core.action_sc_product_project_payroll_v1"
        )
        payment_action = self.env.ref(
            "smart_construction_core.action_sc_product_project_salary_payment_v1"
        )
        self.assertEqual(calculation_action.res_model, "sc.hr.payroll.document")
        self.assertEqual(payment_action.res_model, "sc.hr.salary.payment")
        self.assertNotEqual(calculation_action.res_model, payment_action.res_model)
        self.assertEqual(
            payment_action.groups_id,
            self.env.ref("smart_construction_core.group_sc_cap_project_manager"),
        )
        calculation_contract = self.env.ref(
            "smart_construction_core.business_config_contract_project_payroll_productized_form_v1"
        )
        payment_contract = self.env.ref(
            "smart_construction_core.business_config_contract_project_salary_payment_productized_form_v1"
        )
        self.assertEqual(calculation_contract.model, calculation_action.res_model)
        self.assertEqual(calculation_contract.action_id, calculation_action)
        self.assertEqual(payment_contract.model, payment_action.res_model)
        self.assertEqual(payment_contract.action_id, payment_action)
        calculation_form = calculation_contract.contract_json["view_orchestration"]["views"]["form"]
        payment_form = payment_contract.contract_json["view_orchestration"]["views"]["form"]
        self.assertIn("project_id", [item["name"] for item in calculation_form["fields"]])
        self.assertIn("payment_ids", [item["name"] for item in calculation_form["fields"]])
        self.assertIn("payroll_document_id", [item["name"] for item in payment_form["fields"]])
        self.assertIn("payment_amount", [item["name"] for item in payment_form["fields"]])
