# -*- coding: utf-8 -*-
from lxml import etree

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval

from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler
from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler


PROFILE_CASES = (
    {
        "action": "action_construction_contract_income",
        "menu": "menu_sc_p1_income_contract",
        "view": "view_construction_contract_income_tree",
        "model": "construction.contract.income",
        "tree_column": "subject",
        "navigation_title": "收入合同履约结构",
    },
    {
        "action": "action_construction_contract_expense",
        "menu": "menu_sc_p1_expense_contract",
        "view": "view_construction_contract_expense_tree",
        "model": "construction.contract.expense",
        "tree_column": "subject",
        "navigation_title": "支出合同履约结构",
    },
)


@tagged("contract_execution_component_profile", "post_install", "-at_install")
class TestContractExecutionComponentProfile(TransactionCase):
    def test_profiles_bind_only_to_released_contract_workspaces(self):
        self.env["sc.product.policy"].sync_construction_menu_product_policies()
        policy = self.env["sc.product.policy"].search(
            [("product_key", "=", "construction.standard")], limit=1
        )
        formal_menus = {
            menu.get("menu_xmlid") or menu.get("page_key") or menu.get("menu_key"): menu
            for group in (policy.menu_groups or [])
            if isinstance(group, dict)
            for menu in (group.get("menus") or [])
            if isinstance(menu, dict)
        }
        contract_read = self.env.ref(
            "smart_construction_core.group_sc_cap_contract_read"
        )
        for case in PROFILE_CASES:
            with self.subTest(case=case["menu"]):
                menu = self.env.ref("smart_construction_core.%s" % case["menu"])
                action = self.env.ref("smart_construction_core.%s" % case["action"])
                menu_xmlid = "smart_construction_core.%s" % case["menu"]
                self.assertTrue(menu.active)
                self.assertEqual(menu.action, action)
                self.assertIn(contract_read, action.groups_id)
                self.assertIn(menu_xmlid, formal_menus)
                self.assertEqual(formal_menus[menu_xmlid].get("action_id"), action.id)

    def test_execution_views_declare_registered_worksheet_semantic(self):
        for case in PROFILE_CASES:
            with self.subTest(case=case["view"]):
                view = self.env.ref("smart_construction_core.%s" % case["view"])
                root = etree.fromstring(view.arch_db.encode("utf-8"))
                self.assertEqual(root.tag, "tree")
                self.assertEqual(root.get("js_class"), "smart_hierarchical_worksheet")

    def test_actions_declare_field_owned_execution_profiles(self):
        for case in PROFILE_CASES:
            with self.subTest(case=case["action"]):
                action = self.env.ref("smart_construction_core.%s" % case["action"])
                context = safe_eval(action.context or "{}", {"context": {}})
                profile = context["hierarchical_worksheet"]
                self.assertEqual(profile["navigation_mode"], "sheet_groups")
                self.assertEqual(profile["tree_column"], case["tree_column"])
                self.assertEqual(profile["navigation_title"], case["navigation_title"])
                self.assertEqual(
                    [row["field"] for row in profile["navigation_groups"]],
                    ["project_id", "partner_id", "document_status"],
                )
                declared_fields = set(self.env[case["model"]].fields_get())
                referenced_fields = {
                    row["field"] for row in profile["navigation_groups"]
                }
                referenced_fields.update(profile["column_widths"])
                referenced_fields.update(profile["column_precisions"])
                referenced_fields.update(profile["exclude_fields"])
                referenced_fields.update(
                    field
                    for tab in profile["tabs"]
                    for field in tab["fields"]
                )
                self.assertFalse(referenced_fields - declared_fields)

    def test_effective_action_projection_selects_ready_worksheet(self):
        for case in PROFILE_CASES:
            with self.subTest(case=case["action"]):
                action = self.env.ref("smart_construction_core.%s" % case["action"]).read()[0]
                page, _versions = PageAssembler(
                    self.env,
                    self.env["ir.model"].sudo().env,
                ).assemble_page_contract(
                    {
                        "model": case["model"],
                        "view_types": ["tree", "form"],
                        "action_id": action["id"],
                        "context": safe_eval(action.get("context") or "{}", {"context": {}}),
                    },
                    action=action,
                )
                presentation = page["views"]["tree"]["collection_presentation"]
                self.assertEqual(presentation["semantic"], "hierarchical_worksheet")
                self.assertTrue(presentation["enabled"], presentation)
                config = presentation["config"]
                self.assertEqual(config["hierarchy"]["navigation_mode"], "sheet_groups")
                self.assertEqual(config["hierarchy"]["tree_column"], case["tree_column"])
                self.assertEqual(
                    [row["field"] for row in config["hierarchy"]["navigation_groups"]],
                    ["project_id", "partner_id", "document_status"],
                )
                self.assertGreater(len(config["sheet"]["columns"]), 5)
                self.assertGreaterEqual(len(config["detail"]["tabs"]), 2)

    def test_contract_reader_receives_same_registered_semantic(self):
        user = self.env["res.users"].create(
            {
                "name": "Phase 9 contract execution reader",
                "login": "phase9_contract_execution_reader",
                "groups_id": [
                    (6, 0, [
                        self.env.ref("base.group_user").id,
                        self.env.ref("smart_construction_core.group_sc_cap_contract_read").id,
                    ])
                ],
            }
        )
        user_env = self.env(user=user)
        for case in PROFILE_CASES:
            with self.subTest(case=case["action"]):
                action = self.env.ref("smart_construction_core.%s" % case["action"])
                menu = self.env.ref("smart_construction_core.%s" % case["menu"])
                result = UiContractV2Handler(
                    user_env,
                    su_env=user_env["ir.model"].sudo().env,
                ).handle(
                    {
                        "model": case["model"],
                        "view_type": "tree",
                        "action_id": action.id,
                        "menu_id": menu.id,
                        "client_type": "web_pc",
                    }
                )
                envelope = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
                self.assertTrue(envelope.get("ok", True), envelope)
                presentation = envelope["data"]["layoutContract"]["listProfile"][
                    "collection_presentation"
                ]
                self.assertEqual(presentation["semantic"], "hierarchical_worksheet")
                self.assertTrue(presentation["enabled"], presentation)
