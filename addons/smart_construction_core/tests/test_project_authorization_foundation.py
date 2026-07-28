# -*- coding: utf-8 -*-
from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core.handlers.project_dashboard import (
    ProjectDashboardHandler,
)
from odoo.addons.smart_construction_core.handlers.project_dashboard_block_fetch import (
    ProjectDashboardBlockFetchHandler,
)
from odoo.addons.smart_construction_core.handlers.project_dashboard_enter import (
    ProjectDashboardEnterHandler,
)
from odoo.addons.smart_construction_core.handlers.project_dashboard_open import (
    ProjectDashboardOpenHandler,
)
from odoo.addons.smart_construction_core.handlers.project_entry_context_resolve import (
    ProjectEntryContextResolveHandler,
)
from odoo.addons.smart_construction_core.services.project_authorization_service import (
    COMPANY_SCOPE_NOT_PROVIDED,
    ProjectAuthorizationService,
)
from odoo.addons.smart_construction_core.services.project_dashboard_service import (
    ProjectDashboardService,
)
from odoo.addons.smart_core.security.platform_admin import (
    PLATFORM_ADMIN_GROUP,
    SECURITY_ADMIN_GROUP,
)


@tagged("post_install", "-at_install", "admin_vis_patch_a")
class TestProjectAuthorizationFoundation(TransactionCase):
    SAFE_TRACE_ID = "sc-patch-a-0123456789abcdef"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create(
            {"name": "ADMIN_VIS_PATCH_A synthetic company B"}
        )
        cls.company_c = cls.env["res.company"].create(
            {"name": "ADMIN_VIS_PATCH_A synthetic company C"}
        )
        base_user = cls.env.ref("base.group_user")

        def create_user(login, group_xmlids, companies=None):
            company_records = companies or cls.company_a
            group_ids = {base_user.id}
            group_ids.update(cls.env.ref(xmlid).id for xmlid in group_xmlids)
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.invalid",
                    "company_id": company_records[0].id,
                    "company_ids": [(6, 0, company_records.ids)],
                    "groups_id": [(6, 0, sorted(group_ids))],
                }
            )

        cls.break_glass = create_user(
            "patch_a_break_glass",
            ["base.group_system"],
        )
        cls.platform_admin = create_user(
            "patch_a_platform_admin",
            [PLATFORM_ADMIN_GROUP],
        )
        cls.security_admin = create_user(
            "patch_a_security_admin",
            [SECURITY_ADMIN_GROUP],
        )
        cls.normal_user = create_user(
            "patch_a_normal_user",
            [],
        )
        cls.authorized_user = create_user(
            "patch_a_authorized_user",
            ["smart_construction_core.group_sc_cap_project_read"],
            cls.company_a | cls.company_b,
        )

        project_context = {
            **cls.env.context,
            "allowed_company_ids": [
                cls.company_a.id,
                cls.company_b.id,
                cls.company_c.id,
            ],
            "mail_create_nosubscribe": True,
            "mail_notify_noemail": True,
            "tracking_disable": True,
        }
        Project = cls.env["project.project"].with_context(project_context)
        cls.project_a1 = Project.create(
            {
                "name": "PATCH A Project A1",
                "company_id": cls.company_a.id,
                "privacy_visibility": "followers",
                "user_id": cls.authorized_user.id,
            }
        )
        cls.project_a2 = Project.create(
            {
                "name": "PATCH A Project A2",
                "company_id": cls.company_a.id,
                "privacy_visibility": "followers",
                "user_id": cls.env.user.id,
            }
        )
        cls.project_b1 = Project.create(
            {
                "name": "PATCH A Project B1",
                "company_id": cls.company_b.id,
                "privacy_visibility": "followers",
                "user_id": cls.authorized_user.id,
            }
        )
        cls.project_c1 = Project.create(
            {
                "name": "PATCH A Project C1",
                "company_id": cls.company_c.id,
                "privacy_visibility": "followers",
                "user_id": cls.env.user.id,
            }
        )

    @staticmethod
    def _env_for(test_case, user, context=None):
        return test_case.env(user=user, context=dict(context or {}))

    @staticmethod
    def _assert_no_project_disclosure(test_case, result):
        rendered = repr(result)
        test_case.assertNotIn("PATCH A Project", rendered)
        for project in (
            test_case.project_a1,
            test_case.project_a2,
            test_case.project_b1,
            test_case.project_c1,
        ):
            test_case.assertNotIn("'project_id': %s" % project.id, rendered)
        for company in (
            test_case.company_a,
            test_case.company_b,
            test_case.company_c,
        ):
            test_case.assertNotIn(str(company.name), rendered)

    def _assert_public_responses_equivalent(self, left, right, path="$"):
        self.assertIs(type(left), type(right), "%s has a type mismatch" % path)
        if isinstance(left, dict):
            self.assertEqual(
                set(left),
                set(right),
                "%s has a public field mismatch" % path,
            )
            for key in sorted(left):
                self._assert_public_responses_equivalent(
                    left[key],
                    right[key],
                    "%s.%s" % (path, key),
                )
            return
        if isinstance(left, (list, tuple)):
            self.assertEqual(
                len(left),
                len(right),
                "%s has an element-count mismatch" % path,
            )
            for index, (left_item, right_item) in enumerate(zip(left, right)):
                self._assert_public_responses_equivalent(
                    left_item,
                    right_item,
                    "%s[%s]" % (path, index),
                )
            return
        if path.endswith(".elapsed_ms"):
            self.assertIs(type(left), int)
            self.assertIs(type(right), int)
            self.assertGreaterEqual(left, 0)
            self.assertGreaterEqual(right, 0)
            return
        self.assertEqual(left, right, "%s has a public value mismatch" % path)

    def _assert_recursive_schema(self, actual, schema, path="$"):
        if isinstance(schema, type):
            self.assertIs(
                type(actual),
                schema,
                "%s expected exact type %s" % (path, schema.__name__),
            )
            if path.endswith(".elapsed_ms"):
                self.assertGreaterEqual(actual, 0)
            return
        if isinstance(schema, dict):
            self.assertIs(type(actual), dict, "%s must be an object" % path)
            self.assertEqual(
                set(actual),
                set(schema),
                "%s contains missing or unknown fields" % path,
            )
            for key in sorted(schema):
                self._assert_recursive_schema(
                    actual[key],
                    schema[key],
                    "%s.%s" % (path, key),
                )
            return
        if isinstance(schema, list):
            self.assertIs(type(actual), list, "%s must be a list" % path)
            self.assertEqual(
                len(actual),
                len(schema),
                "%s contains an unexpected number of elements" % path,
            )
            for index, (actual_item, schema_item) in enumerate(
                zip(actual, schema)
            ):
                self._assert_recursive_schema(
                    actual_item,
                    schema_item,
                    "%s[%s]" % (path, index),
                )
            return
        if isinstance(schema, tuple):
            self.assertIs(type(actual), tuple, "%s must be a tuple" % path)
            self.assertEqual(len(actual), len(schema))
            for index, (actual_item, schema_item) in enumerate(
                zip(actual, schema)
            ):
                self._assert_recursive_schema(
                    actual_item,
                    schema_item,
                    "%s[%s]" % (path, index),
                )
            return
        self.assertIs(
            type(actual),
            type(schema),
            "%s has an unexpected scalar type" % path,
        )
        self.assertEqual(actual, schema, "%s has an unexpected value" % path)

    @staticmethod
    def _empty_project_context_schema():
        return {
            "company_id": 0,
            "company_name": "",
            "project_id": 0,
            "project_name": "",
            "operation_strategy": "",
            "operation_strategy_label": "",
            "execution_stage": "",
            "execution_stage_label": "",
            "stage": "",
            "stage_label": "",
            "milestone": "",
            "milestone_label": "",
            "project_condition": "",
            "status": "",
        }

    @staticmethod
    def _missing_project_lifecycle_schema():
        return {
            "stage": "project_not_found",
            "first_action": "create_project",
            "primary_action_label": "创建项目",
            "suggested_action_intent": "project.initiation.enter",
            "suggested_action_title": "创建项目",
        }

    @staticmethod
    def _no_project_context_lifecycle_schema():
        return {
            "stage": "no_project_context",
            "project_id": 0,
            "primary_action_label": "创建项目",
            "suggested_action_intent": "project.initiation.enter",
            "suggested_action_title": "创建项目",
        }

    def _safe_unavailable_schema(self, intent, resolution_path):
        error = {
            "code": "PROJECT_NOT_FOUND_OR_FORBIDDEN",
            "message": "项目不存在或当前账号不可访问",
            "suggested_action": "fix_input",
        }
        trace_meta = {
            "intent": intent,
            "elapsed_ms": int,
            "trace_id": self.SAFE_TRACE_ID,
        }
        if intent == "project.dashboard.enter":
            return {
                "ok": False,
                "error": error,
                "data": {
                    "lifecycle_hints": self._missing_project_lifecycle_schema(),
                    "suggested_action_payload": {
                        "intent": "project.initiation.enter",
                        "reason_code": "PROJECT_NOT_FOUND",
                        "params": {
                            "reason_code": "PROJECT_NOT_FOUND",
                        },
                    },
                },
                "meta": trace_meta,
            }
        if intent == "project.dashboard.open":
            return {
                "ok": False,
                "error": error,
                "data": {
                    "lifecycle_hints": self._missing_project_lifecycle_schema(),
                    "suggested_action_payload": {
                        "intent": "project.initiation.enter",
                        "reason_code": "PROJECT_NOT_FOUND",
                        "params": {
                            "reason_code": "PROJECT_NOT_FOUND",
                        },
                    },
                },
                "meta": {
                    **trace_meta,
                    "deprecated": True,
                    "deprecated_replacement_intent": "project.dashboard.enter",
                    "deprecated_removal_phase": "Phase 12-G",
                    "source_authority": deepcopy(
                        ProjectDashboardOpenHandler.SOURCE_AUTHORITY
                    ),
                },
            }
        if intent == "project.dashboard.block.fetch":
            return {
                "ok": False,
                "error": error,
                "data": {
                    "lifecycle_hints": {
                        "stage": "no_project_context",
                        "first_action": "create_project",
                        "primary_action_label": "创建项目",
                        "suggested_action_intent": "project.initiation.enter",
                        "suggested_action_title": "创建项目",
                    },
                },
                "meta": trace_meta,
            }
        if intent == "project.dashboard":
            return {
                "ok": False,
                "error": error,
                "data": {},
                "meta": {
                    "intent": intent,
                    "trace_id": self.SAFE_TRACE_ID,
                    "contract_version": "v1",
                },
            }
        if intent == "project.entry.context.resolve":
            return {
                "ok": True,
                "data": {
                    "available": False,
                    "project_context": self._empty_project_context_schema(),
                    "source": "none",
                    "confidence": "low",
                    "route": "/my-work",
                    "company_options": [],
                    "operation_options": [
                        {
                            "operation_strategy": "direct",
                            "operation_strategy_label": "公司直营",
                            "active": False,
                            "disabled": False,
                            "disabled_reason": "",
                        },
                        {
                            "operation_strategy": "joint",
                            "operation_strategy_label": "联营项目",
                            "active": False,
                            "disabled": False,
                            "disabled_reason": "",
                        },
                    ],
                    "suggested_action": {
                        "intent": "project.initiation.enter",
                        "reason_code": "PROJECT_CONTEXT_MISSING",
                        "params": {},
                    },
                    "lifecycle_hints": self._no_project_context_lifecycle_schema(),
                    "diagnostics": {
                        "status": "unavailable",
                        "resolution_path": resolution_path,
                    },
                    "diagnostics_summary": {
                        "status": "context_missing",
                        "message": "当前未解析到可用项目，建议先创建项目。",
                        "resolution_path": resolution_path,
                        "option_count": 0,
                        "available": False,
                    },
                },
                "meta": {
                    **trace_meta,
                    "source_authority": deepcopy(
                        ProjectEntryContextResolveHandler.SOURCE_AUTHORITY
                    ),
                },
            }
        raise AssertionError("unsupported intent schema: %s" % intent)

    def _assert_safe_unavailable_contract(
        self,
        result,
        intent,
        resolution_path="project_unavailable",
    ):
        self.assertEqual(
            set(result),
            {"ok", "data", "meta"}
            if intent == "project.entry.context.resolve"
            else {"ok", "error", "data", "meta"},
        )
        meta = result.get("meta") or {}
        self.assertEqual(str(meta.get("intent") or ""), intent)
        expected_meta_keys = {
            "project.dashboard.enter": {"intent", "elapsed_ms", "trace_id"},
            "project.dashboard.open": {
                "intent",
                "elapsed_ms",
                "trace_id",
                "deprecated",
                "deprecated_replacement_intent",
                "deprecated_removal_phase",
                "source_authority",
            },
            "project.dashboard.block.fetch": {
                "intent",
                "elapsed_ms",
                "trace_id",
            },
            "project.dashboard": {"intent", "trace_id", "contract_version"},
            "project.entry.context.resolve": {
                "intent",
                "elapsed_ms",
                "trace_id",
                "source_authority",
            },
        }
        self.assertEqual(set(meta), expected_meta_keys[intent])

        if intent == "project.entry.context.resolve":
            data = result.get("data") or {}
            self.assertTrue(result.get("ok"))
            self.assertEqual(
                set(data),
                {
                    "available",
                    "project_context",
                    "source",
                    "confidence",
                    "route",
                    "company_options",
                    "operation_options",
                    "suggested_action",
                    "lifecycle_hints",
                    "diagnostics",
                    "diagnostics_summary",
                },
            )
            self.assertFalse(data.get("available"))
            self.assertEqual(data.get("company_options"), [])
            self.assertEqual(
                data.get("diagnostics"),
                {
                    "status": "unavailable",
                    "resolution_path": resolution_path,
                },
            )
        else:
            self.assertFalse(result.get("ok"))
            self.assertEqual(
                result.get("error"),
                {
                    "code": "PROJECT_NOT_FOUND_OR_FORBIDDEN",
                    "message": "项目不存在或当前账号不可访问",
                    "suggested_action": "fix_input",
                },
            )
            expected_data_keys = {
                "project.dashboard.enter": {
                    "lifecycle_hints",
                    "suggested_action_payload",
                },
                "project.dashboard.open": {
                    "lifecycle_hints",
                    "suggested_action_payload",
                },
                "project.dashboard.block.fetch": {"lifecycle_hints"},
                "project.dashboard": set(),
            }
            self.assertEqual(
                set(result.get("data") or {}),
                expected_data_keys[intent],
            )
        self._assert_recursive_schema(
            result,
            self._safe_unavailable_schema(intent, resolution_path),
        )
        self._assert_no_project_disclosure(self, result)

    @classmethod
    def _handler_case(cls, env, intent, project_id, extra=None):
        injected = dict(extra or {})
        payload = {"project_id": project_id, **injected}
        handler_context = {"trace_id": cls.SAFE_TRACE_ID}
        if intent == "project.dashboard.enter":
            return ProjectDashboardEnterHandler(
                env,
                context=handler_context,
                payload=payload,
            ).handle(
                    payload=payload,
                    ctx=injected,
                )
        if intent == "project.dashboard.open":
            return ProjectDashboardOpenHandler(
                env,
                context=handler_context,
                payload=payload,
            ).handle(
                    payload=payload,
                    ctx=injected,
                )
        if intent == "project.dashboard.block.fetch":
            block_payload = {**payload, "block_key": "progress"}
            return ProjectDashboardBlockFetchHandler(
                    env,
                    context=handler_context,
                    payload=block_payload,
                ).handle(
                    payload=block_payload,
                    ctx=injected,
                )
        if intent == "project.dashboard":
            return ProjectDashboardHandler(
                env,
                context=handler_context,
                payload=payload,
            ).handle(
                    payload=payload,
                    ctx={**injected, **handler_context},
                )
        if intent == "project.entry.context.resolve":
            return ProjectEntryContextResolveHandler(
                env,
                context=handler_context,
                payload=payload,
            ).handle(
                    payload=payload,
                    ctx=injected,
                )
        raise AssertionError("unsupported handler intent: %s" % intent)

    @classmethod
    def _handler_cases(cls, env, project_id, extra=None):
        intents = (
            "project.dashboard.enter",
            "project.dashboard.open",
            "project.dashboard.block.fetch",
            "project.dashboard",
            "project.entry.context.resolve",
        )
        return tuple(
            (intent, cls._handler_case(env, intent, project_id, extra))
            for intent in intents
        )

    def test_resolver_preserves_caller_and_rebuilds_company_scope(self):
        malicious_context = {
            "allowed_company_ids": [self.company_b.id],
            "company_id": self.company_b.id,
            "sudo": True,
            "user_id": self.env.uid,
            "domain": [("id", "=", self.project_b1.id)],
        }
        user_env = self._env_for(self, self.authorized_user, malicious_context)

        result = ProjectAuthorizationService(user_env).resolve(self.project_a1.id)

        self.assertTrue(result.available)
        self.assertEqual(result.project, self.project_a1)
        self.assertEqual(result.project.env.uid, self.authorized_user.id)
        self.assertFalse(result.project.env.su)
        self.assertEqual(
            result.project.env.context.get("allowed_company_ids"),
            [self.company_a.id, self.company_b.id],
        )
        self.assertNotIn("sudo", result.project.env.context)
        self.assertNotIn("user_id", result.project.env.context)
        self.assertNotIn("domain", result.project.env.context)

    def test_explicit_id_and_default_project_use_real_record_rules(self):
        authorized = ProjectAuthorizationService(
            self._env_for(self, self.authorized_user)
        )
        self.assertEqual(authorized.resolve(self.project_a1.id).project, self.project_a1)
        self.assertIn(authorized.resolve().project, self.project_a1 | self.project_b1)
        self.assertFalse(authorized.resolve(self.project_a2.id).available)
        self.assertEqual(authorized.resolve(self.project_b1.id).project, self.project_b1)
        self.assertFalse(authorized.resolve(self.project_c1.id).available)

        for user in (
            self.break_glass,
            self.platform_admin,
            self.security_admin,
            self.normal_user,
        ):
            with self.subTest(user=user.login):
                service = ProjectAuthorizationService(self._env_for(self, user))
                denied = service.resolve(self.project_a1.id)
                missing = service.resolve(987654321)
                self.assertFalse(denied.available)
                self.assertFalse(missing.available)
                self.assertEqual(denied.code, missing.code)
                self.assertEqual(set(denied.diagnostics), set(missing.diagnostics))
                self.assertFalse(service.resolve().available)

    def test_client_company_selection_can_only_narrow_server_scope(self):
        service = ProjectAuthorizationService(
            self._env_for(self, self.authorized_user)
        )
        self.assertEqual(
            service.resolve(
                self.project_a1.id,
                company_id=self.company_a.id,
            ).project,
            self.project_a1,
        )
        self.assertEqual(
            service.resolve(
                self.project_b1.id,
                company_id=self.company_b.id,
            ).project,
            self.project_b1,
        )
        self.assertFalse(
            service.resolve(
                self.project_a1.id,
                company_id=self.company_b.id,
            ).available
        )
        self.assertFalse(
            service.resolve(
                self.project_b1.id,
                company_id=self.company_a.id,
            ).available
        )
        self.assertFalse(
            service.resolve(
                self.project_c1.id,
                company_id=self.company_c.id,
            ).available
        )
        self.assertFalse(
            service.resolve(
                self.project_a1.id,
                company_id=987654321,
            ).available
        )

    def test_unauthorized_id_is_closed_before_all_patch_a_payload_handlers(self):
        for user in (
            self.break_glass,
            self.platform_admin,
            self.security_admin,
            self.normal_user,
        ):
            user_env = self._env_for(self, user)
            expected_path = (
                ProjectAuthorizationService(user_env)
                .resolve(self.project_a1.id)
                .diagnostics.get("resolution_path")
            )
            for intent, result in self._handler_cases(user_env, self.project_a1.id):
                with self.subTest(user=user.login, intent=intent):
                    self._assert_safe_unavailable_contract(
                        result,
                        intent,
                        resolution_path=expected_path,
                    )

    def test_scope_injection_does_not_expand_authorized_user(self):
        injections = (
            ("company_id", {"company_id": self.company_b.id}, False),
            (
                "allowed_company_ids",
                {"allowed_company_ids": [self.company_b.id]},
                True,
            ),
            ("domain", {"domain": [("id", "=", self.project_b1.id)]}, True),
            (
                "context",
                {"context": {"allowed_company_ids": [self.company_b.id]}},
                True,
            ),
            ("sudo", {"sudo": True}, True),
            ("user_id", {"user_id": self.env.uid}, True),
        )
        for label, injection, expect_a1 in injections:
            with self.subTest(injection=label):
                payload = {"project_id": self.project_a1.id, **injection}
                handler = ProjectEntryContextResolveHandler(
                    self._env_for(self, self.authorized_user, injection),
                    payload=payload,
                )
                result = handler.handle(payload=payload, ctx=injection)
                data = result.get("data") or {}
                project_context = data.get("project_context") or {}
                self.assertEqual(bool(data.get("available")), expect_a1)
                self.assertEqual(
                    int(project_context.get("project_id") or 0),
                    self.project_a1.id if expect_a1 else 0,
                )
                self.assertNotIn("PATCH A Project A2", repr(result))
                self.assertNotIn("PATCH A Project B1", repr(result))

    def test_company_input_matrix_is_explicitly_fail_closed(self):
        service = ProjectAuthorizationService(
            self._env_for(self, self.authorized_user)
        )
        self.assertEqual(
            service.resolve(
                self.project_a1.id,
                company_id=COMPANY_SCOPE_NOT_PROVIDED,
            ).project,
            self.project_a1,
        )
        self.assertEqual(
            service.resolve(
                self.project_a1.id,
                company_id=None,
            ).project,
            self.project_a1,
        )

        malformed_values = (
            "",
            "   ",
            "abc",
            "1.5",
            0,
            "0",
            -1,
            "-1",
            [],
            {},
            True,
            False,
            1.5,
        )
        for raw_company_id in malformed_values:
            with self.subTest(raw_company_id=repr(raw_company_id)):
                result = service.resolve(
                    self.project_a1.id,
                    company_id=raw_company_id,
                )
                self.assertFalse(result.available)
                self.assertEqual(result.code, service.PUBLIC_UNAVAILABLE_CODE)
                self.assertEqual(
                    result.diagnostics,
                    {
                        "status": "unavailable",
                        "resolution_path": "company_scope_unavailable",
                    },
                )

    def test_invalid_company_and_combined_injections_fail_before_all_entries(self):
        malicious_context = {
            "allowed_company_ids": [self.company_c.id],
            "domain": [("id", "=", self.project_c1.id)],
            "context": {"allowed_company_ids": [self.company_c.id]},
            "sudo": True,
            "user_id": self.env.uid,
        }
        user_env = self._env_for(
            self,
            self.authorized_user,
            malicious_context,
        )
        invalid_company_values = (
            "",
            "   ",
            "abc",
            "1.5",
            0,
            "0",
            -1,
            "-1",
            [],
            {},
            True,
            False,
            1.5,
            self.company_c.id,
            987654321,
        )
        for raw_company_id in invalid_company_values:
            injection = {
                **malicious_context,
                "company_id": raw_company_id,
            }
            for intent, result in self._handler_cases(
                user_env,
                self.project_a1.id,
                injection,
            ):
                with self.subTest(
                    intent=intent,
                    raw_company_id=repr(raw_company_id),
                ):
                    self._assert_safe_unavailable_contract(
                        result,
                        intent,
                        resolution_path="company_scope_unavailable",
                    )

    def test_unauthorized_and_missing_public_responses_are_fully_equivalent(self):
        user_env = self._env_for(self, self.authorized_user)
        unauthorized = dict(
            self._handler_cases(
                user_env,
                self.project_a2.id,
                {"company_id": self.company_a.id},
            )
        )
        missing = dict(
            self._handler_cases(
                user_env,
                987654321,
                {"company_id": self.company_a.id},
            )
        )
        self.assertEqual(set(unauthorized), set(missing))
        for intent in sorted(unauthorized):
            with self.subTest(intent=intent):
                self._assert_safe_unavailable_contract(
                    unauthorized[intent],
                    intent,
                )
                self._assert_safe_unavailable_contract(
                    missing[intent],
                    intent,
                )
                self._assert_public_responses_equivalent(
                    unauthorized[intent],
                    missing[intent],
                )

    def test_unauthorized_and_nonexistent_company_responses_are_equivalent(self):
        user_env = self._env_for(self, self.authorized_user)
        unauthorized = dict(
            self._handler_cases(
                user_env,
                self.project_a1.id,
                {"company_id": self.company_c.id},
            )
        )
        nonexistent = dict(
            self._handler_cases(
                user_env,
                self.project_a1.id,
                {"company_id": 987654321},
            )
        )
        self.assertEqual(set(unauthorized), set(nonexistent))
        for intent in sorted(unauthorized):
            with self.subTest(intent=intent):
                self._assert_safe_unavailable_contract(
                    unauthorized[intent],
                    intent,
                    resolution_path="company_scope_unavailable",
                )
                self._assert_safe_unavailable_contract(
                    nonexistent[intent],
                    intent,
                    resolution_path="company_scope_unavailable",
                )
                self._assert_public_responses_equivalent(
                    unauthorized[intent],
                    nonexistent[intent],
                )

    def test_authorized_context_resolve_is_limited_to_selected_company(self):
        user_env = self._env_for(self, self.authorized_user)
        handler = ProjectEntryContextResolveHandler(
            user_env, payload={"project_id": self.project_a1.id}
        )
        allowed = handler.handle(payload={"project_id": self.project_a1.id}, ctx={})
        company_b_allowed = handler.handle(
            payload={
                "project_id": self.project_b1.id,
                "company_id": self.company_b.id,
            },
            ctx={},
        )
        same_company_denied = handler.handle(
            payload={"project_id": self.project_a2.id}, ctx={}
        )
        cross_company_denied = handler.handle(
            payload={
                "project_id": self.project_b1.id,
                "company_id": self.company_a.id,
            },
            ctx={},
        )
        unauthorized_company_denied = handler.handle(
            payload={
                "project_id": self.project_c1.id,
                "company_id": self.company_c.id,
            },
            ctx={},
        )

        self.assertTrue(allowed.get("ok"))
        self.assertTrue((allowed.get("data") or {}).get("available"))
        self.assertEqual(
            ((allowed.get("data") or {}).get("project_context") or {}).get("project_id"),
            self.project_a1.id,
        )
        self.assertTrue((company_b_allowed.get("data") or {}).get("available"))
        self.assertEqual(
            (
                (company_b_allowed.get("data") or {}).get("project_context") or {}
            ).get("project_id"),
            self.project_b1.id,
        )
        self.assertFalse((same_company_denied.get("data") or {}).get("available"))
        self.assertFalse((cross_company_denied.get("data") or {}).get("available"))
        self.assertFalse(
            (unauthorized_company_denied.get("data") or {}).get("available")
        )
        self._assert_no_project_disclosure(self, same_company_denied)
        self._assert_no_project_disclosure(self, cross_company_denied)
        self._assert_no_project_disclosure(self, unauthorized_company_denied)

    def test_authorized_user_reaches_a1_through_all_patch_a_handlers(self):
        user_env = self._env_for(self, self.authorized_user)
        for company_selector in (
            {},
            {"company_id": None},
            {"company_id": self.company_a.id},
        ):
            for intent, result in self._handler_cases(
                user_env,
                self.project_a1.id,
                company_selector,
            ):
                with self.subTest(intent=intent, company_selector=company_selector):
                    self.assertTrue(result.get("ok"))
                    rendered = repr(result)
                    self.assertIn("PATCH A Project A1", rendered)
                    self.assertNotIn("PATCH A Project A2", rendered)
                    self.assertNotIn("PATCH A Project B1", rendered)
                    self.assertNotIn("PATCH A Project C1", rendered)

    def test_authorized_company_b_scope_reaches_only_b1_through_all_entries(self):
        user_env = self._env_for(self, self.authorized_user)
        for intent, result in self._handler_cases(
            user_env,
            self.project_b1.id,
            {"company_id": self.company_b.id},
        ):
            with self.subTest(intent=intent):
                self.assertTrue(result.get("ok"))
                rendered = repr(result)
                self.assertIn("PATCH A Project B1", rendered)
                self.assertNotIn("PATCH A Project A1", rendered)
                self.assertNotIn("PATCH A Project A2", rendered)
                self.assertNotIn("PATCH A Project C1", rendered)

    def test_dashboard_downstream_keeps_verified_single_company_scope(self):
        original_resolve = ProjectDashboardService.resolve_project_with_diagnostics

        for company, project, other_project in (
            (self.company_a, self.project_a1, self.project_b1),
            (self.company_b, self.project_b1, self.project_a1),
        ):
            observed_scopes = []
            observed_superuser_modes = []

            def resolve_spy(service, project_id):
                result = original_resolve(service, project_id)
                observed_scopes.append(
                    tuple(service.env.context.get("allowed_company_ids") or [])
                )
                observed_superuser_modes.append(bool(service.env.su))
                return result

            user_env = self._env_for(self, self.authorized_user)
            with patch.object(
                ProjectDashboardService,
                "resolve_project_with_diagnostics",
                new=resolve_spy,
            ):
                results = dict(
                    self._handler_cases(
                        user_env,
                        project.id,
                        {"company_id": company.id},
                    )
                )

            dashboard_intents = {
                "project.dashboard.enter",
                "project.dashboard.open",
                "project.dashboard.block.fetch",
                "project.dashboard",
            }
            for intent in dashboard_intents:
                with self.subTest(company=company.name, intent=intent):
                    result = results[intent]
                    self.assertTrue(result.get("ok"))
                    rendered = repr(result)
                    self.assertIn(project.name, rendered)
                    self.assertNotIn(other_project.name, rendered)

            self.assertTrue(observed_scopes)
            self.assertEqual(
                set(observed_scopes),
                {(company.id,)},
                "dashboard re-resolution expanded the verified company scope",
            )
            self.assertEqual(set(observed_superuser_modes), {False})

    def test_default_project_selection_keeps_explicit_company_scope(self):
        user_env = self._env_for(self, self.authorized_user)
        for company, project, other_project in (
            (self.company_a, self.project_a1, self.project_b1),
            (self.company_b, self.project_b1, self.project_a1),
        ):
            payload = {"company_id": company.id}
            cases = (
                (
                    "project.dashboard.enter",
                    ProjectDashboardEnterHandler(
                        user_env,
                        payload=payload,
                    ).handle(payload=payload, ctx={}),
                ),
                (
                    "project.dashboard.open",
                    ProjectDashboardOpenHandler(
                        user_env,
                        payload=payload,
                    ).handle(payload=payload, ctx={}),
                ),
                (
                    "project.dashboard",
                    ProjectDashboardHandler(
                        user_env,
                        payload=payload,
                    ).handle(payload=payload, ctx={}),
                ),
                (
                    "project.entry.context.resolve",
                    ProjectEntryContextResolveHandler(
                        user_env,
                        payload=payload,
                    ).handle(payload=payload, ctx={}),
                ),
            )
            for intent, result in cases:
                with self.subTest(company=company.name, intent=intent):
                    self.assertTrue(result.get("ok"))
                    rendered = repr(result)
                    self.assertIn(project.name, rendered)
                    self.assertNotIn(other_project.name, rendered)

            block_result = ProjectDashboardBlockFetchHandler(
                user_env,
                payload={
                    "company_id": company.id,
                    "block_key": "progress",
                },
            ).handle(
                payload={
                    "company_id": company.id,
                    "block_key": "progress",
                },
                ctx={},
            )
            self.assertFalse(block_result.get("ok"))
            self.assertEqual(
                (block_result.get("error") or {}).get("code"),
                "MISSING_PARAMS",
            )
            self._assert_no_project_disclosure(self, block_result)

    def test_valid_company_scope_resists_combined_input_injections(self):
        user_env = self._env_for(self, self.authorized_user)
        injections = (
            {"allowed_company_ids": [self.company_c.id]},
            {"context": {"allowed_company_ids": [self.company_c.id]}},
            {"domain": [("id", "=", self.project_c1.id)]},
            {"sudo": True},
            {"user_id": self.env.uid},
            {
                "allowed_company_ids": [self.company_c.id],
                "context": {"allowed_company_ids": [self.company_c.id]},
                "domain": [("id", "=", self.project_c1.id)],
                "sudo": True,
                "user_id": self.env.uid,
            },
        )
        for company, project, other_project in (
            (self.company_a, self.project_a1, self.project_b1),
            (self.company_b, self.project_b1, self.project_a1),
        ):
            for injection in injections:
                scope = {
                    **injection,
                    "company_id": company.id,
                }
                for intent, result in self._handler_cases(
                    user_env,
                    project.id,
                    scope,
                ):
                    with self.subTest(
                        company=company.name,
                        intent=intent,
                        injection=sorted(injection),
                    ):
                        self.assertTrue(result.get("ok"))
                        rendered = repr(result)
                        self.assertIn(project.name, rendered)
                        self.assertNotIn(other_project.name, rendered)
                        self.assertNotIn(self.project_c1.name, rendered)

    def test_cross_company_project_ids_match_missing_response_for_all_entries(self):
        user_env = self._env_for(self, self.authorized_user)
        for company, cross_company_project in (
            (self.company_a, self.project_b1),
            (self.company_b, self.project_a1),
        ):
            scope = {"company_id": company.id}
            denied = dict(
                self._handler_cases(
                    user_env,
                    cross_company_project.id,
                    scope,
                )
            )
            missing = dict(
                self._handler_cases(
                    user_env,
                    987654321,
                    scope,
                )
            )
            for intent in sorted(denied):
                with self.subTest(company=company.name, intent=intent):
                    self._assert_safe_unavailable_contract(
                        denied[intent],
                        intent,
                    )
                    self._assert_public_responses_equivalent(
                        denied[intent],
                        missing[intent],
                    )

    def test_invalid_company_stops_before_project_id_resolution(self):
        service = ProjectAuthorizationService(
            self._env_for(self, self.authorized_user)
        )
        with patch.object(
            ProjectAuthorizationService,
            "_coerce_positive_id",
            side_effect=AssertionError("project resolution must not run"),
        ):
            for invalid_company in ("", 0, -1, self.company_c.id, 987654321):
                with self.subTest(company_id=invalid_company):
                    result = service.resolve(
                        self.project_a1.id,
                        company_id=invalid_company,
                    )
                    self.assertFalse(result.available)
                    self.assertEqual(
                        result.diagnostics.get("resolution_path"),
                        "company_scope_unavailable",
                    )

    def _assert_access_error_ledger_clean(
        self,
        ledger,
        authenticated_uid,
        allowed_company_ids,
    ):
        project_query_operations = {
            "search",
            "search_count",
            "read_group",
            "browse",
            "exists",
            "read",
        }
        forbidden_after_error = {
            "authorization.resolve",
            "dashboard.resolve_project_with_diagnostics",
            "sudo",
            "with_user",
            "with_company",
            "with_context",
        }
        expected_scope = tuple(allowed_company_ids)
        for call in ledger:
            if (
                call["model"] == "project.project"
                and call["operation"] in project_query_operations
            ):
                self.assertEqual(
                    call["uid"],
                    authenticated_uid,
                    "project query changed authenticated identity: %r" % call,
                )
                self.assertFalse(
                    call["su"],
                    "project query entered superuser mode: %r" % call,
                )
                self.assertEqual(
                    call["allowed_company_ids"],
                    expected_scope,
                    "project query expanded company scope: %r" % call,
                )
            if call["phase"] != "post_error":
                continue
            self.assertNotIn(
                call["operation"],
                forbidden_after_error,
                "authorization helper or environment retry after AccessError: %r"
                % call,
            )
            self.assertFalse(
                call["business_read"],
                "business data access occurred after AccessError: %r" % call,
            )

    def test_access_error_never_retries_with_privilege_or_wider_scope(self):
        user_env = self._env_for(self, self.authorized_user)
        authenticated_uid = int(self.authorized_user.id)
        expected_scope = (self.company_b.id,)
        intents = (
            "project.dashboard.enter",
            "project.dashboard.open",
            "project.dashboard.block.fetch",
            "project.dashboard",
            "project.entry.context.resolve",
        )
        observed_ledgers = []

        for intent in intents:
            state = {"access_error_seen": False}
            ledger = []

            def record_call(
                model,
                operation,
                records,
                *,
                business_read,
                arguments=(),
            ):
                if records.env.cr is not user_env.cr:
                    return None
                call = {
                    "phase": (
                        "post_error"
                        if state["access_error_seen"]
                        else "pre_error"
                    ),
                    "model": model,
                    "operation": operation,
                    "uid": int(records.env.uid),
                    "su": bool(records.env.su),
                    "allowed_company_ids": tuple(
                        records.env.context.get("allowed_company_ids") or []
                    ),
                    "business_read": bool(business_read),
                    "arguments": arguments,
                }
                ledger.append(call)
                return call

            def make_orm_spy(operation, original):
                def spy(records, *args, **kwargs):
                    record_ids = ()
                    if operation in {"browse", "exists", "read"}:
                        if operation == "browse":
                            raw_ids = args[0] if args else ()
                            if hasattr(raw_ids, "ids"):
                                record_ids = tuple(raw_ids.ids)
                            elif isinstance(raw_ids, (list, tuple, set)):
                                record_ids = tuple(raw_ids)
                            elif raw_ids:
                                record_ids = (raw_ids,)
                        else:
                            record_ids = tuple(records.ids)
                    call = record_call(
                        records._name,
                        operation,
                        records,
                        business_read=True,
                        arguments=record_ids or tuple(args[:1]),
                    )
                    if (
                        records._name == "project.project"
                        and operation == "search"
                        and records.env.cr is user_env.cr
                        and not state["access_error_seen"]
                    ):
                        state["access_error_seen"] = True
                        raise AccessError(
                            "synthetic caller-scoped project access failure"
                        )
                    return original(records, *args, **kwargs)

                return spy

            def make_environment_spy(operation, original):
                def spy(records, *args, **kwargs):
                    record_call(
                        records._name,
                        operation,
                        records,
                        business_read=False,
                        arguments=tuple(args),
                    )
                    return original(records, *args, **kwargs)

                return spy

            original_authorization_resolve = ProjectAuthorizationService.resolve
            original_dashboard_resolve = (
                ProjectDashboardService.resolve_project_with_diagnostics
            )

            def authorization_resolve_spy(service, *args, **kwargs):
                record_call(
                    "project.project",
                    "authorization.resolve",
                    service.env["project.project"],
                    business_read=False,
                    arguments=tuple(args),
                )
                return original_authorization_resolve(
                    service,
                    *args,
                    **kwargs,
                )

            def dashboard_resolve_spy(service, *args, **kwargs):
                record_call(
                    "project.project",
                    "dashboard.resolve_project_with_diagnostics",
                    service.env["project.project"],
                    business_read=False,
                    arguments=tuple(args),
                )
                return original_dashboard_resolve(
                    service,
                    *args,
                    **kwargs,
                )

            model_classes = {
                type(user_env[model_name])
                for model_name in user_env.registry.models
            }

            with ExitStack() as stack:
                for ModelClass in model_classes:
                    for operation in (
                        "search",
                        "search_count",
                        "read_group",
                        "browse",
                        "exists",
                        "read",
                    ):
                        original = getattr(ModelClass, operation)
                        stack.enter_context(
                            patch.object(
                                ModelClass,
                                operation,
                                new=make_orm_spy(
                                    operation,
                                    original,
                                ),
                            )
                        )
                    for operation in (
                        "sudo",
                        "with_user",
                        "with_company",
                        "with_context",
                    ):
                        original = getattr(ModelClass, operation)
                        stack.enter_context(
                            patch.object(
                                ModelClass,
                                operation,
                                new=make_environment_spy(
                                    operation,
                                    original,
                                ),
                            )
                        )
                stack.enter_context(
                    patch.object(
                        ProjectAuthorizationService,
                        "resolve",
                        new=authorization_resolve_spy,
                    )
                )
                stack.enter_context(
                    patch.object(
                        ProjectDashboardService,
                        "resolve_project_with_diagnostics",
                        new=dashboard_resolve_spy,
                    )
                )
                result = self._handler_case(
                    user_env,
                    intent,
                    self.project_b1.id,
                    {"company_id": self.company_b.id},
                )

                if intent == intents[0]:
                    def assert_real_mutation_rejected(label, mutation):
                        ledger_start = len(ledger)
                        try:
                            mutation()
                        except Exception:
                            pass
                        mutation_calls = ledger[ledger_start:]
                        self.assertTrue(
                            mutation_calls,
                            "%s did not traverse the ORM observer" % label,
                        )
                        with self.assertRaises(
                            AssertionError,
                            msg="%s escaped the post-error gate" % label,
                        ):
                            self._assert_access_error_ledger_clean(
                                ledger,
                                authenticated_uid,
                                expected_scope,
                            )
                        del ledger[ledger_start:]

                    dynamic_model_name = "construction.contract"
                    dynamic_model = user_env[dynamic_model_name]
                    unlisted_model_name = (
                        "sc.evidence.exception"
                        if "sc.evidence.exception" in user_env.registry
                        else "sc.operating.metrics.project"
                    )
                    unlisted_model = user_env[unlisted_model_name]
                    mutations = (
                        (
                            "unlisted model search_count",
                            lambda: unlisted_model.search_count([]),
                        ),
                        (
                            "dynamic model search",
                            lambda: user_env[dynamic_model_name].search(
                                [],
                                limit=1,
                            ),
                        ),
                        (
                            "dynamic model search_count",
                            lambda: dynamic_model.search_count([]),
                        ),
                        (
                            "dynamic model read_group",
                            lambda: dynamic_model.read_group(
                                [],
                                ["id:count"],
                                [],
                            ),
                        ),
                        (
                            "dynamic empty browse exists",
                            lambda: dynamic_model.browse([]).exists(),
                        ),
                        (
                            "dynamic browse read",
                            lambda: dynamic_model.browse(
                                [self.project_a1.id]
                            ).read(["id"]),
                        ),
                        (
                            "new environment access",
                            lambda: self._env_for(
                                self,
                                self.normal_user,
                            )[dynamic_model_name].search([], limit=1),
                        ),
                        (
                            "non-root administrator access",
                            lambda: dynamic_model.with_user(
                                self.platform_admin
                            ).search([], limit=1),
                        ),
                        (
                            "sudo access",
                            lambda: dynamic_model.sudo().search([], limit=1),
                        ),
                        (
                            "with_company access",
                            lambda: dynamic_model.with_company(
                                self.company_a
                            ).search([], limit=1),
                        ),
                        (
                            "expanded company context access",
                            lambda: dynamic_model.with_context(
                                allowed_company_ids=[
                                    self.company_a.id,
                                    self.company_b.id,
                                ]
                            ).search([], limit=1),
                        ),
                        (
                            "discarded business read",
                            lambda: dynamic_model.search([], limit=1),
                        ),
                        (
                            "safe response after business read",
                            lambda: (
                                dynamic_model.search([], limit=1),
                                {"available": False},
                            ),
                        ),
                        (
                            "project empty browse",
                            lambda: user_env["project.project"].browse([]),
                        ),
                        (
                            "project browse exists",
                            lambda: user_env["project.project"].browse(
                                [self.project_b1.id]
                            ).exists(),
                        ),
                        (
                            "authorization helper retry",
                            lambda: ProjectAuthorizationService(
                                user_env
                            ).resolve(
                                project_id=0,
                                company_id=self.company_b.id,
                            ),
                        ),
                        (
                            "dashboard secondary resolver retry",
                            lambda: ProjectDashboardService(
                                user_env
                            ).resolve_project_with_diagnostics(0),
                        ),
                    )
                    for label, mutation in mutations:
                        with self.subTest(mutation=label):
                            assert_real_mutation_rejected(label, mutation)

            self.assertTrue(state["access_error_seen"])
            self._assert_access_error_ledger_clean(
                ledger,
                authenticated_uid,
                expected_scope,
            )
            first_search = [
                call
                for call in ledger
                if call["model"] == "project.project"
                and call["operation"] == "search"
            ]
            self.assertEqual(len(first_search), 1)
            self.assertEqual(first_search[0]["phase"], "pre_error")
            self.assertEqual(first_search[0]["uid"], authenticated_uid)
            self.assertEqual(
                first_search[0]["allowed_company_ids"],
                expected_scope,
            )
            self._assert_safe_unavailable_contract(
                result,
                intent,
                resolution_path="project_scope_unavailable",
            )
            observed_ledgers.append(ledger)

        self.assertEqual(len(observed_ledgers), len(intents))

    def test_invalid_company_never_reaches_project_discovery_methods(self):
        user_env = self._env_for(self, self.authorized_user)
        ProjectModel = type(user_env["project.project"])
        original_search = ProjectModel.search
        original_search_count = ProjectModel.search_count
        original_read_group = ProjectModel.read_group
        original_browse = ProjectModel.browse
        original_exists = ProjectModel.exists
        discovery_calls = []

        def search_spy(records, domain, *args, **kwargs):
            discovery_calls.append(("search", list(domain or [])))
            return original_search(records, domain, *args, **kwargs)

        def search_count_spy(records, domain, *args, **kwargs):
            discovery_calls.append(("search_count", list(domain or [])))
            return original_search_count(records, domain, *args, **kwargs)

        def read_group_spy(records, domain, *args, **kwargs):
            discovery_calls.append(("read_group", list(domain or [])))
            return original_read_group(records, domain, *args, **kwargs)

        def browse_spy(records, ids=()):
            normalized_ids = ids.ids if hasattr(ids, "ids") else ids
            if normalized_ids:
                discovery_calls.append(("browse", normalized_ids))
            return original_browse(records, ids)

        def exists_spy(records):
            discovery_calls.append(("exists", tuple(records.ids)))
            return original_exists(records)

        malformed = (
            "",
            "   ",
            "abc",
            "1.5",
            0,
            "0",
            -1,
            "-1",
            [],
            {},
            True,
            False,
            1.5,
        )
        invalid_groups = {
            "malformed": malformed,
            "unauthorized": (self.company_c.id,),
            "nonexistent": (987654321,),
        }
        baseline_by_intent = None
        with patch.object(ProjectModel, "search", new=search_spy), patch.object(
            ProjectModel,
            "search_count",
            new=search_count_spy,
        ), patch.object(
            ProjectModel,
            "read_group",
            new=read_group_spy,
        ), patch.object(
            ProjectModel,
            "browse",
            new=browse_spy,
        ), patch.object(
            ProjectModel,
            "exists",
            new=exists_spy,
        ):
            for category, company_values in invalid_groups.items():
                for company_id in company_values:
                    responses = dict(
                        self._handler_cases(
                            user_env,
                            self.project_a1.id,
                            {"company_id": company_id},
                        )
                    )
                    if baseline_by_intent is None:
                        baseline_by_intent = responses
                    for intent, result in responses.items():
                        with self.subTest(
                            category=category,
                            company_id=repr(company_id),
                            intent=intent,
                        ):
                            self._assert_safe_unavailable_contract(
                                result,
                                intent,
                                resolution_path="company_scope_unavailable",
                            )
                            self._assert_public_responses_equivalent(
                                result,
                                baseline_by_intent[intent],
                            )

        self.assertEqual(discovery_calls, [])

    def test_recursive_error_allowlist_rejects_nested_business_mutations(self):
        user_env = self._env_for(self, self.authorized_user)
        responses = dict(
            self._handler_cases(
                user_env,
                self.project_a2.id,
                {"company_id": self.company_a.id},
            )
        )
        for intent, result in responses.items():
            self._assert_safe_unavailable_contract(result, intent)

        mutations = []

        context_mutation = deepcopy(
            responses["project.entry.context.resolve"]
        )
        context_mutation["data"]["diagnostics"]["project_count"] = 1
        mutations.append(
            (
                "diagnostics business count",
                "project.entry.context.resolve",
                context_mutation,
                "$.data.diagnostics",
            )
        )

        error_mutation = deepcopy(responses["project.dashboard.enter"])
        error_mutation["error"]["details"] = {"amount": 100}
        mutations.append(
            (
                "nested error amount",
                "project.dashboard.enter",
                error_mutation,
                "$.error",
            )
        )

        list_mutation = deepcopy(responses["project.dashboard.block.fetch"])
        list_mutation["data"] = [{"company": {"id": 2}}]
        mutations.append(
            (
                "data company list",
                "project.dashboard.block.fetch",
                list_mutation,
                "$.data",
            )
        )

        result_mutation = deepcopy(responses["project.dashboard"])
        result_mutation["result"] = {"stats": {"total": 3}}
        mutations.append(
            (
                "top-level aggregate result",
                "project.dashboard",
                result_mutation,
                "$",
            )
        )

        nested_mutation = deepcopy(responses["project.dashboard.open"])
        nested_mutation["data"]["lifecycle_hints"]["payload"] = {
            "projects": [{"id": self.project_a1.id}]
        }
        mutations.append(
            (
                "deep project payload",
                "project.dashboard.open",
                nested_mutation,
                "$.data.lifecycle_hints",
            )
        )

        unknown_dict = deepcopy(responses["project.dashboard.enter"])
        unknown_dict["error"]["message"] = {
            "internal": {"model": "project.project"}
        }
        mutations.append(
            (
                "allowed scalar replaced by dict",
                "project.dashboard.enter",
                unknown_dict,
                "$.error.message",
            )
        )

        unknown_list = deepcopy(responses["project.dashboard.enter"])
        unknown_list["error"]["message"] = [
            "项目不存在或当前账号不可访问",
            {"amount": 100},
        ]
        mutations.append(
            (
                "allowed scalar replaced by list",
                "project.dashboard.enter",
                unknown_list,
                "$.error.message",
            )
        )

        second_element = deepcopy(
            responses["project.entry.context.resolve"]
        )
        second_element["data"]["operation_options"][1]["project_count"] = 1
        mutations.append(
            (
                "second list element",
                "project.entry.context.resolve",
                second_element,
                "$.data.operation_options[1]",
            )
        )

        later_element = deepcopy(
            responses["project.entry.context.resolve"]
        )
        later_element["data"]["operation_options"].append(
            {"stats": {"total": 3}}
        )
        mutations.append(
            (
                "later list element",
                "project.entry.context.resolve",
                later_element,
                "$.data.operation_options",
            )
        )

        sensitive_trace_values = (
            "AccessError: denied",
            "odoo.exceptions.AccessError",
            "project.project",
            "[('company_id', '=', 2)]",
            "SELECT * FROM project_project",
            "/srv/odoo/addons/file.py",
            "allowed_company_ids=[1,2]",
            "amount=100",
            "arbitrary free text",
            "",
            "x" * 1024,
            self.SAFE_TRACE_ID + ":AccessError",
        )
        for trace_value in sensitive_trace_values:
            trace_mutation = deepcopy(
                responses["project.dashboard.enter"]
            )
            trace_mutation["meta"]["trace_id"] = trace_value
            mutations.append(
                (
                    "invalid trace value %r" % trace_value,
                    "project.dashboard.enter",
                    trace_mutation,
                    "$.meta.trace_id",
                )
            )

        trace_type_mutation = deepcopy(
            responses["project.dashboard.enter"]
        )
        trace_type_mutation["meta"]["trace_id"] = 7
        mutations.append(
            (
                "integer trace value",
                "project.dashboard.enter",
                trace_type_mutation,
                "$.meta.trace_id",
            )
        )

        bool_elapsed = deepcopy(responses["project.dashboard.enter"])
        bool_elapsed["meta"]["elapsed_ms"] = True
        mutations.append(
            (
                "bool masquerading as elapsed integer",
                "project.dashboard.enter",
                bool_elapsed,
                "$.meta.elapsed_ms",
            )
        )

        recordset_mutation = deepcopy(
            responses["project.dashboard.enter"]
        )
        recordset_mutation["error"]["message"] = self.project_a1
        mutations.append(
            (
                "recordset object",
                "project.dashboard.enter",
                recordset_mutation,
                "$.error.message",
            )
        )

        exception_mutation = deepcopy(
            responses["project.dashboard.enter"]
        )
        exception_mutation["error"]["message"] = AccessError(
            "synthetic internal exception"
        )
        mutations.append(
            (
                "exception object",
                "project.dashboard.enter",
                exception_mutation,
                "$.error.message",
            )
        )

        for label, intent, mutation, expected_path in mutations:
            with self.subTest(label=label, intent=intent):
                with self.assertRaises(AssertionError) as caught:
                    self._assert_recursive_schema(
                        mutation,
                        self._safe_unavailable_schema(
                            intent,
                            "project_unavailable",
                        ),
                    )
                self.assertIn(expected_path, str(caught.exception))

    def test_bound_dashboard_resolution_cannot_switch_project_or_company(self):
        user_env = self._env_for(self, self.authorized_user)
        resolution = ProjectAuthorizationService(user_env).resolve(
            self.project_b1.id,
            company_id=self.company_b.id,
        )
        self.assertTrue(resolution.available)
        self.assertEqual(
            resolution.env.context.get("allowed_company_ids"),
            [self.company_b.id],
        )

        service = ProjectDashboardService(resolution.env)
        service.bind_authorized_resolution(resolution)
        project, diagnostics = service.resolve_project_with_diagnostics(
            self.project_b1.id
        )
        self.assertEqual(project, self.project_b1)
        self.assertEqual(
            service.env.context.get("allowed_company_ids"),
            [self.company_b.id],
        )

        denied_project, denied_diagnostics = service.resolve_project_with_diagnostics(
            self.project_a1.id
        )
        self.assertFalse(denied_project)
        self.assertEqual(
            denied_diagnostics,
            {
                "status": "unavailable",
                "resolution_path": "project_unavailable",
            },
        )
        self.assertEqual(
            service.env.context.get("allowed_company_ids"),
            [self.company_b.id],
        )
        self.assertNotEqual(diagnostics, denied_diagnostics)

    def test_zero_parameter_calls_never_fall_back_to_unauthorized_project(self):
        for user in (
            self.break_glass,
            self.platform_admin,
            self.security_admin,
            self.normal_user,
        ):
            with self.subTest(user=user.login):
                result = ProjectDashboardEnterHandler(
                    self._env_for(self, user), payload={}
                ).handle(payload={}, ctx={})
                self.assertFalse(result.get("ok"))
                self._assert_no_project_disclosure(self, result)

        authorized = ProjectEntryContextResolveHandler(
            self._env_for(self, self.authorized_user), payload={}
        ).handle(payload={}, ctx={})
        self.assertTrue((authorized.get("data") or {}).get("available"))
        self.assertIn(
            ((authorized.get("data") or {}).get("project_context") or {}).get("project_id"),
            {self.project_a1.id, self.project_b1.id},
        )
        self.assertNotIn("PATCH A Project A2", repr(authorized))
        self.assertNotIn("PATCH A Project C1", repr(authorized))
