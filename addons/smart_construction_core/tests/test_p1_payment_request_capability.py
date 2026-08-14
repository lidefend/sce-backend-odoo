# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "p1_payment_request")
class TestP1PaymentRequestCapability(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write(
            {
                "groups_id": [
                    (4, self.env.ref("smart_construction_core.group_sc_cap_finance_user").id),
                    (4, self.env.ref("smart_construction_core.group_sc_cap_finance_manager").id),
                ]
            }
        )
        self.project = self.env["project.project"].create(
            {"name": "P1 Payment Project", "company_id": self.env.company.id}
        )
        self.partner = self.env["res.partner"].create(
            {
                "name": "P1 Payment Counterparty",
                "supplier_rank": 1,
                "sc_account_name": "P1 Payment Counterparty",
                "sc_bank_name": "P1 Construction Bank",
                "sc_bank_account": "6222000000000001",
            }
        )
        self.contract = self.env["construction.contract"].create(
            {
                "subject": "P1 Advance Payment Contract",
                "type": "in",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
            }
        )

    def _request(self, **extra):
        values = {
            "type": "pay",
            "contract_id": self.contract.id,
            "amount": 100,
        }
        values.update(extra)
        return self.env["payment.request"].create(values)

    def _set_request_state(self, request, state="approved"):
        self.env.cr.execute(
            "UPDATE payment_request SET state = %s WHERE id = %s",
            (state, request.id),
        )
        request.invalidate_recordset(["state"])
        return request

    def _internal_user(self, login, *group_xmlids):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "groups_id": [
                    (6, 0, [self.env.ref("base.group_user").id] + [self.env.ref(xmlid).id for xmlid in group_xmlids])
                ],
            }
        )

    def _approved_execution(self):
        request = self._set_request_state(self._request())
        execution = self.env["sc.payment.execution"].create(
            {"payment_request_id": request.id}
        )
        return request, execution

    def test_contract_basis_prefills_identity_and_account_snapshot(self):
        request = self._request()
        self.assertEqual(request.project_id, self.project)
        self.assertEqual(request.partner_id, self.partner)
        self.assertEqual(request.payment_basis_type, "contract")
        self.assertEqual(request.payment_account_name, self.partner.sc_account_name)
        self.assertEqual(request.payment_bank_name, self.partner.sc_bank_name)
        self.assertEqual(request.payment_account_no, self.partner.sc_bank_account)
        self.assertEqual(request.payee_account_completeness, "complete")

    def test_contract_identity_mismatch_is_rejected(self):
        other_partner = self.env["res.partner"].create({"name": "P1 Other Counterparty"})
        with self.assertRaisesRegex(ValidationError, "合同往来单位必须与"):
            self._request(partner_id=other_partner.id)

    def test_approved_settlement_unit_is_effective_payee(self):
        settlement_unit = self.env["res.partner"].create({"name": "P1 Settlement Payee"})
        settlement = self.env["sc.settlement.order"].create(
            {
                "name": "P1 Payment Settlement",
                "settlement_type": "out",
                "project_id": self.project.id,
                "contract_id": self.contract.id,
                "partner_id": self.partner.id,
                "settlement_unit_id": settlement_unit.id,
                "settlement_amount": 100,
            }
        )
        self.env.cr.execute(
            "UPDATE sc_settlement_order SET state = 'approve' WHERE id = %s",
            (settlement.id,),
        )
        settlement.invalidate_recordset(["state"])
        request = self.env["payment.request"].create({"type": "pay", "settlement_id": settlement.id})
        self.assertEqual(request.contract_id, self.contract)
        self.assertEqual(request.partner_id, settlement_unit)

    def test_blocked_counterparty_cannot_submit_payment(self):
        self.partner.write(
            {
                "sc_blacklisted": True,
                "sc_blacklist_level": "blocked",
                "sc_blacklist_reason": "停止付款合作",
            }
        )
        request = self._request()
        with self.assertRaisesRegex(UserError, "无法发起付款申请"):
            request.action_submit()
        self.assertEqual(request.state, "draft")

    def test_counterparty_transaction_eligibility_allows_normal_business(self):
        self.assertEqual(self.partner.sc_transaction_eligibility, "eligible")
        self.assertIn("可正常发起业务", self.partner.sc_transaction_eligibility_reason)
        self.assertTrue(self.partner._sc_assert_transaction_eligible("付款申请"))

    def test_counterparty_transaction_eligibility_requires_risk_review(self):
        self.partner.write(
            {
                "sc_blacklisted": True,
                "sc_blacklist_level": "restricted",
                "sc_blacklist_reason": "需复核付款条件",
            }
        )
        self.assertEqual(self.partner.sc_transaction_eligibility, "review_required")
        self.assertEqual(self.partner.sc_transaction_eligibility_reason, "需复核付款条件")
        self.assertTrue(self.partner._sc_assert_transaction_eligible("付款申请"))

    def test_counterparty_transaction_eligibility_blocks_new_business(self):
        self.partner.write(
            {
                "sc_blacklisted": True,
                "sc_blacklist_level": "blocked",
                "sc_blacklist_reason": "停止新付款业务",
            }
        )
        self.assertEqual(self.partner.sc_transaction_eligibility, "blocked")
        with self.assertRaisesRegex(UserError, "无法发起付款申请.*停止新付款业务"):
            self.partner._sc_assert_transaction_eligible("付款申请")

    def test_archived_counterparty_cannot_start_new_business(self):
        self.partner.write({"active": False})
        self.assertEqual(self.partner.sc_transaction_eligibility, "blocked")
        self.assertIn("档案已归档", self.partner.sc_transaction_eligibility_reason)
        with self.assertRaisesRegex(UserError, "无法发起付款申请.*档案已归档"):
            self.partner._sc_assert_transaction_eligible("付款申请")

    def test_approved_flow_business_facts_are_immutable(self):
        request = self._request()
        self.env.cr.execute(
            "UPDATE payment_request SET state = 'submit' WHERE id = %s",
            (request.id,),
        )
        request.invalidate_recordset(["state"])
        with self.assertRaisesRegex(UserError, "业务事实不可直接修改"):
            request.write({"amount": 200})
        self.assertEqual(request.amount, 100)

    def test_contract_only_request_is_valid_execution_basis(self):
        request = self._request()
        contracts = self.env["sc.payment.execution"]._payment_basis_contracts(request)
        self.assertEqual(contracts, self.contract)

    def test_approved_complete_payment_can_open_and_create_execution(self):
        request = self._set_request_state(self._request())
        action = request.action_create_payment_execution()
        self.assertEqual(action.get("res_model"), "sc.payment.execution")
        self.assertEqual(action.get("view_mode"), "form")
        self.assertEqual(action.get("target"), "new")
        self.assertEqual(action.get("context", {}).get("default_payment_request_id"), request.id)
        execution = self.env["sc.payment.execution"].create(
            {"payment_request_id": request.id}
        )
        self.assertEqual(execution.payment_request_id, request)
        self.assertEqual(execution.project_id, self.project)
        self.assertEqual(execution.partner_id, self.partner)
        self.assertEqual(execution.contract_id, self.contract)

    def test_draft_request_cannot_generate_or_anchor_execution(self):
        request = self._request()
        with self.assertRaisesRegex(UserError, "必须处于已批准状态"):
            request.action_create_payment_execution()
        with self.assertRaisesRegex(UserError, "必须处于已批准状态"):
            self.env["sc.payment.execution"].create({"payment_request_id": request.id})

    def test_receive_request_cannot_generate_or_anchor_payment_execution(self):
        income_contract = self.env["construction.contract"].create(
            {
                "subject": "P1 Receipt Contract",
                "type": "out",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
            }
        )
        request = self.env["payment.request"].create(
            {"type": "receive", "contract_id": income_contract.id, "amount": 100}
        )
        self._set_request_state(request)
        with self.assertRaisesRegex(UserError, "只有付款申请"):
            request.action_create_payment_execution()
        with self.assertRaisesRegex(UserError, "只有付款申请"):
            self.env["sc.payment.execution"].create({"payment_request_id": request.id})

    def test_incomplete_payee_account_cannot_generate_or_anchor_execution(self):
        partner = self.env["res.partner"].create({"name": "P1 Incomplete Payee"})
        contract = self.env["construction.contract"].create(
            {
                "subject": "P1 Incomplete Account Contract",
                "type": "in",
                "project_id": self.project.id,
                "partner_id": partner.id,
            }
        )
        request = self.env["payment.request"].create(
            {"type": "pay", "contract_id": contract.id, "amount": 100}
        )
        self._set_request_state(request)
        self.assertEqual(request.payee_account_completeness, "incomplete")
        with self.assertRaisesRegex(UserError, "收款户名、开户行和账号必须完整"):
            request.action_create_payment_execution()
        with self.assertRaisesRegex(UserError, "收款户名、开户行和账号必须完整"):
            self.env["sc.payment.execution"].create({"payment_request_id": request.id})

    def test_non_finance_manager_cannot_generate_or_create_linked_execution(self):
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "P1 Payment Operator",
                "login": "p1_payment_operator",
                "groups_id": [
                    (6, 0, [
                        self.env.ref("base.group_user").id,
                        self.env.ref("smart_construction_core.group_sc_cap_finance_user").id,
                    ])
                ],
            }
        )
        self.project.user_id = user
        request = self._set_request_state(self._request())
        request_as_user = request.with_user(user)
        with self.assertRaisesRegex(UserError, "没有生成付款登记的财务确认权限"):
            request_as_user.action_create_payment_execution()
        with self.assertRaisesRegex(UserError, "没有生成付款登记的财务确认权限"):
            self.env["sc.payment.execution"].with_user(user).create(
                {"payment_request_id": request.id}
            )

    def test_finance_user_cannot_rebind_existing_execution_anchor(self):
        _, execution = self._approved_execution()
        finance_user = self._internal_user(
            "p1_execution_finance_user",
            "smart_construction_core.group_sc_cap_finance_user",
        )
        self.project.user_id = finance_user
        other_partner = self.env["res.partner"].create({"name": "P1 Other Execution Payee"})
        with self.assertRaisesRegex(UserError, "不允许改绑"):
            execution.with_user(finance_user).write({"partner_id": other_partner.id})
        self.assertEqual(execution.partner_id, self.partner)

    def test_finance_manager_cannot_rebind_existing_execution_anchor(self):
        _, execution = self._approved_execution()
        finance_manager = self._internal_user(
            "p1_execution_finance_manager",
            "smart_construction_core.group_sc_cap_finance_manager",
        )
        with self.assertRaisesRegex(UserError, "不允许改绑"):
            execution.with_user(finance_manager).write({"contract_id": False})
        self.assertEqual(execution.contract_id, self.contract)

    def test_non_draft_execution_cannot_rebind_existing_anchor(self):
        _, execution = self._approved_execution()
        self.env.cr.execute(
            "UPDATE sc_payment_execution SET state = 'confirmed' WHERE id = %s",
            (execution.id,),
        )
        execution.invalidate_recordset(["state"])
        other_project = self.env["project.project"].create(
            {"name": "P1 Other Payment Project", "company_id": self.env.company.id}
        )
        with self.assertRaisesRegex(UserError, "不允许改绑"):
            execution.write({"project_id": other_project.id})
        self.assertEqual(execution.project_id, self.project)

    def test_history_sync_cannot_replace_nonempty_execution_anchor(self):
        execution = self.env["sc.payment.execution"].create(
            {
                "source_origin": "legacy",
                "state": "legacy_confirmed",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
            }
        )
        other_partner = self.env["res.partner"].create({"name": "P1 Forged Legacy Payee"})
        with self.assertRaisesRegex(UserError, "历史同步仅可补充空锚点"):
            execution.sudo().with_context(history_surface_sync=True).write(
                {"partner_id": other_partner.id}
            )
        self.assertEqual(execution.partner_id, self.partner)

    def test_controlled_history_sync_can_fill_empty_request_anchor(self):
        request = self._set_request_state(self._request())
        execution = self.env["sc.payment.execution"].create(
            {
                "source_origin": "legacy",
                "state": "legacy_confirmed",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
            }
        )
        execution.sudo().with_context(history_surface_sync=True).write(
            {"payment_request_id": request.id}
        )
        self.assertEqual(execution.payment_request_id, request)

    def test_payment_form_exposes_controls_and_task_sections(self):
        form = self.env.ref("smart_construction_core.view_payment_request_form")
        self.assertIn("项目与收款对象", form.arch_db)
        self.assertIn("结算与合同依据", form.arch_db)
        self.assertIn("本次付款事实", form.arch_db)
        self.assertIn('name="partner_transaction_eligibility"', form.arch_db)
        self.assertIn('name="payee_account_completeness"', form.arch_db)
        self.assertIn("state != 'approved'", form.arch_db)
