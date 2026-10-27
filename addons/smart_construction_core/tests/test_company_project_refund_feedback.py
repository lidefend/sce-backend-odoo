"""Controlled native advisory migration tests for the company project refund workbench."""
import copy
import json
import secrets
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

from lxml import etree
from odoo.exceptions import AccessError
from odoo.tests.common import HttpCase, TransactionCase, tagged

from odoo.addons.smart_core.core import draft_feedback, native_advisory
from odoo.addons.smart_core.core.form_configuration_compiler import FormConfigurationError
from odoo.addons.smart_core.tests.test_intent_smoke import setup_test_entry_namespace


MODEL = "sc.company.project.refund.workspace"
FIELD = "processing_advisory"
VIEW = "smart_construction_core.view_sc_company_project_refund_workspace_form"
OTHER_MODEL = "sc.labor.worker"
LOCATOR = "/form[1]/sheet[1]/div[1]/field[1]"
EVIDENCE_PREFIX = "LOCAL_DEV_COMPANY_PROJECT_REFUND_FEEDBACK_JSON="
ADVISORY_MODELS = (
    MODEL,
    "sc.current.account.workspace",
    "sc.team.loan.deduction.workspace",
    "sc.equipment.usage",
    "sc.hr.payroll.document",
    "sc.hr.salary.payment",
    "sc.subcontract.register",
    "sc.labor.usage",
    "sc.quality.acceptance",
    "sc.approval.policy",
    OTHER_MODEL,
)


def _fixture(env):
    base_group = env.ref("base.group_user")
    finance_group = env.ref("smart_construction_core.group_sc_cap_finance_user")
    company = env.company
    other_company = env["res.company"].create({"name": "Refund feedback denied company"})
    project = env["project.project"].create({"name": "Refund feedback regression project"})
    partner = env["res.partner"].create({"name": "Refund feedback regression partner"})
    password = secrets.token_urlsafe(24)
    denied_password = secrets.token_urlsafe(24)
    operator = env["res.users"].with_context(no_reset_password=True).create({
        "name": "Refund feedback finance operator",
        "login": "refund_feedback_finance_operator",
        "password": password,
        "company_id": company.id,
        "company_ids": [(6, 0, [company.id])],
        "groups_id": [(6, 0, (base_group | finance_group).ids)],
    })
    denied = env["res.users"].with_context(no_reset_password=True).create({
        "name": "Refund feedback denied operator",
        "login": "refund_feedback_denied_operator",
        "password": denied_password,
        "company_id": company.id,
        "company_ids": [(6, 0, [company.id])],
        "groups_id": [(6, 0, base_group.ids)],
    })
    return {
        "company": company,
        "other_company": other_company,
        "project": project,
        "partner": partner,
        "operator": operator,
        "denied": denied,
        "password": password,
        "denied_password": denied_password,
    }


