# -*- coding: utf-8 -*-
from lxml import etree

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "smart_core", "native_action_selection")
class TestNativeActionSelectionAlignment(TransactionCase):
    def test_parser_form_header_object_button_uses_record_context(self):
        parser = self.env["app.view.parser"]
        root = etree.fromstring(
            b"""
            <form string="Demo">
              <header>
                <button name="action_confirm" type="object" string="Confirm" class="btn-primary"/>
              </header>
            </form>
            """
        )
        btn = root.xpath(".//header//button")[0]

        row = parser._button_to_action(btn, level="header")

        self.assertEqual(row.get("level"), "header")
        self.assertEqual(row.get("source_widget_id"), "page.header")
        self.assertEqual((row.get("presentation") or {}).get("tier"), "primary")
        self.assertEqual(row.get("selection"), "none")
        self.assertEqual(row.get("visible_profiles"), ["create", "edit", "readonly"])

    def test_parser_tree_row_object_button_is_not_selection_action(self):
        parser = self.env["app.view.parser"]
        root = etree.fromstring(
            b"""
            <tree string="Demo">
              <field name="name"/>
              <button name="action_open" type="object" string="Open"/>
            </tree>
            """
        )
        btn = root.xpath(".//button")[0]

        row = parser._button_to_action(btn, level="row")

        self.assertEqual(row.get("level"), "row")
        self.assertEqual(row.get("selection"), "none")
        self.assertEqual(row.get("visible_profiles"), ["readonly", "list"])

    def test_parser_tree_header_object_button_uses_multi_selection(self):
        parser = self.env["app.view.parser"]
        root = etree.fromstring(
            b"""
            <tree string="Demo">
              <header>
                <button name="action_batch" type="object" string="Batch"/>
              </header>
              <field name="name"/>
            </tree>
            """
        )
        btn = root.xpath(".//header//button")[0]

        row = parser._button_to_action(btn, level="row")

        self.assertEqual(row.get("level"), "toolbar")
        self.assertEqual(row.get("selection"), "multi")
        self.assertEqual(row.get("visible_profiles"), ["readonly", "list"])

    def test_app_action_config_server_action_scope_respects_binding_view_types(self):
        config = self.env["app.action.config"]

        list_scope = config._native_server_action_scope("list")
        form_scope = config._native_server_action_scope("form")
        mixed_scope = config._native_server_action_scope("tree,form")

        self.assertEqual(list_scope.get("selection"), "multi")
        self.assertEqual(list_scope.get("visible_profiles"), ["readonly", "list"])
        self.assertEqual(form_scope.get("selection"), "none")
        self.assertEqual(form_scope.get("visible_profiles"), ["edit", "readonly"])
        self.assertEqual(mixed_scope.get("selection"), "multi")
        self.assertEqual(mixed_scope.get("visible_profiles"), ["edit", "readonly", "list"])

    def test_parser_record_bound_stat_action_excludes_create(self):
        parser = self.env["app.view.parser"]
        root = etree.fromstring(
            b"""
            <form string="Demo">
              <div class="oe_button_box">
                <button name="91" type="action" string="Lines" class="oe_stat_button"
                  context="{'default_record_id': context.get('active_id')}"/>
              </div>
            </form>
            """
        )

        row = parser._button_to_action(root.xpath(".//button")[0], level="smart")

        self.assertEqual(row.get("level"), "smart")
        self.assertEqual(row.get("visible_profiles"), ["edit", "readonly"])

    def test_parser_independent_stat_action_preserves_create(self):
        parser = self.env["app.view.parser"]
        root = etree.fromstring(
            b"""
            <form string="Demo">
              <div class="oe_button_box">
                <button name="92" type="action" string="Quick create" class="oe_stat_button"/>
              </div>
            </form>
            """
        )

        row = parser._button_to_action(root.xpath(".//button")[0], level="smart")

        self.assertEqual(row.get("level"), "smart")
        self.assertEqual(row.get("visible_profiles"), ["create", "edit", "readonly"])

    def test_app_action_config_only_projects_explicit_model_bindings(self):
        model = self.env["ir.model"]._get("res.partner")
        bound = self.env["ir.actions.act_window"].sudo().create({
            "name": "Bound partner helper",
            "res_model": "res.partner",
            "view_mode": "tree,form",
            "binding_model_id": model.id,
        })
        unbound = self.env["ir.actions.act_window"].sudo().create({
            "name": "Unbound partner entry",
            "res_model": "res.partner",
            "view_mode": "tree,form",
        })

        config = self.env["app.action.config"].with_context(
            contract_projection_readonly=True,
        )._generate_from_ir_actions("res.partner")
        action_ids = {
            (row.get("payload") or {}).get("action_id")
            for row in (config.actions_def or [])
            if isinstance(row, dict)
        }

        self.assertIn(bound.id, action_ids)
        self.assertNotIn(unbound.id, action_ids)
        bound_row = next(
            row for row in config.actions_def
            if (row.get("payload") or {}).get("action_id") == bound.id
        )
        self.assertNotIn("create", bound_row.get("visible_profiles") or [])
        self.assertEqual(bound_row.get("visible_profiles"), ["edit", "readonly", "list"])
        self.assertFalse(hasattr(config, "_scan_view_buttons"))
