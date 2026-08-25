# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


CORE_DIR = Path(__file__).resolve().parents[1] / "core"


def _load_assembler():
    sys.modules.setdefault("odoo", types.ModuleType("odoo"))
    sys.modules.setdefault("odoo.addons", types.ModuleType("odoo.addons"))
    smart_core_pkg = sys.modules.setdefault("odoo.addons.smart_core", types.ModuleType("odoo.addons.smart_core"))
    smart_core_pkg.__path__ = [str(CORE_DIR.parent)]
    core_pkg = sys.modules.setdefault("odoo.addons.smart_core.core", types.ModuleType("odoo.addons.smart_core.core"))
    core_pkg.__path__ = [str(CORE_DIR)]
    for module_name in (
        "odoo.addons.smart_core.core.source_authority",
        "odoo.addons.smart_core.core.unified_page_contract_v2_assembler",
    ):
        sys.modules.pop(module_name, None)
    source_spec = importlib.util.spec_from_file_location(
        "odoo.addons.smart_core.core.source_authority",
        CORE_DIR / "source_authority.py",
    )
    source_module = importlib.util.module_from_spec(source_spec)
    assert source_spec and source_spec.loader
    sys.modules["odoo.addons.smart_core.core.source_authority"] = source_module
    source_spec.loader.exec_module(source_module)
    spec = importlib.util.spec_from_file_location(
        "odoo.addons.smart_core.core.unified_page_contract_v2_assembler",
        CORE_DIR / "unified_page_contract_v2_assembler.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["odoo.addons.smart_core.core.unified_page_contract_v2_assembler"] = module
    spec.loader.exec_module(module)
    return module


def _kanban_source():
    return {
        "model": "project.project",
        "view_type": "kanban",
        "fields": {"name": {"name": "name", "type": "char"}},
        "views": {"kanban": {"fields": [{"name": "name", "label": "名称"}]}},
    }


class UnifiedPageContractV2KanbanActionRegistryTests(unittest.TestCase):
    def setUp(self):
        self.assembler = _load_assembler()

    def test_core_has_no_default_business_kanban_row_actions(self):
        self.assertEqual(self.assembler._KANBAN_ROW_ACTION_REGISTRY, {})

        contract = self.assembler.assemble_unified_page_contract_v2(
            _kanban_source(),
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.kanban.no.default",
        )

        actions = (contract.get("actionContract") or {}).get("actionRuleList") or []
        self.assertEqual(actions, [])

    def test_business_kanban_row_action_must_be_registered_explicitly(self):
        self.assembler.register_kanban_row_action(
            "project.project",
            {
                "key": "open_project_dashboard",
                "name": "open_project_dashboard",
                "label": "进入项目驾驶舱",
                "intent": "open_scene",
                "target": {"route": "/s/project.management", "scene_key": "project.management"},
                "trigger": "row_click",
                "level": "row",
                "target_scope": "row",
            },
        )

        contract = self.assembler.assemble_unified_page_contract_v2(
            _kanban_source(),
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.kanban.registered",
        )

        actions = (contract.get("actionContract") or {}).get("actionRuleList") or []
        self.assertEqual(actions[0]["actionKey"], "open_project_dashboard")
        self.assertEqual(actions[0]["sourceWidgetId"], "page.row")
        self.assertEqual(actions[0]["triggerType"], "click")

    def test_business_value_component_keys_follow_field_metadata(self):
        cases = (
            ({"type": "monetary"}, "number", "sc.value.money"),
            ({"type": "many2one", "relation": "res.currency"}, "select", "sc.value.currency"),
            ({"type": "float"}, "percentage", "sc.value.percentage"),
            ({"type": "selection"}, "statusbar", "sc.display.status"),
            ({"type": "float"}, "float_time", "sc.value.duration"),
            ({"type": "many2one", "relation": "res.users"}, "select", "sc.value.user"),
            ({"type": "many2one", "relation": "res.company"}, "select", "sc.value.company"),
            ({"type": "many2one", "relation": "x.related"}, "select", "sc.relation.many2one"),
            ({"type": "many2many", "relation": "x.related"}, "table", "sc.relation.many2many"),
            ({"type": "many2many", "relation": "res.users"}, "table", "sc.relation.many2many"),
            ({"type": "many2many", "relation": "res.users"}, "many2many_tags", "sc.select.tags"),
            ({"type": "one2many", "relation": "x.line"}, "table", "sc.relation.table"),
        )
        for descriptor, widget_type, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(self.assembler._component_key(widget_type, descriptor), expected)
                widget = self.assembler._field_widget(
                    {"name": "value", "string": "Value", **descriptor, "widget": widget_type},
                    layout_type="form",
                )
                self.assertEqual(widget["componentKey"], expected)

    def test_business_value_component_keys_do_not_guess_from_field_names(self):
        self.assertEqual(
            self.assembler._component_key("number", {"name": "payment_percentage", "type": "float"}),
            "sc.input.number",
        )

    def test_native_form_header_button_is_projected_as_root_business_action(self):
        contract = self.assembler.assemble_unified_page_contract_v2(
            {
                "model": "x.relation.wizard",
                "view_type": "form",
                "fields": {"note": {"name": "note", "type": "text"}},
                "views": {
                    "form": {
                        "layout": [],
                        "header_buttons": [
                            {
                                "name": "action_apply",
                                "string": "保存修正",
                                "type": "object",
                            }
                        ],
                    }
                },
            },
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.form.native.header.action",
        )

        actions = (contract.get("actionContract") or {}).get("actionRuleList") or []
        action = next(row for row in actions if row.get("actionKey") == "action_apply")
        self.assertEqual(action["label"], "保存修正")
        self.assertEqual(action["button"], {"name": "action_apply", "type": "object"})
        self.assertEqual(action["sourceWidgetId"], "page.root")
        self.assertEqual(action["targetScope"], "page")


if __name__ == "__main__":
    unittest.main()
