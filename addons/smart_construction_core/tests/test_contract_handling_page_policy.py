# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval

from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler
from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
from odoo.addons.smart_construction_core import smart_core_business_category_policy_bindings
from odoo.addons.smart_construction_core.models.support.business_form_policy_templates import (
    get_business_category_form_policy_templates,
)


ENTRY_CASES = (
    (
        "action_construction_contract_income",
        "construction.contract.income",
        "contract.income",
        "business_category_contract_income",
    ),
    (
        "action_construction_contract_expense",
        "construction.contract.expense",
        "contract.expense",
        "business_category_contract_expense",
    ),
)


@tagged("contract_handling_page_policy", "post_install", "-at_install")
class TestContractHandlingPagePolicy(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env["sc.business.category"]._sync_seed_form_policies()
        self.assembler = PageAssembler(self.env, self.env["ir.model"].sudo().env)

    def test_formal_wrapper_entries_bind_to_their_explicit_category_policy(self):
        declarations = smart_core_business_category_policy_bindings(self.env, {})["bindings"]
        self.assertEqual(
            declarations,
            [
                {
                    "entry_model": "construction.contract.income",
                    "category_code": "contract.income",
                    "policy_target_model": "construction.contract",
                },
                {
                    "entry_model": "construction.contract.expense",
                    "category_code": "contract.expense",
                    "policy_target_model": "construction.contract",
                },
            ],
        )

        for action_xmlid, model_name, category_code, category_xmlid in ENTRY_CASES:
            with self.subTest(model=model_name):
                action = self.env.ref("smart_construction_core.%s" % action_xmlid)
                context = safe_eval(action.context or "{}", {"context": {}})
                self.assertEqual(action.res_model, model_name)
                self.assertEqual(context["default_business_category_code"], category_code)
                resolved = self.assembler._business_category_from_context(
                    {"context": context},
                    model_name,
                )
                self.assertEqual(
                    resolved,
                    self.env.ref("smart_construction_core.%s" % category_xmlid),
                )

    def test_direct_model_binding_remains_authoritative(self):
        resolved = self.assembler._business_category_from_context(
            {"context": {"default_business_category_code": "contract.income"}},
            "construction.contract",
        )
        self.assertEqual(
            resolved,
            self.env.ref("smart_construction_core.business_category_contract_income"),
        )

    def test_missing_or_crossed_wrapper_binding_does_not_select_another_policy(self):
        self.assertFalse(
            self.assembler._business_category_from_context(
                {"context": {"default_business_category_code": "contract.expense"}},
                "construction.contract.income",
            )
        )
        self.assertFalse(
            self.assembler._business_category_from_context(
                {"context": {"default_business_category_code": "contract.income.supplement"}},
                "construction.contract.income",
            )
        )

    def test_income_policy_reaches_source_contract_with_profile_visibility(self):
        action = self.env.ref("smart_construction_core.action_construction_contract_income")
        action_payload = action.read()[0]
        context = safe_eval(action.context or "{}", {"context": {}})
        policy = get_business_category_form_policy_templates()["contract.income"]
        contract_scope = next(
            section
            for section in policy["sections"]
            if section["name"] == "contract_scope"
        )
        self.assertIn("contract_type_id", contract_scope["fields"])
        contract_type_policy = next(
            field_policy
            for field_policy in policy["fields"]
            if field_policy["name"] == "contract_type_id"
        )
        self.assertEqual(
            contract_type_policy["visible_profiles"],
            ["create", "edit", "readonly"],
        )
        self.assertEqual(contract_type_policy["readonly_profiles"], ["readonly"])

        create_page, _versions = self.assembler.assemble_page_contract(
            {
                "model": action.res_model,
                "view_types": ["form"],
                "action_id": action.id,
                "context": context,
                "render_profile": "create",
            },
            action=action_payload,
        )
        readonly_page, _versions = self.assembler.assemble_page_contract(
            {
                "model": action.res_model,
                "view_types": ["form"],
                "action_id": action.id,
                "context": context,
                "render_profile": "readonly",
            },
            action=action_payload,
        )

        self.assertEqual(create_page["business_form_policy"]["category_code"], "contract.income")
        self.assertEqual(readonly_page["business_form_policy"]["category_code"], "contract.income")
        self.assertEqual(create_page["business_form_policy"]["source"], "sc.business.category.form_policy_json")
        self.assertEqual(
            create_page["business_form_policy"]["field_labels"]["attachment_text"],
            "历史附件文本",
        )
        state_policy = next(
            row
            for row in create_page["business_form_policy"]["fields"]
            if row.get("name") == "state"
        )
        self.assertEqual(state_policy["visible_profiles"], ["edit", "readonly"])
        self.assertEqual(state_policy["readonly_profiles"], ["create", "edit", "readonly"])
        self.assertEqual(
            [group["label"] for group in create_page["field_groups"]],
            [
                "身份与基本资料",
                "合同范围",
                "合同明细与金额",
                "说明与附件",
                "履约信息",
            ],
        )
        self.assertEqual(
            [group["label"] for group in readonly_page["field_groups"]],
            [
                "身份与基本资料",
                "合同范围",
                "合同明细与金额",
                "说明与附件",
                "履约信息",
                "系统信息",
                "来源与系统追溯",
            ],
        )

    def test_expense_policy_declares_its_own_handling_sections_and_labels(self):
        policy = get_business_category_form_policy_templates()["contract.expense"]
        self.assertEqual(
            [section["title"] for section in policy["sections"]],
            [
                "身份与基本资料",
                "合同范围",
                "合同明细与金额",
                "说明与附件",
                "履约信息",
                "系统信息",
                "来源与系统追溯",
                "历史付款承接",
            ],
        )
        field_labels = {
            field["name"]: field.get("label")
            for field in policy["fields"]
        }
        self.assertEqual(field_labels["partner_id"], "供应商/分包方")
        self.assertEqual(field_labels["attachment_text"], "平台附件文本")

    def test_income_policy_reaches_final_v2_sections_and_state_status(self):
        action = self.env.ref("smart_construction_core.action_construction_contract_income")
        menu = self.env.ref("smart_construction_core.menu_sc_p1_income_contract")
        common = {
            "model": action.res_model,
            "view_type": "form",
            "record_id": "new",
            "action_id": action.id,
            "menu_id": menu.id,
            "client_type": "web_pc",
        }
        handler = UiContractV2Handler(
            self.env,
            su_env=self.env["ir.model"].sudo().env,
        )
        create_result = handler.handle({**common, "render_profile": "create"})
        readonly_result = handler.handle(
            {
                **{key: value for key, value in common.items() if key != "record_id"},
                "render_profile": "readonly",
            }
        )
        create_envelope = (
            create_result.to_legacy_dict()
            if hasattr(create_result, "to_legacy_dict")
            else create_result
        )
        readonly_envelope = (
            readonly_result.to_legacy_dict()
            if hasattr(readonly_result, "to_legacy_dict")
            else readonly_result
        )
        self.assertTrue(create_envelope.get("ok", True), create_envelope)
        self.assertTrue(readonly_envelope.get("ok", True), readonly_envelope)

        create_contract = create_envelope["data"]
        readonly_contract = readonly_envelope["data"]
        structure = create_contract["formStructureContract"]
        self.assertEqual(structure["presentationMode"], "task")
        self.assertEqual(structure["sourceAuthority"]["governance_source"]["categoryCode"], "contract.income")
        self.assertEqual(structure["fieldLabels"]["attachment_text"], "历史附件文本")

        def collect_field_codes(value):
            if isinstance(value, dict):
                codes = [value["fieldCode"]] if value.get("fieldCode") else []
                for nested in value.values():
                    codes.extend(collect_field_codes(nested))
                return codes
            if isinstance(value, list):
                codes = []
                for nested in value:
                    codes.extend(collect_field_codes(nested))
                return codes
            return []

        self.assertIn(
            "contract_type_id",
            collect_field_codes(create_contract["layoutContract"]["containerTree"]),
        )
        contract_type_widget_ids = []

        def collect_contract_type_widgets(value):
            if isinstance(value, dict):
                if value.get("fieldCode") == "contract_type_id" and value.get("widgetId"):
                    contract_type_widget_ids.append(value["widgetId"])
                for nested in value.values():
                    collect_contract_type_widgets(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect_contract_type_widgets(nested)

        collect_contract_type_widgets(create_contract["layoutContract"]["containerTree"])
        status_by_widget = {
            row["widgetId"]: row
            for row in create_contract["statusContract"]["widgetStatus"]
        }
        self.assertTrue(contract_type_widget_ids)
        self.assertTrue(
            all(status_by_widget[widget_id]["visible"] for widget_id in contract_type_widget_ids)
        )
        self.assertTrue(
            all(not status_by_widget[widget_id]["readonly"] for widget_id in contract_type_widget_ids)
        )
        self.assertEqual(
            [slot["title"] for slot in structure["slots"]],
            [
                "身份与基本资料",
                "合同范围",
                "合同明细与金额",
                "说明与附件",
            ],
        )
        self.assertEqual(
            [slot["title"] for slot in readonly_contract["formStructureContract"]["slots"]],
            [
                "身份与基本资料",
                "合同范围",
                "合同明细与金额",
                "说明与附件",
                "履约信息",
                "系统信息",
                "来源与系统追溯",
            ],
        )

        def state_widget_status(contract):
            state_widget_ids = []

            def visit(value):
                if isinstance(value, dict):
                    if value.get("fieldCode") == "state" and value.get("widgetId"):
                        state_widget_ids.append(value["widgetId"])
                    for nested in value.values():
                        visit(nested)
                elif isinstance(value, list):
                    for nested in value:
                        visit(nested)

            visit(contract["layoutContract"]["containerTree"])
            statuses = {
                row["widgetId"]: row
                for row in contract["statusContract"]["widgetStatus"]
            }
            return [statuses[widget_id] for widget_id in state_widget_ids]

        create_state_status = state_widget_status(create_contract)
        readonly_state_status = state_widget_status(readonly_contract)
        self.assertTrue(create_state_status)
        self.assertTrue(readonly_state_status)
        self.assertTrue(all(row.get("visible") is False for row in create_state_status))
        self.assertTrue(all(row.get("visible") is True for row in readonly_state_status))
        self.assertTrue(all(row.get("readonly") is True for row in readonly_state_status))

    def test_expense_policy_reaches_final_v2_sections_labels_and_state_status(self):
        action = self.env.ref("smart_construction_core.action_construction_contract_expense")
        menu = self.env.ref("smart_construction_core.menu_sc_p1_expense_contract")
        common = {
            "model": action.res_model,
            "view_type": "form",
            "record_id": "new",
            "action_id": action.id,
            "menu_id": menu.id,
            "client_type": "web_pc",
        }
        handler = UiContractV2Handler(
            self.env,
            su_env=self.env["ir.model"].sudo().env,
        )
        create_result = handler.handle({**common, "render_profile": "create"})
        readonly_result = handler.handle(
            {
                **{key: value for key, value in common.items() if key != "record_id"},
                "render_profile": "readonly",
            }
        )
        create_envelope = (
            create_result.to_legacy_dict()
            if hasattr(create_result, "to_legacy_dict")
            else create_result
        )
        readonly_envelope = (
            readonly_result.to_legacy_dict()
            if hasattr(readonly_result, "to_legacy_dict")
            else readonly_result
        )
        self.assertTrue(create_envelope.get("ok", True), create_envelope)
        self.assertTrue(readonly_envelope.get("ok", True), readonly_envelope)

        create_contract = create_envelope["data"]
        readonly_contract = readonly_envelope["data"]
        structure = create_contract["formStructureContract"]
        self.assertEqual(structure["presentationMode"], "task")
        self.assertEqual(
            structure["sourceAuthority"]["governance_source"]["categoryCode"],
            "contract.expense",
        )
        self.assertEqual(structure["fieldLabels"]["partner_id"], "供应商/分包方")
        self.assertEqual(structure["fieldLabels"]["attachment_text"], "平台附件文本")
        self.assertEqual(
            [slot["title"] for slot in structure["slots"]],
            [
                "身份与基本资料",
                "合同范围",
                "合同明细与金额",
                "说明与附件",
            ],
        )
        self.assertEqual(
            [slot["title"] for slot in readonly_contract["formStructureContract"]["slots"]],
            [
                "身份与基本资料",
                "合同范围",
                "合同明细与金额",
                "说明与附件",
                "履约信息",
                "系统信息",
                "来源与系统追溯",
                "历史付款承接",
            ],
        )

        def state_widget_status(contract):
            state_widget_ids = []

            def visit(value):
                if isinstance(value, dict):
                    if value.get("fieldCode") == "state" and value.get("widgetId"):
                        state_widget_ids.append(value["widgetId"])
                    for nested in value.values():
                        visit(nested)
                elif isinstance(value, list):
                    for nested in value:
                        visit(nested)

            visit(contract["layoutContract"]["containerTree"])
            statuses = {
                row["widgetId"]: row
                for row in contract["statusContract"]["widgetStatus"]
            }
            return [statuses[widget_id] for widget_id in state_widget_ids]

        create_state_status = state_widget_status(create_contract)
        readonly_state_status = state_widget_status(readonly_contract)
        self.assertTrue(create_state_status)
        self.assertTrue(readonly_state_status)
        self.assertTrue(all(row.get("visible") is False for row in create_state_status))
        self.assertTrue(all(row.get("visible") is True for row in readonly_state_status))
        self.assertTrue(all(row.get("readonly") is True for row in readonly_state_status))
