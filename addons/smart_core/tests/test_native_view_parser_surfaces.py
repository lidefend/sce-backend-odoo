# -*- coding: utf-8 -*-
import importlib.util
import ast
import sys
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


class _ElementWrapper:
    def __init__(self, element, parent=None):
        self._element = element
        self._parent = parent
        self.tag = element.tag
        self.attrib = element.attrib

    @property
    def text(self):
        return self._element.text

    @property
    def tail(self):
        return self._element.tail

    def get(self, key, default=None):
        return self._element.get(key, default)

    def getparent(self):
        return self._parent

    def __iter__(self):
        return iter([_ElementWrapper(item, self) for item in list(self._element)])

    def __eq__(self, other):
        return isinstance(other, _ElementWrapper) and self._element is other._element

    def xpath(self, expr):
        if expr.startswith("./") and not expr.startswith(".//"):
            tag = expr[2:]
            attr = None
            if "[@" in tag and tag.endswith("]"):
                tag, attr = tag[:-1].split("[@", 1)
            return [
                _ElementWrapper(item, self)
                for item in list(self._element)
                if item.tag == tag and (not attr or item.get(attr) is not None)
            ]
        if expr.startswith(".//"):
            tag = expr[3:]
            attr = None
            if "[@" in tag and tag.endswith("]"):
                tag, attr = tag[:-1].split("[@", 1)
            rows = []
            for item in self._element.iter(tag):
                if attr and item.get(attr) is None:
                    continue
                rows.append(_ElementWrapper(item, self))
            return rows
        return []


def _parse_test_xml(raw):
    return sys.modules["lxml"].etree.fromstring(raw)


def _install_lxml_shim():
    if "lxml" in sys.modules:
        return
    try:
        import lxml  # noqa: F401
        return
    except Exception:
        pass

    etree = types.SimpleNamespace()
    etree.fromstring = lambda raw: _ElementWrapper(ET.fromstring(raw.decode("utf-8") if isinstance(raw, bytes) else raw))
    etree.tostring = lambda node, encoding="unicode": ET.tostring(node._element, encoding=encoding)
    lxml_mod = types.ModuleType("lxml")
    lxml_mod.etree = etree
    sys.modules["lxml"] = lxml_mod
    sys.modules["lxml.etree"] = etree


def _install_odoo_shim():
    if "odoo" in sys.modules:
        return
    odoo_mod = types.ModuleType("odoo")
    odoo_mod._ = lambda message, *args: message % args if args else message
    odoo_mod.models = types.SimpleNamespace()
    odoo_mod.api = types.SimpleNamespace()
    tools_mod = types.ModuleType("odoo.tools")
    safe_eval_mod = types.ModuleType("odoo.tools.safe_eval")
    safe_eval_mod.safe_eval = lambda value, *_args, **_kwargs: ast.literal_eval(value)
    descriptor_module_name = "odoo.addons.smart_core.utils.native_field_descriptor"
    descriptor_path = Path(__file__).resolve().parents[1] / "utils" / "native_field_descriptor.py"
    descriptor_spec = importlib.util.spec_from_file_location(descriptor_module_name, descriptor_path)
    descriptor_mod = importlib.util.module_from_spec(descriptor_spec)
    descriptor_spec.loader.exec_module(descriptor_mod)
    addons_mod = types.ModuleType("odoo.addons")
    smart_core_mod = types.ModuleType("odoo.addons.smart_core")
    utils_mod = types.ModuleType("odoo.addons.smart_core.utils")
    native_modifier_mod = types.ModuleType("odoo.addons.smart_core.utils.native_modifier")
    native_modifier_mod.normalize_native_modifier = lambda value: value
    sys.modules["odoo"] = odoo_mod
    sys.modules["odoo.tools"] = tools_mod
    sys.modules["odoo.tools.safe_eval"] = safe_eval_mod
    sys.modules["odoo.addons"] = addons_mod
    sys.modules["odoo.addons.smart_core"] = smart_core_mod
    sys.modules["odoo.addons.smart_core.utils"] = utils_mod
    sys.modules[descriptor_module_name] = descriptor_mod
    sys.modules["odoo.addons.smart_core.utils.native_modifier"] = native_modifier_mod


