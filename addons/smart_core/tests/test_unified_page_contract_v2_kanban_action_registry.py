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


def _load_native_field_descriptor():
    sys.modules.setdefault("odoo", types.ModuleType("odoo"))
    utils_pkg = sys.modules.setdefault("odoo.addons.smart_core.utils", types.ModuleType("odoo.addons.smart_core.utils"))
    utils_pkg.__path__ = [str(CORE_DIR.parent / "utils")]
    spec = importlib.util.spec_from_file_location(
        "odoo.addons.smart_core.utils.native_field_descriptor",
        CORE_DIR.parent / "utils" / "native_field_descriptor.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["odoo.addons.smart_core.utils.native_field_descriptor"] = module
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
            ({"type": "many2one", "relation": "res.currency"}, "select", "sc.relation.many2one"),
            ({"type": "float"}, "percentage", "sc.value.percentage"),
            ({"type": "selection"}, "statusbar", "sc.display.status"),
            ({"type": "selection"}, "badge", "sc.display.status"),
            ({"type": "float"}, "float_time", "sc.value.duration"),
            ({"type": "many2one", "relation": "res.users"}, "select", "sc.relation.many2one"),
            ({"type": "many2one", "relation": "res.company"}, "select", "sc.relation.many2one"),
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

    def test_json_field_declares_readable_display_instead_of_a_text_input(self):
        # A JSON value has no client editor.  The contract must declare the
        # readable display whether the widget is explicit, absent, or carries a
        # producer default that cannot transport an object value.
        for descriptor in (
            {"type": "json"},
            {"type": "json", "widget": "json"},
            {"type": "json", "widget": "input"},
            {"ttype": "json"},
        ):
            with self.subTest(descriptor=descriptor):
                widget = self.assembler._field_widget(
                    {"name": "quick_encoding_vals", "string": "快速编码值", **descriptor},
                    layout_type="form",
                )
                self.assertEqual(widget["widgetType"], "display")
                self.assertEqual(widget["componentKey"], "sc.display.text")

    def test_reference_field_declares_readable_display_instead_of_a_text_input(self):
        # A ``many2one_reference`` value is a (model, id) pair the client
        # resolves to a record.  No client registers a reference editor, so the
        # contract must declare the readable display for every spelling that
        # reaches the assembler -- including the producer default that carries
        # the field type in the widget slot, which is what bound
        # ``sc.input.text`` to ``many2one_reference`` and rejected the page.
        for descriptor in (
            {"type": "many2one_reference", "model_field": "sc_source_model"},
            {"type": "many2one_reference", "model_field": "sc_source_model", "widget": "input"},
            {"type": "many2one_reference", "model_field": "sc_source_model", "widget": "many2one_reference"},
            {"ttype": "many2one_reference", "model_field": "sc_source_model", "widget": "select"},
        ):
            with self.subTest(descriptor=descriptor):
                widget = self.assembler._field_widget(
                    {"name": "sc_source_res_id", "string": "来源记录", **descriptor},
                    layout_type="form",
                )
                self.assertEqual(widget["widgetType"], "display")
                self.assertEqual(widget["componentKey"], "sc.display.text")
                config = widget["componentConfig"]
                # The declared type and the target-model authority survive; the
                # widget is not disguised as text and not smuggled as a string.
                self.assertEqual(config["fieldType"], "many2one_reference")
                self.assertEqual(config["model_field"], "sc_source_model")
                self.assertEqual(config["referenceModelField"], "sc_source_model")

    def test_reference_component_key_never_binds_a_text_input(self):
        for field_type in ("many2one_reference", "reference"):
            for widget_type in ("input", field_type, "select", "number"):
                with self.subTest(field_type=field_type, widget_type=widget_type):
                    self.assertEqual(
                        self.assembler._component_key(widget_type, {"name": "src", "type": field_type}),
                        "sc.display.text",
                    )

    def test_native_field_descriptor_carries_the_reference_target_model_only_when_declared(self):
        descriptor_module = _load_native_field_descriptor()
        reference = descriptor_module.project_native_field_descriptor(
            "sc_source_res_id",
            {"type": "many2one_reference", "string": "来源记录", "model_field": "sc_source_model"},
        )
        self.assertEqual(reference["type"], "many2one_reference")
        self.assertEqual(reference["model_field"], "sc_source_model")
        # Absent authority must stay absent: an empty pointer is not evidence
        # that the reference is unscoped.
        self.assertNotIn(
            "model_field",
            descriptor_module.project_native_field_descriptor(
                "sc_source_res_id", {"type": "many2one_reference", "string": "来源记录"}
            ),
        )
        self.assertNotIn(
            "model_field",
            descriptor_module.project_native_field_descriptor(
                "name", {"type": "char", "string": "名称", "model_field": "sc_source_model"}
            ),
        )

    def test_date_range_widget_preserves_native_semantics_for_public_component_consumers(self):
        widget = self.assembler._field_widget(
            {
                "name": "date_start",
                "string": "安排的日期",
                "type": "date",
                "widget": "daterange",
                "widget_options": {"end_date_field": "date"},
                "widget_semantics": {
                    "kind": "date_range",
                    "start_field": "date_start",
                    "end_field": "date",
                },
            },
            layout_type="form",
        )

        self.assertEqual(widget["widgetType"], "date")
        self.assertEqual(widget["componentConfig"]["nativeWidget"], "daterange")
        self.assertEqual(
            widget["componentConfig"]["widgetSemantics"],
            {"kind": "date_range", "start_field": "date_start", "end_field": "date"},
        )

        native_node = self.assembler._native_field_node(
            {
                "type": "field",
                "name": "date_start",
                "fieldInfo": {
                    "type": "date",
                    "widget": "date",
                    "widget_semantics": {
                        "kind": "date_range",
                        "start_field": "date_start",
                        "end_field": "date",
                    },
                },
                "widget": "daterange",
            },
            {
                "name": "date_start",
                "type": "date",
                "widget": "daterange",
                "widget_semantics": {
                    "kind": "date_range",
                    "start_field": "date_start",
                    "end_field": "date",
                },
            },
            layout_type="form",
        )
        self.assertEqual(native_node["fieldInfo"]["widget"], "daterange")
        self.assertEqual(native_node["componentConfig"]["nativeWidget"], "daterange")

        direct_widgets = self.assembler._direct_field_widgets_from_nodes(
            [{
                "type": "field",
                "name": "date_start",
                "widget": "date",
                "attributes": {"widget": "daterange"},
                "fieldInfo": {
                    "type": "date",
                    "widget": "date",
                    "widget_semantics": {
                        "kind": "date_range",
                        "start_field": "date_start",
                        "end_field": "date",
                    },
                },
            }],
            {"date_start": {"name": "date_start", "type": "date"}},
            layout_type="form",
        )
        self.assertEqual(direct_widgets[0]["componentConfig"]["nativeWidget"], "daterange")
        self.assertEqual(direct_widgets[0]["componentConfig"]["widgetSemantics"]["end_field"], "date")

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
