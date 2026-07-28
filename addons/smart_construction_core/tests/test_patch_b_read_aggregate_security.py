# -*- coding: utf-8 -*-
from __future__ import annotations

import inspect
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core.handlers.business_evidence_trace import (
    BusinessEvidenceTraceHandler,
)
from odoo.addons.smart_construction_core.handlers.cost_tracking_block_fetch import (
    CostTrackingBlockFetchHandler,
)
from odoo.addons.smart_construction_core.handlers.cost_tracking_enter import (
    CostTrackingEnterHandler,
)
from odoo.addons.smart_construction_core.handlers.dashboard_company_enter import (
    DashboardCompanyEnterHandler,
)
from odoo.addons.smart_construction_core.handlers.my_work_summary import (
    MyWorkSummaryHandler,
)
from odoo.addons.smart_construction_core.handlers.payment_slice_block_fetch import (
    PaymentSliceBlockFetchHandler,
)
from odoo.addons.smart_construction_core.handlers.payment_slice_enter import (
    PaymentSliceEnterHandler,
)
from odoo.addons.smart_construction_core.handlers.project_execution_block_fetch import (
    ProjectExecutionBlockFetchHandler,
)
from odoo.addons.smart_construction_core.handlers.project_execution_enter import (
    ProjectExecutionEnterHandler,
)
from odoo.addons.smart_construction_core.handlers.project_plan_bootstrap_block_fetch import (
    ProjectPlanBootstrapBlockFetchHandler,
)
from odoo.addons.smart_construction_core.handlers.project_plan_bootstrap_enter import (
    ProjectPlanBootstrapEnterHandler,
)
from odoo.addons.smart_construction_core.handlers.settlement_slice_block_fetch import (
    SettlementSliceBlockFetchHandler,
)
from odoo.addons.smart_construction_core.handlers.settlement_slice_enter import (
    SettlementSliceEnterHandler,
)
from odoo.addons.smart_construction_core.services.cost_tracking_native_adapter import (
    CostTrackingNativeAdapter,
)
from odoo.addons.smart_construction_core.services.cost_tracking_service import (
    CostTrackingService,
)
from odoo.addons.smart_construction_core.services.evidence_chain_service import (
    EvidenceChainService,
)
from odoo.addons.smart_construction_core.services.payment_slice_native_adapter import (
    PaymentSliceNativeAdapter,
)
from odoo.addons.smart_construction_core.services.payment_slice_service import (
    PaymentSliceService,
)
from odoo.addons.smart_construction_core.services.project_execution_item_projection_service import (
    ProjectExecutionItemProjectionService,
)
from odoo.addons.smart_construction_core.services.project_execution_consistency_guard import (
    ProjectExecutionConsistencyGuard,
)
from odoo.addons.smart_construction_core.services.project_execution_service import (
    ProjectExecutionService,
)
from odoo.addons.smart_construction_core.services.project_plan_bootstrap_service import (
    ProjectPlanBootstrapService,
)
from odoo.addons.smart_construction_core.services.settlement_slice_service import (
    SettlementSliceService,
)


