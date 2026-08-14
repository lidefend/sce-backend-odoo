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
        project = self.env["project.project"].create({"name": "Action Matrix Project", "funding_enabled": True})
        partner = self.env["res.partner"].create({"name": "Action Matrix Partner"})
        contract = self.env["construction.contract"].create(
            {
                "subject": "Action Matrix Contract",
                "type": "in",
                "project_id": project.id,
                "partner_id": partner.id,
            }
        )
        return self.env["payment.request"].sudo().create(
            {
                "name": "INTENT-ACTIONS-PR-001",
                "type": "pay",
                "project_id": project.id,
                "contract_id": contract.id,
                "partner_id": partner.id,
                "amount": 100,
                "state": "draft",
            }
        )

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
        handler = PaymentRequestAvailableActionsHandler(self.env, payload={})
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
        self.assertTrue((submit.get("presentation") or {}).get("requires_confirmation"))
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
