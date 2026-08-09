#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import copy
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "addons/smart_core/app_config_engine/services/assemblers/page_assembler.py"


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_page_assembler():
    for name in list(sys.modules):
        if name == "odoo" or name.startswith("odoo."):
            sys.modules.pop(name, None)
    odoo = _install_module("odoo", _=lambda value: value)
    _install_module("odoo.http", request=types.SimpleNamespace(env=None))
    odoo.http = sys.modules["odoo.http"]
    _install_module("odoo.addons")
    smart_core = _install_module("odoo.addons.smart_core")
    app_config = _install_module("odoo.addons.smart_core.app_config_engine")
    services = _install_module("odoo.addons.smart_core.app_config_engine.services")
    assemblers = _install_module("odoo.addons.smart_core.app_config_engine.services.assemblers")
    utils = _install_module("odoo.addons.smart_core.utils")
    smart_core.__path__ = [str(ROOT / "addons/smart_core")]
    app_config.__path__ = [str(ROOT / "addons/smart_core/app_config_engine")]
    services.__path__ = [str(ROOT / "addons/smart_core/app_config_engine/services")]
    assemblers.__path__ = [str(ROOT / "addons/smart_core/app_config_engine/services/assemblers")]
    utils.__path__ = [str(ROOT / "addons/smart_core/utils")]
    _install_module(
        "odoo.addons.smart_core.utils.delete_policy",
        resolve_unlink_policy=lambda *_args, **_kwargs: {},
    )
    _install_module(
        "odoo.addons.smart_core.utils.extension_hooks",
        call_extension_hook_first=lambda *_args, **_kwargs: None,
    )
    _install_module(
        "odoo.addons.smart_core.app_config_engine.utils.misc",
        safe_eval=lambda value: value,
    )
    _install_module(
        "odoo.addons.smart_core.app_config_engine.utils.view_utils",
        extract_tree_columns_strict=lambda *_args, **_kwargs: ([], None),
        normalize_cols_safely=lambda value: value,
    )
    module_name = "odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.PageAssembler


