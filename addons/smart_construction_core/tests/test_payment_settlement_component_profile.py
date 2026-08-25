# -*- coding: utf-8 -*-
from lxml import etree

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval

from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler
from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler


PROFILE_CASES = (
    {
        "action": "action_sc_payment_execution_actual_outflow",
        "menu": "menu_sc_payment_execution",
        "view": "view_sc_payment_execution_tree",
        "model": "sc.payment.execution",
        "reader_group": "group_sc_cap_finance_read",
        "tree_column": "name",
        "navigation_title": "付款执行工作表",
        "navigation_fields": ["project_id", "partner_id", "state"],
    },
    {
        "action": "action_sc_settlement_order_income",
        "menu": "menu_sc_p1_income_settlement",
        "view": "view_sc_settlement_order_user_confirmed_tree",
        "model": "sc.settlement.order",
        "reader_group": "group_sc_cap_settlement_read",
        "tree_column": "title",
        "navigation_title": "收入结算工作表",
        "navigation_fields": ["project_id", "settlement_unit_id", "state"],
    },
    {
        "action": "action_sc_settlement_order_expense",
        "menu": "menu_sc_p1_expense_settlement",
        "view": "view_sc_settlement_order_user_confirmed_tree",
        "model": "sc.settlement.order",
        "reader_group": "group_sc_cap_settlement_read",
        "tree_column": "title",
        "navigation_title": "支出结算工作表",
        "navigation_fields": ["project_id", "settlement_unit_id", "state"],
    },
)


@tagged("payment_settlement_component_profile", "post_install", "-at_install")
class TestPaymentSettlementComponentProfile(TransactionCase):
    def test_profiles_bind_only_to_released_product_entries(self):
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
        for case in PROFILE_CASES:
            with self.subTest(case=case["menu"]):
                menu = self.env.ref("smart_construction_core.%s" % case["menu"])
                action = self.env.ref("smart_construction_core.%s" % case["action"])
                view = self.env.ref("smart_construction_core.%s" % case["view"])
                reader_group = self.env.ref(
                    "smart_construction_core.%s" % case["reader_group"]
                )
                menu_xmlid = "smart_construction_core.%s" % case["menu"]
                self.assertTrue(menu.active)
                self.assertEqual(menu.action, action)
                self.assertEqual(action.view_id, view)
                self.assertIn(reader_group, action.groups_id)
                self.assertIn(menu_xmlid, formal_menus)
                self.assertEqual(formal_menus[menu_xmlid].get("action_id"), action.id)

    def test_released_views_declare_registered_worksheet_semantic(self):
        for case in PROFILE_CASES:
            with self.subTest(case=case["view"]):
                view = self.env.ref("smart_construction_core.%s" % case["view"])
                root = etree.fromstring(view.arch_db.encode("utf-8"))
                self.assertEqual(root.tag, "tree")
                self.assertEqual(root.get("js_class"), "smart_hierarchical_worksheet")

    def test_actions_declare_field_owned_profiles(self):
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
                    case["navigation_fields"],
                )
                declared_fields = set(self.env[case["model"]].fields_get())
                referenced_fields = {
                    row["field"] for row in profile["navigation_groups"]
                }
                referenced_fields.add(profile["tree_column"])
                referenced_fields.update(profile.get("column_widths", {}))
                referenced_fields.update(profile.get("column_precisions", {}))
                referenced_fields.update(profile.get("exclude_fields", []))
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
                    case["navigation_fields"],
                )
                self.assertGreater(len(config["sheet"]["columns"]), 5)
                self.assertGreaterEqual(len(config["detail"]["tabs"]), 3)

    def test_readers_receive_same_registered_semantic(self):
        users = {}
        for group_xmlid in {case["reader_group"] for case in PROFILE_CASES}:
            group = self.env.ref("smart_construction_core.%s" % group_xmlid)
            users[group_xmlid] = self.env["res.users"].create(
                {
                    "name": "Phase 9 %s reader" % group_xmlid,
                    "login": "phase9_%s_reader" % group_xmlid,
                    "groups_id": [(6, 0, [self.env.ref("base.group_user").id, group.id])],
                }
            )
        for case in PROFILE_CASES:
            with self.subTest(case=case["action"]):
                user_env = self.env(user=users[case["reader_group"]])
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
