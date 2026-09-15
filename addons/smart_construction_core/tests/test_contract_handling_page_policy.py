# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval
from odoo.tools.convert import convert_file

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
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Exercise the actual upgrade declarations inside this rolled-back test
        # transaction; local.dev.test deliberately does not upgrade its database.
        for filename in ("view_orchestration_contract_data.xml", "view_orchestration_form_section_contract_data.xml"):
            convert_file(cls.env, "smart_construction_core", "data/" + filename, {},
                         mode="update", noupdate=False)

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

    def test_category_templates_keep_semantics_without_structure(self):
        policies = get_business_category_form_policy_templates()
        for code in ("contract.income", "contract.expense"):
            policy = policies[code]
            self.assertNotIn("sections", policy)
            fields = {row["name"]: row for row in policy["fields"]}
            self.assertEqual(fields["tax_id"]["required_profiles"], ["create", "edit"])
            self.assertEqual(fields["state"]["visible_profiles"], ["edit", "readonly"])
            self.assertEqual(fields["state"]["readonly_profiles"], ["create", "edit", "readonly"])
            self.assertEqual(fields["settlement_amount"]["visible_profiles"], ["readonly"])
            self.assertEqual(fields["attachment_text"]["label"],
                             "历史附件文本" if code.endswith("income") else "平台附件文本")
            # Supplement entries have not migrated in this batch.
            self.assertTrue(policies[code + ".supplement"]["sections"])

    def test_policy_profiles_still_reach_native_source_contract(self):
        for action_xmlid, model_name, code, _category_xmlid in ENTRY_CASES:
            action = self.env.ref("smart_construction_core." + action_xmlid)
            context = safe_eval(action.context or "{}", {"context": {}})
            for profile in ("create", "edit", "readonly"):
                page, _versions = self.assembler.assemble_page_contract(
                    {"model": model_name, "view_types": ["form"], "action_id": action.id,
                     "context": context, "render_profile": profile}, action=action.read()[0])
                self.assertEqual(page["business_form_policy"]["category_code"], code)
                self.assertEqual(page["business_form_policy"]["layout_fields"], [])
                self.assertEqual(page["field_policies"]["state"]["visible_profiles"], ["edit", "readonly"])
                self.assertEqual(page["field_policies"]["tax_id"]["required_profiles"], ["create", "edit"])

    @staticmethod
    def _nodes(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from TestContractHandlingPagePolicy._nodes(child)
        elif isinstance(value, list):
            for child in value:
                yield from TestContractHandlingPagePolicy._nodes(child)

    def test_contract_entries_use_native_tree_and_preserve_profiles(self):
        handler = UiContractV2Handler(self.env, su_env=self.env["ir.model"].sudo().env)
        for action_xmlid, model_name, code, _category_xmlid in ENTRY_CASES:
            action = self.env.ref("smart_construction_core." + action_xmlid)
            direction = code.split(".")[1]
            menu = self.env.ref("smart_construction_core.menu_sc_p1_" + direction + "_contract")
            for profile in ("create", "readonly"):
                with self.subTest(model=model_name, profile=profile):
                    params = {"model": model_name, "view_type": "form", "action_id": action.id,
                              "menu_id": menu.id, "client_type": "web_pc", "render_profile": profile}
                    if profile == "create":
                        params["record_id"] = "new"
                    result = handler.handle(params)
                    envelope = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
                    self.assertTrue(envelope.get("ok", True), envelope)
                    contract = envelope["data"]
                    structure = contract["formStructureContract"]
                    self.assertEqual(structure["layoutPolicy"], "container_tree_authority")
                    self.assertEqual(structure["presentationMode"], "task")
                    self.assertEqual(structure["slots"], [])
                    if profile == "readonly":
                        self.assertEqual(contract["statusContract"]["globalStatus"]["pageAuth"], "read")
                    provenance = structure["sourceAuthority"]["governance_source"]
                    self.assertEqual(provenance.get("compatibilityDependencies", []), [])
                    self.assertEqual(provenance.get("structureDiagnostics", []), [])
                    nodes = list(self._nodes(contract["layoutContract"]["containerTree"]))
                    field_nodes = [n for n in nodes if n.get("fieldCode") and n.get("widgetId")]
                    names = {n["fieldCode"] for n in field_nodes}
                    self.assertTrue({"line_ids", "tax_id", "project_id", "partner_id", "subject"} <= names)
                    statuses = {row["widgetId"]: row for row in contract["statusContract"]["widgetStatus"]}
                    for n in field_nodes:
                        if n["fieldCode"] == "state":
                            self.assertEqual(statuses[n["widgetId"]]["visible"], profile != "create")
                            self.assertTrue(statuses[n["widgetId"]]["readonly"])
                        if n["fieldCode"] in ("document_status", "company_id", "approval_info", "visible_invoice_amount", "visible_received_amount"):
                            self.assertEqual(statuses[n["widgetId"]]["visible"], profile == "readonly")
                        if n["fieldCode"] in ("amount_untaxed", "amount_tax", "amount_total"):
                            self.assertTrue(statuses[n["widgetId"]]["readonly"])

    def test_upgrade_retires_only_the_expense_order_owner(self):
        old = self.env.ref("smart_construction_core.business_config_contract_construction_contract_expense_form_structure_generated")
        self.assertFalse(old.active)
        for xmlid in ("business_config_contract_income_contract_form_structure", "business_config_contract_expense_contract_native_form"):
            record = self.env.ref("smart_construction_core." + xmlid)
            self.assertTrue(record.active)
            spec = record.contract_json["view_orchestration"]["views"]["form"]
            self.assertEqual(spec, {"composition_mode": "native_semantic_surface"})


@tagged("settlement_native_structure", "post_install", "-at_install")
class TestSettlementNativeStructure(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for filename in ("views/core/settlement_views.xml", "data/settlement_order_form_productization_contract.xml",
                         "data/view_orchestration_form_section_contract_data.xml"):
            convert_file(cls.env, "smart_construction_core", filename, {}, mode="update", noupdate=False)
        cls.env["sc.business.category"]._sync_seed_form_policies()

    def test_actions_keep_direction_domain_category_and_shared_form(self):
        for direction, flow in (("income", "in"), ("expense", "out")):
            action = self.env.ref("smart_construction_core.action_sc_settlement_order_" + direction)
            context = safe_eval(action.context or "{}", {"context": {}})
            self.assertEqual(context["default_settlement_type"], flow)
            self.assertEqual(context["default_business_category_code"], "settlement." + direction)
            self.assertIn(("business_category_id.code", "=", "settlement." + direction), safe_eval(action.domain))
            self.assertIn(("contract_source_kind", "!=", "general_contract"), safe_eval(action.domain))
            defaults = self.env["sc.settlement.order"].with_context(**context).default_get(["settlement_type"])
            self.assertEqual(defaults["settlement_type"], flow)
            self.assertIn((self.env.ref("smart_construction_core.view_sc_settlement_order_form").id, "form"), action.views)

    def test_category_retains_field_policies_without_structure(self):
        policies = get_business_category_form_policy_templates()
        for code in ("settlement.income", "settlement.expense"):
            policy = policies[code]
            self.assertNotIn("sections", policy)
            fields = {f["name"]: f for f in policy["fields"]}
            self.assertEqual(fields["project_id"]["required_profiles"], ["create", "edit"])
            self.assertEqual(fields["line_ids"]["required_profiles"], ["create", "edit"])
            for name in ("settlement_type", "settlement_flow_label", "state"):
                self.assertEqual(fields[name]["readonly_profiles"], ["create", "edit", "readonly"])
            for name in ("amount_paid", "amount_payable", "invoice_amount", "legacy_fact_id"):
                self.assertEqual(fields[name]["visible_profiles"], ["readonly"])
            self.assertIn("attachment_ids", fields)

    def test_native_contract_requires_explicit_empty_compatibility_and_keeps_controls(self):
        handler = UiContractV2Handler(self.env, su_env=self.env["ir.model"].sudo().env)
        for direction in ("income", "expense"):
            action = self.env.ref("smart_construction_core.action_sc_settlement_order_" + direction)
            context = safe_eval(action.context or "{}", {"context": {}})
            for profile in ("create", "readonly"):
                params = {"op": "model", "model": "sc.settlement.order", "view_type": "form",
                          "action_id": action.id, "context": context, "render_profile": profile}
                if profile == "create":
                    params["record_id"] = "new"
                result = handler.handle(params)
                contract = (result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result)["data"]
                structure = contract["formStructureContract"]
                self.assertEqual(structure["layoutPolicy"], "container_tree_authority")
                provenance = structure["sourceAuthority"]["governance_source"]
                self.assertIn("compatibilityDependencies", provenance)
                self.assertEqual(provenance["compatibilityDependencies"], [])
                self.assertEqual(provenance["configuredSections"], [])
                self.assertFalse(provenance["legacyFieldPolicyOverlay"])
                self.assertFalse(provenance["formLayoutOverlay"])
                nodes = list(TestContractHandlingPagePolicy._nodes(contract["layoutContract"]["containerTree"]))
                widgets = [n for n in nodes if n.get("fieldCode") and n.get("widgetId")]
                self.assertTrue({"line_ids", "amount_total", "settlement_amount", "attachment_ids", "settlement_type"}
                                <= {n["fieldCode"] for n in widgets})
                statuses = {s["widgetId"]: s for s in contract["statusContract"]["widgetStatus"]}
                for widget in widgets:
                    if widget["fieldCode"] in ("amount_total", "settlement_type", "business_category_id", "deduction_amount"):
                        self.assertTrue(statuses[widget["widgetId"]]["readonly"])
                if profile == "readonly":
                    self.assertEqual(contract["statusContract"]["globalStatus"]["pageAuth"], "read")
                detail = next(n for n in nodes if n.get("containerId") == "sc_settlement_detail_amount")
                self.assertEqual(detail["span"], 24)

    def test_retirement_is_explicit_and_native_optins_are_action_scoped(self):
        retired = self.env.ref("smart_construction_core.business_config_contract_sc_settlement_order_form_structure_generated")
        self.assertFalse(retired.active)
        for direction in ("income", "expense"):
            action = self.env.ref("smart_construction_core.action_sc_settlement_order_" + direction)
            native = self.env.ref("smart_construction_core.business_config_contract_settlement_" + direction + "_native_form")
            self.assertEqual(native.action_id, action)
            self.assertEqual(native.contract_json["view_orchestration"]["views"]["form"],
                             {"composition_mode": "native_semantic_surface"})
        # Other same-model entries retain their own compatibility ownership.
        for xmlid in ("business_config_contract_daily_contract_settlement_form_v1",
                      "business_config_contract_settlement_order_productized_form_v1"):
            other = self.env.ref("smart_construction_core." + xmlid)
            self.assertTrue(other.active)
            self.assertTrue(other.contract_json["view_orchestration"]["views"]["form"]["sections"])

    def test_shared_native_form_keeps_conditional_contract_columns_and_attachment_ownership(self):
        from lxml import etree
        view = self.env.ref("smart_construction_core.view_sc_settlement_order_form")
        arch = etree.fromstring(view.arch_db.encode())
        detail = arch.xpath(".//group[@name='sc_settlement_detail_amount']/field[@name='line_ids']")[0]
        for nested in ("tree", "form/group"):
            self.assertEqual(detail.find(nested + "/field[@name='contract_id']").get("invisible"),
                             "parent.contract_source_kind == 'general_contract'")
            self.assertEqual(detail.find(nested + "/field[@name='general_contract_id']").get("invisible"),
                             "parent.contract_source_kind != 'general_contract'")
        self.assertTrue(arch.xpath(".//group[@name='sc_settlement_handling']//field[@name='attachment_ids']"))
        category = arch.xpath(".//group[@name='sc_settlement_business_object']/field[@name='business_category_id']")[0]
        self.assertEqual(category.get("readonly"), "1")
        for group in arch.xpath(".//group[@data-sc-collapsed-by-default='1']"):
            self.assertEqual(group.get("data-sc-collapsible"), "1")
