"""Native workspace feedback: exact view binding, draft behavior and isolation."""
from contextlib import ExitStack
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged
from odoo.addons.smart_core.core import draft_feedback, native_advisory


@tagged("post_install", "-at_install", "workspace_processing_feedback")
class TestWorkspaceProcessingFeedback(TransactionCase):
    CASES = (
        ("sc.team.loan.deduction.workspace", "team_loan_deduction_workspace",
         "建议补充办理日期；建议补充办理说明", False),
        ("sc.current.account.workspace", "current_account_workspace",
         "办理承包人借还款前请选择承包人/往来单位；建议补充办理日期；建议补充办理说明", True),
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = cls.env.ref("base.group_user") | cls.env.ref(
            "smart_construction_core.group_sc_cap_project_user"
        ) | cls.env.ref("smart_construction_core.group_sc_cap_finance_user")
        cls.operator = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Workspace feedback regression operator",
            "login": "workspace_feedback_regression_operator",
            "company_id": cls.env.company.id,
            "company_ids": [(6, 0, cls.env.company.ids)],
            "groups_id": [(6, 0, groups.ids)],
        })

    def model(self, name):
        return self.env[name].with_user(self.operator).with_context(
            allowed_company_ids=self.env.company.ids, lang="en_US",
        )

    def binding(self, model, stem):
        view = self.env.ref("smart_construction_core.view_sc_%s_form" % stem)
        contract, _proof = draft_feedback._assemble_contract(model, view.id)
        nodes = list(native_advisory.walk(contract["layoutContract"]["containerTree"]))
        hosts = [n for n, _ in nodes if n.get("componentKey") == draft_feedback.COMPONENT_KEY]
        self.assertEqual(len(hosts), 1)
        host = hosts[0]
        source = next(n for n, _ in nodes if n.get("containerId") ==
                      host["componentConfig"]["contentRef"]["containerId"])
        self.assertEqual(source["name"], "processing_advisory")
        request = {
            "version": draft_feedback.VERSION, "operation": "describe",
            "request_id": "workspace_describe", "view_id": view.id,
            "container_id": host["containerId"],
        }
        binding = draft_feedback.evaluate(model, request)["binding"]
        return request, binding

    def test_native_binding_and_draft_visibility_without_business_writes(self):
        for name, stem, empty_message, has_partner in self.CASES:
            with self.subTest(model=name):
                model = self.model(name)
                request, binding = self.binding(model, stem)
                expected = ([{"field": "partner_id", "type": "many2one_presence"}]
                            if has_partner else []) + [
                    {"field": "business_date", "type": "date"},
                    {"field": "note", "type": "text"},
                ]
                self.assertEqual(binding["dependencies"], expected)
                before = model.search_count([])
                with ExitStack() as stack:
                    for target in (model, self.env["res.partner"], self.env["project.project"]):
                        for method in ("create", "write", "unlink"):
                            stack.enter_context(patch.object(type(target), method,
                                side_effect=AssertionError("feedback attempted business mutation")))
                    for complete in (False, True):
                        values = {"partner_id": complete,
                                  "business_date": "2026-10-26" if complete else False,
                                  "note": "已核实办理背景" if complete else False}
                        result = draft_feedback.evaluate(model, {
                            **request, "operation": "evaluate",
                            "binding_etag": binding["etag"],
                            "inputs": [{"field": dep["field"], "present": True,
                                        "value": values[dep["field"]]} for dep in expected],
                        })
                        self.assertEqual(result["result"], {
                            "content": "" if complete else empty_message,
                            "visible": not complete,
                        })
                self.assertEqual(model.search_count([]), before)

    def test_binding_cannot_be_reused_for_another_workspace(self):
        name, stem, *_ = self.CASES[0]
        request, _binding = self.binding(self.model(name), stem)
        with self.assertRaises(draft_feedback.DraftFeedbackError):
            draft_feedback.evaluate(self.model(self.CASES[1][0]), request)

    def test_each_dependency_removes_only_its_own_suggestion(self):
        for name, stem, empty_message, _has_partner in self.CASES:
            with self.subTest(model=name):
                model = self.model(name)
                request, binding = self.binding(model, stem)
                messages = empty_message.split("；")
                complete_values = {"partner_id": True, "business_date": "2026-10-26",
                                   "note": "已核实办理背景"}
                for index, dependency in enumerate(binding["dependencies"]):
                    with self.subTest(changed_field=dependency["field"]):
                        result = draft_feedback.evaluate(model, {
                            **request, "operation": "evaluate", "binding_etag": binding["etag"],
                            "inputs": [{"field": dep["field"], "present": True,
                                "value": complete_values[dep["field"]] if dep == dependency else False}
                                for dep in binding["dependencies"]],
                        })
                        self.assertEqual(result["result"], {
                            "content": "；".join(messages[:index] + messages[index + 1:]),
                            "visible": True,
                        })

    def test_new_form_defaults_explicitly_cover_feedback_dependencies(self):
        for name, stem, _message, _has_partner in self.CASES:
            with self.subTest(model=name):
                model = self.model(name)
                request, binding = self.binding(model, stem)
                fields = [dep["field"] for dep in binding["dependencies"]]
                defaults = model.default_get(fields)
                self.assertEqual(set(defaults), set(fields))
                # Odoo Text converts its explicit false default to None; the
                # key must remain present so draft feedback sees known empty.
                self.assertIsNone(defaults["note"])
                self.assertTrue(defaults["business_date"])
                if "partner_id" in defaults:
                    self.assertIs(defaults["partner_id"], False)
