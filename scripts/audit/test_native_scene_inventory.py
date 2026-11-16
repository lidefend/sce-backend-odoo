from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.audit import native_scene_inventory as inventory


MODEL = """
from odoo import api, fields, models

class Demo(models.Model):
    _name = "x.demo"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _sql_constraints = [("x_unique", "unique(name)", "unique")]

    name = fields.Char(required=True)
    partner_id = fields.Many2one("res.partner")
    total = fields.Float(compute="_compute_total")

    @api.depends("name")
    def _compute_total(self):
        for record in self:
            record.total = len(record.name or "")

    @api.constrains("name")
    def _check_name(self):
        return None

    def action_open(self):
        return {"type": "ir.actions.act_window", "res_model": "x.demo", "view_mode": "tree,form"}
"""

DATA = """
<odoo>
  <record id="view_demo_tree" model="ir.ui.view">
    <field name="model">x.demo</field>
    <field name="arch" type="xml">
      <tree js_class="smart_hierarchy_browser"><field name="name"/></tree>
    </field>
  </record>
  <record id="view_demo_form" model="ir.ui.view">
    <field name="model">x.demo</field>
    <field name="arch" type="xml">
      <form>
        <header><button type="action" name="%(action_demo)d">Open</button></header>
        <field name="name"/><field name="partner_id" widget="many2one_avatar_user"/>
      </form>
    </field>
  </record>
  <record id="action_demo" model="ir.actions.act_window">
    <field name="name">Demo</field>
    <field name="res_model">x.demo</field>
    <field name="view_mode">tree,form</field>
    <field name="view_id" ref="view_demo_tree"/>
    <field name="search_view_id" ref="view_demo_search"/>
  </record>
  <record id="view_demo_search" model="ir.ui.view">
    <field name="model">x.demo</field>
    <field name="arch" type="xml"><search><field name="name"/></search></field>
  </record>
  <menuitem id="menu_demo" name="Demo" action="action_demo"/>
</odoo>
"""


class NativeSceneInventoryTest(unittest.TestCase):
    def _fixture(self, root: Path) -> None:
        module = root / "addons/demo_module"
        (module / "models").mkdir(parents=True)
        (module / "views").mkdir(parents=True)
        (module / "__manifest__.py").write_text(
            repr(
                {
                    "name": "Demo",
                    "version": "17.0.0.1",
                    "depends": ["base"],
                    "data": ["views/demo.xml"],
                }
            ),
            encoding="utf-8",
        )
        (module / "models/__init__.py").write_text("", encoding="utf-8")
        (module / "models/demo.py").write_text(MODEL, encoding="utf-8")
        (module / "views/demo.xml").write_text(DATA, encoding="utf-8")

    def test_inventory_contains_model_menu_action_and_view_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._fixture(root)
            output = root / "out"
            built = inventory.write_outputs(root, output, source_revision="a" * 40)
            payloads = built["payloads"]
            self.assertEqual(payloads["native_model_inventory.json"]["summary"]["distinct_models"], 1)
            self.assertEqual(payloads["native_menu_inventory.json"]["summary"]["unique_menu_xmlids"], 1)
            self.assertEqual(payloads["native_action_inventory.json"]["summary"]["unique_action_xmlids"], 1)
            self.assertEqual(payloads["native_view_inventory.json"]["summary"]["unique_view_xmlids"], 3)
            menu = payloads["native_menu_inventory.json"]["menus"][0]
            self.assertEqual(menu["action_xmlid"], "demo_module.action_demo")
            self.assertTrue(menu["other_entry_references"])
            tree = next(
                row
                for row in payloads["native_view_inventory.json"]["views"]
                if row["xmlid"] == "demo_module.view_demo_tree"
            )
            self.assertEqual(tree["js_class"], "smart_hierarchy_browser")
            self.assertEqual(tree["resolved_type"], "tree")
            form = next(
                row
                for row in payloads["native_view_inventory.json"]["views"]
                if row["xmlid"] == "demo_module.view_demo_form"
            )
            self.assertEqual(form["resolved_type"], "form")

    def test_check_detects_source_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._fixture(root)
            output = root / "out"
            inventory.write_outputs(root, output, source_revision="a" * 40)
            self.assertEqual(inventory.check_outputs(root, output), [])
            (root / "addons/demo_module/models/demo.py").write_text(
                MODEL.replace("required=True", "required=False"),
                encoding="utf-8",
            )
            errors = inventory.check_outputs(root, output)
            self.assertTrue(any("native_model_inventory.json" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
