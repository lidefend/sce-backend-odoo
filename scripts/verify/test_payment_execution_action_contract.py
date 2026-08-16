#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_NAME = "addons.smart_construction_core.services.financial_workspace_contract"
for package_name, package_path in (
    ("addons.smart_construction_core", ROOT / "addons" / "smart_construction_core"),
    ("addons.smart_construction_core.services", ROOT / "addons" / "smart_construction_core" / "services"),
    ("addons.smart_construction_core.models", ROOT / "addons" / "smart_construction_core" / "models"),
    ("addons.smart_construction_core.models.support", ROOT / "addons" / "smart_construction_core" / "models" / "support"),
):
    package = types.ModuleType(package_name)
    package.__path__ = [str(package_path)]
    sys.modules[package_name] = package
sys.modules["addons.smart_construction_core.models.support.operating_metrics"] = types.ModuleType(
    "addons.smart_construction_core.models.support.operating_metrics"
)
SPEC = importlib.util.spec_from_file_location(
    MODULE_NAME,
    ROOT / "addons" / "smart_construction_core" / "services" / "financial_workspace_contract.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[MODULE_NAME] = MODULE
SPEC.loader.exec_module(MODULE)
ACTION_MODULE_NAME = "addons.smart_construction_core.services.payment_execution_business_actions"
ACTION_SPEC = importlib.util.spec_from_file_location(
    ACTION_MODULE_NAME,
    ROOT / "addons" / "smart_construction_core" / "services" / "payment_execution_business_actions.py",
)
ACTION_MODULE = importlib.util.module_from_spec(ACTION_SPEC)
assert ACTION_SPEC and ACTION_SPEC.loader
sys.modules[ACTION_MODULE_NAME] = ACTION_MODULE
ACTION_SPEC.loader.exec_module(ACTION_MODULE)
build_actions = ACTION_MODULE.build_payment_execution_form_actions
build_semantics = ACTION_MODULE.build_payment_execution_task_semantics
build_form_actions = MODULE.build_financial_form_business_actions


class Record:
    _name = "sc.payment.execution"

    def __init__(
        self,
        *,
        state="draft",
        validation_status="no",
        source_origin="manual",
        finance_handler=True,
        finance_manager=False,
        can_review=False,
        reversal_reason="",
        precheck_error="",
    ):
        self.state = state
        self.validation_status = validation_status
        self.source_origin = source_origin
        self.can_review = can_review
        self.reversal_reason = reversal_reason
        self._finance_handler = finance_handler
        self._finance_manager = finance_manager
        self._precheck_error = precheck_error
        self.project_id = 11
        self.payment_request_id = Request()
        self.contract_id = 12
        self.partner_id = 13
        self.paid_amount = 80
        self.payment_account_name = "FE Company"
        self.payment_bank_name = "FE Bank"
        self.payment_account_no = "****5678"
        self.bank_account = ""
        self.receipt_account_name = "FE Partner"
        self.receipt_bank_name = "FE Receipt Bank"
        self.receipt_account_no = "****1234"
        self.payment_method = "bank"

    def _has_finance_handling_access(self):
        return self._finance_handler

    def _has_finance_confirm_access(self):
        return self._finance_manager

    def _check_business_anchor_or_raise(self):
        if self._precheck_error:
            raise ValueError(self._precheck_error)

    def _check_payment_request_scope_or_raise(self):
        return None

    def _check_company_contractor_payment_responsibility_or_raise(self):
        return None


class Request:
    material_settlement_id = None
    unpaid_amount = 80

    def _has_payment_basis(self):
        return True


def by_method(record: Record) -> dict[str, dict]:
    return {row["method"]: row for row in build_actions(record)}


class PaymentExecutionActionContractTest(unittest.TestCase):
    def test_financial_form_dispatches_payment_execution_authority(self):
        record = Record()

        class Model:
            def browse(self, record_id):
                self.record_id = record_id
                return record

        model = Model()
        original = MODULE._safe_record
        MODULE._safe_record = lambda value: value
        try:
            payload = build_form_actions({"sc.payment.execution": model}, "sc.payment.execution", 17)
        finally:
            MODULE._safe_record = original
        self.assertEqual(model.record_id, 17)
        self.assertIn("action_confirm", {row["method"] for row in payload["actions"]})
        self.assertEqual(payload["task_semantics"]["version"], "v1")
        self.assertFalse(payload["task_semantics"]["blockers"]["payment_fact_readiness"]["active"])

    def test_draft_uses_model_handling_capability_and_keeps_manager_handoff_visible(self):
        rows = by_method(Record())
        self.assertTrue(rows["action_confirm"]["business_available"])
        self.assertTrue(rows["action_confirm"]["authorization_allowed"])
        self.assertTrue(rows["action_confirm"]["enabled"])
        self.assertTrue(rows["action_cancel"]["allowed"])
        self.assertFalse(rows["action_cancel"]["enabled"])
        self.assertEqual(rows["action_cancel"]["reason_code"], "ROLE_HANDOFF_REQUIRED")

    def test_precheck_failure_disables_submit_without_hiding_it(self):
        row = by_method(Record(precheck_error="缺少付款账户"))["action_confirm"]
        self.assertTrue(row["allowed"])
        self.assertFalse(row["business_available"])
        self.assertFalse(row["enabled"])
        self.assertEqual(row["reason_code"], "PAYMENT_EXECUTION_FACTS_INCOMPLETE")
        self.assertEqual(row["blocked_message"], "缺少付款账户")

    def test_task_semantics_materialize_exact_model_precheck(self):
        record = Record(precheck_error="缺少付款账户")
        record.payment_account_name = ""
        semantics = build_semantics(record)
        blocker = semantics["blockers"]["payment_fact_readiness"]
        self.assertTrue(blocker["active"])
        self.assertEqual(blocker["reason_code"], "PAYMENT_EXECUTION_FACTS_INCOMPLETE")
        self.assertEqual(blocker["message"], "缺少付款账户")
        self.assertIn("付款户名", blocker["missing_items"])
        self.assertIn("payment_account_name", blocker["repair_field_names"])

    def test_task_semantics_do_not_turn_optional_reversal_into_global_blocker(self):
        semantics = build_semantics(Record(state="paid", finance_manager=True, reversal_reason=""))
        self.assertFalse(semantics["blockers"]["payment_fact_readiness"]["active"])

    def test_invalid_amount_is_named_by_domain_blocker(self):
        record = Record(precheck_error="实付金额必须大于0")
        record.paid_amount = -1
        blocker = build_semantics(record)["blockers"]["payment_fact_readiness"]
        self.assertTrue(blocker["active"])
        self.assertIn("本次实付金额", blocker["missing_items"])
        self.assertIn("paid_amount", blocker["repair_field_names"])

    def test_readonly_source_gap_has_no_false_local_repair_field(self):
        record = Record(precheck_error="收款账号缺失")
        record.receipt_account_no = ""
        blocker = build_semantics(record)["blockers"]["payment_fact_readiness"]
        self.assertIn("收款账号", blocker["missing_items"])
        self.assertNotIn("receipt_account_no", blocker["repair_field_names"])

    def test_pending_approval_uses_oca_can_review_verdict(self):
        denied = by_method(Record(validation_status="pending", can_review=False))
        self.assertFalse(denied["validate_tier"]["enabled"])
        self.assertEqual(denied["validate_tier"]["reason_code"], "ROLE_HANDOFF_REQUIRED")
        allowed = by_method(Record(validation_status="pending", can_review=True))
        self.assertTrue(allowed["validate_tier"]["enabled"])
        self.assertTrue(allowed["reject_tier"]["enabled"])
        self.assertTrue(allowed["reject_tier"]["requires_reason"])

    def test_confirmed_paid_action_uses_finance_manager_capability(self):
        denied = by_method(Record(state="confirmed", validation_status="validated"))
        self.assertFalse(denied["action_paid"]["enabled"])
        allowed = by_method(Record(state="confirmed", validation_status="validated", finance_manager=True))
        self.assertTrue(allowed["action_paid"]["enabled"])

    def test_reversal_requires_reason_and_manager(self):
        missing = by_method(Record(state="paid", validation_status="validated", finance_manager=True))
        self.assertFalse(missing["action_reverse_payment"]["enabled"])
        self.assertEqual(missing["action_reverse_payment"]["reason_code"], "REVERSAL_REASON_REQUIRED")
        ready = by_method(Record(state="paid", validation_status="validated", finance_manager=True, reversal_reason="重复付款"))
        self.assertTrue(ready["action_reverse_payment"]["enabled"])

    def test_legacy_records_do_not_publish_cancel_or_reverse(self):
        confirmed = by_method(Record(state="legacy_confirmed", source_origin="legacy", finance_manager=True))
        paid = by_method(Record(state="paid", source_origin="legacy", finance_manager=True, reversal_reason="x"))
        self.assertNotIn("action_cancel", confirmed)
        self.assertNotIn("action_reverse_payment", paid)


if __name__ == "__main__":
    unittest.main()