class CompanyRefundFeedbackAssertions:
    def model(self):
        return self.env[MODEL].with_user(self.operator).with_context(
            allowed_company_ids=[self.company.id],
            lang="en_US",
        )

    def contract_parts(self, model=None):
        model = model or self.model()
        contract, _proof = draft_feedback._assemble_contract(model, self.view.id)
        rows = list(native_advisory.walk(contract["layoutContract"]["containerTree"]))
        hosts = [
            node for node, _parent in rows
            if node.get("componentKey") == draft_feedback.COMPONENT_KEY
        ]
        self.assertEqual(len(hosts), 1)
        host = hosts[0]
        source_id = host["componentConfig"]["contentRef"]["containerId"]
        sources = [node for node, _parent in rows if node.get("containerId") == source_id]
        self.assertEqual(len(sources), 1)
        return contract, host, sources[0]

    def request(self, operation, container_id, **values):
        block = {
            "version": draft_feedback.VERSION,
            "operation": operation,
            "request_id": "refund_" + operation,
            "view_id": self.view.id,
            "container_id": container_id,
        }
        if operation == "evaluate":
            block.update(
                binding_etag=values.pop("binding_etag"),
                inputs=values.pop("inputs"),
            )
        return block

    @contextmanager
    def no_business_writes(self):
        self.env.flush_all()
        cursor_type = type(self.env.cr)
        original = cursor_type.execute

        def readonly(cursor, query, *args, **kwargs):
            text = query.code if hasattr(query, "code") else query
            if isinstance(text, bytes):
                text = text.decode()
            statement = text.lstrip().upper() if isinstance(text, str) else ""
            self.assertTrue(
                statement.startswith((
                    "SELECT",
                    "SAVEPOINT",
                    "RELEASE SAVEPOINT",
                    "ROLLBACK TO SAVEPOINT",
                )),
                "Business mutation during refund feedback evaluation",
            )
            return original(cursor, query, *args, **kwargs)

        models = [
            type(self.model()),
            type(self.env["project.project"]),
            type(self.env["res.partner"]),
        ]
        with ExitStack() as stack:
            stack.enter_context(patch.object(cursor_type, "execute", readonly))
            for model in models:
                stack.enter_context(patch.object(
                    model, "create", side_effect=AssertionError("business create"),
                ))
                stack.enter_context(patch.object(
                    model, "write", side_effect=AssertionError("business write"),
                ))
                stack.enter_context(patch.object(
                    model, "unlink", side_effect=AssertionError("business unlink"),
                ))
            yield


