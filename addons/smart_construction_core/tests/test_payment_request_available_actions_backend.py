# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core.handlers.payment_request_available_actions import (
    PaymentRequestAvailableActionsHandler,
)
from odoo.addons.smart_core.handlers.reason_codes import (
    REASON_BUSINESS_RULE_FAILED,
    REASON_MISSING_PARAMS,
    REASON_NOT_FOUND,
    REASON_OK,
)


@tagged("sc_smoke", "payment_request_available_actions_backend")
class TestPaymentRequestAvailableActionsBackend(TransactionCase):
    def _create_user(self, login, group_xmlids):
        groups = [self.env.ref(xmlid).id for xmlid in group_xmlids]
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@example.com",
                "groups_id": [(6, 0, groups)],
            }
        )

    def _create_payment_request_minimal(self):
        project = self.env["project.project"].create(
            {
                "name": "Action Matrix Project",
                "funding_enabled": True,
                "company_id": self.env.company.id,
            }
        )
        partner = self.env["res.partner"].create({"name": "Action Matrix Partner"})
        contract = self.env["construction.contract"].create(
            {
                "subject": "Action Matrix Contract",
                "type": "in",
                "project_id": project.id,
                "partner_id": partner.id,
            }
        )
        payment = self.env["payment.request"].sudo().create(
            {
                "name": "INTENT-ACTIONS-PR-001",
                "type": "pay",
                "project_id": project.id,
                "partner_id": partner.id,
                "amount": 100,
                "state": "draft",
            }
        )
        self.env["payment.request.line"].sudo().create(
            {
                "request_id": payment.id,
                "legacy_line_id": "INTENT-ACTIONS-LINE-%s" % payment.id,
                "legacy_parent_id": "INTENT-ACTIONS-PARENT-%s" % payment.id,
                "contract_id": contract.id,
                "amount": payment.amount,
                "current_pay_amount": payment.amount,
            }
        )
        payment.write({"contract_id": contract.id})
        return payment

    def test_native_partner_guidance_default_soft_and_explicit_policy(self):
        """Real ORM facts/policy and available precheck; no submission side effects."""
        payment = self._create_payment_request_minimal()
        baseline = self.env["project.funding.baseline"].create({
            "project_id": payment.project_id.id, "total_amount": 1000.0,
            "period_start": "2026-01-01", "period_end": "2026-12-31",
            "line_ids": [(0, 0, {"name": "风险验收预算", "planned_amount": 1000.0})],
        })
        baseline.action_activate()
        partner = payment.partner_id
        params = self.env["ir.config_parameter"].sudo()
        handler = PaymentRequestAvailableActionsHandler(self.env, payload={})
        for active, blacklisted, level in ((True, False, "attention"), (True, True, "restricted"), (True, True, "blocked"), (False, False, "attention")):
            with self.subTest(active=active, blacklisted=blacklisted, level=level), self.env.cr.savepoint():
                partner.write({"active": active, "sc_blacklisted": blacklisted, "sc_blacklist_level": level, "sc_blacklist_reason": "Native test risk"})
                for global_force, code_force in ((False, False), (False, True), (True, False)):
                    params.set_param("sc.payment.force_block_all", global_force)
                    for code in ("PARTNER_TRANSACTION_BLOCKED", "PARTNER_TRANSACTION_REVIEW_REQUIRED"):
                        params.set_param("sc.payment.force_block." + code.lower(), code_force)
                    payment.invalidate_recordset(["submit_action_guidance"])
                    fact = payment.submit_action_guidance
                    expected_block = not active or (blacklisted and (global_force or code_force))
                    self.assertEqual(fact["blocking"], expected_block)
                    self.assertEqual(fact["requires_confirmation"], active and blacklisted and not expected_block)
                    self.assertEqual(fact["method"], "action_submit")
                    advisories = payment._collect_payment_advisories("submit")
                    partner_items = [item for item in advisories if item["reason_code"].startswith("PARTNER_TRANSACTION_")]
                    if fact["message"]:
                        self.assertEqual(len(partner_items), 1)
                        self.assertEqual(partner_items[0]["force_block_enabled"], expected_block)
                    else:
                        self.assertEqual(partner_items, [])
                    # Other native advisories remain distinct; this gate exercises the
                    # actual collector's partner result rather than rebuilding it.
                    allowed, _reason = handler._evaluate_prerequisites(payment, "submit", advisories=partner_items)
                    self.assertEqual(allowed, not expected_block)
                    if not active or blacklisted:
                        self.assertTrue(fact["message"])
        # TransactionCase rolls back parameters and fixtures; this is not a live policy edit.

    def test_available_actions_missing_id(self):
        handler = PaymentRequestAvailableActionsHandler(self.env, payload={})
        result = handler.handle({"request_id": "req-pr-actions-missing"})
        self.assertFalse(result.get("ok"))
        self.assertEqual(int(result.get("code") or 0), 400)
        self.assertEqual(((result.get("error") or {}).get("reason_code")), REASON_MISSING_PARAMS)

    def test_available_actions_not_found(self):
        handler = PaymentRequestAvailableActionsHandler(self.env, payload={})
        result = handler.handle({"id": 999999999})
        self.assertFalse(result.get("ok"))
        self.assertEqual(int(result.get("code") or 0), 404)
        self.assertEqual(((result.get("error") or {}).get("reason_code")), REASON_NOT_FOUND)

    def test_available_actions_success_shape(self):
        payment = self._create_payment_request_minimal()
        finance_user = self._create_user(
            "payment_actions_finance_user",
            ["base.group_user", "smart_construction_core.group_sc_cap_finance_user"],
        )
        payment.project_id.user_id = finance_user
        handler = PaymentRequestAvailableActionsHandler(
            self.env(user=finance_user.id), payload={}
        )
        result = handler.handle({"id": payment.id})
        self.assertTrue(result.get("ok"))
        data = result.get("data") or {}
        self.assertEqual(data.get("reason_code"), REASON_OK)
        self.assertEqual(data.get("primary_action_key"), "submit")
        actions = data.get("actions") or []
        keys = {str(item.get("key") or "") for item in actions if isinstance(item, dict)}
        self.assertEqual(keys, {"submit", "approve", "reject", "done"})
        by_key = {str(item.get("key") or ""): item for item in actions if isinstance(item, dict)}
        submit = by_key.get("submit") or {}
        self.assertEqual(submit.get("label"), "提交审批")
        self.assertEqual(submit.get("execute_intent"), "payment.request.execute")
        self.assertEqual((submit.get("execute_params") or {}).get("id"), payment.id)
        self.assertEqual((submit.get("execute_params") or {}).get("action"), "submit")
        self.assertTrue(bool(submit.get("idempotency_required")))
        self.assertEqual(submit.get("reason_code"), REASON_OK)
        self.assertTrue(bool(submit.get("allowed")))
        self.assertEqual(submit.get("current_state"), "draft")
        self.assertEqual(submit.get("next_state_hint"), "submit")
        self.assertTrue(bool(submit.get("allowed_by_state")))
        self.assertTrue(bool(submit.get("allowed_by_method")))
        self.assertTrue(bool(submit.get("allowed_by_precheck")))
        self.assertFalse(str(submit.get("blocked_message") or "").strip())
        self.assertEqual(submit.get("required_role_key"), "finance")
        self.assertEqual(submit.get("required_role_label"), "财务")
        self.assertEqual(submit.get("required_group_xmlid"), "smart_construction_core.group_sc_cap_finance_user")
        self.assertTrue(str(submit.get("handoff_hint") or "").strip())
        self.assertEqual((submit.get("presentation") or {}).get("tier"), "primary")
        self.assertEqual((submit.get("presentation") or {}).get("semantic"), "default")
        self.assertEqual((submit.get("presentation") or {}).get("requires_confirmation"), bool(submit.get("warning_message")))
        reject = by_key.get("reject") or {}
        self.assertEqual((reject.get("presentation") or {}).get("tier"), "secondary")
        self.assertEqual((reject.get("presentation") or {}).get("semantic"), "destructive")
        self.assertTrue((reject.get("presentation") or {}).get("requires_reason"))
        self.assertIsInstance(submit.get("actor_matches_required_role"), bool)
        self.assertIsInstance(submit.get("handoff_required"), bool)
        self.assertEqual(int(submit.get("delivery_priority") or 0), 10)
        reject = by_key.get("reject") or {}
        self.assertEqual(reject.get("reason_code"), REASON_BUSINESS_RULE_FAILED)
        self.assertTrue(bool(reject.get("requires_reason")))
        self.assertEqual(reject.get("required_role_key"), "executive")
        self.assertEqual(reject.get("required_role_label"), "管理层")
        self.assertEqual(reject.get("required_group_xmlid"), "smart_construction_core.group_sc_role_executive")
        self.assertIsInstance(reject.get("actor_matches_required_role"), bool)
        self.assertIsInstance(reject.get("handoff_required"), bool)
        self.assertEqual(int(reject.get("delivery_priority") or 0), 30)
        submit = next(item for item in actions if item.get("key") == "submit")
        self.assertTrue(bool(submit.get("allowed")))
        reject = next(item for item in actions if item.get("key") == "reject")
        self.assertIn("reason", list(reject.get("required_params") or []))

    def test_finance_manager_inherits_submit_capability(self):
        payment = self._create_payment_request_minimal()
        manager = self._create_user(
            "payment_submit_finance_manager",
            ["base.group_user", "smart_construction_core.group_sc_role_finance_manager"],
        )
        result = PaymentRequestAvailableActionsHandler(
            self.env(user=manager.id), payload={"id": payment.id}
        ).handle({"id": payment.id})
        self.assertTrue(result.get("ok"))
        submit = next(row for row in (result.get("data") or {}).get("actions", []) if row.get("key") == "submit")
        self.assertTrue(submit.get("allowed"))
        self.assertTrue(submit.get("actor_matches_required_role"))
        self.assertFalse(submit.get("handoff_required"))

    def test_pay_request_done_action_requires_professional_execution(self):
        payment = self._create_payment_request_minimal()
        manager = self._create_user(
            "payment_done_finance_manager",
            ["base.group_user", "smart_construction_core.group_sc_cap_finance_manager"],
        )
        payment.project_id.user_id = manager
        self.env.cr.execute(
            "UPDATE payment_request SET state='approved', validation_status='validated' WHERE id=%s",
            (payment.id,),
        )
        payment.invalidate_recordset(["state", "validation_status"])
        result = PaymentRequestAvailableActionsHandler(
            self.env(user=manager.id), payload={"id": payment.id}
        ).handle({"id": payment.id})
        done = next(
            row
            for row in (result.get("data") or {}).get("actions", [])
            if row.get("key") == "done"
        )
        self.assertFalse(done.get("allowed"))
        self.assertEqual(done.get("reason_code"), "PAYMENT_EXECUTION_REQUIRED")

    def test_rejected_request_exposes_re_submit_as_the_legal_primary_action(self):
        payment = self._create_payment_request_minimal()
        finance_user = self._create_user(
            "payment_actions_rejected_finance_user",
            ["base.group_user", "smart_construction_core.group_sc_cap_finance_user"],
        )
        payment.project_id.user_id = finance_user
        self.env.cr.execute(
            "UPDATE payment_request SET state='rejected', reject_reason=%s WHERE id=%s",
            ("请补充合同签章页", payment.id),
        )
        payment.invalidate_recordset(["state", "reject_reason"])
        result = PaymentRequestAvailableActionsHandler(
            self.env(user=finance_user.id), payload={"id": payment.id}
        ).handle({"id": payment.id})
        self.assertTrue(result.get("ok"))
        self.assertEqual((result.get("data") or {}).get("primary_action_key"), "submit")
        submit = next(
            row
            for row in (result.get("data") or {}).get("actions", [])
            if row.get("key") == "submit"
        )
        self.assertEqual(submit.get("label"), "重新提交审批")
        self.assertTrue(submit.get("allowed"))
        self.assertTrue(submit.get("allowed_by_state"))
        self.assertEqual(submit.get("state_required"), ["draft", "rejected"])