class PageAssemblerViewOrchestrationVersionTests(unittest.TestCase):
    def setUp(self):
        self.PageAssembler = _load_page_assembler()
        self.assembler = self.PageAssembler.__new__(self.PageAssembler)

    def test_append_view_version_token_adds_search_orchestration_version(self):
        versions = {"view": "12:native", "search": 4}

        self.assembler._append_view_version_token(versions, "7:9.3")

        self.assertEqual(versions["view"], "12:native,7:9.3")
        self.assertEqual(versions["search"], 4)

    def test_append_view_version_token_is_idempotent(self):
        versions = {"view": "12:native,7:9.3"}

        self.assembler._append_view_version_token(versions, "7:9.3")

        self.assertEqual(versions["view"], "12:native,7:9.3")

    def test_coerce_calendar_preserves_orchestrated_slot_semantics(self):
        result = self.assembler._coerce_view_contract_semantics(
            "calendar",
            {
                "calendar": {
                    "date_start": "planned_start",
                    "date_stop": "planned_stop",
                    "date_slots": {"start": "planned_start", "stop": "planned_stop"},
                    "color_slots": {"color": "user_id"},
                    "fields": [{"name": "planned_start"}],
                }
            },
        )

        self.assertEqual(result["date_start"], "planned_start")
        self.assertEqual(result["date_slots"]["start"], "planned_start")
        self.assertEqual(result["color_slots"]["color"], "user_id")
        self.assertEqual(result["fields"][0]["name"], "planned_start")

    def test_coerce_dashboard_preserves_orchestrated_slots(self):
        result = self.assembler._coerce_view_contract_semantics(
            "dashboard",
            {
                "dashboard": {
                    "cards": [{"name": "revenue"}],
                    "kpis": [{"name": "margin"}],
                    "metric_slots": {"primary": ["amount_total"]},
                    "navigation_slots": {"next": "project.dashboard.enter"},
                }
            },
        )

        self.assertEqual(result["cards"][0]["name"], "revenue")
        self.assertEqual(result["kpis"][0]["name"], "margin")
        self.assertEqual(result["metric_slots"]["primary"], ["amount_total"])
        self.assertEqual(result["navigation_slots"]["next"], "project.dashboard.enter")

    def test_native_hierarchy_contract_is_assembled_from_model_view_and_action_context(self):
        class MenuModel:
            @staticmethod
            def _visible_menu_ids():
                return []

        class Env:
            def __getitem__(self, name):
                if name == "ir.ui.menu":
                    return MenuModel()
                raise KeyError(name)

        self.assembler.env = Env()
        data = {
            "head": {"title": "定额库", "model": "sc.norm.item", "permissions": {"create": True}},
            "fields": {
                "catalog_id": {
                    "type": "many2one", "relation": "sc.norm.catalog", "string": "所属定额库",
                    "relation_entry": {"search_dialog": {"read_fields": ["code", "name"], "order": "code asc"}},
                },
                "specialty_id": {
                    "type": "many2one", "relation": "sc.norm.specialty", "string": "所属专业",
                    "relation_entry": {"search_dialog": {"read_fields": ["code", "name", "catalog_id"], "order": "code asc"}},
                },
                "chapter_id": {
                    "type": "many2one", "relation": "sc.norm.chapter", "string": "所属章节",
                    "relation_entry": {"search_dialog": {"read_fields": ["code", "name", "specialty_id", "parent_id"], "order": "code asc"}},
                },
                "code": {"type": "char", "string": "定额编号"},
                "name": {"type": "char", "string": "项目名称"},
            },
            "views": {
                "tree": {
                    "collection_presentation": {"semantic": "hierarchy_browser", "source": "native_view_derived"},
                    "columns_schema": [{"name": "code", "label": "定额编号"}, {"name": "name", "label": "项目名称"}],
                    "toolbar": {"header": [{"key": "action:856", "action_id": 856, "label": "导入定额", "source": "native_view_header"}]},
                    "order": "code asc",
                },
                "form": {},
            },
        }
        context = {
            "hierarchy_create": {"label": "新增定额项"},
            "hierarchy_commands": [
                {"key": "add_child", "label": "Add child", "kind": "object", "method": "action_add_child"},
                {"key": "missing_method", "label": "Invalid", "kind": "object"},
                {"key": "frontend_route", "label": "Invalid", "kind": "route", "method": "ignored"},
            ],
            "hierarchy_levels": [
                {"field": "catalog_id", "code_field": "code", "label_field": "name"},
                {"field": "specialty_id", "code_field": "code", "label_field": "name", "parent_field": "catalog_id"},
                {"field": "chapter_id", "code_field": "code", "label_field": "name", "parent_field": "specialty_id", "self_parent_field": "parent_id", "domain_operator": "child_of", "order": "sequence, id"},
            ]
        }

        self.assembler._inject_native_collection_presentation(data, context)

        presentation = data["views"]["tree"]["collection_presentation"]
        self.assertTrue(presentation["enabled"])
        self.assertEqual(presentation["source"], "native_view_derived")
        config = presentation["config"]
        self.assertEqual(config["create"], {"enabled": True, "label": "新增定额项"})
        self.assertEqual([row["model"] for row in config["tree"]["levels"]], ["sc.norm.catalog", "sc.norm.specialty", "sc.norm.chapter"])
        self.assertEqual(config["tree"]["levels"][2]["self_parent_field"], "parent_id")
        self.assertEqual(config["tree"]["levels"][2]["order"], "sequence, id")
        self.assertEqual(config["list"]["bindings"]["chapter_id"], {"field": "chapter_id", "operator": "child_of"})
        self.assertEqual(
            config["list"]["columns"],
            [
                {"field": "code", "label": "定额编号", "type": "char"},
                {"field": "name", "label": "项目名称", "type": "char"},
            ],
        )
        self.assertEqual(config["actions"][0]["key"], "action:856")
        self.assertEqual(
            config["commands"],
            [
                {
                    "key": "add_child",
                    "label": "Add child",
                    "kind": "object",
                    "method": "action_add_child",
                    "placement": "toolbar",
                    "group": "structure",
                    "availability_field": "",
                }
            ],
        )
        self.assertEqual(config["tree_title"], "所属定额库 / 所属专业 / 所属章节")

        planner_data = copy.deepcopy(data)
        planner_data["views"]["tree"]["collection_presentation"]["semantic"] = "hierarchy_planner"
        self.assembler._inject_native_collection_presentation(planner_data, context)
        planner_presentation = planner_data["views"]["tree"]["collection_presentation"]
        self.assertEqual(planner_presentation["semantic"], "hierarchy_planner")
        self.assertTrue(planner_presentation["enabled"])
        self.assertEqual(planner_presentation["config"]["planner"]["node_level_key"], "chapter_id")
        self.assertEqual(planner_presentation["config"]["planner"]["outline_field"], "name")
        self.assertEqual(planner_presentation["config"]["planner"]["code_field"], "code")

        fail_closed_data = copy.deepcopy(data)
        fail_closed_context = dict(context)
        fail_closed_context.pop("hierarchy_create")
        self.assembler._inject_native_collection_presentation(fail_closed_data, fail_closed_context)
        self.assertEqual(
            fail_closed_data["views"]["tree"]["collection_presentation"]["config"]["create"],
            {"enabled": False, "label": ""},
            "通用装配器不得补写任何新增业务文案",
        )

    def test_hierarchy_structural_fields_can_extend_relation_dialog_columns(self):
        class RelationModel:
            @staticmethod
            def check_access_rights(_operation, raise_exception=False):
                return not raise_exception

            @staticmethod
            def fields_get(names):
                available = {"code", "name", "project_id", "parent_id"}
                return {name: {"type": "many2one"} for name in names if name in available}

        class Env:
            def __getitem__(self, name):
                if name == "construction.work.breakdown":
                    return RelationModel()
                raise KeyError(name)

        self.assembler.env = Env()

        self.assertTrue(
            self.assembler._hierarchy_relation_fields_available(
                "construction.work.breakdown",
                ["id", "code", "name", "project_id", "parent_id"],
                {"id", "display_name", "name"},
            )
        )
        self.assertFalse(
            self.assembler._hierarchy_relation_fields_available(
                "construction.work.breakdown",
                ["id", "code", "missing_parent_id"],
                {"id", "display_name", "name"},
            )
        )

    def test_hierarchy_planner_scope_is_derived_from_declared_default_context(self):
        class MenuModel:
            @staticmethod
            def _visible_menu_ids():
                return []

        class Env:
            def __getitem__(self, name):
                if name == "ir.ui.menu":
                    return MenuModel()
                raise KeyError(name)

        self.assembler.env = Env()
        data = {
            "head": {"title": "Cost plan", "model": "project.cost.plan.node", "permissions": {"create": False}},
            "domain": [],
            "fields": {
                "plan_id": {"type": "many2one", "relation": "project.cost.plan", "string": "Plan"},
                "parent_id": {
                    "type": "many2one", "relation": "project.cost.plan.node", "string": "Parent",
                    "relation_entry": {"search_dialog": {"read_fields": ["code", "name", "parent_id"]}},
                },
                "code": {"type": "char", "string": "Code"},
                "name": {"type": "char", "string": "Name"},
            },
            "views": {
                "tree": {
                    "collection_presentation": {"semantic": "hierarchy_planner"},
                    "columns_schema": [{"name": "code", "label": "Code"}, {"name": "name", "label": "Name"}],
                    "toolbar": {"header": []},
                    "order": "parent_path, sequence, id",
                },
                "form": {},
            },
        }
        context = {
            "default_plan_id": 21,
            "hierarchy_scope": {"field": "plan_id", "context_field": "default_plan_id"},
            "hierarchy_default_expand_depth": 0,
            "hierarchy_page_size": 12000,
            "hierarchy_levels": [{
                "field": "parent_id", "code_field": "code", "label_field": "name",
                "self_parent_field": "parent_id", "domain_operator": "child_of",
            }],
        }

        self.assembler._inject_native_collection_presentation(data, context)

        config = data["views"]["tree"]["collection_presentation"]["config"]
        self.assertEqual(config["tree"]["levels"][0]["domain"], [("plan_id", "=", 21)])
        self.assertEqual(config["list"]["domain"], [("plan_id", "=", 21)])
        self.assertEqual(config["list"]["page_size"], 12000)
        self.assertEqual(config["planner"]["default_expand_depth"], 0)

    def test_native_hierarchical_worksheet_is_assembled_from_relation_contract(self):
        class HierarchyModel:
            @staticmethod
            def check_access_rights(_operation, raise_exception=False):
                return not raise_exception

            @staticmethod
            def fields_get(names):
                available = {"parent_id", "project_id", "code", "name", "level_type", "amount_total"}
                return {name: {"type": "char"} for name in names if name in available}

        class MenuModel:
            @staticmethod
            def _visible_menu_ids():
                return []

        class Env:
            def __getitem__(self, name):
                if name == "generic.hierarchy":
                    return HierarchyModel()
                if name == "ir.ui.menu":
                    return MenuModel()
                raise KeyError(name)

        self.assembler.env = Env()
        data = {
            "head": {"title": "Worksheet", "model": "generic.line"},
            "fields": {
                "binding_id": {"type": "many2one", "relation": "generic.hierarchy"},
                "code": {"type": "char", "string": "Code"},
                "name": {"type": "char", "string": "Name"},
                "amount": {"type": "monetary", "string": "Amount"},
                "description": {"type": "char", "string": "Description"},
                "row_kind": {"type": "selection", "string": "Row kind"},
            },
            "views": {
                "tree": {
                    "collection_presentation": {"semantic": "hierarchical_worksheet", "source": "native_view_derived"},
                    "columns_schema": [
                        {"name": "code", "label": "Code"},
                        {"name": "name", "label": "Name"},
                        {"name": "amount", "label": "Amount"},
                    ],
                    "toolbar": {"header": []},
                    "order": "code asc",
                },
            },
        }
        context = {
            "hierarchical_worksheet": {
                "binding_field": "binding_id",
                "parent_field": "parent_id",
                "project_field": "project_id",
                "code_field": "code",
                "label_field": "name",
                "type_field": "level_type",
                "leaf_values": ["item"],
                "group_field_map": {"amount": "amount_total"},
                "column_precisions": {"amount": 2},
                "presentation_mode": "source_order",
                "row_kind_field": "row_kind",
                "item_values": ["item"],
                "heading_values": ["heading"],
                "summary_values": ["subtotal", "total"],
                "variance_field": "amount",
                "variance_tolerance": 0.005,
                "sheet_order": "source_index, sequence, id",
                "tabs": [{"key": "detail", "label": "Detail", "fields": ["description"]}],
            },
        }

        self.assembler._inject_native_collection_presentation(data, context)

        presentation = data["views"]["tree"]["collection_presentation"]
        self.assertTrue(presentation["enabled"])
        self.assertEqual(presentation["config"]["hierarchy"]["model"], "generic.hierarchy")
        self.assertEqual(presentation["config"]["sheet"]["binding_field"], "binding_id")
        self.assertEqual(presentation["config"]["sheet"]["columns"][2]["align"], "right")
        self.assertEqual(presentation["config"]["sheet"]["columns"][2]["precision"], 2)
        self.assertEqual(presentation["config"]["sheet"]["presentation_mode"], "source_order")
        self.assertEqual(presentation["config"]["sheet"]["row_kind_field"], "row_kind")
        self.assertIn("row_kind", presentation["config"]["sheet"]["fields"])
        self.assertEqual(presentation["config"]["sheet"]["order"], "source_index, sequence, id")
        self.assertEqual(presentation["config"]["sheet"]["variance_field"], "amount")
        self.assertEqual(presentation["config"]["sheet"]["variance_tolerance"], 0.005)
        self.assertEqual(presentation["config"]["detail"]["tabs"][0]["fields"][0]["field"], "description")

    def test_source_order_worksheet_can_build_navigation_from_sheet_groups(self):
        class MenuModel:
            @staticmethod
            def _visible_menu_ids():
                return []

        class Env:
            def __getitem__(self, name):
                if name == "ir.ui.menu":
                    return MenuModel()
                raise KeyError(name)

        self.assembler.env = Env()
        data = {
            "head": {"title": "Source worksheet", "model": "source.line"},
            "fields": {
                "name": {"type": "char", "string": "Name"},
                "single_name": {"type": "char", "string": "Single"},
                "unit_name": {"type": "char", "string": "Unit"},
                "row_kind": {"type": "selection", "string": "Row kind"},
            },
            "views": {
                "tree": {
                    "collection_presentation": {"semantic": "hierarchical_worksheet"},
                    "columns_schema": [{"name": "name", "label": "Name"}],
                    "toolbar": {"header": []},
                    "order": "id asc",
                },
            },
        }
        context = {
            "hierarchical_worksheet": {
                "navigation_mode": "sheet_groups",
                "navigation_groups": [
                    {"field": "single_name", "label": "Single"},
                    {"field": "unit_name", "label": "Unit"},
                ],
                "presentation_mode": "source_order",
                "row_kind_field": "row_kind",
                "item_values": ["item"],
            },
        }

        self.assembler._inject_native_collection_presentation(data, context)

        config = data["views"]["tree"]["collection_presentation"]["config"]
        self.assertTrue(data["views"]["tree"]["collection_presentation"]["enabled"])
        self.assertEqual(config["hierarchy"]["navigation_mode"], "sheet_groups")
        self.assertEqual([row["field"] for row in config["hierarchy"]["navigation_groups"]], ["single_name", "unit_name"])
        self.assertEqual(config["sheet"]["binding_field"], "")
        self.assertIn("single_name", config["sheet"]["fields"])


if __name__ == "__main__":
    unittest.main()