@tagged(
    "post_install", "-at_install", "company_project_refund_feedback",
    "company_project_refund_feedback_orm",
)
class TestCompanyProjectRefundFeedback(CompanyRefundFeedbackAssertions, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for name, value in _fixture(cls.env).items():
            setattr(cls, name, value)
        cls.view = cls.env.ref(VIEW)

    def test_current_get_view_identity_and_single_declaration(self):
        model = self.model()
        layout, metadata = draft_feedback._native_layout(model, self.view.id)
        self.assertEqual(self.view.model, MODEL)
        self.assertEqual(self.view.type, "form")
        self.assertIn(FIELD, metadata)
        matches = [
            (node, parent) for node, parent in native_advisory.walk(layout)
            if native_advisory.identity(node) == (LOCATOR, 1)
        ]
        self.assertEqual(len(matches), 1)
        source, host = matches[0]
        self.assertEqual(source.get("type"), "field")
        self.assertEqual(source.get("name"), FIELD)
        native_advisory.host_shape(host, source, "test.refund")
        self.assertEqual(
            self.model()._fields[FIELD].sc_feedback_usage,
            {
                "purpose": "advisory",
                "occurrences": [{
                    "view_xmlid": VIEW,
                    "native_locator": LOCATOR,
                    "occurrence_index": 1,
                }],
            },
        )
        review = getattr(
            type(self.model())._compute_processing_advisory,
            "_sc_feedback_evaluation_review",
            None,
        )
        self.assertEqual(review, {
            "purpose": "advisory",
            "inputs": [
                {"field": "partner_id", "type": "many2one_presence"},
                {"field": "business_date", "type": "date"},
                {"field": "note", "type": "text"},
            ],
        })
        self.assertIsNone(
            getattr(self.env[OTHER_MODEL]._fields[FIELD], "sc_feedback_usage", None)
        )

    def test_only_reviewed_workspace_advisories_are_enabled(self):
        enabled = []
        for model_name in ADVISORY_MODELS:
            field = self.env[model_name]._fields.get(FIELD)
            self.assertIsNotNone(field, model_name)
            if getattr(field, "sc_feedback_usage", None) is not None:
                enabled.append(model_name)
        self.assertEqual(enabled, [
            MODEL, "sc.current.account.workspace", "sc.team.loan.deduction.workspace",
            "sc.equipment.usage", "sc.hr.payroll.document", "sc.hr.salary.payment", "sc.subcontract.register",
            "sc.labor.usage", "sc.quality.acceptance", "sc.approval.policy",
        ])

    def test_create_ui_contract_uses_request_local_feedback_proof(self):
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler

        action = self.env.ref("smart_construction_core.action_sc_product_company_project_refund_v1")
        result = UiContractV2Handler(
            self.model().env,
            su_env=self.env["ir.model"].sudo().env,
        ).handle({
            "op": "model",
            "model": MODEL,
            "action_id": action.id,
            "view_id": self.view.id,
            "view_type": "form",
            "render_profile": "create",
            "client_contract_capabilities": [
                "form.feedback.message.v1",
                "form.feedback.draft.v1",
            ],
        })
        payload = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
        self.assertTrue(payload.get("ok"), payload.get("error") or payload)
        rows = list(native_advisory.walk(
            payload["data"]["layoutContract"]["containerTree"]
        ))
        hosts = [
            node for node, _parent in rows
            if node.get("componentKey") == draft_feedback.COMPONENT_KEY
        ]
        self.assertEqual(len(hosts), 1)
        self.assertEqual(
            hosts[0]["componentConfig"]["evaluation"],
            {
                "capability": draft_feedback.CAPABILITY,
                "visibilityOwner": draft_feedback.VISIBILITY_OWNER,
            },
        )

    def test_presence_false_true_and_missing_are_distinct(self):
        model = self.model()
        contract, host, source = self.contract_parts(model)
        self.assertEqual(source["name"], FIELD)
        binding = draft_feedback.evaluate(
            model,
            self.request("describe", host["containerId"]),
        )["binding"]
        self.assertEqual(binding["dependencies"], [
            {"field": "partner_id", "type": "many2one_presence"},
            {"field": "business_date", "type": "date"},
            {"field": "note", "type": "text"},
        ])

        def evaluate(inputs, request_id):
            return draft_feedback.evaluate(model, {
                **self.request(
                    "evaluate",
                    host["containerId"],
                    binding_etag=binding["etag"],
                    inputs=inputs,
                ),
                "request_id": request_id,
            })

        before = self.env[MODEL].search_count([])
        with self.no_business_writes(), \
                patch.object(type(self.env["res.partner"]), "read",
                             side_effect=AssertionError("partner read")), \
                patch.object(type(self.env["res.partner"]), "search",
                             side_effect=AssertionError("partner search")):
            absent = evaluate([
                {"field": "partner_id", "present": True, "value": False},
                {"field": "business_date", "present": True, "value": False},
                {"field": "note", "present": True, "value": False},
            ], "refund_absent")
            self.assertEqual(absent["result"], {
                "content": "建议选择退款方/收款方，便于责任与资金台账归集；建议补充办理日期；建议补充退款原因或办理说明",
                "visible": True,
            })
            selected = evaluate([
                {"field": "partner_id", "present": True, "value": True},
                {"field": "business_date", "present": True, "value": False},
                {"field": "note", "present": True, "value": False},
            ], "refund_selected")
            self.assertEqual(selected["result"], {
                "content": "建议补充办理日期；建议补充退款原因或办理说明",
                "visible": True,
            })
            date_only = evaluate([
                {"field": "partner_id", "present": True, "value": True},
                {"field": "business_date", "present": True, "value": "2026-10-23"},
                {"field": "note", "present": True, "value": False},
            ], "refund_date_only")
            self.assertEqual(date_only["result"], {
                "content": "建议补充退款原因或办理说明",
                "visible": True,
            })
            note_only = evaluate([
                {"field": "partner_id", "present": True, "value": True},
                {"field": "business_date", "present": True, "value": False},
                {"field": "note", "present": True, "value": "退款说明"},
            ], "refund_note_only")
            self.assertEqual(note_only["result"], {
                "content": "建议补充办理日期",
                "visible": True,
            })
            complete = evaluate([
                {"field": "partner_id", "present": True, "value": True},
                {"field": "business_date", "present": True, "value": "2026-10-23"},
                {"field": "note", "present": True, "value": "退款说明"},
            ], "refund_complete")
            self.assertEqual(complete["result"], {"content": "", "visible": False})
        self.assertEqual(self.env[MODEL].search_count([]), before)
        serialized = json.dumps(
            [absent, selected, date_only, note_only, complete],
            ensure_ascii=False,
        )
        self.assertNotIn(str(self.partner.id), serialized)
        self.assertNotIn(self.partner.name, serialized)
        with self.assertRaisesRegex(
                draft_feedback.DraftFeedbackError, "FEEDBACK_INPUT_INVALID",
        ):
            evaluate([
                {"field": "partner_id", "present": False},
                {"field": "business_date", "present": True, "value": False},
                {"field": "note", "present": True, "value": False},
            ], "refund_missing")

    def test_invalid_relation_values_and_input_identity(self):
        model = self.model()
        _contract, host, _source = self.contract_parts(model)
        binding = draft_feedback.evaluate(
            model, self.request("describe", host["containerId"]),
        )["binding"]
        valid = [
            {"field": "partner_id", "present": True, "value": True},
            {"field": "business_date", "present": True, "value": False},
            {"field": "note", "present": True, "value": False},
        ]
        cases = [
            ([{**valid[0], "value": self.partner.id}, *valid[1:]], "FEEDBACK_CONFIG_INVALID"),
            ([{**valid[0], "value": "present"}, *valid[1:]], "FEEDBACK_INPUT_INVALID"),
            ([{**valid[0], "extra": True}, *valid[1:]], "FEEDBACK_CONFIG_INVALID"),
            ([valid[0], valid[0], valid[1], valid[2]], "FEEDBACK_CONFIG_INVALID"),
            ([*valid, {"field": "project_id", "present": True, "value": True}],
             "FEEDBACK_INPUT_INVALID"),
        ]
        for index, (inputs, reason_code) in enumerate(cases):
            with self.subTest(index=index), self.assertRaisesRegex(
                    draft_feedback.DraftFeedbackError, reason_code,
            ):
                draft_feedback.evaluate(model, {
                    **self.request(
                        "evaluate",
                        host["containerId"],
                        binding_etag=binding["etag"],
                        inputs=inputs,
                    ),
                    "request_id": f"refund_invalid_{index}",
                })

    def test_permissions_context_and_source_denials(self):
        denied_model = self.env[MODEL].with_user(self.denied).with_context(
            allowed_company_ids=[self.company.id],
        )
        with self.assertRaisesRegex(
                draft_feedback.DraftFeedbackError, "FEEDBACK_SOURCE_FORBIDDEN",
        ):
            draft_feedback.evaluate(
                denied_model,
                self.request("describe", "container.native.1.children.2"),
            )
        model = self.model()
        _contract, host, _source = self.contract_parts(model)
        describe = self.request("describe", host["containerId"])
        with patch.object(
                type(model), "check_field_access_rights", return_value=set(),
        ), self.assertRaisesRegex(
                draft_feedback.DraftFeedbackError, "FEEDBACK_SOURCE_FORBIDDEN",
        ):
            draft_feedback.evaluate(model, describe)
        wrong_company = model.with_context(
            allowed_company_ids=[self.other_company.id],
            company_id=self.other_company.id,
        )
        with self.assertRaisesRegex(
                draft_feedback.DraftFeedbackError, "FEEDBACK_SOURCE_FORBIDDEN",
        ):
            draft_feedback.evaluate(wrong_company, describe)

    def test_wrong_view_and_container_are_rejected(self):
        model = self.model()
        _contract, host, _source = self.contract_parts(model)
        with self.assertRaisesRegex(
                draft_feedback.DraftFeedbackError, "FEEDBACK_SOURCE_INVALID",
        ):
            draft_feedback.evaluate(model, {
                **self.request("describe", host["containerId"]),
                "view_id": self.env.ref("project.edit_project").id,
            })
        with self.assertRaisesRegex(
                draft_feedback.DraftFeedbackError, "FEEDBACK_SOURCE_INVALID",
        ):
            draft_feedback.evaluate(
                model, self.request("describe", "missing-refund-container"),
            )

    def test_compute_exception_is_structured_failure(self):
        model = self.model()
        _contract, host, _source = self.contract_parts(model)
        binding = draft_feedback.evaluate(
            model, self.request("describe", host["containerId"]),
        )["binding"]
        field_type = type(model._fields[FIELD])
        original = field_type.__get__

        def raising(field, record, owner=None):
            if field is model._fields[FIELD] and record:
                raise RuntimeError("synthetic refund compute failure")
            return original(field, record, owner)

        with patch.object(field_type, "__get__", raising), self.assertRaisesRegex(
                draft_feedback.DraftFeedbackError, "FEEDBACK_EVALUATION_FAILED",
        ):
            draft_feedback.evaluate(model, {
                **self.request(
                    "evaluate",
                    host["containerId"],
                    binding_etag=binding["etag"],
                    inputs=[
                        {"field": "partner_id", "present": True, "value": False},
                        {"field": "business_date", "present": True, "value": False},
                        {"field": "note", "present": True, "value": False},
                    ],
                ),
                "request_id": "refund_compute_failure",
            })

    def test_rollback_removes_only_singleton_and_fails_closed(self):
        model = self.model()
        field = model._fields[FIELD]
        method = type(model)._compute_processing_advisory
        self.assertIsNotNone(getattr(field, "sc_feedback_usage", None))
        self.assertTrue(hasattr(method, "_sc_feedback_evaluation_review"))
        self.assertIsNone(
            getattr(self.env[OTHER_MODEL]._fields[FIELD], "sc_feedback_usage", None)
        )
        with patch.object(field, "sc_feedback_usage", None), \
                patch.object(method, "_sc_feedback_evaluation_review", None, create=True):
            with self.assertRaisesRegex(
                    FormConfigurationError, "INTERACTION_FIELD_BODY_FORBIDDEN",
            ):
                draft_feedback._assemble_contract(model, self.view.id)
        self.assertIsNotNone(getattr(field, "sc_feedback_usage", None))
        self.assertTrue(hasattr(method, "_sc_feedback_evaluation_review"))


@tagged(
    "post_install", "-at_install", "company_project_refund_feedback",
    "company_project_refund_feedback_http",
)
class TestCompanyProjectRefundFeedbackHttp(
        CompanyRefundFeedbackAssertions, HttpCase,
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for name, value in _fixture(cls.env).items():
            setattr(cls, name, value)
        cls.view = cls.env.ref(VIEW)
        cls.entry_namespace = setup_test_entry_namespace(
            cls.env, "company-project-refund-feedback",
        )
        cls.entry_secret = secrets.token_urlsafe(24)
        cls.env["ir.config_parameter"].sudo().set_param(
            "sc.entry.shared_secret", cls.entry_secret,
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            "sc.entry.route_version", "company-refund-feedback-v1",
        )

    def headers(self, token="", anonymous=False):
        headers = {
            "X-SC-Namespace": self.entry_namespace,
            "X-SC-Audience": "tenant",
            "X-SC-Entry-Secret": self.entry_secret,
            "X-SC-Route-Version": "company-refund-feedback-v1",
            "Content-Type": "application/json",
        }
        if token:
            headers["Authorization"] = "Bearer " + token
        if anonymous:
            headers["X-Anonymous-Intent"] = "true"
        return headers

    def intent(self, intent, params, token="", anonymous=False):
        response = self.url_open(
            "/api/v1/intent",
            data=json.dumps({"intent": intent, "params": params or {}}),
            headers=self.headers(token, anonymous),
        )
        return response.status_code, response.json()

    def login(self, login, password):
        status, body = self.intent(
            "login",
            {"login": login, "password": password, "contract_mode": "compat"},
            anonymous=True,
        )
        self.assertEqual(status, 200, body.get("error"))
        token = (
            (body.get("data") or {}).get("token")
            or (((body.get("data") or {}).get("session") or {}).get("token"))
        )
        self.assertTrue(token, body.get("error"))
        status, initialized = self.intent("system.init", {}, token=token)
        self.assertEqual(status, 200, initialized.get("error"))
        self.assertTrue(initialized.get("ok"), initialized.get("error"))
        return token

    def feedback_params(self, block, capabilities=None, context=None):
        return {
            "model": MODEL,
            "values": {},
            "changed_fields": [],
            "context": context or {
                "allowed_company_ids": [self.company.id],
                "lang": "en_US",
            },
            "client_contract_capabilities": capabilities if capabilities is not None else [
                "form.feedback.message.v1",
                "form.feedback.draft.v1",
            ],
            "feedback_evaluation": block,
        }

    @staticmethod
    def reason(body):
        error = body.get("error") if isinstance(body.get("error"), dict) else {}
        return error.get("reason_code") or error.get("code") or ""

    @staticmethod
    def outcome(cases, name, status, body):
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        error = body.get("error") if isinstance(body.get("error"), dict) else {}
        feedback = (
            data.get("feedback_evaluation")
            or ((error.get("details") or {}).get("feedback_evaluation"))
            or {}
        )
        binding = feedback.get("binding") if isinstance(feedback.get("binding"), dict) else {}
        diagnostic = feedback.get("diagnostic") if isinstance(feedback.get("diagnostic"), dict) else {}
        cases.append({
            "case": name,
            "http_status": status,
            "business_ok": body.get("ok") is True,
            "reason_code": (
                error.get("reason_code") or error.get("code") or ""
            ),
            "feedback_status": feedback.get("status", ""),
            "result": feedback.get("result"),
            "diagnostic_path": diagnostic.get("path", ""),
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

    def test_real_http_presence_permissions_and_ordinary_onchange(self):
        cases = []
        model = self.model()
        _contract, host, _source = self.contract_parts(model)
        token = self.login(self.operator.login, self.password)
        status, described = self.intent(
            "api.onchange",
            self.feedback_params(self.request("describe", host["containerId"])),
            token=token,
        )
        self.outcome(cases, "describe", status, described)
        self.assertEqual(status, 200, described.get("error"))
        binding = described["data"]["feedback_evaluation"]["binding"]
        self.assertEqual(binding["view_id"], self.view.id)
        self.assertEqual(binding["native_locator"], LOCATOR)
        self.assertEqual(binding["dependencies"][0], {
            "field": "partner_id",
            "type": "many2one_presence",
        })

        def evaluate(inputs, request_id):
            return self.intent(
                "api.onchange",
                self.feedback_params({
                    **self.request(
                        "evaluate",
                        host["containerId"],
                        binding_etag=binding["etag"],
                        inputs=inputs,
                    ),
                    "request_id": request_id,
                }),
                token=token,
            )

        before = self.env[MODEL].search_count([])
        with self.no_business_writes():
            status, selected = evaluate([
                {"field": "partner_id", "present": True, "value": True},
                {"field": "business_date", "present": True, "value": False},
                {"field": "note", "present": True, "value": False},
            ], "refund_http_selected")
            self.outcome(cases, "presence_selected", status, selected)
            self.assertEqual(status, 200, selected.get("error"))
            self.assertEqual(selected["data"]["feedback_evaluation"]["result"], {
                "content": "建议补充办理日期；建议补充退款原因或办理说明",
                "visible": True,
            })
            status, hidden = evaluate([
                {"field": "partner_id", "present": True, "value": True},
                {"field": "business_date", "present": True, "value": "2026-10-23"},
                {"field": "note", "present": True, "value": "已填写"},
            ], "refund_http_hidden")
            self.outcome(cases, "visible_to_hidden", status, hidden)
            self.assertEqual(status, 200, hidden.get("error"))
            self.assertEqual(hidden["data"]["feedback_evaluation"]["result"], {
                "content": "",
                "visible": False,
            })
        self.assertEqual(self.env[MODEL].search_count([]), before)
        serialized = json.dumps([described, selected, hidden], ensure_ascii=False)
        self.assertNotIn(self.partner.name, serialized)
        self.assertNotIn(str(self.partner.id), serialized)

        status, missing = evaluate([
            {"field": "partner_id", "present": False},
            {"field": "business_date", "present": True, "value": False},
            {"field": "note", "present": True, "value": False},
        ], "refund_http_missing")
        self.outcome(cases, "missing_presence", status, missing)
        self.assertEqual(status, 422, missing)
        self.assertEqual(self.reason(missing), "FEEDBACK_INPUT_INVALID")

        status, ordinary = self.intent("api.onchange", {
            "model": MODEL,
            "values": {"project_id": self.project.id},
            "changed_fields": ["project_id"],
            "context": {"allowed_company_ids": [self.company.id], "lang": "en_US"},
        }, token=token)
        self.outcome(cases, "ordinary_onchange", status, ordinary)
        self.assertEqual(status, 200, ordinary.get("error"))
        self.assertNotIn("feedback_evaluation", ordinary.get("data") or {})

        denied_token = self.login(self.denied.login, self.denied_password)
        status, denied = self.intent(
            "api.onchange",
            self.feedback_params(self.request("describe", host["containerId"])),
            token=denied_token,
        )
        self.outcome(cases, "permission_denied", status, denied)
        self.assertEqual(status, 403, denied)

        wrong_company = self.intent(
            "api.onchange",
            self.feedback_params(
                self.request("describe", host["containerId"]),
                context={
                    "allowed_company_ids": [self.other_company.id],
                    "company_id": self.other_company.id,
                    "lang": "en_US",
                },
            ),
            token=token,
        )
        status, wrong_company_body = wrong_company
        self.outcome(cases, "wrong_company", status, wrong_company_body)
        self.assertEqual(status, 403, wrong_company_body)

        status, wrong_view = self.intent(
            "api.onchange",
            self.feedback_params({
                **self.request("describe", host["containerId"]),
                "view_id": self.env.ref("project.edit_project").id,
            }),
            token=token,
        )
        self.outcome(cases, "wrong_view", status, wrong_view)
        self.assertEqual(status, 422, wrong_view)

        status, no_capability = self.intent(
            "api.onchange",
            self.feedback_params(
                self.request("describe", host["containerId"]),
                capabilities=["form.feedback.message.v1"],
            ),
            token=token,
        )
        self.outcome(cases, "missing_draft_capability", status, no_capability)
        self.assertEqual(status, 409, no_capability)

        evidence = {
            "database": self.env.cr.dbname,
            "model": MODEL,
            "view_id": self.view.id,
            "cases": cases,
        }
        print(EVIDENCE_PREFIX + json.dumps(evidence, ensure_ascii=False, sort_keys=True))


@tagged(
    "post_install", "-at_install", "company_project_refund_feedback_restore",
)
class TestCompanyProjectRefundFeedbackRestore(TransactionCase):
    def test_no_fixture_residue(self):
        self.assertFalse(self.env["res.users"].sudo().search([
            ("login", "in", [
                "refund_feedback_finance_operator",
                "refund_feedback_denied_operator",
            ]),
        ]))
        self.assertFalse(self.env["project.project"].sudo().search([
            ("name", "=", "Refund feedback regression project"),
        ]))
        self.assertFalse(self.env["res.partner"].sudo().search([
            ("name", "=", "Refund feedback regression partner"),
        ]))
        self.assertFalse(self.env["sc.platform.namespace.alias"].sudo().search([
            ("alias", "=", "company-project-refund-feedback"),
            ("alias_kind", "=", "path"),
        ]))
        print("company_project_refund_feedback_restore: PASS")
