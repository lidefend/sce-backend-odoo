# -*- coding: utf-8 -*-
"""Real approval-task to final contract and execution regression."""

from odoo.tests.common import tagged

from odoo.addons.smart_core.handlers.execute_button import ExecuteButtonHandler
from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler

from ..services.review_work_item_service import CurrentWorkItemService, authorize_review_origin
from .business_case import BusinessTransactionCase


@tagged("post_install", "-at_install", "approval_contract_closure")
class TestApprovalContractClosure(BusinessTransactionCase):
    """Prove approval page/action authority and execution use the same facts."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.reviewer = cls._create_user(
            cls,
            "synthetic_approval_contract_reviewer",
            cls.env.ref("smart_construction_core.group_sc_cap_finance_manager"),
        )
        cls.contract_submitter = cls._create_user(
            cls,
            "synthetic_approval_contract_submitter",
            cls.env.ref("smart_construction_core.group_sc_cap_contract_user"),
        )
        cls.payment_submitter = cls._create_user(
            cls,
            "synthetic_approval_payment_submitter",
            cls.env.ref("smart_construction_core.group_sc_cap_finance_user"),
        )
        for model_name, label in (
            ("sc.general.contract", "Synthetic general contract approval"),
            ("payment.request", "Synthetic payment request approval"),
        ):
            cls.env["sc.approval.policy"].sudo().create(
                {
                    "name": label,
                    "code": "synthetic_u06_%s_%s" % (model_name.replace(".", "_"), cls.company.id),
                    "target_model": model_name,
                    "company_id": cls.company.id,
                    "approval_required": True,
                    "mode": "single",
                    "manager_scope_key": "finance_manager",
                    "step_ids": [
                        (
                            0,
                            0,
                            {
                                "name": "Synthetic finance manager decision",
                                "approval_scope_key": "finance_manager",
                            },
                        )
                    ],
                }
            )

    @classmethod
    def _create_user(cls, owner, login, permission_group):
        groups = (
            owner.env.ref("base.group_user")
            | permission_group
        )
        return owner.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": "%s@invalid.local" % login,
                "company_id": owner.company.id,
                "company_ids": [(6, 0, [owner.company.id])],
                "groups_id": [(6, 0, groups.ids)],
            }
        )

    @staticmethod
    def _envelope(result):
        return result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result

    def _final_contract(self, env, model, record_id):
        result = UiContractV2Handler(
            env,
            su_env=env["ir.model"].sudo().env,
        ).handle(
            {
                "op": "model",
                "model": model,
                "view_type": "form",
                "record_id": record_id,
                "action_id": 0,
                "menu_id": 0,
                "render_profile": "edit",
                "delivery_profile": "full",
                "client_type": "web_pc",
                "accepted_contract_versions": ["2.2.x"],
                "client_contract_capabilities": [
                    "container_tree.v2",
                    "data_source.v2",
                    "action_rule.v2",
                    "relation_entry.v2",
                    "status_contract.v2",
                ],
            }
        )
        envelope = self._envelope(result)
        self.assertTrue(envelope.get("ok", True), envelope)
        return envelope["data"]

    @staticmethod
    def _action_rows(contract, methods):
        rows = (contract.get("actionContract") or {}).get("actionRuleList") or []
        return {
            method: [row for row in rows if (row.get("button") or {}).get("name") == method]
            for method in methods
        }

    @staticmethod
    def _button_status(contract, row):
        statuses = (contract.get("statusContract") or {}).get("buttonStatus") or []
        action_id = str(row.get("actionId") or "").strip()
        action_key = str(row.get("actionKey") or "").strip()
        backend_identity = str(row.get("backendIdentity") or "").strip()
        status_ids = {
            action_id,
            "btn.%s" % action_id,
            action_key,
            "btn.%s" % action_key,
        }
        matches = [
            status
            for status in statuses
            if str(status.get("backendIdentity") or "").strip() == backend_identity
            or str(status.get("btnId") or "").strip() in status_ids
        ]
        return matches

    def _assert_decision_rows(self, contract, expected):
        rows_by_method = self._action_rows(contract, expected)
        visible = {}
        for method, purpose in expected.items():
            rows = rows_by_method[method]
            self.assertEqual(len(rows), 1, (method, rows))
            row = rows[0]
            self.assertEqual((row.get("button") or {}).get("type"), "object")
            self.assertTrue(row.get("actionId"), row)
            self.assertTrue(row.get("backendIdentity"), row)
            self.assertTrue(row.get("sourceWidgetId"), row)
            self.assertIs(row.get("allowed"), True, row)
            self.assertIs(row.get("enabled"), True, row)
            self.assertIs(row.get("disabled"), False, row)
            self.assertIs(row.get("entitlementEvaluated"), True, row)
            self.assertEqual((row.get("actionSemantics") or {}).get("purpose"), purpose, row)
            statuses = self._button_status(contract, row)
            self.assertEqual(len(statuses), 1, (method, statuses))
            self.assertIs(statuses[0].get("visible"), True, statuses[0])
            self.assertIs(statuses[0].get("disabled"), False, statuses[0])
            visible[method] = row
        return visible

    def _decision_is_available(self, contract, row):
        if not (
            row.get("allowed") is True
            and row.get("enabled") is True
            and row.get("disabled") is False
            and row.get("entitlementEvaluated") is True
        ):
            return False
        statuses = self._button_status(contract, row)
        return (
            len(statuses) == 1
            and statuses[0].get("visible") is True
            and statuses[0].get("disabled") is False
        )

    def _execute_contract_action(self, env, record, row, review, action_params=None):
        button = {
            **(row.get("button") or {}),
            "action_id": row["actionId"],
            "backend_identity": row["backendIdentity"],
            "source_widget_id": row["sourceWidgetId"],
        }
        request_params = {
            "model": record._name,
            "res_id": record.id,
            "button": button,
        }
        if action_params is not None:
            request_params["action_params"] = action_params
        result = ExecuteButtonHandler(
            env,
            payload={
                "params": request_params,
                "meta": {
                    "work_item_origin": {
                        "source": "tier.review",
                        "id": review.id,
                    }
                },
            },
        ).handle()
        return self._envelope(result)

    def _current_review_item(self, env, model, record_id, review_id):
        workspace = CurrentWorkItemService(env).build()
        needle = "%s:%s" % (model, record_id)
        for section in workspace.get("sections") or []:
            for item in section.get("items") or []:
                origin = (item.get("target") or {}).get("work_item_origin") or {}
                if item.get("key") == needle and origin.get("source") == "tier.review" and origin.get("id") == review_id:
                    return item
        return None

    def _general_contract_with_review(self):
        contract = self.env["sc.general.contract"].create(
            {
                "contract_name": "Synthetic U06 approval contract",
                "partner_name_text": "Synthetic U06 counterparty",
                "amount_total": 100.0,
                "company_id": self.company.id,
            }
        )
        contract.with_user(self.contract_submitter).action_confirm()
        contract.invalidate_recordset()
        review = contract.review_ids.filtered(
            lambda row: row.status in ("waiting", "pending")
        )
        self.assertEqual(len(review), 1, contract.review_ids)
        return contract, review

    def _payment_request_with_review(self):
        project = self.env["project.project"].create(
            {
                "name": "Synthetic U06 payment project",
                "company_id": self.company.id,
                "funding_enabled": True,
                "user_id": self.payment_submitter.id,
            }
        )
        project.message_subscribe(partner_ids=[self.payment_submitter.partner_id.id])
        partner = self.env["res.partner"].create({"name": "Synthetic U06 payee"})
        contract = self.env["construction.contract"].create(
            {
                "subject": "Synthetic U06 payment basis",
                "type": "in",
                "project_id": project.id,
                "partner_id": partner.id,
            }
        )
        payment = self.env["payment.request"].sudo().create(
            {
                "name": "Synthetic U06 payment request",
                "type": "pay",
                "project_id": project.id,
                "partner_id": partner.id,
                "amount": 100.0,
                "state": "draft",
            }
        )
        self.env["payment.request.line"].sudo().create(
            {
                "request_id": payment.id,
                "legacy_line_id": "U06-PAYMENT-LINE-%s" % payment.id,
                "legacy_parent_id": "U06-PAYMENT-PARENT-%s" % payment.id,
                "contract_id": contract.id,
                "amount": payment.amount,
                "current_pay_amount": payment.amount,
            }
        )
        payment.sudo().write({"contract_id": contract.id})
        baseline = self.env["project.funding.baseline"].create(
            {
                "project_id": project.id,
                "total_amount": 1000.0,
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
                "line_ids": [(0, 0, {"name": "Synthetic U06 budget", "planned_amount": 1000.0})],
            }
        )
        baseline.action_activate()
        payment.with_user(self.payment_submitter).action_submit()
        payment.invalidate_recordset()
        review = payment.review_ids.filtered(
            lambda row: row.status in ("waiting", "pending")
        )
        self.assertEqual(len(review), 1, payment.review_ids)
        return payment, review

    def test_general_contract_task_drives_page_and_execution_without_general_write(self):
        contract, review = self._general_contract_with_review()
        reviewer_env = contract.with_user(self.reviewer).env
        origin = {"source": "tier.review", "id": review.id}

        self.assertFalse(
            contract.with_user(self.reviewer).check_access_rights("write", raise_exception=False)
        )
        self.assertEqual(
            authorize_review_origin(
                reviewer_env,
                origin,
                model=contract._name,
                record_id=contract.id,
                method_name="validate_tier",
            ),
            {"allowed": True, "record_access_mode": "read"},
        )
        current = self._current_review_item(reviewer_env, contract._name, contract.id, review.id)
        self.assertTrue(current, "assigned approval must be a current work item")
        self.assertEqual(current["target"]["work_item_origin"], origin)
        self.assertEqual(
            current["target"]["route"],
            "/r/sc.general.contract/%s?work_item_source=tier.review&work_item_id=%s"
            % (contract.id, review.id),
        )

        contract_data = self._final_contract(reviewer_env, contract._name, contract.id)
        self.assertEqual(contract_data["pageInfo"]["model"], contract._name)
        self.assertEqual(contract_data["dataContract"]["mainData"]["id"], contract.id)
        actions = self._assert_decision_rows(
            contract_data,
            {"validate_tier": "approve", "reject_tier": "reject"},
        )

        result = self._execute_contract_action(
            reviewer_env,
            contract.with_user(self.reviewer),
            actions["validate_tier"],
            review,
        )
        self.assertTrue(result.get("ok"), result)
        self.assertEqual((result.get("data") or {}).get("result", {}).get("reason_code"), "OK")

        review.invalidate_recordset()
        contract.invalidate_recordset()
        self.assertEqual(review.status, "approved")
        self.assertEqual(contract.validation_status, "validated")
        self.assertEqual(contract.state, "confirmed")
        self.assertIsNone(self._current_review_item(reviewer_env, contract._name, contract.id, review.id))
        self.assertFalse(
            authorize_review_origin(
                reviewer_env,
                origin,
                model=contract._name,
                record_id=contract.id,
                method_name="validate_tier",
            )
        )

        stale = self._execute_contract_action(
            reviewer_env,
            contract.with_user(self.reviewer),
            actions["validate_tier"],
            review,
        )
        self.assertFalse(stale.get("ok"), stale)
        self.assertEqual(int(stale.get("code") or 0), 403)

        completed_contract = self._final_contract(reviewer_env, contract._name, contract.id)
        completed_actions = self._action_rows(
            completed_contract,
            ("validate_tier", "reject_tier"),
        )
        for method, rows in completed_actions.items():
            available = [
                row for row in rows
                if self._decision_is_available(completed_contract, row)
            ]
            self.assertEqual(available, [], (method, available))

    def test_payment_request_control_uses_the_same_contract_and_execution_boundary(self):
        payment, review = self._payment_request_with_review()
        reviewer_env = payment.with_user(self.reviewer).env
        origin = {"source": "tier.review", "id": review.id}

        self.assertEqual(
            authorize_review_origin(
                reviewer_env,
                origin,
                model=payment._name,
                record_id=payment.id,
                method_name="action_approval_decision",
            ),
            True,
        )
        payment_data = self._final_contract(reviewer_env, payment._name, payment.id)
        self.assertEqual(payment_data["pageInfo"]["model"], payment._name)
        self.assertEqual(payment_data["dataContract"]["mainData"]["id"], payment.id)
        actions = self._assert_decision_rows(
            payment_data,
            {
                "action_approval_decision": "approve",
                "action_approval_reject": "reject",
            },
        )

        result = self._execute_contract_action(
            reviewer_env,
            payment.with_user(self.reviewer),
            actions["action_approval_decision"],
            review,
        )
        self.assertTrue(result.get("ok"), result)
        self.assertEqual((result.get("data") or {}).get("result", {}).get("reason_code"), "OK")

        review.invalidate_recordset()
        payment.invalidate_recordset()
        self.assertEqual(review.status, "approved")
        self.assertEqual(payment.validation_status, "validated")
        self.assertEqual(payment.state, "approved")
        self.assertFalse(
            authorize_review_origin(
                reviewer_env,
                origin,
                model=payment._name,
                record_id=payment.id,
                method_name="action_approval_decision",
            )
        )

        stale = self._execute_contract_action(
            reviewer_env,
            payment.with_user(self.reviewer),
            actions["action_approval_decision"],
            review,
        )
        self.assertFalse(stale.get("ok"), stale)
        self.assertEqual(int(stale.get("code") or 0), 403)

    def test_payment_reject_consumes_the_declared_reason_before_and_at_execution(self):
        payment, review = self._payment_request_with_review()
        reviewer_env = payment.with_user(self.reviewer).env
        origin = {"source": "tier.review", "id": review.id}
        self.assertTrue(
            authorize_review_origin(
                reviewer_env,
                origin,
                model=payment._name,
                record_id=payment.id,
                method_name="action_approval_reject",
            )
        )

        payment_data = self._final_contract(reviewer_env, payment._name, payment.id)
        actions = self._assert_decision_rows(
            payment_data,
            {
                "action_approval_decision": "approve",
                "action_approval_reject": "reject",
            },
        )
        self.assertFalse(
            any(
                (row.get("button") or {}).get("name") == "reject_tier"
                for row in (payment_data.get("actionContract") or {}).get("actionRuleList", [])
            ),
            "the runtime business-action projection must not republish the legacy reject method",
        )
        reject = actions["action_approval_reject"]
        self.assertEqual(reject.get("required_params"), ["reason"], reject)
        self.assertIs(reject.get("requires_reason"), True, reject)

        missing = self._execute_contract_action(reviewer_env, payment.with_user(self.reviewer), reject, review)
        self.assertFalse(missing.get("ok"), missing)
        self.assertEqual(int(missing.get("code") or 0), 400)
        review.invalidate_recordset()
        payment.invalidate_recordset()
        self.assertEqual(review.status, "pending")
        self.assertEqual(payment.state, "submit")
        self.assertFalse(payment.reject_reason)

        undeclared = self._execute_contract_action(
            reviewer_env,
            payment.with_user(self.reviewer),
            reject,
            review,
            action_params={"reason": "Synthetic rejection", "write_all_fields": True},
        )
        self.assertFalse(undeclared.get("ok"), undeclared)
        self.assertEqual(int(undeclared.get("code") or 0), 400)
        review.invalidate_recordset()
        payment.invalidate_recordset()
        self.assertEqual(review.status, "pending")
        self.assertEqual(payment.state, "submit")
        self.assertFalse(payment.reject_reason)

        result = self._execute_contract_action(
            reviewer_env,
            payment.with_user(self.reviewer),
            reject,
            review,
            action_params={"reason": "Synthetic rejection"},
        )
        self.assertTrue(result.get("ok"), result)
        self.assertEqual((result.get("data") or {}).get("result", {}).get("reason_code"), "OK")

        review.invalidate_recordset()
        payment.invalidate_recordset()
        self.assertEqual(review.status, "rejected")
        self.assertEqual(payment.validation_status, "rejected")
        self.assertEqual(payment.state, "rejected")
        self.assertEqual(payment.reject_reason, "Synthetic rejection")
        self.assertIsNone(self._current_review_item(reviewer_env, payment._name, payment.id, review.id))

        stale = self._execute_contract_action(
            reviewer_env,
            payment.with_user(self.reviewer),
            reject,
            review,
            action_params={"reason": "Replay must not execute"},
        )
        self.assertFalse(stale.get("ok"), stale)
        self.assertEqual(int(stale.get("code") or 0), 403)
