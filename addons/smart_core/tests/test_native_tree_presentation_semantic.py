# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler


@tagged("native_tree_presentation_semantic", "post_install", "-at_install")
class TestNativeTreePresentationSemantic(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.view = cls.env["ir.ui.view"].create({
            "name": "native.presentation.semantic.partner.tree",
            "model": "res.partner",
            "type": "tree",
            "arch": """
                <tree js_class="smart_hierarchy_browser">
                    <field name="name"/>
                    <field name="email"/>
                    <field name="parent_id" column_invisible="1"/>
                </tree>
            """,
        })
        cls.action = cls.env["ir.actions.act_window"].create({
            "name": "Native hierarchy partners",
            "res_model": "res.partner",
            "view_mode": "tree,form",
            "view_id": cls.view.id,
            "context": {
                "hierarchy_levels": [{
                    "field": "parent_id",
                    "label_field": "name",
                    "self_parent_field": "parent_id",
                    "domain_operator": "child_of",
                }],
            },
        })

    def test_primary_parser_semantic_reaches_effective_page_contract(self):
        page, _versions = PageAssembler(
            self.env,
            self.env["ir.model"].sudo().env,
        ).assemble_page_contract(
            {
                "model": "res.partner",
                "view_types": ["tree", "form"],
                "action_id": self.action.id,
            },
            action=self.action.read()[0],
        )

        presentation = page["views"]["tree"]["collection_presentation"]
        self.assertEqual(presentation["semantic"], "hierarchy_browser")
        self.assertEqual(presentation["source"], "native_view_derived")
        self.assertTrue(presentation["enabled"])
        self.assertEqual(
            presentation["config"]["tree"]["levels"][0]["model"],
            "res.partner",
        )

    def test_unknown_native_class_does_not_create_collection_authority(self):
        unknown_view = self.view.copy({
            "name": "unknown.native.presentation.partner.tree",
            "arch": '<tree js_class="customer_special_tree"><field name="name"/></tree>',
        })
        unknown_action = self.action.copy({
            "name": "Unknown native hierarchy partners",
            "view_id": unknown_view.id,
        })

        page, _versions = PageAssembler(
            self.env,
            self.env["ir.model"].sudo().env,
        ).assemble_page_contract(
            {
                "model": "res.partner",
                "view_types": ["tree"],
                "action_id": unknown_action.id,
            },
            action=unknown_action.read()[0],
        )

        self.assertFalse(page["views"]["tree"].get("collection_presentation"))
