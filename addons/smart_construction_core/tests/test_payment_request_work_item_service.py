# -*- coding: utf-8 -*-

import base64
from types import SimpleNamespace

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core.services.payment_request_work_item_service import (
    PaymentRequestWorkItemService,
)
from odoo.addons.smart_construction_core.handlers.my_work_summary import MyWorkSummaryHandler


@tagged("sc_smoke", "payment_request_work_item_service")
class TestPaymentRequestWorkItemService(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create({"name": "Work Item Vendor"})
        cls.project = cls.env["project.project"].create(
            {
                "name": "Work Item Project",
                "code": "WORK-ITEM",
                "company_id": cls.company.id,
                "funding_enabled": True,
            }
        )
        baseline = cls.env["project.funding.baseline"].create({
            "project_id": cls.project.id, "total_amount": 1000.0,
            "period_start": "2020-01-01", "period_end": "2099-12-31",
            "line_ids": [(0, 0, {"name": "综合资金计划", "planned_amount": 1000.0})],
        })
        baseline.action_activate()
        cls.contract = cls.env["construction.contract"].create(
            {
                "subject": "Work Item Contract",
                "type": "in",
                "project_id": cls.project.id,
                "partner_id": cls.partner.id,
            }
        )
        cls.finance = cls._user(
            "work_item_finance",
            ["smart_construction_core.group_sc_cap_finance_manager"],
        )
        cls.executive = cls._user(
            "work_item_executive",
            ["smart_construction_core.group_sc_role_executive"],
        )
        cls.member = cls._user(
            "work_item_member",
            ["smart_construction_core.group_sc_cap_project_read"],
        )
        cls.project.message_subscribe(partner_ids=[cls.member.partner_id.id])
        cls.draft = cls.env["payment.request"].create(
            {
                "name": "WORK-ITEM-DRAFT-001",
                "type": "pay",
                "project_id": cls.project.id,
                "partner_id": cls.partner.id,
                "amount": 100.0,
                "state": "draft",
            }
        )
        cls.submitted = cls.env["payment.request"].create(
            {
                "name": "WORK-ITEM-SUBMIT-001",
                "type": "pay",
                "project_id": cls.project.id,
                "partner_id": cls.partner.id,
                "amount": 80.0,
                # The work-item projection is the unit under test.  Establish
                # the submitted starting state below without coupling this
                # fixture to the independent funding-gate workflow.
                "state": "draft",
            }
        )
        cls.rejected = cls.env["payment.request"].create(
            {
                "name": "WORK-ITEM-REJECTED-001",
                "type": "pay",
                "project_id": cls.project.id,
                "partner_id": cls.partner.id,
                "amount": 60.0,
                "state": "draft",
            }
        )
        for index, request in enumerate((cls.draft, cls.submitted, cls.rejected), start=1):
            cls.env["payment.request.line"].create(
                {
                    "request_id": request.id,
                    "legacy_line_id": "WORK-ITEM-LINE-%s" % index,
                    "legacy_parent_id": "WORK-ITEM-PARENT-%s" % index,
                    "contract_id": cls.contract.id,
                    "amount": request.amount,
                    "current_pay_amount": request.amount,
                }
            )
            request.write({"contract_id": cls.contract.id})
        cls.env["ir.attachment"].create(
            {
                "name": "work-item.txt",
                "type": "binary",
                "datas": base64.b64encode(b"work item").decode("ascii"),
                "res_model": "payment.request",
                "res_id": cls.draft.id,
            }
        )
        cls.env.cr.execute(
            """UPDATE payment_request
                  SET create_uid=%s,
                      state=CASE
                          WHEN id=%s THEN 'submit'
                          WHEN id=%s THEN 'rejected'
                          ELSE state
                      END,
                      reject_reason=CASE WHEN id=%s THEN '请补充签章页' ELSE reject_reason END
                WHERE id IN %s""",
            (
                cls.finance.id,
                cls.submitted.id,
                cls.rejected.id,
                cls.rejected.id,
                tuple([cls.draft.id, cls.submitted.id, cls.rejected.id]),
            ),
        )
        (cls.draft | cls.submitted | cls.rejected).invalidate_recordset(
            ["create_uid", "state", "reject_reason"]
        )

    @classmethod
    def _user(cls, login, group_xmlids):
        group_ids = [cls.env.ref("base.group_user").id]
        group_ids.extend(cls.env.ref(xmlid).id for xmlid in group_xmlids)
        return cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": "%s@example.com" % login,
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "groups_id": [(6, 0, group_ids)],
            }
        )

    def _workspace(self, user):
        service = PaymentRequestWorkItemService(
            self.env(user=user.id),
            params={},
            context={},
        )
        return service.build()

    def test_finance_sees_submit_and_own_items_with_matching_counts(self):
        workspace = self._workspace(self.finance)
        by_key = {row["key"]: row for row in workspace["sections"]}
        todo_names = {item["record"]["label"] for item in by_key["todo"]["items"]}
        initiated_names = {item["record"]["label"] for item in by_key["initiated"]["items"]}
        self.assertTrue(any("WORK-ITEM-DRAFT-001" in name for name in todo_names))
        self.assertTrue(any("WORK-ITEM-REJECTED-001" in name for name in todo_names))
        self.assertTrue(any("WORK-ITEM-SUBMIT-001" in name for name in todo_names))
        self.assertTrue(any("WORK-ITEM-DRAFT-001" in name for name in initiated_names))
        self.assertTrue(any("WORK-ITEM-SUBMIT-001" in name for name in initiated_names))
        self.assertEqual(workspace["counts"]["todo"], len(by_key["todo"]["items"]))
        self.assertEqual(workspace["counts"]["initiated"], len(by_key["initiated"]["items"]))
        draft = next(item for item in by_key["todo"]["items"] if "WORK-ITEM-DRAFT-001" in item["record"]["label"])
        rejected = next(
            item
            for item in by_key["todo"]["items"]
            if "WORK-ITEM-REJECTED-001" in item["record"]["label"]
        )
        self.assertEqual([row["key"] for row in draft["actions"]], ["submit"])
        self.assertEqual([row["key"] for row in rejected["actions"]], ["submit"])
        submitted = next(
            item
            for item in by_key["todo"]["items"]
            if "WORK-ITEM-SUBMIT-001" in item["record"]["label"]
        )
        self.assertEqual([row["key"] for row in submitted["actions"]], ["approve", "reject"])
        self.assertEqual(rejected["actions"][0]["label"], "重新提交审批")
        self.assertEqual(rejected["facts"][0], {"key": "reject_reason", "label": "驳回原因", "value": "请补充签章页"})
        self.assertEqual(draft["actions"][0]["presentation"]["tier"], "primary")
        self.assertEqual(draft["amount"]["value"], 100.0)
        self.assertEqual(
            [row["label"] for row in draft["facts"]],
            ["项目", "公司", "往来方", "金额", "发起人", "发起时间"],
        )
        self.assertIn("WORK-ITEM-DRAFT-001", draft["search_text"])
        self.assertEqual(workspace["presentation"]["default_sort"], "updated_desc")
        self.assertEqual(workspace["presentation"]["quick_links"][0]["label"], "付款申请")
        self.assertEqual(workspace["presentation"]["quick_links"][0]["route"], "/s/finance.payment_requests")
        action = self.env.ref("smart_construction_core.action_payment_request_user_payment_apply")
        menu = self.env.ref("smart_construction_core.menu_sc_user_payment_apply")
        self.assertEqual(draft["target"]["action_ref"], action.get_external_id()[action.id])
        self.assertEqual(draft["target"]["action_id"], action.id)
        self.assertEqual(draft["target"]["menu_id"], menu.id)
        self.assertEqual(
            draft["target"]["route"],
            "/r/payment.request/%s?action_id=%s&menu_id=%s" % (self.draft.id, action.id, menu.id),
        )
        self.assertNotIn("model", draft["record"])

    def test_executive_only_gets_submitted_approval_item(self):
        workspace = self._workspace(self.executive)
        todo = next(row for row in workspace["sections"] if row["key"] == "todo")
        submitted = next(item for item in todo["items"] if "WORK-ITEM-SUBMIT-001" in item["record"]["label"])
        self.assertEqual({row["key"] for row in submitted["actions"]}, {"approve", "reject"})
        by_action = {row["key"]: row for row in submitted["actions"]}
        self.assertEqual(by_action["approve"]["presentation"]["tier"], "primary")
        self.assertEqual(by_action["reject"]["presentation"]["semantic"], "destructive")
        self.assertFalse(any("WORK-ITEM-DRAFT-001" in item["record"]["label"] for item in todo["items"]))

    def test_project_member_has_no_payment_work_item_or_sensitive_facts(self):
        workspace = self._workspace(self.member)
        self.assertEqual(workspace["counts"].get("todo"), 0)
        self.assertEqual(workspace["counts"].get("initiated"), 0)
        serialized = str(workspace)
        self.assertNotIn("WORK-ITEM-DRAFT-001", serialized)
        self.assertNotIn("100.0", serialized)
        self.assertEqual(workspace["presentation"]["quick_links"], [])

    def test_company_scope_is_part_of_query_contract(self):
        workspace = self._workspace(self.finance)
        self.assertEqual(workspace["query_scope"]["company_ids"], [self.company.id])
        for section in workspace["sections"]:
            self.assertEqual(section["count"], len(section["items"]))

    def test_service_source_contains_no_sudo(self):
        import inspect

        source = inspect.getsource(PaymentRequestWorkItemService)
        self.assertNotIn(".sudo(", source)

    def test_action_projection_reuses_record_result_and_skips_impossible_states(self):
        service = PaymentRequestWorkItemService(
            self.env(user=self.finance.id),
            params={},
            context={},
        )
        calls = []
        original = service._action_handler._action_entry

        def counted(record, spec):
            calls.append(str(spec.get("key") or ""))
            return original(record, spec)

        service._action_handler._action_entry = counted
        first = service._allowed_actions(self.draft)
        second = service._allowed_actions(self.draft)

        self.assertEqual(first, second)
        self.assertEqual(calls, ["submit"])

    def test_action_entry_collects_expensive_advisories_once(self):
        handler = PaymentRequestWorkItemService(
            self.env(user=self.finance.id),
            params={},
            context={},
        )._action_handler
        calls = []
        observed_caches = []

        class Contract:
            state = "active"

        class Record:
            id = 987
            state = "draft"
            contract_id = Contract()

            def action_submit(self):
                return True

            def _collect_payment_advisories(self, action_key, evaluation_cache=None):
                observed_caches.append(evaluation_cache)
                calls.append(action_key)
                return []

        submit = next(spec for spec in handler._ACTION_SPECS if spec["key"] == "submit")
        handler._action_entry(Record(), submit)

        self.assertEqual(calls, ["submit"])
        self.assertEqual(len(observed_caches), 1)
        self.assertIsInstance(observed_caches[0], dict)

    def test_action_projection_does_not_evaluate_inapplicable_state_prerequisites(self):
        handler = PaymentRequestWorkItemService(
            self.env(user=self.finance.id),
            params={},
            context={},
        )._action_handler
        advisory_calls = []

        class Contract:
            state = "active"

        class Record:
            id = 988
            state = "draft"
            contract_id = Contract()

            def action_submit(self):
                return True

            def action_approve(self):
                return True

            def action_on_tier_rejected(self):
                return True

            def action_done(self):
                return True

            def _collect_payment_advisories(self, action_key, evaluation_cache=None):
                advisory_calls.append(action_key)
                return []

        actions = [handler._action_entry(Record(), spec) for spec in handler._ACTION_SPECS]

        self.assertEqual(advisory_calls, ["submit"])
        self.assertTrue(actions[0]["allowed_by_precheck"])
        self.assertTrue(all(not action["allowed_by_precheck"] for action in actions[1:]))

    def test_action_projection_reuses_one_advisory_cache_across_records(self):
        handler = PaymentRequestWorkItemService(
            self.env(user=self.finance.id),
            params={},
            context={},
        )._action_handler
        observed_caches = []

        class Contract:
            state = "active"

        class Record:
            state = "draft"
            contract_id = Contract()

            def __init__(self, record_id):
                self.id = record_id

            def action_submit(self):
                return True

            def _collect_payment_advisories(self, action_key, evaluation_cache=None):
                observed_caches.append(evaluation_cache)
                return []

        submit = next(spec for spec in handler._ACTION_SPECS if spec["key"] == "submit")
        handler._action_entry(Record(991), submit)
        handler._action_entry(Record(992), submit)

        self.assertEqual(len(observed_caches), 2)
        self.assertIs(observed_caches[0], observed_caches[1])

    def test_funding_advisory_cache_reuses_project_facts_and_preserves_exclusion(self):
        cache = {}
        baseline_draft = self.draft._get_active_funding_baseline(
            self.project,
            evaluation_cache=cache,
        )
        queries_after_first_baseline = self.env.cr.sql_log_count
        baseline_submitted = self.submitted._get_active_funding_baseline(
            self.project,
            evaluation_cache=cache,
        )
        self.assertEqual(baseline_draft, baseline_submitted)
        self.assertEqual(self.env.cr.sql_log_count, queries_after_first_baseline)
        self.assertIn(("active_funding_baseline", self.project.id), cache)

        (self.draft | self.submitted).read(["project_id", "type", "state", "amount"])
        without_draft = self.draft._get_reserved_amount(
            self.project,
            exclude_ids=self.draft.ids,
            evaluation_cache=cache,
        )
        queries_after_first_reservation = self.env.cr.sql_log_count
        without_submitted = self.submitted._get_reserved_amount(
            self.project,
            exclude_ids=self.submitted.ids,
            evaluation_cache=cache,
        )
        self.assertEqual(without_draft, self.submitted.amount)
        self.assertEqual(without_submitted, 0.0)
        self.assertEqual(self.env.cr.sql_log_count, queries_after_first_reservation)
        self.assertIn(("reserved_amount", self.project.id), cache)

    def test_completed_projection_batches_payment_request_resolution(self):
        service = PaymentRequestWorkItemService(
            self.env(user=self.finance.id),
            params={},
            context={},
        )
        draft_id = self.draft.id
        submitted_id = self.submitted.id

        class AuditModel:
            def check_access_rights(self, operation, raise_exception=False):
                return operation == "read"

            def search(self, domain, order=None, limit=None):
                del domain, order, limit
                return [
                    SimpleNamespace(
                        res_id=draft_id,
                        event_code="PAYMENT_REQUEST_SUBMIT_INTENT",
                        action="submit",
                        ts="2026-08-15 10:00:00",
                    ),
                    SimpleNamespace(
                        res_id=submitted_id,
                        event_code="PAYMENT_REQUEST_APPROVE_INTENT",
                        action="approve",
                        ts="2026-08-15 09:00:00",
                    ),
                ]

        class EnvProxy:
            def __init__(self, env, audit_model):
                self._env = env
                self._audit_model = audit_model

            def get(self, model_name):
                if model_name == "sc.audit.log":
                    return self._audit_model
                return self._env.get(model_name)

            def __getattr__(self, name):
                return getattr(self._env, name)

        service.env = EnvProxy(service.env, AuditModel())
        resolved_batches = []
        original = service._payment_requests_by_id

        def counted(record_ids):
            ids = list(record_ids)
            resolved_batches.append(ids)
            return original(ids)

        service._payment_requests_by_id = counted
        rows, unavailable_reason = service._completed()

        self.assertEqual(unavailable_reason, "")
        self.assertEqual(len(resolved_batches), 1)
        self.assertTrue({self.draft.id, self.submitted.id}.issubset(set(resolved_batches[0])))
        self.assertTrue({self.draft.id, self.submitted.id}.issubset({row["target"]["record_id"] for row in rows}))

    def test_product_handler_does_not_execute_legacy_sudo_aggregation(self):
        handler = MyWorkSummaryHandler(self.env(user=self.finance.id), payload={})
        handler._safe_count = lambda *args, **kwargs: self.fail("legacy aggregation executed")
        result = handler.handle({"product_workspace": True})
        self.assertTrue(result.get("ok"))
        data = result.get("data") or {}
        self.assertEqual(data.get("items"), [])
        self.assertTrue((data.get("product_workspace") or {}).get("version"))