@tagged("post_install", "-at_install", "admin_vis_patch_b")
class TestPatchBReadAggregateSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create(
            {"name": "PATCH B synthetic company B"}
        )
        base_user = cls.env.ref("base.group_user")
        project_read = cls.env.ref(
            "smart_construction_core.group_sc_cap_project_read"
        )

        def create_user(login, companies):
            return cls.env["res.users"].with_context(
                no_reset_password=True
            ).create(
                {
                    "name": login,
                    "login": login,
                    "email": "%s@example.invalid" % login,
                    "company_id": companies[0].id,
                    "company_ids": [(6, 0, companies.ids)],
                    "groups_id": [(6, 0, [base_user.id, project_read.id])],
                }
            )

        cls.user_a1 = create_user("patch_b_user_a1", cls.company_a)
        cls.user_a2 = create_user("patch_b_user_a2", cls.company_a)
        cls.user_same_company_denied = create_user(
            "patch_b_user_same_company_denied",
            cls.company_a,
        )
        cls.user_b1 = create_user("patch_b_user_b1", cls.company_b)
        cls.multi_company_user = create_user(
            "patch_b_multi_company_user",
            cls.company_a | cls.company_b,
        )

        project_context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company_a.id, cls.company_b.id],
            "mail_create_nosubscribe": True,
            "mail_notify_noemail": True,
            "tracking_disable": True,
        }
        Project = cls.env["project.project"].with_context(project_context)
        cls.project_a1 = Project.create(
            {
                "name": "PATCH B Project A1",
                "company_id": cls.company_a.id,
                "privacy_visibility": "followers",
                "user_id": cls.user_a1.id,
            }
        )
        cls.project_a2 = Project.create(
            {
                "name": "PATCH B Project A2",
                "company_id": cls.company_a.id,
                "privacy_visibility": "followers",
                "user_id": cls.user_a2.id,
            }
        )
        cls.project_b1 = Project.create(
            {
                "name": "PATCH B Project B1",
                "company_id": cls.company_b.id,
                "privacy_visibility": "followers",
                "user_id": cls.user_b1.id,
            }
        )
        cls.project_a1.message_subscribe(
            partner_ids=[cls.multi_company_user.partner_id.id]
        )
        cls.project_b1.message_subscribe(
            partner_ids=[cls.multi_company_user.partner_id.id]
        )
        Task = cls.env["project.task"].with_context(project_context)
        cls.task_a1 = Task.create(
            {"name": "PATCH B Task A1", "project_id": cls.project_a1.id}
        )
        cls.task_a2 = Task.create(
            {"name": "PATCH B Task A2", "project_id": cls.project_a2.id}
        )
        cls.task_b1 = Task.create(
            {"name": "PATCH B Task B1", "project_id": cls.project_b1.id}
        )
        activity_type = cls.env.ref("mail.mail_activity_data_todo")
        activity_model = cls.env["mail.activity"].with_context(project_context)
        cls.activity_a1 = activity_model.create(
            {
                "activity_type_id": activity_type.id,
                "summary": ProjectExecutionConsistencyGuard.FOLLOWUP_SUMMARY,
                "res_model_id": cls.env["ir.model"]._get_id("project.project"),
                "res_id": cls.project_a1.id,
                "user_id": cls.user_a1.id,
            }
        )
        cls.activity_a2 = activity_model.create(
            {
                "activity_type_id": activity_type.id,
                "summary": ProjectExecutionConsistencyGuard.FOLLOWUP_SUMMARY,
                "res_model_id": cls.env["ir.model"]._get_id("project.project"),
                "res_id": cls.project_a2.id,
                "user_id": cls.user_a2.id,
            }
        )
        cls.activity_b1 = activity_model.create(
            {
                "activity_type_id": activity_type.id,
                "summary": ProjectExecutionConsistencyGuard.FOLLOWUP_SUMMARY,
                "res_model_id": cls.env["ir.model"]._get_id("project.project"),
                "res_id": cls.project_b1.id,
                "user_id": cls.user_b1.id,
            }
        )

    def _env_for(self, user, context=None):
        return self.env(user=user, context=dict(context or {}))

    @staticmethod
    def _without_timing(value):
        if isinstance(value, dict):
            return {
                key: TestPatchBReadAggregateSecurity._without_timing(item)
                for key, item in value.items()
                if key != "elapsed_ms"
            }
        if isinstance(value, list):
            return [
                TestPatchBReadAggregateSecurity._without_timing(item)
                for item in value
            ]
        return value

    def _handler_cases(self):
        return (
            (ProjectPlanBootstrapEnterHandler, {}),
            (
                ProjectPlanBootstrapBlockFetchHandler,
                {"block_key": "plan_tasks"},
            ),
            (ProjectExecutionEnterHandler, {}),
            (
                ProjectExecutionBlockFetchHandler,
                {"block_key": "tasks"},
            ),
            (CostTrackingEnterHandler, {}),
            (
                CostTrackingBlockFetchHandler,
                {"block_key": "cost_summary"},
            ),
            (PaymentSliceEnterHandler, {}),
            (
                PaymentSliceBlockFetchHandler,
                {"block_key": "summary"},
            ),
            (SettlementSliceEnterHandler, {}),
            (
                SettlementSliceBlockFetchHandler,
                {"block_key": "summary"},
            ),
        )

    def _call_handler(self, handler_cls, user, payload):
        user_env = self._env_for(user)
        return handler_cls(user_env, payload=payload).handle(
            payload=payload,
            ctx={},
        )

    def test_five_slice_handlers_use_real_caller_scoped_authorization(self):
        missing_id = max(
            self.project_a1.id,
            self.project_a2.id,
            self.project_b1.id,
        ) + 100000
        for handler_cls, base_payload in self._handler_cases():
            with self.subTest(handler=handler_cls.__name__, case="authorized"):
                result = self._call_handler(
                    handler_cls,
                    self.user_a1,
                    {**base_payload, "project_id": self.project_a1.id},
                )
                self.assertTrue(result.get("ok"), result)
                rendered = repr(result)
                self.assertNotIn(self.project_a2.name, rendered)
                self.assertNotIn(self.project_b1.name, rendered)

            denied = self._call_handler(
                handler_cls,
                self.user_a1,
                {**base_payload, "project_id": self.project_a2.id},
            )
            missing = self._call_handler(
                handler_cls,
                self.user_a1,
                {**base_payload, "project_id": missing_id},
            )
            self.assertFalse(denied.get("ok"), denied)
            self.assertEqual(
                self._without_timing(denied),
                self._without_timing(missing),
                handler_cls.__name__,
            )
            rendered = repr(denied)
            self.assertNotIn(self.project_a2.name, rendered)
            self.assertNotIn(self.task_a2.name, rendered)

    def test_client_scope_injection_cannot_expand_five_slice_handlers(self):
        injections = {
            "company_id": self.company_b.id,
            "allowed_company_ids": [self.company_a.id, self.company_b.id],
            "context": {"allowed_company_ids": [self.company_b.id]},
            "domain": [],
            "sudo": True,
            "user_id": self.user_a2.id,
            "owner_id": self.user_a2.id,
            "manager_id": self.user_a2.id,
        }
        for handler_cls, base_payload in self._handler_cases():
            result = self._call_handler(
                handler_cls,
                self.user_a1,
                {
                    **base_payload,
                    **injections,
                    "project_id": self.project_a2.id,
                },
            )
            self.assertFalse(result.get("ok"), (handler_cls.__name__, result))
            self.assertNotIn(self.project_a2.name, repr(result))
            nested = self._call_handler(
                handler_cls,
                self.user_a1,
                {
                    "params": {
                        **base_payload,
                        **injections,
                        "project_id": self.project_a2.id,
                    }
                },
            )
            self.assertFalse(nested.get("ok"), (handler_cls.__name__, nested))
            self.assertNotIn(self.project_a2.name, repr(nested))

    def test_five_slice_identity_project_and_company_matrix(self):
        missing_id = self.project_b1.id + 100000
        positive_cases = (
            (self.user_a1, self.project_a1, self.company_a),
            (self.user_a2, self.project_a2, self.company_a),
            (self.user_b1, self.project_b1, self.company_b),
        )
        for handler_cls, base_payload in self._handler_cases():
            for user, project, company in positive_cases:
                with self.subTest(
                    handler=handler_cls.__name__,
                    user=user.login,
                    case="authorized",
                ):
                    response = self._call_handler(
                        handler_cls,
                        user,
                        {
                            **base_payload,
                            "project_id": project.id,
                            "company_id": company.id,
                        },
                    )
                    self.assertTrue(response.get("ok"), response)

            for project_id in (
                self.project_a1.id,
                self.project_a2.id,
                self.project_b1.id,
                missing_id,
            ):
                denied = self._call_handler(
                    handler_cls,
                    self.user_same_company_denied,
                    {**base_payload, "project_id": project_id},
                )
                self.assertFalse(denied.get("ok"), denied)
                rendered = repr(denied)
                for project in (
                    self.project_a1,
                    self.project_a2,
                    self.project_b1,
                ):
                    self.assertNotIn(project.name, rendered)

    def test_multi_company_scope_remains_single_company_in_all_slice_handlers(self):
        for handler_cls, base_payload in self._handler_cases():
            for company, authorized, opposite in (
                (self.company_a, self.project_a1, self.project_b1),
                (self.company_b, self.project_b1, self.project_a1),
            ):
                with self.subTest(
                    handler=handler_cls.__name__,
                    company=company.name,
                ):
                    accepted = self._call_handler(
                        handler_cls,
                        self.multi_company_user,
                        {
                            **base_payload,
                            "project_id": authorized.id,
                            "company_id": company.id,
                            "allowed_company_ids": [
                                self.company_a.id,
                                self.company_b.id,
                            ],
                            "context": {
                                "allowed_company_ids": [
                                    opposite.company_id.id,
                                ],
                            },
                        },
                    )
                    self.assertTrue(accepted.get("ok"), accepted)
                    denied = self._call_handler(
                        handler_cls,
                        self.multi_company_user,
                        {
                            **base_payload,
                            "project_id": opposite.id,
                            "company_id": company.id,
                        },
                    )
                    self.assertFalse(denied.get("ok"), denied)
                    self.assertNotIn(opposite.name, repr(denied))

    def test_invalid_and_zero_parameter_inputs_never_expand_slice_scope(self):
        invalid_project_ids = ("", "abc", 0, -1, True, [], {}, self.project_b1.id + 100000)
        for handler_cls, base_payload in self._handler_cases():
            if handler_cls is ProjectPlanBootstrapEnterHandler:
                expected_code = "PROJECT_CONTEXT_MISSING"
            elif handler_cls in (
                ProjectPlanBootstrapBlockFetchHandler,
                ProjectExecutionBlockFetchHandler,
                CostTrackingBlockFetchHandler,
                PaymentSliceBlockFetchHandler,
                SettlementSliceBlockFetchHandler,
            ):
                expected_code = "MISSING_PARAMS"
            else:
                expected_code = "PROJECT_NOT_FOUND"
            no_project = self._call_handler(
                handler_cls,
                self.user_same_company_denied,
                dict(base_payload),
            )
            self.assertFalse(no_project.get("ok"), no_project)
            self.assertEqual(
                (no_project.get("error") or {}).get("code"),
                expected_code,
                no_project,
            )
            for project_id in invalid_project_ids:
                with self.subTest(
                    handler=handler_cls.__name__,
                    project_id=repr(project_id),
                ):
                    response_code = expected_code
                    if project_id is True or (
                        isinstance(project_id, int)
                        and not isinstance(project_id, bool)
                        and project_id > 0
                    ):
                        response_code = "PROJECT_NOT_FOUND"
                    for caller in (
                        self.user_same_company_denied,
                        self.user_a1,
                    ):
                        response = self._call_handler(
                            handler_cls,
                            caller,
                            {**base_payload, "project_id": project_id},
                        )
                        self.assertFalse(response.get("ok"), response)
                        self.assertEqual(
                            (response.get("error") or {}).get("code"),
                            response_code,
                            response,
                        )
                        rendered = repr(response)
                        self.assertNotIn(self.project_a1.name, rendered)
                        self.assertNotIn(self.project_a2.name, rendered)
                        self.assertNotIn(self.project_b1.name, rendered)

    def test_slice_services_have_no_ad_hoc_project_fallback(self):
        service_classes = (
            ProjectPlanBootstrapService,
            ProjectExecutionService,
            CostTrackingService,
            PaymentSliceService,
            SettlementSliceService,
        )
        user_env = self._env_for(self.user_a1)
        for service_cls in service_classes:
            with self.subTest(service=service_cls.__name__):
                service = service_cls(user_env)
                denied, diagnostics = service.resolve_project_with_diagnostics(
                    self.project_a2.id
                )
                self.assertFalse(denied)
                self.assertEqual(diagnostics.get("status"), "unavailable")
                authorized, _diagnostics = service.resolve_project_with_diagnostics(
                    self.project_a1.id
                )
                self.assertEqual(authorized.id, self.project_a1.id)
                self.assertEqual(authorized.env.uid, self.user_a1.id)

    def test_task_detail_count_and_group_share_record_rule_scope(self):
        Task = self._env_for(self.user_a1)["project.task"]
        a1_domain = [("project_id", "=", self.project_a1.id)]
        denied_domain = [("project_id", "=", self.project_a2.id)]
        self.assertEqual(Task.search(a1_domain).ids, [self.task_a1.id])
        self.assertEqual(Task.search_count(a1_domain), 1)
        grouped = Task.read_group(
            a1_domain,
            ["id:count"],
            ["project_id"],
        )
        grouped_count = 0
        for row in grouped:
            grouped_count += next(
                (
                    value
                    for key, value in row.items()
                    if key.endswith("_count")
                    and isinstance(value, int)
                    and not isinstance(value, bool)
                ),
                row.get("__count", 0),
            )
        self.assertEqual(
            grouped_count,
            1,
        )
        self.assertFalse(Task.search(denied_domain))
        self.assertEqual(Task.search_count(denied_domain), 0)
        self.assertEqual(
            Task.read_group(denied_domain, ["id:count"], ["project_id"]),
            [],
        )

    def test_project_execution_followup_detail_and_count_use_caller_scope(self):
        activity_domain = [
            ("res_model", "=", "project.project"),
            ("res_id", "=", self.project_a1.id),
            ("summary", "=", ProjectExecutionConsistencyGuard.FOLLOWUP_SUMMARY),
        ]
        caller_activity = self._env_for(self.user_a1)["mail.activity"]
        visible_activity_ids = caller_activity.search(activity_domain).ids
        self.assertEqual(visible_activity_ids, [self.activity_a1.id])
        self.assertEqual(caller_activity.search_count(activity_domain), 1)

        for block_key in ("readiness_precheck", "next_actions"):
            with self.subTest(block_key=block_key):
                observed_activity_reads = []
                original_followup = (
                    ProjectExecutionConsistencyGuard._followup_activities
                )

                def observe_followup(guard, project):
                    records = original_followup(guard, project)
                    observed_activity_reads.append(
                        {
                            "uid": records.env.uid,
                            "project_id": int(project.id),
                            "ids": records.ids,
                        }
                    )
                    return records

                with patch.object(
                    ProjectExecutionConsistencyGuard,
                    "_followup_activities",
                    autospec=True,
                    side_effect=observe_followup,
                ):
                    response = self._call_handler(
                        ProjectExecutionBlockFetchHandler,
                        self.user_a1,
                        {
                            "project_id": self.project_a1.id,
                            "block_key": block_key,
                        },
                    )
                self.assertTrue(response.get("ok"), response)
                self.assertTrue(observed_activity_reads, response)
                self.assertTrue(
                    all(
                        item["uid"] == self.user_a1.id
                        and item["project_id"] == self.project_a1.id
                        and item["ids"] == visible_activity_ids
                        for item in observed_activity_reads
                    ),
                    observed_activity_reads,
                )
                block = (response.get("data") or {}).get("block") or {}
                block_data = block.get("data") or {}
                if block_key == "readiness_precheck":
                    followup_count = int(
                        (block_data.get("summary") or {}).get(
                            "followup_activity_count"
                        )
                        or 0
                    )
                    self.assertEqual(
                        followup_count,
                        len(visible_activity_ids),
                        response,
                    )
                else:
                    self.assertEqual(
                        (block.get("error") or {}).get("code"),
                        "BLOCK_BUILD_FAILED",
                        response,
                    )
                rendered = repr(response)
                self.assertNotIn(self.project_a2.name, rendered)
                self.assertNotIn(self.project_b1.name, rendered)

    def test_project_execution_followup_rejects_scope_injection_before_read(self):
        missing_id = self.project_b1.id + 100000
        injections = {
            "allowed_company_ids": [self.company_a.id, self.company_b.id],
            "context": {"allowed_company_ids": [self.company_b.id]},
            "domain": [],
            "sudo": True,
            "user_id": self.user_a2.id,
            "owner_id": self.user_a2.id,
            "manager_id": self.user_a2.id,
        }
        for block_key in ("readiness_precheck", "next_actions"):
            for denied_project_id in (
                self.project_a2.id,
                self.project_b1.id,
                missing_id,
            ):
                with self.subTest(
                    block_key=block_key,
                    denied_project_id=denied_project_id,
                ):
                    followup_calls = []
                    original_followup = (
                        ProjectExecutionConsistencyGuard._followup_activities
                    )

                    def observe_followup(guard, project):
                        followup_calls.append(
                            (guard.env.uid, int(project.id))
                        )
                        return original_followup(guard, project)

                    with patch.object(
                        ProjectExecutionConsistencyGuard,
                        "_followup_activities",
                        autospec=True,
                        side_effect=observe_followup,
                    ):
                        denied = self._call_handler(
                            ProjectExecutionBlockFetchHandler,
                            self.user_a1,
                            {
                                **injections,
                                "project_id": denied_project_id,
                                "block_key": block_key,
                            },
                        )
                        missing = self._call_handler(
                            ProjectExecutionBlockFetchHandler,
                            self.user_a1,
                            {
                                **injections,
                                "project_id": missing_id,
                                "block_key": block_key,
                            },
                        )
                    self.assertEqual(followup_calls, [])
                    self.assertFalse(denied.get("ok"), denied)
                    self.assertEqual(
                        self._without_timing(denied),
                        self._without_timing(missing),
                    )
                    self.assertEqual(
                        (denied.get("error") or {}).get("code"),
                        "PROJECT_NOT_FOUND",
                    )
                    rendered = repr(denied)
                    self.assertNotIn(self.project_a2.name, rendered)
                    self.assertNotIn(self.project_b1.name, rendered)

    def test_overview_filters_mixed_ids_before_aggregation(self):
        overview = self._env_for(self.user_a1)[
            "sc.project.overview.service"
        ].get_overview(
            [
                self.project_a1.id,
                self.project_a2.id,
                self.project_b1.id,
                self.project_a1.id,
                "invalid",
                None,
            ]
        )
        self.assertEqual(set(overview), {self.project_a1.id})
        self.assertEqual(
            self._env_for(self.user_same_company_denied)[
                "sc.project.overview.service"
            ].get_overview([self.project_a1.id, self.project_a2.id]),
            {},
        )
        user_overview = self._env_for(self.user_a1)["sc.project.overview.service"]
        self.assertEqual(user_overview.get_overview([]), {})
        self.assertEqual(user_overview.get_overview([None, "", True, {}, []]), {})

    def test_evidence_carrier_must_be_visible_and_allowlisted(self):
        service = EvidenceChainService(self._env_for(self.user_a1))
        self.assertEqual(
            service.resolve_visible_carrier(
                "project.project",
                self.project_a1.id,
            ).id,
            self.project_a1.id,
        )
        self.assertIsNone(
            service.resolve_visible_carrier(
                "project.project",
                self.project_a2.id,
            )
        )
        self.assertIsNone(
            service.resolve_visible_carrier("res.users", self.user_a1.id)
        )
        denied = BusinessEvidenceTraceHandler(
            self._env_for(self.user_a1),
            payload={},
        ).handle(
            {
                "business_model": "project.project",
                "business_id": self.project_a2.id,
            },
            {},
        )
        missing = BusinessEvidenceTraceHandler(
            self._env_for(self.user_a1),
            payload={},
        ).handle(
            {
                "business_model": "project.project",
                "business_id": self.project_a2.id + 100000,
            },
            {},
        )
        self.assertEqual(
            (denied.get("data") or {}).get("evidence_refs"),
            [],
        )
        self.assertEqual(
            self._without_timing(denied),
            self._without_timing(missing),
        )

    def test_legacy_my_work_and_company_dashboard_remain_caller_scoped(self):
        user_env = self._env_for(self.user_a1)
        legacy = MyWorkSummaryHandler(user_env, payload={}).handle({}, {})
        self.assertTrue(legacy.get("ok"), legacy)
        serialized = repr(legacy)
        self.assertNotIn(self.project_a2.name, serialized)
        self.assertNotIn(self.task_a2.name, serialized)
        self.assertNotIn(self.project_b1.name, serialized)

        dashboard = DashboardCompanyEnterHandler(user_env, payload={}).handle(
            {},
            {},
        )
        self.assertTrue(dashboard.get("ok"), dashboard)
        rendered = repr(dashboard)
        self.assertNotIn(self.project_a2.name, rendered)
        self.assertNotIn(self.project_b1.name, rendered)
        injected = DashboardCompanyEnterHandler(user_env, payload={}).handle(
            {
                "company_id": self.company_b.id,
                "allowed_company_ids": [self.company_b.id],
                "sudo": True,
                "user_id": self.user_b1.id,
                "domain": [],
                "context": {"allowed_company_ids": [self.company_b.id]},
            },
            {"allowed_company_ids": [self.company_b.id]},
        )
        self.assertEqual(
            self._without_timing(dashboard),
            self._without_timing(injected),
        )

    def test_patch_b_read_sources_do_not_elevate(self):
        classes = (
            CostTrackingNativeAdapter,
            PaymentSliceNativeAdapter,
            ProjectExecutionItemProjectionService,
            EvidenceChainService,
            MyWorkSummaryHandler,
        )
        for class_ in classes:
            with self.subTest(class_name=class_.__name__):
                source = inspect.getsource(class_)
                self.assertNotIn(".sudo(", source)
                self.assertNotIn("with_user(", source)
        followup_source = inspect.getsource(
            ProjectExecutionConsistencyGuard._followup_activities
        )
        self.assertNotIn(".sudo(", followup_source)
        self.assertNotIn("with_user(", followup_source)
