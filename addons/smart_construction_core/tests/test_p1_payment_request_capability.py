# -*- coding: utf-8 -*-
import threading

import odoo
from odoo import SUPERUSER_ID, api
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged
from lxml import etree

from odoo.addons.smart_construction_core.services.financial_workspace_contract import (
    build_financial_form_business_actions,
)
from odoo.addons.smart_construction_core.core_extension_policy_maps import (
    BUSINESS_LIST_DEFAULT_VISIBILITY_BY_MODEL,
)


@tagged("post_install", "-at_install", "sc_gate", "p1_payment_request")
class TestP1PaymentRequestCapability(TransactionCase):
    def test_payment_request_search_prioritizes_workflow_status_filters(self):
        search_view = self.env.ref(
            "smart_construction_core.view_payment_request_search"
        )
        arch = etree.fromstring(search_view.arch_db.encode("utf-8"))
        visible_filter_names = [
            node.get("name")
            for node in arch.xpath(".//filter")
            if "group_by" not in (node.get("context") or "")
        ][:8]
        self.assertEqual(
            visible_filter_names[:6],
            [
                "type_pay",
                "type_receive",
                "state_draft",
                "state_submit",
                "state_approved",
                "state_done",
            ],
        )

    def test_payment_request_list_prioritizes_complete_handling_facts(self):
        policy = BUSINESS_LIST_DEFAULT_VISIBILITY_BY_MODEL["payment.request"]
        expected = [
            "document_status_display",
            "name",
            "date_request",
            "project_name_display",
            "payee_unit_display",
            "related_document_text",
            "payee_account_completeness",
            "legal_next_action_display",
            "request_amount_display",
        ]
        self.assertEqual(policy["visible"], expected)
        self.assertEqual(policy["critical"], expected)
        self.assertEqual(
            set(policy["hidden"]),
            {
                "actual_payee_unit_display",
                "payer_unit_display",
                "actual_paid_amount_display",
                "cost_type_display",
                "note_display",
                "payment_account_no_display",
                "amount_uppercase_display",
                "payee_account_name_display",
                "payee_bank_name_display",
                "payee_account_no_display",
                "attachment_ids",
            },
        )
        self.assertEqual(policy["roles"]["payee_account_completeness"], "status")
        self.assertEqual(policy["roles"]["legal_next_action_display"], "status")

    def test_payment_request_formal_list_declares_amount_sum(self):
        view = self.env.ref(
            "smart_construction_core.view_payment_request_formal_payment_apply_tree"
        )
        arch = etree.fromstring(view.arch_db.encode("utf-8"))
        nodes = arch.xpath(".//field[@name='request_amount_display']")

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].get("sum"), "申请付款金额合计")

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
                "contract_payment_method_text": "按审定进度并扣除应扣款项后支付",
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

    def _cleanup_concurrent_payment_fixture(
        self, database, request_id, contract_id, project_id, partner_id, manager_id
    ):
        """Remove records committed by the independent-transaction race test."""
        registry = odoo.registry(database)
        with registry.cursor() as cursor:
            env = api.Environment(cursor, SUPERUSER_ID, {"tracking_disable": True})
            env["sc.payment.execution"].sudo().search(
                [("payment_request_id", "=", request_id)]
            ).unlink()
            cursor.execute(
                "UPDATE payment_request SET state = 'cancel' WHERE id = %s",
                (request_id,),
            )
            env["payment.request"].sudo().browse(request_id).invalidate_recordset()
            env["payment.request"].sudo().browse(request_id).unlink()
            env["construction.contract"].sudo().browse(contract_id).unlink()
            env["project.project"].sudo().browse(project_id).unlink()
            env["res.users"].sudo().browse(manager_id).unlink()
            env["res.partner"].sudo().browse(partner_id).unlink()
            cursor.commit()

    def _approved_execution(self):
        request = self._set_request_state(self._request())
        execution = self.env["sc.payment.execution"].create(
            {"payment_request_id": request.id}
        )
        return request, execution

    def _execution_action(self, env, request):
        payload = build_financial_form_business_actions(env, "payment.request", request.id)
        actions = payload.get("actions") if isinstance(payload, dict) else []
        return next(row for row in actions if row.get("key") == "payment_execution")

    def test_execution_continuation_is_primary_for_capable_manager(self):
        request = self._set_request_state(self._request())
        action = self._execution_action(self.env, request)
        self.assertTrue(action["business_available"])
        self.assertTrue(action["authorization_allowed"])
        self.assertTrue(action["allowed"])
        self.assertTrue(action["enabled"])
        self.assertFalse(action["disabled"])
        self.assertTrue(action["primary"])
        self.assertEqual(action["presentation"]["tier"], "primary")
        self.assertEqual(action["method"], "action_create_payment_execution")
        self.assertEqual(action["visible_profiles"], ["edit", "readonly"])

    def test_execution_continuation_requires_exact_manager_capability(self):
        request = self._set_request_state(self._request())
        finance_user = self._internal_user(
            "p1_execution_action_finance_user",
            "smart_construction_core.group_sc_cap_finance_user",
        )
        self.project.user_id = finance_user
        action = self._execution_action(self.env(user=finance_user), request)
        self.assertTrue(action["business_available"])
        self.assertFalse(action["authorization_allowed"])
        self.assertFalse(action["allowed"])
        self.assertFalse(action["enabled"])
        self.assertTrue(action["disabled"])
        self.assertFalse(action["primary"])
        self.assertEqual(action["reason_code"], "ROLE_HANDOFF_REQUIRED")

    def test_execution_continuation_is_disabled_after_execution_exists(self):
        request, execution = self._approved_execution()
        action = self._execution_action(self.env, request)
        self.assertFalse(action["business_available"])
        self.assertTrue(action["authorization_allowed"])
        self.assertFalse(action["allowed"])
        self.assertFalse(action["enabled"])
        self.assertTrue(action["disabled"])
        self.assertFalse(action["primary"])
        self.assertEqual(action["reason_code"], "PAYMENT_EXECUTION_ALREADY_EXISTS")
        payload = build_financial_form_business_actions(self.env, "payment.request", request.id)
        view_action = next(row for row in payload["actions"] if row.get("key") == "view_payment_execution")
        self.assertTrue(view_action["allowed"])
        self.assertTrue(view_action["enabled"])
        self.assertFalse(view_action["disabled"])
        self.assertTrue(view_action["primary"])
        self.assertEqual(view_action["method"], "action_view_payment_execution")
        self.assertEqual(view_action["visible_profiles"], ["edit", "readonly"])
        opened = request.action_view_payment_execution()
        self.assertEqual(opened["res_id"], execution.id)
        self.assertEqual(opened["name"], "查看付款登记")

    def test_finance_manager_can_read_same_company_project_and_contract_anchors(self):
        finance_manager = self._internal_user(
            "p1_anchor_finance_manager",
            "smart_construction_core.group_sc_role_finance_manager",
        )
        self.project.with_user(finance_manager).check_access_rule("read")
        self.contract.with_user(finance_manager).check_access_rule("read")

    def test_finance_manager_cannot_read_cross_company_project_anchor(self):
        other_company = self.env["res.company"].create({"name": "P1 Other Anchor Company"})
        other_project = self.env["project.project"].sudo().create(
            {"name": "P1 Other Anchor Project", "company_id": other_company.id, "user_id": False}
        )
        finance_manager = self._internal_user(
            "p1_cross_company_anchor_finance_manager",
            "smart_construction_core.group_sc_role_finance_manager",
        )
        with self.assertRaises(AccessError):
            other_project.with_user(finance_manager).check_access_rule("read")

    def test_contract_basis_prefills_identity_and_account_snapshot(self):
        request = self._request()
        self.assertEqual(request.project_id, self.project)
        self.assertEqual(request.partner_id, self.partner)
        self.assertEqual(request.payment_basis_type, "contract")
        self.assertEqual(request.payment_account_name, self.partner.sc_account_name)
        self.assertEqual(request.payment_bank_name, self.partner.sc_bank_name)
        self.assertEqual(request.payment_account_no, self.partner.sc_bank_account)
        self.assertEqual(request.payee_account_completeness, "complete")
        self.assertEqual(request.payment_blocking_reason_display, "无业务阻断")

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
                "submitted_amount": 120,
                "approved_amount": 100,
                "settlement_period_start": "2026-07-01",
                "settlement_period_end": "2026-07-31",
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
        self.assertEqual(request.contract_payment_terms, self.contract.contract_payment_method_text)
        self.assertEqual(request.contract_change_amount, self.contract.amount_change)
        self.assertEqual(request.contract_final_amount, self.contract.amount_final)
        self.assertEqual(request.contract_settlement_amount, self.contract.settlement_amount)
        self.assertEqual(request.contract_invoice_amount, self.contract.invoice_amount)
        self.assertEqual(request.contract_paid_amount, self.contract.paid_amount)
        self.assertEqual(request.contract_unpaid_amount, self.contract.unpaid_amount)
        self.assertEqual(request.settlement_period_start, settlement.settlement_period_start)
        self.assertEqual(request.settlement_period_end, settlement.settlement_period_end)
        self.assertEqual(request.settlement_submitted_amount, settlement.submitted_amount)
        self.assertEqual(request.settlement_approved_amount, settlement.approved_amount)
        self.assertEqual(request.settlement_deduction_amount, settlement.deduction_amount)
        self._set_request_state(request)
        self.assertEqual(request.payment_basis_type, "standard_settlement")
        ledger = request._ensure_payment_ledger()
        self.assertEqual(ledger.payment_request_id, request)

    def test_payment_ledger_rejects_unapproved_standard_settlement(self):
        settlement = self.env["sc.settlement.order"].create(
            {
                "name": "P1 Draft Payment Settlement",
                "settlement_type": "out",
                "project_id": self.project.id,
                "contract_id": self.contract.id,
                "partner_id": self.partner.id,
                "settlement_amount": 100,
            }
        )
        request = self._set_request_state(
            self.env["payment.request"].create(
                {
                    "type": "pay",
                    "settlement_id": settlement.id,
                    "amount": 100,
                }
            )
        )
        self.assertEqual(request.payment_basis_type, "standard_settlement")
        with self.assertRaisesRegex(UserError, "结算单未处于已审批状态"):
            request._ensure_payment_ledger()

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

    def test_submit_only_accepts_draft_or_rejected_requests(self):
        request = self._set_request_state(self._request(), "approved")
        with self.assertRaisesRegex(UserError, "只有草稿或已驳回"):
            request.action_submit()
        self.assertEqual(request.state, "approved")

    def test_rejection_requires_explicit_reason_and_resubmit_preserves_audit(self):
        request = self._set_request_state(self._request(), "submit")
        with self.assertRaisesRegex(UserError, "reason is required"):
            request.action_on_tier_rejected()
        self.assertEqual(request.state, "submit")
        self.assertFalse(
            self.env["sc.audit.log"].search_count(
                [
                    ("model", "=", "payment.request"),
                    ("res_id", "=", request.id),
                    ("event_code", "=", "payment_rejected"),
                ]
            )
        )

        request.action_on_tier_rejected("合同付款依据需补充签章页")
        self.assertEqual(request.state, "rejected")
        self.assertEqual(request.reject_reason, "合同付款依据需补充签章页")
        self.assertEqual(request.legal_next_action_display, "重新提交审批")
        self.assertIn("合同付款依据需补充签章页", request.payment_blocking_reason_display)
        request.write({"amount": 90, "note": "已补充签章页并修正申请金额"})
        self.assertEqual(request.amount, 90)
        submit_action = next(
            row
            for row in build_financial_form_business_actions(
                self.env, "payment.request", request.id
            )["actions"]
            if row.get("key") == "payment_submit"
        )
        self.assertTrue(submit_action["allowed"])
        self.assertTrue(submit_action["enabled"])
        self.assertFalse(submit_action["disabled"])
        self.assertEqual(submit_action["label"], "重新提交审批")
        rejection = self.env["sc.audit.log"].search(
            [
                ("model", "=", "payment.request"),
                ("res_id", "=", request.id),
                ("event_code", "=", "payment_rejected"),
            ],
            limit=1,
        )
        self.assertEqual(rejection.reason, "合同付款依据需补充签章页")

        request.action_submit()
        self.assertEqual(request.state, "submit")
        self.assertFalse(request.reject_reason)
        with self.assertRaisesRegex(UserError, "业务事实不可直接修改"):
            request.write({"note": "审批中不得覆盖原办理说明"})
        events = self.env["sc.audit.log"].search(
            [("model", "=", "payment.request"), ("res_id", "=", request.id)]
        ).mapped("event_code")
        self.assertIn("payment_rejected", events)
        self.assertIn("payment_submitted", events)

    def test_contract_only_request_is_valid_execution_basis(self):
        request = self._request()
        contracts = self.env["sc.payment.execution"]._payment_basis_contracts(request)
        self.assertEqual(contracts, self.contract)

    def test_approved_complete_payment_can_open_and_create_execution(self):
        request = self._set_request_state(self._request())
        action = request.with_context(
            current_business_category_code="finance.payment.apply.pay",
            current_business_category_label="付款申请",
        ).action_create_payment_execution()
        self.assertEqual(action.get("res_model"), "sc.payment.execution")
        self.assertEqual(action.get("view_mode"), "form")
        self.assertEqual(action.get("target"), "new")
        self.assertEqual(action.get("name"), "新建付款登记")
        self.assertEqual(action.get("context", {}).get("default_payment_request_id"), request.id)
        self.assertEqual(action.get("context", {}).get("default_payment_request_id_label"), request.display_name)
        self.assertEqual(action.get("context", {}).get("default_project_id_label"), self.project.display_name)
        self.assertEqual(action.get("context", {}).get("default_partner_id_label"), self.partner.display_name)
        self.assertEqual(action.get("context", {}).get("default_contract_id_label"), self.contract.display_name)
        self.assertEqual(
            action.get("context", {}).get("default_business_category_code"),
            "finance.payment.execution.partner",
        )
        self.assertEqual(action.get("context", {}).get("default_business_category_label"), "往来单位付款")
        execution = self.env["sc.payment.execution"].create(
            {"payment_request_id": request.id}
        )
        self.assertEqual(execution.payment_request_id, request)
        self.assertEqual(execution.project_id, self.project)
        self.assertEqual(execution.partner_id, self.partner)
        self.assertEqual(execution.contract_id, self.contract)

    def test_duplicate_tabs_and_retries_create_only_one_active_execution(self):
        request = self._set_request_state(self._request())
        first = self.env["sc.payment.execution"].create(
            {"payment_request_id": request.id}
        )
        with self.assertRaisesRegex(ValidationError, "已存在办理中的付款登记"):
            self.env["sc.payment.execution"].create(
                {"payment_request_id": request.id}
            )
        with self.assertRaisesRegex(ValidationError, "不能在一次操作中生成多条付款登记"):
            self.env["sc.payment.execution"].create(
                [
                    {"payment_request_id": request.id},
                    {"payment_request_id": request.id},
                ]
            )
        self.assertEqual(
            self.env["sc.payment.execution"].search_count(
                [("payment_request_id", "=", request.id), ("state", "!=", "cancel")]
            ),
            1,
        )
        first.action_cancel()
        replacement = self.env["sc.payment.execution"].create(
            {"payment_request_id": request.id}
        )
        self.assertNotEqual(replacement, first)
        self.assertEqual(first.state, "cancel")

    def _run_concurrent_tabs_serialize_and_create_one_active_execution(self):
        """Two committed transactions must compete for the same request row."""
        database = self.env.cr.dbname
        registry = odoo.registry(database)
        with registry.cursor() as cursor:
            env = api.Environment(cursor, SUPERUSER_ID, {"tracking_disable": True})
            project = env["project.project"].create(
                {
                    "name": "P1 concurrent payment project",
                    "company_id": env.company.id,
                }
            )
            partner = env["res.partner"].create(
                {
                    "name": "P1 concurrent payment partner",
                    "supplier_rank": 1,
                    "sc_account_name": "P1 concurrent payment partner",
                    "sc_bank_name": "P1 concurrent bank",
                    "sc_bank_account": "6222000000000099",
                }
            )
            contract = env["construction.contract"].create(
                {
                    "subject": "P1 concurrent payment contract",
                    "type": "in",
                    "project_id": project.id,
                    "partner_id": partner.id,
                }
            )
            request = env["payment.request"].create(
                {
                    "type": "pay",
                    "contract_id": contract.id,
                    "amount": 100,
                }
            )
            cursor.execute(
                "UPDATE payment_request SET state = 'approved' WHERE id = %s",
                (request.id,),
            )
            manager = env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": "P1 concurrent finance manager %s" % request.id,
                    "login": "p1_concurrent_finance_manager_%s" % request.id,
                    "groups_id": [
                        (
                            6,
                            0,
                            [
                                env.ref("base.group_user").id,
                                env.ref(
                                    "smart_construction_core.group_sc_cap_finance_manager"
                                ).id,
                            ],
                        )
                    ],
                }
            )
            project.user_id = manager
            request_id = request.id
            contract_id = contract.id
            project_id = project.id
            partner_id = partner.id
            manager_id = manager.id
            cursor.commit()
        self.addCleanup(
            self._cleanup_concurrent_payment_fixture,
            database,
            request_id,
            contract_id,
            project_id,
            partner_id,
            manager_id,
        )

        barrier = threading.Barrier(2)
        result_lock = threading.Lock()
        outcomes = []

        def create_execution():
            outcome = "unexpected"
            with registry.cursor() as cursor:
                env = api.Environment(cursor, manager_id, {"tracking_disable": True})
                try:
                    barrier.wait(timeout=15)
                    execution = env["sc.payment.execution"].create(
                        {"payment_request_id": request_id}
                    )
                    cursor.commit()
                    outcome = ("created", execution.id)
                except ValidationError as error:
                    cursor.rollback()
                    outcome = ("rejected", str(error))
                except Exception as error:  # pragma: no cover - evidence surface
                    cursor.rollback()
                    outcome = ("unexpected", repr(error))
            with result_lock:
                outcomes.append(outcome)

        threads = [threading.Thread(target=create_execution) for _index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(
            sorted(row[0] for row in outcomes),
            ["created", "rejected"],
            outcomes,
        )
        rejection = next(row[1] for row in outcomes if row[0] == "rejected")
        self.assertIn("已存在办理中的付款登记", rejection)
        with registry.cursor() as cursor:
            env = api.Environment(cursor, SUPERUSER_ID, {})
            self.assertEqual(
                env["sc.payment.execution"].search_count(
                    [("payment_request_id", "=", request_id), ("state", "!=", "cancel")]
                ),
                1,
            )

    def test_paid_and_reversal_keep_request_ledger_and_audit_consistent(self):
        request = self._set_request_state(self._request())
        self.env.cr.execute(
            "UPDATE payment_request SET validation_status = 'validated' WHERE id = %s",
            (request.id,),
        )
        request.invalidate_recordset(["validation_status"])
        execution = self.env["sc.payment.execution"].create(
            {
                "payment_request_id": request.id,
                "payment_account_name": "P1 Company Operating Account",
                "payment_bank_name": "P1 Construction Bank",
                "payment_account_no": "1000000000001",
                "payment_method": "bank_transfer",
            }
        )
        with self.assertRaisesRegex(UserError, "完成审批.*已确认状态"):
            execution.action_paid()
        self.env.cr.execute(
            "UPDATE sc_payment_execution SET state = 'confirmed', validation_status = 'validated' WHERE id = %s",
            (execution.id,),
        )
        execution.invalidate_recordset(["state", "validation_status"])
        with self.assertRaisesRegex(UserError, "提交后业务事实不可直接修改"):
            execution.write({"paid_amount": 99, "payment_account_no": "REBOUND"})
        execution.action_paid()
        request.invalidate_recordset(["state"])
        execution.invalidate_recordset(["state"])
        ledger = self.env["payment.ledger"].search(
            [("payment_request_id", "=", request.id)]
        )
        self.assertEqual(execution.state, "paid")
        self.assertEqual(request.state, "done")
        self.assertEqual(len(ledger), 1)
        self.assertEqual(ledger.amount, request.amount)

        with self.assertRaisesRegex(UserError, "必须填写冲销原因"):
            execution.action_cancel()
        execution.reversal_reason = "银行退票，撤销原付款并重新办理"
        execution.action_cancel()
        request.invalidate_recordset(["state"])
        execution.invalidate_recordset(["state"])
        self.assertEqual(execution.state, "cancel")
        self.assertEqual(request.state, "approved")
        self.assertTrue(ledger.exists())
        self.assertEqual(ledger.state, "reversed")
        self.assertEqual(ledger.reversal_execution_id, execution)
        self.assertEqual(ledger.reversed_by_id, self.env.user)
        self.assertTrue(ledger.reversed_at)
        self.assertEqual(ledger.reversal_reason, "银行退票，撤销原付款并重新办理")
        self.assertEqual(execution.cancellation_kind, "payment_reversed")
        self.assertEqual(request.paid_amount_total, 0.0)
        self.assertEqual(request.unpaid_amount, request.amount)
        self.assertEqual(
            request.payment_execution_status_display,
            "最近付款登记已取消或冲销，尚无有效付款登记",
        )
        self.assertEqual(request.legal_next_action_display, "生成付款登记")
        self.assertFalse(request.has_active_payment_execution)
        with self.assertRaisesRegex(UserError, "尚未生成有效的付款登记"):
            request.action_view_payment_execution()
        replacement = self.env["sc.payment.execution"].create(
            {"payment_request_id": request.id}
        )
        self.assertNotEqual(replacement, execution)
        audit_codes = self.env["sc.audit.log"].search(
            [("model", "=", "payment.request"), ("res_id", "=", request.id)]
        ).mapped("event_code")
        self.assertIn("payment_paid", audit_codes)
        self.assertIn("payment_reversed", audit_codes)
        request.action_cancel()
        with self.assertRaisesRegex(UserError, "已冲销付款台账"):
            request.unlink()

    def test_payment_installment_unique_indexes_exist_on_clean_schema_contract(self):
        self.env.cr.execute(
            """
            SELECT indexname, indexdef
              FROM pg_indexes
             WHERE schemaname = current_schema()
               AND indexname IN (
                   'payment_ledger_one_posted_per_execution_idx',
                   'sc_payment_execution_one_active_per_request_idx'
               )
            """
        )
        indexes = {name: " ".join((definition or "").lower().split()) for name, definition in self.env.cr.fetchall()}
        ledger_index = indexes["payment_ledger_one_posted_per_execution_idx"]
        execution_index = indexes["sc_payment_execution_one_active_per_request_idx"]
        self.assertIn("payment_execution_id", ledger_index)
        self.assertIn("posted", ledger_index)
        self.assertIn("payment_request_id", execution_index)
        self.assertIn("state", execution_index)
        self.assertIn("draft", execution_index)
        self.assertIn("confirmed", execution_index)

    def test_one_request_can_be_paid_in_two_installments(self):
        request = self._set_request_state(self._request())
        self.env.cr.execute(
            "UPDATE payment_request SET validation_status = 'validated' WHERE id = %s",
            (request.id,),
        )
        request.invalidate_recordset(["validation_status"])

        first = self.env["sc.payment.execution"].create({
            "payment_request_id": request.id,
            "paid_amount": 40,
            "payment_account_name": "P1 Company Operating Account",
            "payment_bank_name": "P1 Construction Bank",
            "payment_account_no": "1000000000001",
            "payment_method": "bank_transfer",
        })
        self.env.cr.execute(
            "UPDATE sc_payment_execution SET state = 'confirmed', validation_status = 'validated' WHERE id = %s",
            (first.id,),
        )
        first.invalidate_recordset(["state", "validation_status"])
        first.action_paid()
        request.invalidate_recordset()
        self.assertEqual(request.state, "approved")
        self.assertEqual(request.paid_amount_total, 40)
        self.assertEqual(request.unpaid_amount, 60)

        second = self.env["sc.payment.execution"].create({
            "payment_request_id": request.id,
            "payment_account_name": "P1 Company Operating Account",
            "payment_bank_name": "P1 Construction Bank",
            "payment_account_no": "1000000000001",
            "payment_method": "bank_transfer",
        })
        self.assertEqual(second.paid_amount, 60)
        self.env.cr.execute(
            "UPDATE sc_payment_execution SET state = 'confirmed', validation_status = 'validated' WHERE id = %s",
            (second.id,),
        )
        second.invalidate_recordset(["state", "validation_status"])
        second.action_paid()
        request.invalidate_recordset()
        self.assertEqual(request.state, "done")
        self.assertEqual(request.paid_amount_total, 100)
        self.assertEqual(request.unpaid_amount, 0)
        ledgers = self.env["payment.ledger"].search([
            ("payment_request_id", "=", request.id),
            ("state", "=", "posted"),
        ])
        self.assertEqual(len(ledgers), 2)
        self.assertEqual(set(ledgers.mapped("payment_execution_id").ids), {first.id, second.id})
        self.assertEqual(sum(ledgers.mapped("amount")), request.amount)

        first.reversal_reason = "首笔分次付款银行退回"
        first.action_cancel()
        request.invalidate_recordset()
        self.assertEqual(request.state, "approved")
        self.assertEqual(request.paid_amount_total, 60)
        self.assertEqual(request.unpaid_amount, 40)
        first_ledger = self.env["payment.ledger"].search([
            ("payment_execution_id", "=", first.id),
        ])
        second_ledger = self.env["payment.ledger"].search([
            ("payment_execution_id", "=", second.id),
        ])
        self.assertEqual(first_ledger.state, "reversed")
        self.assertEqual(second_ledger.state, "posted")

        replacement = self.env["sc.payment.execution"].create({
            "payment_request_id": request.id,
            "payment_account_name": "P1 Company Operating Account",
            "payment_bank_name": "P1 Construction Bank",
            "payment_account_no": "1000000000001",
            "payment_method": "bank_transfer",
        })
        self.assertEqual(replacement.paid_amount, 40)
        self.env.cr.execute(
            "UPDATE sc_payment_execution SET state = 'confirmed', validation_status = 'validated' WHERE id = %s",
            (replacement.id,),
        )
        replacement.invalidate_recordset(["state", "validation_status"])
        replacement.action_paid()
        request.invalidate_recordset()
        self.assertEqual(request.state, "done")
        self.assertEqual(request.paid_amount_total, 100)
        self.assertEqual(request.unpaid_amount, 0)
        posted_ledgers = self.env["payment.ledger"].search([
            ("payment_request_id", "=", request.id),
            ("state", "=", "posted"),
        ])
        self.assertEqual(set(posted_ledgers.mapped("payment_execution_id").ids), {second.id, replacement.id})
        self.assertEqual(sum(posted_ledgers.mapped("amount")), request.amount)

    def test_payment_flow_label_is_live_derived_fact_for_existing_rows(self):
        request = self._request()
        self.assertFalse(request._fields["payment_flow_label"].store)
        self.assertFalse(request._fields["payee_account_source_display"].store)
        self.assertFalse(request._fields["has_active_payment_execution"].store)
        self.assertFalse(request._fields["payment_execution_status_display"].store)
        self.assertEqual(request.payment_flow_label, "付款申请")
        request.invalidate_recordset(["payment_flow_label"])
        self.assertEqual(request.payment_flow_label, "付款申请")

    def test_payment_request_cannot_bypass_execution_with_direct_done(self):
        request = self._set_request_state(self._request())
        self.env.cr.execute(
            "UPDATE payment_request SET validation_status = 'validated' WHERE id = %s",
            (request.id,),
        )
        request.invalidate_recordset(["validation_status"])
        with self.assertRaisesRegex(UserError, "必须通过专业付款登记完成实付"):
            request.action_done()
        self.assertEqual(request.state, "approved")
        self.assertFalse(
            self.env["payment.ledger"].search_count(
                [("payment_request_id", "=", request.id)]
            )
        )

    def test_payment_execution_native_actions_follow_submit_approve_paid_sequence(self):
        form = self.env.ref("smart_construction_core.view_sc_payment_execution_form")
        arch = form.arch_db
        root = etree.fromstring(arch.encode())
        paid_button = root.xpath(".//button[@name='action_paid']")
        submit_button = root.xpath(".//button[@name='action_confirm']")
        self.assertEqual(len(paid_button), 1)
        self.assertEqual(len(submit_button), 1)
        self.assertIn('name="action_confirm"', arch)
        self.assertIn('string="提交审批"', arch)
        self.assertEqual(paid_button[0].get("invisible"), "state != 'confirmed'")
        self.assertEqual(
            paid_button[0].get("groups"),
            "smart_construction_core.group_sc_cap_finance_manager",
        )
        self.assertEqual(
            submit_button[0].get("groups"),
            "smart_construction_core.group_sc_cap_finance_user",
        )
        self.assertIn('name="paid_amount" readonly="state != \'draft\'"', arch)
        self.assertIn('name="payment_account_no" readonly="state != \'draft\'"', arch)
        self.assertIn('name="receipt_account_name" readonly="1"', arch)
        self.assertIn('name="receipt_bank_name" readonly="1"', arch)
        self.assertIn('name="receipt_account_no" readonly="1"', arch)
        request_form = self.env.ref("smart_construction_core.view_payment_request_form")
        request_arch = request_form.arch_db
        self.assertIn("type == 'pay' or state not in ['approve', 'approved']", request_arch)
        self.assertIn("or has_active_payment_execution", request_arch)
        self.assertIn("or not has_active_payment_execution", request_arch)

    def test_readonly_finance_capability_cannot_submit_payment_execution(self):
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "P1 Payment Readonly",
                "login": "p1_payment_readonly",
                "groups_id": [
                    (6, 0, [
                        self.env.ref("base.group_user").id,
                        self.env.ref("smart_construction_core.group_sc_cap_finance_read").id,
                    ])
                ],
            }
        )
        self.project.user_id = user
        _, execution = self._approved_execution()
        with self.assertRaisesRegex(UserError, "没有提交付款登记的财务办理权限"):
            execution.with_user(user).action_confirm()
        self.assertEqual(execution.state, "draft")

    def test_payment_execution_requires_complete_accounts_method_and_amount_ceiling(self):
        request, execution = self._approved_execution()
        base_values = {
            "payment_account_name": "P1 Company Operating Account",
            "payment_bank_name": "P1 Construction Bank",
            "payment_account_no": "1000000000001",
            "payment_method": "bank_transfer",
        }
        execution.write(base_values)
        execution.write({"paid_amount": request.amount + 1})
        with self.assertRaisesRegex(UserError, "实付金额不得超过付款申请剩余可付金额"):
            execution.action_confirm()
        execution.write({"paid_amount": request.amount, "payment_method": False})
        with self.assertRaisesRegex(UserError, "必须选择付款方式"):
            execution.action_confirm()
        execution.write({"payment_method": "bank_transfer", "payment_bank_name": False})
        with self.assertRaisesRegex(UserError, "完整填写付款户名、开户行和账号"):
            execution.action_confirm()

    def test_payment_execution_payee_snapshot_cannot_be_overridden(self):
        request = self._set_request_state(self._request())
        with self.assertRaisesRegex(ValidationError, "权威账户快照"):
            self.env["sc.payment.execution"].create(
                {
                    "payment_request_id": request.id,
                    "receipt_account_no": "FORGED",
                }
            )
        execution = self.env["sc.payment.execution"].create(
            {"payment_request_id": request.id}
        )
        with self.assertRaisesRegex(UserError, "付款登记中不可改写"):
            execution.write({"receipt_bank_name": "FORGED BANK"})

    def test_available_actions_use_model_capabilities_not_role_names(self):
        initiator = self._internal_user(
            "p1_business_initiator",
            "smart_construction_core.group_sc_cap_business_initiator",
        )
        self.project.user_id = initiator
        request = self._request()
        payload = build_financial_form_business_actions(
            self.env(user=initiator), "payment.request", request.id
        )
        submit = next(
            row for row in payload["actions"] if row.get("action_key") == "submit"
        )
        self.assertTrue(submit["business_available"])
        self.assertTrue(submit["authorization_allowed"])
        self.assertTrue(submit["enabled"])

        manager = self._internal_user(
            "p1_finance_manager_capability",
            "smart_construction_core.group_sc_cap_finance_manager",
        )
        self.project.user_id = manager
        self._set_request_state(request, "submit")
        payload = build_financial_form_business_actions(
            self.env(user=manager), "payment.request", request.id
        )
        approve = next(
            row for row in payload["actions"] if row.get("action_key") == "approve"
        )
        self.assertTrue(approve["business_available"])
        self.assertTrue(approve["authorization_allowed"])
        self.assertTrue(approve["enabled"])

    def test_payment_ledger_rejects_approved_request_without_business_basis(self):
        request = self._set_request_state(
            self.env["payment.request"].create(
                {
                    "type": "pay",
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "amount": 100,
                }
            )
        )
        self.assertEqual(request.payment_basis_type, "none")
        with self.assertRaisesRegex(UserError, "缺少有效的合同或结算依据"):
            request._ensure_payment_ledger()

    def test_payment_ledger_rejects_forged_create_context_without_side_effect(self):
        request = self._set_request_state(self._request())
        finance_user = self._internal_user(
            "p1_ledger_context_spoof_user",
            "smart_construction_core.group_sc_cap_finance_user",
        )
        Ledger = self.env["payment.ledger"].sudo()
        before_count = Ledger.search_count([("payment_request_id", "=", request.id)])

        with self.assertRaisesRegex(AccessError, "受控付款执行服务创建"):
            self.env["payment.ledger"].with_user(finance_user).with_context(
                allow_payment_ledger_create=True,
            ).create({
                "payment_request_id": request.id,
                "amount": request.amount,
            })

        self.assertEqual(
            Ledger.search_count([("payment_request_id", "=", request.id)]),
            before_count,
        )

    def test_payment_ledger_rejects_forged_reversal_context_without_side_effect(self):
        request = self._set_request_state(self._request())
        ledger = request._ensure_payment_ledger()
        finance_user = self._internal_user(
            "p1_ledger_reversal_spoof_user",
            "smart_construction_core.group_sc_cap_finance_user",
        )

        with self.assertRaisesRegex(AccessError, "不允许直接修改"):
            ledger.with_user(finance_user).with_context(
                allow_payment_reversal=True,
            ).write({
                "state": "reversed",
                "reversal_reason": "伪造冲销",
                "reversed_by_id": finance_user.id,
            })

        ledger.invalidate_recordset()
        self.assertEqual(ledger.state, "posted")
        self.assertFalse(ledger.reversal_reason)
        self.assertFalse(ledger.reversed_by_id)

    def test_payment_ledger_rejects_cancelled_contract_basis(self):
        request = self._set_request_state(self._request())
        self.env.cr.execute(
            "UPDATE construction_contract SET state = 'cancel' WHERE id = %s",
            (self.contract.id,),
        )
        self.contract.invalidate_recordset(["state"])
        with self.assertRaisesRegex(UserError, "合同无效或已取消"):
            request._ensure_payment_ledger()

    def test_handling_summary_exposes_account_source_execution_and_legal_next_action(self):
        request = self._set_request_state(self._request())
        self.assertEqual(request.payee_account_source_display, "本次申请账户快照")
        self.assertEqual(request.payment_execution_status_display, "尚未生成")
        self.assertEqual(request.legal_next_action_display, "生成付款登记")

        execution = self.env["sc.payment.execution"].create({"payment_request_id": request.id})
        request.invalidate_recordset([
            "payment_execution_ids",
            "payment_execution_status_display",
            "legal_next_action_display",
        ])
        self.assertIn("草稿", request.payment_execution_status_display)
        self.assertEqual(request.legal_next_action_display, "查看付款登记")
        self.assertEqual(execution.payment_request_id, request)

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
        self.assertIn("缺少户名、开户行、账号", request.payment_blocking_reason_display)
        self.assertIn("维护往来单位默认结算账户", request.payment_blocking_reason_display)
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
        from odoo.addons.smart_construction_core.models.support.business_form_policy_templates import (
            get_business_category_form_policy_templates,
        )

        form = self.env.ref("smart_construction_core.view_payment_request_form")
        self.assertIn("项目与收款对象", form.arch_db)
        self.assertIn("结算与合同依据", form.arch_db)
        self.assertIn("本次付款事实", form.arch_db)
        self.assertIn('name="partner_transaction_eligibility"', form.arch_db)
        self.assertIn('name="payee_account_completeness"', form.arch_db)
        self.assertIn('name="payee_account_source_display"', form.arch_db)
        self.assertIn('name="payment_execution_status_display"', form.arch_db)
        self.assertIn('name="legal_next_action_display"', form.arch_db)
        self.assertIn('name="payment_blocking_reason_display"', form.arch_db)
        self.assertIn("state != 'approved'", form.arch_db)

        product_contract = self.env.ref(
            "smart_construction_core.business_config_contract_payment_request_pay_productized_form_v1"
        )
        product_payload = product_contract.contract_json["view_orchestration"]["views"]["form"]
        self.assertEqual(len(product_payload["sections"]), 7)
        self.assertIn("legal_next_action_display", product_payload["sections"][0]["fields"])
        self.assertIn("payment_blocking_reason_display", product_payload["sections"][0]["fields"])
        self.assertEqual(product_payload["actions"][0]["name"], "action_create_payment_execution")
        self.assertEqual(product_payload["actions"][0]["style"], "primary")
        self.assertEqual(
            product_payload["actions"][0]["visible_profiles"],
            ["edit", "readonly"],
        )

        execution_contract = self.env.ref(
            "smart_construction_core.business_config_contract_payment_execution_from_request_productized_form_v1"
        )
        execution_payload = execution_contract.contract_json["view_orchestration"]["views"]["form"]
        self.assertEqual(
            [section["title"] for section in execution_payload["sections"]],
            ["来源申请", "本次实付", "收款账户", "付款账户", "凭证与说明", "责任与追溯"],
        )
        fields = {row["name"]: row for row in execution_payload["fields"]}
        for anchor in ("payment_request_id", "project_id", "partner_id", "contract_id"):
            self.assertTrue(fields[anchor]["readonly"])

        generated_contract = self.env.ref(
            "smart_construction_core.business_config_contract_payment_request_form_structure_generated"
        )
        generated_fields = {
            row["name"]
            for row in generated_contract.contract_json["view_orchestration"]["views"]["form"]["fields"]
        }
        self.assertTrue(
            {
                "payment_flow_label",
                "payee_account_completeness",
                "payee_account_source_display",
                "payment_execution_status_display",
                "payment_blocking_reason_display",
                "legal_next_action_display",
            }.issubset(generated_fields)
        )
        payment_policy = get_business_category_form_policy_templates()[
            "finance.payment.apply.pay"
        ]
        governed_fields = {
            field_name
            for section in payment_policy["sections"]
            for field_name in section["fields"]
        }
        self.assertTrue(
            {
                "payment_flow_label",
                "payee_account_completeness",
                "payee_account_source_display",
                "payment_execution_status_display",
                "payment_blocking_reason_display",
                "legal_next_action_display",
                "partner_transaction_eligibility",
                "partner_transaction_eligibility_reason",
                "settlement_period_start",
                "settlement_period_end",
                "settlement_submitted_amount",
                "settlement_approved_amount",
                "settlement_deduction_amount",
                "paid_amount_total",
                "unpaid_amount",
            }.issubset(governed_fields)
        )
        payment_field_policies = {
            row["name"]: row for row in payment_policy["fields"]
        }
        for fact_name in (
            "payee_account_completeness",
            "payee_account_source_display",
            "payment_execution_status_display",
            "payment_blocking_reason_display",
            "legal_next_action_display",
            "partner_transaction_eligibility",
            "partner_transaction_eligibility_reason",
            "settlement_period_start",
            "settlement_period_end",
            "settlement_submitted_amount",
            "settlement_approved_amount",
            "settlement_deduction_amount",
            "paid_amount_total",
            "unpaid_amount",
        ):
            self.assertNotIn("visible_profiles", payment_field_policies[fact_name])
            self.assertEqual(
                payment_field_policies[fact_name]["readonly_profiles"],
                ["create", "edit", "readonly"],
            )


@tagged("post_install", "-at_install", "sc_gate", "p1_payment_request_concurrency")
class TestP1PaymentRequestConcurrency(TransactionCase):
    """Run the committed-transaction race after savepoint-based capability tests."""

    _cleanup_concurrent_payment_fixture = (
        TestP1PaymentRequestCapability._cleanup_concurrent_payment_fixture
    )

    def test_concurrent_tabs_serialize_and_create_one_active_execution(self):
        TestP1PaymentRequestCapability._run_concurrent_tabs_serialize_and_create_one_active_execution(
            self
        )
