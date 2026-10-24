"""Real HTTP verification for R6.3 draft feedback, with rollback-only fixtures."""
import copy
import hashlib
import json
import logging
import secrets
from unittest.mock import patch

from odoo import release
from odoo.tests.common import HttpCase, tagged
from odoo.addons.smart_core.core import draft_feedback
from odoo.addons.smart_core.tests.test_intent_smoke import setup_test_entry_namespace

from .test_native_advisory_draft import BINDING, CONTENT, FEEDBACK_REVIEW, LOCATOR, MODEL, VIEW


_logger = logging.getLogger(__name__)
EVIDENCE_PREFIX = "LOCAL_DEV_FEEDBACK_RT_HTTP_JSON="


@tagged("post_install", "-at_install", "feedback_evaluation_rt_http")
class TestFeedbackEvaluationRtHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.password = secrets.token_urlsafe(24)
        cls.denied_password = secrets.token_urlsafe(24)
        project_group = cls.env.ref("smart_construction_core.group_sc_cap_project_user")
        base_group = cls.env.ref("base.group_user")
        system_group = cls.env.ref("base.group_system")
        cls.operator = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "R6.3 RT HTTP operator",
            "login": "r6_3_rt_http_operator",
            "password": cls.password,
            "company_id": cls.env.company.id,
            "company_ids": [(6, 0, [cls.env.company.id])],
            "groups_id": [(6, 0, (base_group | system_group | project_group).ids)],
        })
        cls.denied = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "R6.3 RT HTTP denied",
            "login": "r6_3_rt_http_denied",
            "password": cls.denied_password,
            "company_id": cls.env.company.id,
            "company_ids": [(6, 0, [cls.env.company.id])],
            "groups_id": [(6, 0, base_group.ids)],
        })
        cls.entry_namespace = setup_test_entry_namespace(cls.env, "r6-3-rt")
        cls.entry_secret = secrets.token_urlsafe(24)
        cls.entry_route_version = "r6-3-rt-v1"
        cls.env["ir.config_parameter"].sudo().set_param("sc.entry.shared_secret", cls.entry_secret)
        cls.env["ir.config_parameter"].sudo().set_param("sc.entry.route_version", cls.entry_route_version)

    def setUp(self):
        super().setUp()
        self.model = self.env[MODEL].with_user(self.operator)
        self.field = self.model._fields[CONTENT]
        self.declaration_patch = patch.object(
            self.field, "sc_feedback_usage", copy.deepcopy(BINDING), create=True,
        )
        self.review_patch = patch.object(
            type(self.model)._compute_processing_advisory,
            "_sc_feedback_evaluation_review",
            copy.deepcopy(FEEDBACK_REVIEW),
            create=True,
        )
        self.declaration_patch.start()
        self.review_patch.start()
        self.view = self.env.ref(VIEW)
        contract, _proof = draft_feedback._assemble_contract(self.model, self.view.id)
        host = self._find_component(contract, draft_feedback.COMPONENT_KEY)
        self.container_id = host["containerId"]

    def tearDown(self):
        try:
            self.declaration_patch.stop()
            self.review_patch.stop()
            self.assertFalse(hasattr(self.field, "sc_feedback_usage"))
            self.assertFalse(hasattr(
                type(self.model)._compute_processing_advisory,
                "_sc_feedback_evaluation_review",
            ))
        finally:
            super().tearDown()

    def _find_component(self, contract, key):
        matches = []
        def walk(nodes):
            for node in nodes:
                if node.get("componentKey") == key:
                    matches.append(node)
                walk(node.get("children") or [])
        walk(contract["layoutContract"]["containerTree"])
        self.assertEqual(len(matches), 1)
        return matches[0]

    def _entry_headers(self):
        return {
            "X-SC-Namespace": self.entry_namespace,
            "X-SC-Audience": "tenant",
            "X-SC-Entry-Secret": self.entry_secret,
            "X-SC-Route-Version": self.entry_route_version,
        }

    def _intent(self, intent, params=None, token="", anonymous=False):
        headers = {**self._entry_headers(), "Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if anonymous:
            headers["X-Anonymous-Intent"] = "true"
        response = self.url_open(
            "/api/v1/intent",
            data=json.dumps({"intent": intent, "params": params or {}}),
            headers=headers,
        )
        return response.status_code, response.json()

    def _login(self, login, password):
        status, body = self._intent(
            "login",
            {"login": login, "password": password, "contract_mode": "compat"},
            anonymous=True,
        )
        self.assertEqual(status, 200, body.get("error"))
        self.assertTrue(body.get("ok"), body.get("error"))
        data = body.get("data") or {}
        token = data.get("token") or ((data.get("session") or {}).get("token"))
        self.assertTrue(token)
        status, initialized = self._intent("system.init", token=token)
        self.assertEqual(status, 200, initialized.get("error"))
        self.assertTrue(initialized.get("ok"), initialized.get("error"))
        return token

    def _feedback_params(self, block, capabilities=None):
        return {
            "model": MODEL,
            "values": {},
            "changed_fields": [],
            "context": {
                "allowed_company_ids": [self.env.company.id],
                "lang": "en_US",
            },
            "client_contract_capabilities": capabilities if capabilities is not None else [
                "form.feedback.message.v1",
                "form.feedback.draft.v1",
            ],
            "feedback_evaluation": block,
        }

    def _describe(self, token, request_id="rt_describe_1"):
        return self._intent("api.onchange", self._feedback_params({
            "version": "1.0.0",
            "operation": "describe",
            "request_id": request_id,
            "view_id": self.view.id,
            "container_id": self.container_id,
        }), token=token)

    def _evaluate(self, token, etag, inputs, request_id="rt_evaluate_1"):
        return self._intent("api.onchange", self._feedback_params({
            "version": "1.0.0",
            "operation": "evaluate",
            "request_id": request_id,
            "view_id": self.view.id,
            "container_id": self.container_id,
            "binding_etag": etag,
            "inputs": inputs,
        }), token=token)

    @staticmethod
    def _reason(body):
        return ((body.get("error") or {}).get("reason_code")
                or (body.get("error") or {}).get("code")
                or "")

    def _record_case(self, cases, name, status, body):
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        error = body.get("error") if isinstance(body.get("error"), dict) else {}
        feedback = (
            data.get("feedback_evaluation")
            or ((error.get("details") or {}).get("feedback_evaluation"))
            or {}
        )
        diagnostic = feedback.get("diagnostic") or {}
        binding = feedback.get("binding") or {}
        cases.append({
            "case": name,
            "http_status": status,
            "business_ok": body.get("ok") is True,
            "reason_code": self._reason(body),
            "request_id": feedback.get("request_id", ""),
            "status": feedback.get("status", ""),
            "diagnostic_path": diagnostic.get("path", ""),
            "result": feedback.get("result"),
            "binding": {
                key: binding.get(key) for key in (
                    "etag", "model", "view_id", "container_id", "source_container_id",
                    "native_locator", "occurrence_index", "component_key",
                    "component_version", "purpose", "dependencies", "visibility_owner",
                )
            } if binding else None,
            "patch_empty": data.get("patch") == {} if data else None,
            "modifiers_patch_empty": data.get("modifiers_patch") == {} if data else None,
            "line_patches_empty": data.get("line_patches") == [] if data else None,
        })

    def test_controlled_http_describe_evaluate_and_regressions(self):
        cases = []
        operator_token = self._login(self.operator.login, self.password)
        target_class = type(self.model)
        project_class = self.env["project.project"]
        partner_class = self.env["res.partner"]
        with patch.object(target_class, "create", side_effect=AssertionError("business create")), \
                patch.object(target_class, "write", side_effect=AssertionError("business write")), \
                patch.object(target_class, "unlink", side_effect=AssertionError("business unlink")), \
                patch.object(type(project_class), "create", side_effect=AssertionError("project create")), \
                patch.object(type(project_class), "write", side_effect=AssertionError("project write")), \
                patch.object(type(partner_class), "create", side_effect=AssertionError("partner create")), \
                patch.object(type(partner_class), "write", side_effect=AssertionError("partner write")):
            status, described = self._describe(operator_token)
            self._record_case(cases, "describe", status, described)
            self.assertEqual(status, 200, described.get("error"))
            binding = described["data"]["feedback_evaluation"]["binding"]
            self.assertEqual(binding["native_locator"], LOCATOR)
            self.assertEqual(binding["dependencies"], FEEDBACK_REVIEW["inputs"])

            status, cleared = self._evaluate(operator_token, binding["etag"], [
                {"field": "business_date", "present": True, "value": False},
                {"field": "note", "present": True, "value": ""},
            ], "rt_evaluate_clear")
            self._record_case(cases, "evaluate_explicit_clear", status, cleared)
            self.assertEqual(status, 200, cleared.get("error"))
            self.assertEqual(cleared["data"]["feedback_evaluation"]["result"], {
                "content": "建议补充办理日期；建议补充办理说明",
                "visible": True,
            })

            status, hidden = self._evaluate(operator_token, binding["etag"], [
                {"field": "business_date", "present": True, "value": "2026-10-23"},
                {"field": "note", "present": True, "value": "已填写"},
            ], "rt_evaluate_hidden")
            self._record_case(cases, "evaluate_valid_hidden", status, hidden)
            self.assertEqual(status, 200, hidden.get("error"))
            self.assertEqual(hidden["data"]["feedback_evaluation"]["result"], {
                "content": "",
                "visible": False,
            })

            status, missing = self._evaluate(operator_token, binding["etag"], [
                {"field": "business_date", "present": False},
                {"field": "note", "present": True, "value": ""},
            ], "rt_evaluate_missing")
            self._record_case(cases, "evaluate_missing_dependency", status, missing)
            self.assertEqual(status, 422, missing)
            self.assertEqual(self._reason(missing), "FEEDBACK_INPUT_INVALID")

            status, stale = self._evaluate(operator_token, "0" * 64, [
                {"field": "business_date", "present": True, "value": False},
                {"field": "note", "present": True, "value": False},
            ], "rt_evaluate_stale")
            self._record_case(cases, "evaluate_stale_binding", status, stale)
            self.assertEqual(status, 409, stale)
            self.assertEqual(self._reason(stale), "FEEDBACK_BINDING_STALE")

            no_draft_capability = self._feedback_params({
                "version": "1.0.0",
                "operation": "describe",
                "request_id": "rt_no_capability",
                "view_id": self.view.id,
                "container_id": self.container_id,
            }, capabilities=["form.feedback.message.v1"])
            status, denied_capability = self._intent(
                "api.onchange", no_draft_capability, token=operator_token,
            )
            self._record_case(cases, "missing_draft_capability", status, denied_capability)
            self.assertEqual(status, 409, denied_capability)
            self.assertEqual(self._reason(denied_capability), "COMPONENT_CAPABILITY_REQUIRED")

            invalid_view = self._feedback_params({
                "version": "1.0.0",
                "operation": "describe",
                "request_id": "rt_invalid_view",
                "view_id": self.env.ref("project.edit_project").id,
                "container_id": self.container_id,
            })
            status, invalid = self._intent("api.onchange", invalid_view, token=operator_token)
            self._record_case(cases, "invalid_context_view", status, invalid)
            self.assertEqual(status, 422, invalid)
            self.assertEqual(self._reason(invalid), "FEEDBACK_SOURCE_INVALID")

            ordinary_params = {
                "model": MODEL,
                "values": {"business_date": False, "note": ""},
                "changed_fields": ["business_date"],
                "context": {"allowed_company_ids": [self.env.company.id]},
            }
            status, ordinary = self._intent("api.onchange", ordinary_params, token=operator_token)
            cases.append({
                "case": "ordinary_onchange",
                "http_status": status,
                "business_ok": ordinary.get("ok") is True,
                "reason_code": self._reason(ordinary),
                "status": "ordinary",
                "result": None,
                "patch_empty": (ordinary.get("data") or {}).get("patch") == {},
                "patch_keys": sorted(((ordinary.get("data") or {}).get("patch") or {}).keys()),
            })
            self.assertEqual(status, 200, ordinary.get("error"))
            self.assertTrue(ordinary.get("ok"), ordinary.get("error"))
            self.assertNotIn("feedback_evaluation", ordinary.get("data") or {})

            self.assertEqual(self.env[MODEL].search_count([]), 0)

        denied_token = self._login(self.denied.login, self.denied_password)
        status, permission = self._describe(denied_token, "rt_permission")
        self._record_case(cases, "permission_denied", status, permission)
        self.assertEqual(status, 403, permission)
        self.assertFalse(permission.get("ok"))

        evidence = {
            "database": self.env.cr.dbname,
            "odoo_version": release.version,
            "source_file": draft_feedback.__file__,
            "model": MODEL,
            "view_id": self.view.id,
            "container_id": self.container_id,
            "user_id": self.operator.id,
            "case_count": len(cases),
            "cases": cases,
            "sha256": hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest(),
        }
        _logger.info("%s%s", EVIDENCE_PREFIX, json.dumps(evidence, ensure_ascii=False, sort_keys=True))