def _load_calendar_mixin():
    _install_lxml_shim()
    root = Path(__file__).resolve().parents[1]
    module_path = root / "app_config_engine" / "services" / "view_Parser" / "parsers_Calendar_Gantt Activity.py"
    spec = importlib.util.spec_from_file_location("calendar_gantt_activity_parser_probe", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._CalendarGanttActivitySearchParserMixin


def _load_kanban_mixin():
    _install_lxml_shim()
    root = Path(__file__).resolve().parents[1]
    module_path = root / "app_config_engine" / "services" / "view_Parser" / "parsers Kanban Pivot Graph.py"
    spec = importlib.util.spec_from_file_location("kanban_pivot_graph_parser_probe", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._KanbanPivotGraphParserMixin


def _load_tree_form_mixin():
    _install_lxml_shim()
    _install_odoo_shim()
    root = Path(__file__).resolve().parents[1]
    module_path = root / "app_config_engine" / "services" / "view_Parser" / "parsers Tree Form.py"
    spec = importlib.util.spec_from_file_location("tree_form_parser_probe", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._TreeFormParserMixin


def _load_base_mixin():
    _install_lxml_shim()
    _install_odoo_shim()
    root = Path(__file__).resolve().parents[1]
    module_path = root / "app_config_engine" / "services" / "view_Parser" / "base.py"
    spec = importlib.util.spec_from_file_location("base_view_parser_probe", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._BaseViewParserMixin


class _ParserProbe(_load_calendar_mixin()):
    def _safe_eval_expr(self, expr):
        try:
            return eval(expr, {"__builtins__": {}}, {})
        except Exception:
            return None


class _KanbanParserProbe(_load_kanban_mixin()):
    def _safe_eval_expr(self, expr):
        return expr

    def _button_to_action(self, _button, level='header'):
        return None


class _TreeFormParserProbe(_load_tree_form_mixin()):
    def _safe_eval_expr(self, expr):
        try:
            return ast.literal_eval(expr)
        except Exception:
            return None

    def _normalize_modifier_value(self, value):
        text = str(value).strip()
        if text in ("1", "True", "true"):
            return True
        if text in ("0", "False", "false"):
            return False
        return value

    def _resolve_action_label(self, button, name):
        return button.get("string") or button.get("title") or name

    def _button_action_safety(self, **_kwargs):
        return {"classification": "safe", "requires_confirm": False, "reason_code": "TEST"}

    def _has_class(self, element, class_name):
        return class_name in (element.get("class") or "").split()

    def _layout_type(self, tag):
        return tag

    def _field_info_for_layout(self, name, fields_info):
        return super()._field_info_for_layout(name, fields_info)

    def _view_bool_attr(self, element, name, default=False):
        value = element.get(name)
        return default if value is None else self._normalize_modifier_value(value)

    def _field_widget_semantics(self, *_args):
        return {}


class _BaseParserProbe(_load_base_mixin()):
    pass


class TestNativeViewParserSurfaces(unittest.TestCase):
    def setUp(self):
        self.parser = _ParserProbe()
        self.kanban_parser = _KanbanParserProbe()
        self.tree_form_parser = _TreeFormParserProbe()
        self.base_parser = _BaseParserProbe()

    def test_calendar_parser_preserves_native_slots_and_fields(self):
        result = self.parser._parse_calendar_view(
            """
            <calendar date_start="planned_start" date_stop="planned_stop" color="user_id" default_scale="week">
                <field name="name" string="Title"/>
                <field name="user_id" string="Owner"/>
            </calendar>
            """
        )

        self.assertEqual(result["date_slots"]["start"], "planned_start")
        self.assertEqual(result["date_slots"]["stop"], "planned_stop")
        self.assertEqual(result["color_slots"]["color"], "user_id")
        self.assertEqual([row["name"] for row in result["fields"]], ["name", "user_id"])
        self.assertEqual(result["native_attrs"]["default_scale"], "week")

    def test_gantt_parser_preserves_dependency_and_resource_slots(self):
        result = self.parser._parse_gantt_view(
            """
            <gantt date_start="start_date" date_stop="end_date" default_group_by="employee_id" dependency_field="depends_on_ids">
                <field name="name"/>
                <field name="employee_id"/>
            </gantt>
            """
        )

        self.assertEqual(result["date_slots"]["start"], "start_date")
        self.assertEqual(result["resource_slots"]["group_by"], "employee_id")
        self.assertEqual(result["dependency_slots"]["dependency_field"], "depends_on_ids")
        self.assertEqual([row["name"] for row in result["fields"]], ["name", "employee_id"])

    def test_search_parser_preserves_search_fields_and_group_by_metadata(self):
        result = self.parser._parse_search_from_arch(
            """
            <search>
                <field name="partner_id" string="Customer" operator="ilike"/>
                <filter name="mine" string="Mine" domain="[('user_id', '=', uid)]"/>
                <filter name="by_user" string="By User" context="{'group_by': 'user_id'}"/>
            </search>
            """
        )

        self.assertEqual(result["search_fields"][0]["name"], "partner_id")
        self.assertEqual(result["filters"][0]["name"], "mine")
        self.assertEqual(result["group_by"], ["user_id"])
        self.assertEqual(result["group_by_fields"][0]["field"], "user_id")

    def test_workflow_board_requires_group_semantics(self):
        result = self.kanban_parser._parse_kanban_view(
            '<kanban default_group_by="state"><field name="name"/><field name="state"/></kanban>',
            {"name": {}, "state": {}},
        )
        presentation = result["collection_presentation"]
        self.assertEqual(presentation["semantic"], "workflow_board")
        self.assertEqual(presentation["group_field"], "state")
        self.assertTrue(presentation["capabilities"]["grouped_lanes"])

    def test_unknown_kanban_semantic_fails_safe(self):
        result = self.kanban_parser._parse_kanban_view(
            '<kanban><field name="name"/></kanban>',
            {"name": {}},
        )
        presentation = result["collection_presentation"]
        self.assertEqual(presentation["semantic"], "card")
        self.assertFalse(presentation["capabilities"]["grouped_lanes"])

    def test_primary_arch_root_is_reused_across_view_projections(self):
        root = _parse_test_xml(
            '<tree default_order="name"><field name="name" readonly="1"/></tree>'
        )

        structure = self.base_parser._lossless_parse_xml(root)
        modifiers = self.base_parser._collect_modifiers('', root=root)
        tree = self.tree_form_parser._parse_tree_view('', {"name": {"type": "char"}}, root=root)
        search = self.parser._parse_search_from_arch('', root=root)

        self.assertEqual(structure["tag"], "tree")
        self.assertEqual(modifiers["name"]["readonly"][0]["raw"], "1")
        self.assertEqual(tree["columns"], ["name"])
        self.assertEqual(tree["default_order"], "name")
        self.assertEqual(search["filters"], [])

    def test_private_arch_root_is_not_serialized_into_contract(self):
        root = _parse_test_xml('<form><field name="name"/></form>')
        serialized = self.base_parser._serialize_odoo_view({
            "arch": '<form><field name="name"/></form>',
            "fields": {"name": {"type": "char"}},
            "_arch_root": root,
        })

        self.assertNotIn("_arch_root", serialized)
        self.assertEqual(serialized["fields"]["name"]["type"], "char")

    def test_tree_parser_preserves_duplicate_field_behavior_occurrences(self):
        result = self.tree_form_parser._parse_tree_view(
            """
            <tree>
                <field name="partner_id" readonly="1" can_write="0"/>
                <field name="partner_id" invisible="state == 'done'" can_write="1"/>
            </tree>
            """,
            {"partner_id": {"type": "many2one", "string": "Partner"}},
        )

        self.assertEqual(result["columns"], ["partner_id"])
        self.assertEqual(len(result["column_occurrences"]), 2)
        self.assertEqual(result["column_occurrences"][0]["source_position"], 0)
        self.assertEqual(result["column_occurrences"][0]["field_type"], "many2one")
        self.assertEqual(result["column_occurrences"][1]["source_position"], 1)
        self.assertEqual(result["column_occurrences"][0]["occurrence_index"], 1)
        self.assertEqual(result["column_occurrences"][1]["occurrence_index"], 2)
        self.assertEqual(result["column_occurrences"][0]["modifiers"], {"readonly": True})
        self.assertEqual(result["column_occurrences"][0]["relation_active_actions"], {"write": False})
        self.assertEqual(result["column_occurrences"][1]["modifiers"], {"invisible": "state == 'done'"})
        self.assertEqual(result["column_occurrences"][1]["relation_active_actions"], {"write": True})

    def test_form_field_keeps_raw_and_normalized_modifier_values(self):
        element = _parse_test_xml(
            '<field name="partner_id" modifiers="{\'readonly\': true}" can_create="0"/>'
        )
        node = self.tree_form_parser._node_to_layout_from_dom(element, {"partner_id": {"type": "many2one"}})

        self.assertEqual(node["attributes"]["modifiers"], "{'readonly': true}")
        self.assertEqual(node["relation_active_actions"], {"create": False})

    def test_monetary_occurrences_preserve_currency_field_and_digits(self):
        fields_info = {
            "amount_total": {
                "type": "monetary",
                "string": "Total",
                "currency_field": "company_currency_id",
                "digits": (16, 2),
            }
        }
        tree = self.tree_form_parser._parse_tree_view(
            '<tree><field name="amount_total" widget="monetary"/></tree>',
            fields_info,
        )
        form = self.tree_form_parser._node_to_layout_from_dom(
            _parse_test_xml('<field name="amount_total" widget="monetary"/>'),
            fields_info,
        )

        self.assertEqual(tree["column_occurrences"][0]["currency_field"], "company_currency_id")
        self.assertEqual(tree["column_occurrences"][0]["digits"], [16, 2])
        self.assertEqual(form["fieldInfo"]["currency_field"], "company_currency_id")
        self.assertEqual(form["fieldInfo"]["digits"], [16, 2])
        base_info = self.base_parser._field_info_for_layout("amount_total", fields_info)
        self.assertEqual(base_info["currency_field"], "company_currency_id")
        self.assertEqual(base_info["digits"], [16, 2])

    def test_non_relational_can_create_remains_raw_without_fake_active_action(self):
        element = _parse_test_xml('<field name="reference" can_create="0"/>')
        node = self.tree_form_parser._node_to_layout_from_dom(element, {"reference": {"type": "char"}})

        self.assertEqual(node["attributes"]["can_create"], "0")
        self.assertNotIn("relation_active_actions", node)

    def test_button_action_preserves_native_identity_without_aliasing(self):
        element = _parse_test_xml(
            '<button id="approve_button" type="object" name="approve" string="Approve" title="Approval" '
            'help="Help text" data-hotkey="a" special="save" context="{\'x\': 1}" '
            'domain="[(\'state\', \'=\', \'draft\')]" confirm="Confirm" icon="fa-check"/>'
        )
        action = self.tree_form_parser._button_to_action(element, level="body")

        self.assertEqual(action["native_identity"]["name"], "approve")
        self.assertEqual(action["native_identity"]["id"], "approve_button")
        self.assertEqual(action["native_identity"]["title"], "Approval")
        self.assertEqual(action["native_identity"]["data_hotkey"], "a")
        self.assertEqual(action["native_identity"]["special"], "save")
        self.assertEqual(action["native_identity"]["confirm_raw"], "Confirm")
        self.assertEqual(action["native_identity"]["occurrence_index"], 1)
        self.assertEqual(action["native_identity"]["canonical_region"], "layout")
        self.assertTrue(action["native_identity"]["authoritative"])


    def test_x2many_inline_tree_reuses_occurrence_aware_parser(self):
        relation_fields = {
            "partner_id": {"type": "many2one", "relation": "res.partner", "string": "Partner"},
            "amount": {"type": "float", "string": "Amount"},
        }
        self.tree_form_parser._safe_relation_fields_for_subview = lambda _relation: relation_fields
        root = _parse_test_xml(
            """
            <form>
                <field name="line_ids">
                    <tree>
                        <field name="partner_id" can_write="0" readonly="1"/>
                        <field name="partner_id" can_write="1" invisible="state == 'done'"/>
                        <group><button name="open_partner" type="object" string="Open"/></group>
                        <field name="amount"/>
                    </tree>
                </field>
            </form>
            """
        )

        result = self.tree_form_parser._collect_x2many_subviews_from_dom(
            root,
            {"line_ids": {"type": "one2many", "relation": "test.line"}},
        )
        tree = result["line_ids"]["tree"]
        partner_occurrences = [
            row for row in tree["column_occurrences"] if row["name"] == "partner_id"
        ]
        self.assertEqual(len(partner_occurrences), 2)
        self.assertEqual([row["occurrence_index"] for row in partner_occurrences], [1, 2])
        self.assertEqual(partner_occurrences[0]["relation_active_actions"], {"write": False})
        self.assertEqual(partner_occurrences[1]["relation_active_actions"], {"write": True})
        self.assertEqual(partner_occurrences[0]["modifiers"], {"readonly": True})
        self.assertEqual(partner_occurrences[1]["modifiers"], {"invisible": "state == 'done'"})
        self.assertEqual(len(tree["row_actions"]), 1)
        self.assertEqual(tree["row_actions"][0]["payload"]["method"], "open_partner")
        self.assertEqual(
            [row["name"] for row in tree["columns"]],
            ["partner_id", "amount"],
        )

    def test_duplicate_x2many_host_occurrence_fails_closed(self):
        self.tree_form_parser._safe_relation_fields_for_subview = lambda _relation: {
            "name": {"type": "char", "string": "Name"},
        }
        root = _parse_test_xml(
            """
            <form>
                <field name="line_ids"><tree><field name="name"/></tree></field>
                <group><field name="line_ids"><tree><field name="name"/></tree></field></group>
            </form>
            """
        )
        result = self.tree_form_parser._collect_x2many_subviews_from_dom(
            root,
            {"line_ids": {"type": "one2many", "relation": "test.line"}},
        )
        entry = result["line_ids"]
        self.assertTrue(entry["host_occurrence_ambiguous"])
        self.assertEqual(entry["host_occurrence_count"], 2)
        self.assertFalse(entry["policies"]["inline_edit"])
        self.assertEqual(entry["policies"]["reason_code"], "AMBIGUOUS_NATIVE_HOST_OCCURRENCE")


if __name__ == "__main__":
    unittest.main()
