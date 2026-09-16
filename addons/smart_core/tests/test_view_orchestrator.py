# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from pathlib import Path


def _install_module(name):
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module


def _load_orchestrator():
    root = Path(__file__).resolve().parents[1]
    _install_module("odoo")
    _install_module("odoo.addons")
    smart_core_mod = _install_module("odoo.addons.smart_core")
    core_mod = _install_module("odoo.addons.smart_core.core")
    smart_core_mod.__path__ = [str(root)]
    core_mod.__path__ = [str(root / "core")]
    for module_name in (
        "odoo.addons.smart_core.core.source_authority",
        "odoo.addons.smart_core.core.view_orchestration_contract",
        "odoo.addons.smart_core.core.view_orchestrator",
    ):
        sys.modules.pop(module_name, None)
    for filename, module_name in (
        ("source_authority.py", "odoo.addons.smart_core.core.source_authority"),
        ("view_orchestration_contract.py", "odoo.addons.smart_core.core.view_orchestration_contract"),
        ("view_orchestrator.py", "odoo.addons.smart_core.core.view_orchestrator"),
    ):
        spec = importlib.util.spec_from_file_location(module_name, root / "core" / filename)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    return sys.modules["odoo.addons.smart_core.core.view_orchestrator"].ViewOrchestrator


class _Config:
    id = 9
    name = "demo"
    version_no = 3

    def __init__(self, payload):
        self.contract_json = payload


class _ConfigModel:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def _effective_view_orchestration_contracts(self, model_name, **kwargs):
        self.calls.append((model_name, kwargs))
        return [_Config(self.payload)]


class _LegacyPolicyModel:
    def __init__(self):
        self.calls = []

    def apply_to_view_contract(
        self,
        contract,
        *,
        model_name,
        view_type,
        action_id=None,
        view_id=None,
        excluded_field_names=None,
        allow_layout_append=True,
        preserve_native_restrictions=False,
    ):
        self.calls.append({"allow_layout_append": bool(allow_layout_append)})
        excluded = {str(name or "").strip() for name in (excluded_field_names or []) if str(name or "").strip()}
        out = dict(contract or {})
        layout = out.get("layout")
        if isinstance(layout, list):
            out["layout"] = self._filter_layout(layout, excluded)
            if allow_layout_append and "email" not in excluded:
                out["layout"].append({
                    "type": "sheet",
                    "children": [{
                        "type": "group",
                        "string": "Legacy Contact",
                        "children": [{"type": "field", "name": "email"}],
                    }],
                })
        return out

    def _filter_layout(self, nodes, excluded):
        result = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            row = dict(node)
            if row.get("type") == "field" and row.get("name") == "email" and "email" not in excluded:
                continue
            children = row.get("children")
            if isinstance(children, list):
                row["children"] = self._filter_layout(children, excluded)
            result.append(row)
        return result


class _Env(dict):
    pass


class _Model:
    _fields = {
        "name": object(),
        "email": object(),
        "company_id": object(),
        "amount_total": object(),
        "start_date": object(),
        "end_date": object(),
        "user_id": object(),
        "state": object(),
        "line_ids": object(),
    }

    def fields_get(self):
        return {
            "name": {"string": "Name", "type": "char"},
            "email": {"string": "Email", "type": "char"},
            "state": {"string": "Status", "type": "selection"},
            "line_ids": {"string": "Lines", "type": "one2many"},
        }


class TestViewOrchestrator(unittest.TestCase):
    def setUp(self):
        self.ViewOrchestrator = _load_orchestrator()

    def _compose(self, payload, contract, view_type, *, legacy_policy=False, view_id=22):
        env = _Env({"ui.business.config.contract": _ConfigModel(payload), "res.partner": _Model()})
        if legacy_policy:
            env["ui.form.field.policy"] = _LegacyPolicyModel()
        result = self.ViewOrchestrator(env).compose(
            contract,
            model_name="res.partner",
            view_type=view_type,
            action_id=11,
            view_id=view_id,
        )
        return result, env["ui.business.config.contract"].calls

    def test_entry_semantic_surface_blocks_legacy_root_layout_append(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "form": {
                        "composition_mode": "entry_semantic_surface",
                        "sections": [{"title": "Identity", "fields": ["name"]}],
                        "fields": [{"name": "name", "label": "Name"}],
                    }
                }
            }
        }
        env = _Env({
            "ui.business.config.contract": _ConfigModel(payload),
            "ui.form.field.policy": _LegacyPolicyModel(),
            "res.partner": _Model(),
        })
        source = {
            "layout": [{
                "type": "notebook",
                "tabs": [{
                    "type": "page",
                    "string": "Relations",
                    "children": [{
                        "type": "field",
                        "name": "line_ids",
                        "widget": "one2many_list",
                        "subview": {"tree": {"columns": ["display_name"]}},
                    }],
                }],
            }],
        }

        result = self.ViewOrchestrator(env).compose(
            source,
            model_name="res.partner",
            view_type="form",
            action_id=81,
        )

        self.assertNotIn("Legacy Contact", str(result["layout"]))
        self.assertEqual(result["layout"], source["layout"])
        self.assertIn("one2many_list", str(result["layout"]))
        self.assertEqual(env["ui.form.field.policy"].calls, [{"allow_layout_append": False}])

    def test_native_semantic_surface_keeps_native_tree_as_task_structure_authority(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "form": {
                        "title": "Payment application",
                        "composition_mode": "native_semantic_surface",
                        "semantic_anchors": [
                            {"role": "summary", "fields": ["name", "state"]},
                        ],
                    },
                },
            },
        }
        source_layout = [{
            "type": "sheet",
            "children": [{
                "type": "group",
                "string": "Basic",
                "attributes": {"data-sc-anchor": "payment-basic"},
                "children": [
                    {"type": "field", "name": "name"},
                    {"type": "field", "name": "state", "readonly": True},
                ],
            }],
        }]

        result, _calls = self._compose(
            payload,
            {"layout": source_layout},
            "form",
            legacy_policy=True,
            view_id=None,
        )

        self.assertEqual(result["layout"], source_layout)
        governance = result["governance"]["view_orchestration"]
        self.assertEqual(governance["form_structure_authority"], "native_authority")
        self.assertEqual(governance["form_presentation_mode"], "task")
        self.assertTrue(governance["native_semantic_surface"])
        self.assertFalse(governance["form_layout_overlay"])
        self.assertNotIn("Legacy Contact", str(result["layout"]))

    def test_native_semantic_surface_reports_structure_conflict(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "form": {
                        "composition_mode": "native_semantic_surface",
                        "sections": [{"title": "Competing section", "fields": ["name"]}],
                    },
                },
            },
        }

        with self.assertRaisesRegex(ValueError, "NATIVE_SEMANTIC_SURFACE_STRUCTURE_CONFLICT"):
            self._compose(payload, {"layout": []}, "form", view_id=1701)

    def test_native_semantic_surface_reports_unknown_anchor_field(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "form": {
                        "composition_mode": "native_semantic_surface",
                        "semantic_anchors": [{"role": "summary", "fields": ["missing_field"]}],
                    },
                },
            },
        }

        with self.assertRaisesRegex(ValueError, "NATIVE_SEMANTIC_SURFACE_UNKNOWN_FIELD: missing_field"):
            self._compose(payload, {"layout": []}, "form", view_id=1701)

    def test_explicit_native_form_view_blocks_legacy_layout_append(self):
        env = _Env({
            "ui.business.config.contract": _ConfigModel({}),
            "ui.form.field.policy": _LegacyPolicyModel(),
            "res.partner": _Model(),
        })
        source = {
            "layout": [{
                "type": "sheet",
                "children": [{
                    "type": "field",
                    "name": "name",
                    "native_locator": "/form/sheet[1]/field[@name='name'][1]",
                    "occurrence_index": 1,
                    "source_position": 0,
                }],
            }],
        }

        result = self.ViewOrchestrator(env).compose(
            source,
            model_name="res.partner",
            view_type="form",
            action_id=11,
            view_id=22,
        )

        self.assertEqual(env["ui.form.field.policy"].calls, [{"allow_layout_append": False}])
        self.assertNotIn("Legacy Contact", str(result["layout"]))
        self.assertEqual(result["layout"], source["layout"])

    def test_search_view_uses_business_config_filters_and_group_by(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "search": {
                        "filters": [
                            {"name": "late", "label": "Late", "domain": [["active", "=", False]], "sequence": 20},
                            {"name": "active_customers", "label": "Active", "domain": [["active", "=", True]], "sequence": 10},
                        ],
                        "groupBys": [
                            {"name": "by_state", "field": "state", "label": "State", "sequence": 20},
                            {"name": "by_company", "field": "company_id", "label": "Company", "sequence": 10},
                        ],
                    }
                }
            }
        }

        result, calls = self._compose(payload, {"search": {"filters": [], "group_by": []}}, "search")

        self.assertEqual(result["search"]["filters"][0]["name"], "active_customers")
        self.assertEqual(result["search"]["filters"][0]["key"], "active_customers")
        self.assertEqual(result["search"]["filters"][0]["label"], "Active")
        self.assertEqual(result["search"]["group_by"][0]["field"], "company_id")
        self.assertEqual(result["search"]["group_by"][0]["label"], "Company")
        self.assertEqual(calls[0][1]["view_type"], "search")
        self.assertEqual((result["governance"]["view_orchestration"])["owner_layer"], "business_view_orchestration")
        trace = result["source_trace"]["view_orchestration"]
        self.assertEqual(trace["owner_layer"], "business_view_orchestration")
        self.assertEqual(trace["view_type"], "search")
        self.assertEqual(trace["action_id"], 11)
        self.assertEqual(trace["view_id"], 22)
        self.assertEqual(trace["business_config_contracts"][0]["id"], 9)

    def test_form_view_can_use_business_config_layout_overlay(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "form": {
                        "layout": [
                            {
                                "type": "sheet",
                                "children": [
                                    {
                                        "type": "group",
                                        "name": "flat_fields",
                                        "columns": 3,
                                        "children": [
                                            {"type": "field", "name": "email"},
                                            {"type": "field", "name": "missing_field"},
                                            {"type": "field", "name": "name"},
                                        ],
                                    }
                                ],
                            }
                        ],
                        "fields": [
                            {"name": "name", "label": "Partner Name", "sequence": 10},
                            {"name": "email", "label": "Email Alias", "sequence": 20},
                        ],
                    }
                }
            }
        }
        source_layout = [
            {
                "type": "sheet",
                "children": [
                    {"type": "group", "name": "native_group", "children": [{"type": "field", "name": "name"}]}
                ],
            }
        ]

        result, _calls = self._compose(payload, {"layout": source_layout}, "form", view_id=None)

        sheet = result["layout"][0]
        group = sheet["children"][0]
        self.assertEqual(group.get("name"), "flat_fields")
        self.assertEqual(group.get("columns"), 3)
        self.assertEqual([row.get("name") for row in group.get("children")], ["name", "email"])
        self.assertEqual(group["children"][0].get("label"), "Partner Name")
        self.assertNotIn("native_group", str(result["layout"]))
        self.assertNotIn("missing_field", str(result["layout"]))

    def test_form_view_appends_missing_fields_to_declared_group(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "form": {
                        "layout": [
                            {
                                "type": "sheet",
                                "children": [
                                    {
                                        "type": "group",
                                        "name": "primary",
                                        "string": "Primary",
                                        "children": [{"type": "field", "name": "name"}],
                                    }
                                ],
                            }
                        ],
                        "fields": [
                            {"name": "name", "label": "Partner Name", "sequence": 10, "group_title": "Primary"},
                            {"name": "email", "label": "Email Alias", "sequence": 20, "group_title": "Primary"},
                        ],
                    }
                }
            }
        }

        result, _calls = self._compose(payload, {"layout": []}, "form", view_id=None)

        group = result["layout"][0]["children"][0]
        self.assertEqual(group.get("string"), "Primary")
        self.assertEqual([row.get("name") for row in group.get("children")], ["name", "email"])
        self.assertNotIn("business_config_orchestration_fields", str(result["layout"]))

    def test_explicit_form_view_preserves_native_member_set(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "form": {
                        "actions": [{"name": "configured_only", "intent": "record.configured"}],
                        "fields": [
                            {"name": "name", "sequence": 10},
                            {"name": "email", "sequence": 20},
                        ],
                    }
                }
            }
        }
        source_layout = [{
            "type": "sheet",
            "children": [{"type": "group", "children": [{"type": "field", "name": "name"}]}],
        }]

        result, _calls = self._compose(
            payload,
            {"layout": source_layout, "header_buttons": [{"name": "native_only", "intent": "record.native"}]},
            "form",
            view_id=1700,
        )

        self.assertIn("name", str(result["layout"]))
        self.assertNotIn("email", str(result["layout"]))
        self.assertNotIn("business_config_orchestration_fields", str(result["layout"]))
        self.assertEqual(result["header_buttons"], [{"name": "native_only", "intent": "record.native"}])

    def test_explicit_form_view_preserves_native_field_order(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "form": {
                        "fields": [
                            {"name": "email", "sequence": 10, "readonly": True},
                            {"name": "name", "sequence": 20},
                        ],
                    }
                }
            }
        }
        source_layout = [{
            "type": "sheet",
            "children": [
                {"type": "field", "name": "name"},
                {"type": "field", "name": "email"},
            ],
        }]

        result, _calls = self._compose(
            payload,
            {"layout": source_layout},
            "form",
            view_id=1700,
        )

        fields = result["layout"][0]["children"]
        self.assertEqual([field["name"] for field in fields], ["name", "email"])
        self.assertTrue(fields[1]["readonly"])

    def test_form_view_can_compose_entry_semantic_surface_without_layout_overlay(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "form": {
                        "composition_mode": "entry_semantic_surface",
                        "layout": [{"type": "sheet", "children": [{"type": "field", "name": "email"}]}],
                        "sections": [
                            {"title": "Primary", "sequence": 10, "columns": 2, "fields": ["name", "state"]},
                            {"title": "Contact", "sequence": 20, "columns": 2, "fields": ["email"]},
                            {"title": "Relations", "sequence": 30, "fields": ["line_ids"]},
                        ],
                        "fields": [
                            {"name": "email", "label": "Email Alias", "sequence": 20, "group_title": "Contact"},
                            {"name": "name", "label": "Partner Name", "sequence": 10, "group_title": "Primary"},
                            {"name": "state", "label": "Status", "sequence": 15, "group_title": "Primary"},
                            {"name": "line_ids", "label": "Lines", "sequence": 30, "group_title": "Relations"},
                        ],
                    }
                }
            }
        }
        source_layout = [
            {"type": "header", "children": [
                {"type": "field", "name": "state", "widget": "statusbar"},
                {"type": "button", "name": "action_save"},
            ]},
            {
                "type": "sheet",
                "children": [
                    {"type": "group", "name": "native_group", "children": [{"type": "field", "name": "company_id"}]},
                    {"type": "notebook", "tabs": [{"type": "page", "string": "Relations", "children": [
                        {"type": "field", "name": "name"},
                        {
                            "type": "field",
                            "name": "line_ids",
                            "widget": "one2many_list",
                            "context": {"default_parent_id": "active_id"},
                            "subview": {"tree": {"columns": ["display_name"]}},
                        },
                    ]}]},
                    {"type": "attachment", "name": "native_attachments"},
                    {"type": "chatter", "name": "native_chatter"},
                ],
            }
        ]

        result, _calls = self._compose(
            payload,
            {
                "layout": source_layout,
                "subviews": {"line_ids": {"tree": {"columns": ["display_name"]}}},
            },
            "form",
        )

        self.assertEqual([row.get("type") for row in result["layout"]], ["header", "sheet"])
        self.assertIn("native_group", str(result["layout"]))
        self.assertIn("Relations", str(result["layout"]))
        def field_occurrences(nodes, field_name):
            count = 0
            for node in nodes if isinstance(nodes, list) else []:
                if not isinstance(node, dict):
                    continue
                if node.get("type") == "field" and node.get("name") == field_name:
                    count += 1
                for child_key in ("children", "pages", "tabs", "nodes", "items"):
                    count += field_occurrences(node.get(child_key), field_name)
            return count

        self.assertEqual(field_occurrences(result["layout"], "name"), 1)
        self.assertEqual(field_occurrences(result["layout"], "state"), 1)
        self.assertIn("statusbar", str(result["layout"]))
        self.assertEqual(field_occurrences(result["layout"], "line_ids"), 1)
        self.assertEqual(field_occurrences(result["layout"], "email"), 0)
        self.assertIn("line_ids", str(result["layout"]))
        self.assertIn("one2many_list", str(result["layout"]))
        self.assertIn("default_parent_id", str(result["layout"]))
        self.assertEqual(
            result["subviews"]["line_ids"]["tree"]["columns"],
            ["display_name"],
        )
        self.assertIn("native_chatter", str(result["layout"]))
        self.assertIn("native_attachments", str(result["layout"]))
        governance = result["governance"]["view_orchestration"]
        trace = result["source_trace"]["view_orchestration"]
        self.assertEqual(governance["form_structure_authority"], "entry_semantic_surface")
        self.assertEqual(trace["form_structure_authority"], "entry_semantic_surface")

        second, _calls = self._compose(payload, result, "form")
        self.assertEqual(second["layout"], result["layout"])
        self.assertEqual(
            second["governance"]["view_orchestration"]["form_structure_authority"],
            "entry_semantic_surface",
        )
        self.assertEqual(
            second["source_trace"]["view_orchestration"]["form_structure_authority"],
            "entry_semantic_surface",
        )
        self.assertEqual(
            second["governance"]["view_orchestration"]["business_config_contracts"][0]["id"],
            9,
        )

    def test_prior_legacy_policy_application_survives_later_noop(self):
        payload = {
            "view_orchestration": {
                "views": {"form": {"fields": [{"name": "email", "label": "Email"}]}}
            }
        }
        contract = {
            "layout": [{"type": "sheet", "children": [{"type": "field", "name": "email"}]}],
            "governance": {"view_orchestration": {"legacy_field_policy_overlay": True}},
        }

        result, _calls = self._compose(payload, contract, "form", legacy_policy=True)

        self.assertTrue(result["governance"]["view_orchestration"]["legacy_field_policy_overlay"])
        self.assertTrue(result["source_trace"]["view_orchestration"]["legacy_field_policy_overlay"])

    def test_plain_business_form_contract_does_not_claim_semantic_structure_authority(self):
        payload = {
            "view_orchestration": {
                "views": {"form": {"fields": [{"name": "name", "label": "Partner Name"}]}}
            }
        }

        result, _calls = self._compose(payload, {"layout": []}, "form")

        self.assertEqual(result["governance"]["view_orchestration"]["form_structure_authority"], "")

    def test_pivot_view_uses_business_config_measures_dimensions_and_defaults(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "pivot": {
                        "measures": [{"name": "amount_total", "label": "Amount", "sequence": 20}],
                        "dimensions": [{"name": "company_id", "label": "Company", "sequence": 10}],
                        "defaults": {"measure": "amount_total"},
                        "chart_policy": {"type": "bar"},
                    }
                }
            }
        }

        result, _calls = self._compose(payload, {"pivot": {"measures": ["legacy"]}}, "pivot")

        self.assertEqual(result["pivot"]["measures"][0]["name"], "amount_total")
        self.assertEqual(result["pivot"]["measures"][0]["label"], "Amount")
        self.assertEqual(result["pivot"]["dimensions"][0]["name"], "company_id")
        self.assertEqual(result["pivot"]["dimensions"][0]["label"], "Company")
        self.assertEqual(result["pivot"]["defaults"]["measure"], "amount_total")
        self.assertEqual(result["pivot"]["chart_policy"]["type"], "bar")

    def test_generic_view_uses_business_config_slots_and_actions(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "kanban": {
                        "fields": [
                            {"name": "email", "label": "Email", "sequence": 10},
                            {"name": "name", "label": "Name", "sequence": 20},
                            {"name": "state", "visible": False, "sequence": 30},
                        ],
                        "slots": {"primary": ["name", "state", "email"]},
                        "actions": [{"name": "open", "intent": "form.open"}],
                    }
                }
            }
        }

        result, _calls = self._compose(payload, {"kanban": {}}, "kanban")

        self.assertEqual([row["name"] for row in result["kanban"]["fields"]], ["email", "name"])
        self.assertEqual(result["kanban"]["fields"][0]["label"], "Email")
        self.assertEqual(result["kanban"]["slots"]["primary"], ["email", "name"])
        self.assertEqual(result["kanban"]["actions"][0]["intent"], "form.open")

    def test_graph_view_uses_business_config_scalar_and_display_rows(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "graph": {
                        "type": "line",
                        "measure": "amount_total",
                        "dimension": "company_id",
                        "measures": [{"name": "amount_total", "label": "Amount", "sequence": 20}],
                        "dimensions": [{"name": "company_id", "label": "Company", "sequence": 10}],
                    }
                }
            }
        }

        result, _calls = self._compose(payload, {"graph": {}}, "graph")

        self.assertEqual(result["graph"]["type"], "line")
        self.assertEqual(result["graph"]["measure"], "amount_total")
        self.assertEqual(result["graph"]["dimension"], "company_id")
        self.assertEqual(result["graph"]["dimensions"][0]["label"], "Company")

    def test_calendar_view_uses_business_config_date_resource_and_color_slots(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "calendar": {
                        "date_slots": {"start": "start_date", "stop": "end_date"},
                        "resource_slots": {"owner": "user_id"},
                        "color_slots": {"state": "state"},
                    }
                }
            }
        }

        result, _calls = self._compose(payload, {"calendar": {}}, "calendar")

        self.assertEqual(result["calendar"]["date_slots"]["start"], "start_date")
        self.assertEqual(result["calendar"]["resource_slots"]["owner"], "user_id")
        self.assertEqual(result["calendar"]["color_slots"]["state"], "state")

    def test_dashboard_view_uses_business_config_metric_chart_and_navigation_slots(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "dashboard": {
                        "metric_slots": {"primary": ["amount_total"]},
                        "chart_slots": {"trend": {"type": "line"}},
                        "navigation_slots": {"next": "project.dashboard.enter"},
                    }
                }
            }
        }

        result, _calls = self._compose(payload, {"dashboard": {}}, "dashboard")

        self.assertEqual(result["dashboard"]["metric_slots"]["primary"], ["amount_total"])
        self.assertEqual(result["dashboard"]["chart_slots"]["trend"]["type"], "line")
        self.assertEqual(result["dashboard"]["navigation_slots"]["next"], "project.dashboard.enter")

    def test_list_view_uses_business_config_row_actions(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "tree": {
                        "columns": [{"name": "name", "sequence": 10}],
                        "actions": [{"name": "open_dashboard", "intent": "project.dashboard.enter"}],
                    }
                }
            }
        }

        result, _calls = self._compose(payload, {"columns": ["name"], "row_actions": []}, "tree")

        self.assertEqual(result["row_actions"][0]["intent"], "project.dashboard.enter")

    def test_form_view_uses_business_config_action_slots_without_field_rows(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "form": {
                        "action_slots": {
                            "header_buttons": [{"name": "approve", "intent": "record.approve"}],
                            "stat_buttons": [{"name": "analytics", "intent": "analytics.open"}],
                        }
                    }
                }
            }
        }

        result, _calls = self._compose(payload, {"layout": [], "header_buttons": []}, "form", view_id=None)

        self.assertEqual(result["header_buttons"][0]["intent"], "record.approve")
        self.assertEqual(result["stat_buttons"][0]["intent"], "analytics.open")

    def test_form_view_uses_business_config_field_display_policy(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "form": {
                        "fields": [
                            {
                                "name": "email",
                                "label": "Contact Email",
                                "readonly": True,
                                "required": "true",
                                "help": "Shown to the customer",
                                "widget": "email",
                                "class": "important",
                                "sequence": 10,
                            }
                        ]
                    }
                }
            }
        }
        contract = {
            "layout": [
                {
                    "type": "sheet",
                    "children": [
                        {
                            "type": "field",
                            "name": "email",
                            "fieldInfo": {"name": "email", "label": "Email"},
                        }
                    ],
                }
            ]
        }

        result, _calls = self._compose(payload, contract, "form", view_id=None)
        field = result["layout"][0]["children"][0]

        self.assertEqual(field["label"], "Contact Email")
        self.assertTrue(field["readonly"])
        self.assertTrue(field["required"])
        self.assertEqual(field["help"], "Shown to the customer")
        self.assertEqual(field["widget"], "email")
        self.assertEqual(field["fieldInfo"]["label"], "Contact Email")

    def test_business_config_declared_form_fields_are_not_overridden_by_legacy_policy(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "form": {
                        "fields": [{"name": "email", "label": "Contract Email", "sequence": 10}]
                    }
                }
            }
        }
        contract = {
            "layout": [
                {
                    "type": "sheet",
                    "children": [
                        {"type": "field", "name": "email", "fieldInfo": {"name": "email", "label": "Email"}},
                    ],
                }
            ]
        }

        result, _calls = self._compose(payload, contract, "form", legacy_policy=True)

        fields = result["layout"][0]["children"]
        self.assertEqual([field["name"] for field in fields], ["email"])
        self.assertEqual(fields[0]["label"], "Contract Email")
        governance = result["governance"]["view_orchestration"]
        self.assertEqual(governance["business_config_form_fields"], ["email"])
        self.assertFalse(governance["legacy_field_policy_overlay"])

    def test_legacy_policy_still_applies_to_fields_not_declared_by_business_config(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "form": {
                        "fields": [{"name": "name", "label": "Partner", "sequence": 10}]
                    }
                }
            }
        }
        contract = {
            "layout": [
                {
                    "type": "sheet",
                    "children": [
                        {"type": "field", "name": "name"},
                        {"type": "field", "name": "email"},
                    ],
                }
            ]
        }

        result, _calls = self._compose(payload, contract, "form", legacy_policy=True)

        fields = result["layout"][0]["children"]
        self.assertEqual([field["name"] for field in fields], ["name"])
        self.assertTrue(result["governance"]["view_orchestration"]["legacy_field_policy_overlay"])

    def test_form_view_uses_business_config_field_order_in_native_layout(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "form": {
                        "fields": [
                            {"name": "email", "sequence": 10},
                            {"name": "name", "sequence": 20},
                        ]
                    }
                }
            }
        }
        contract = {
            "layout": [
                {
                    "type": "sheet",
                    "children": [
                        {"type": "field", "name": "name"},
                        {"type": "field", "name": "email"},
                    ],
                }
            ]
        }

        result, _calls = self._compose(payload, contract, "form", view_id=None)

        self.assertEqual([node["name"] for node in result["layout"][0]["children"]], ["email", "name"])

    def test_list_view_uses_business_config_column_display_policy(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "tree": {
                        "columns": [
                            {
                                "name": "email",
                                "label": "Contact Email",
                                "readonly": True,
                                "help": "Shown to the customer",
                                "widget": "email",
                                "width": "180px",
                                "sequence": 10,
                            }
                        ]
                    }
                }
            }
        }
        contract = {"columns": ["email"], "columns_schema": [{"name": "email", "label": "Email"}]}

        result, _calls = self._compose(payload, contract, "tree")
        column = result["columns_schema"][0]

        self.assertEqual(column["label"], "Contact Email")
        self.assertTrue(column["readonly"])
        self.assertEqual(column["help"], "Shown to the customer")
        self.assertEqual(column["widget"], "email")
        self.assertEqual(column["width"], "180px")

    def test_list_view_uses_business_config_view_options(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "tree": {
                        "columns": [{"name": "email", "sequence": 10}],
                        "order": "write_date desc",
                        "page_size": 80,
                        "row_classes": [{"class": "late", "expr": "date_deadline < today"}],
                        "domain": {"base": [["active", "=", True]]},
                        "context": {"default_active": True},
                    }
                }
            }
        }
        contract = {"columns": ["email"], "columns_schema": [{"name": "email"}], "page_size": 20}

        result, _calls = self._compose(payload, contract, "tree")

        self.assertEqual(result["order"], "write_date desc")
        self.assertEqual(result["page_size"], 80)
        self.assertEqual(result["row_classes"][0]["class"], "late")
        self.assertEqual(result["domain"]["base"][0][0], "active")
        self.assertTrue(result["context"]["default_active"])

    def test_dashboard_view_uses_business_config_cards_and_kpis(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "dashboard": {
                        "title": "Executive Overview",
                        "cards": [{"name": "revenue", "label": "Revenue"}],
                        "kpis": [{"name": "win_rate", "label": "Win Rate"}],
                    }
                }
            }
        }

        result, _calls = self._compose(payload, {"dashboard": {}}, "dashboard")

        self.assertEqual(result["dashboard"]["title"], "Executive Overview")
        self.assertEqual(result["dashboard"]["cards"][0]["name"], "revenue")
        self.assertEqual(result["dashboard"]["kpis"][0]["name"], "win_rate")

    def test_runtime_orchestration_drops_unknown_field_refs_from_existing_configs(self):
        payload = {
            "view_orchestration": {
                "views": {
                    "tree": {
                        "columns": [
                            {"name": "email", "sequence": 10},
                            {"name": "missing_column", "sequence": 20},
                        ],
                        "default_group_by": "missing_group",
                        "actions": [{"name": "open_dashboard", "intent": "project.dashboard.enter"}],
                    }
                }
            }
        }
        contract = {
            "columns": ["name", "email"],
            "columns_schema": [{"name": "name"}, {"name": "email"}],
        }

        result, _calls = self._compose(payload, contract, "tree")

        self.assertEqual(result["columns"], ["email", "name"])
        self.assertEqual([row["name"] for row in result["columns_schema"]], ["email", "name"])
        self.assertEqual(result["row_actions"][0]["intent"], "project.dashboard.enter")
        self.assertNotIn("default_group_by", result)



class TestSingleStructureResolution(unittest.TestCase):
    def test_legacy_scoped_structure_remains_supported_until_its_migration(self):
        from types import SimpleNamespace
        _load_orchestrator()
        helper = sys.modules["odoo.addons.smart_core.core.form_structure_authority"]
        config = _Config({"view_orchestration": {"views": {"form": {"sections": [{"key": "legacy", "fields": ["name"]}]}}}})
        config.action_id = SimpleNamespace(id=12)
        self.assertEqual(helper.diagnose_structure_ownership([config], model="demo.business", action_id=12), [])
        native = _Config({"view_orchestration": {"views": {"form": {"composition_mode": "native_semantic_surface"}}}})
        native.id = 99
        for scope in (SimpleNamespace(id=12), 12):
            config.action_id = scope
            with self.assertRaisesRegex(ValueError, "STRUCTURE_CONFLICT"):
                helper.diagnose_structure_ownership([config, native], model="demo.business", action_id=12)
        config.action_id = 0
        config.view_id = 34
        with self.assertRaisesRegex(ValueError, "STRUCTURE_CONFLICT"):
            helper.diagnose_structure_ownership([config, native], model="demo.business", action_id=12, view_id=34)

    def test_role_selection_uses_authenticated_identity_at_single_boundary(self):
        from unittest import mock
        orchestrator = _load_orchestrator()
        configs = _ConfigModel({})
        env = _Env({"ui.business.config.contract": configs})
        env.user = object()
        class Resolver:
            def __init__(self, actual_env):
                self.env = actual_env
            def user_group_xmlids(self, user):
                assert user is env.user
                return ["verified.group"]
            def resolve_role_code(self, groups):
                assert groups == ["verified.group"]
                return "finance"
        identity = types.ModuleType("odoo.addons.smart_core.identity.identity_resolver")
        identity.IdentityResolver = Resolver
        with mock.patch.dict(sys.modules, {identity.__name__: identity}):
            result = orchestrator(env).compose({"layout": [{"type": "field", "name": "name"}]},
                model_name="res.partner", view_type="form", role_key="untrusted_source_role", view_id=34)
        self.assertEqual(len(configs.calls), 1)
        self.assertEqual(configs.calls[0][1]["role_key"], "finance")
        self.assertEqual(result["source_trace"]["view_orchestration"]["authenticated_role_key"], "finance")

    def test_real_payment_config_chain_retains_semantics_without_second_structure(self):
        import ast
        import xml.etree.ElementTree as ET
        from types import SimpleNamespace
        orchestrator = _load_orchestrator()
        data = Path(__file__).resolve().parents[2] / "smart_construction_core/data"
        configs = []
        for filename in ("p1_daily_business_form_orchestration_contract_data.xml", "view_orchestration_contract_generated_data.xml",
                         "view_orchestration_form_section_contract_data.xml", "payment_request_form_productization_contract.xml"):
            for record in ET.parse(data / filename).getroot().iter("record"):
                if record.get("model") != "ui.business.config.contract":
                    continue
                fields = {field.get("name"): field for field in record.findall("field")}
                if fields.get("model") is None or fields["model"].text != "payment.request":
                    continue
                payload = ast.literal_eval(fields["contract_json"].get("eval"))
                if not ((payload.get("view_orchestration") or {}).get("views") or {}).get("form"):
                    continue
                configs.append(SimpleNamespace(id=len(configs)+1, name=record.get("id"), version_no=1, contract_json=payload))
        self.assertGreaterEqual(len(configs), 4)
        config_model = _ConfigModel({})
        config_model._effective_view_orchestration_contracts = lambda *a, **kw: configs
        layout = [{"type": "group", "string": "Native business", "children": [{"type": "field", "name": "name"}]}]
        result = orchestrator(_Env({"ui.business.config.contract": config_model})).compose(
            {"layout": layout}, model_name="payment.request", view_type="form", action_id=12, view_id=34)
        self.assertEqual(result["layout"], layout)
        resolved = result["governance"]["view_orchestration"]["form_structure_projection"]
        self.assertEqual(resolved["form_structure_authority"], "native_authority")
        self.assertEqual(resolved["configured_sections"], [])
        self.assertTrue(resolved["field_semantic_roles"])
        self.assertEqual(resolved["resolved_view_id"], 34)
        self.assertEqual(resolved["compatibility_dependencies"], ["legacy_configuration_structure_suppression"])
        self.assertTrue(resolved["structure_diagnostics"])

    def test_semantic_field_policy_cannot_relax_native_restrictions(self):
        from copy import deepcopy
        orchestrator = _load_orchestrator()(_Env())
        for restriction in (True, [["state", "!=", "draft"]]):
            node = {"type": "field", "name": "name", "readonly": restriction,
                    "required": True, "modifiers": {"readonly": restriction},
                    "fieldInfo": {"readonly": True, "required": True}}
            before = deepcopy(node)
            orchestrator._apply_field_display_policy(node, {"readonly": False, "required": False, "help": "Guidance"})
            self.assertEqual(node["readonly"], before["readonly"])
            self.assertEqual(node["required"], before["required"])
            self.assertEqual(node["modifiers"], before["modifiers"])
            self.assertEqual(node["fieldInfo"]["readonly"], True)
            self.assertEqual(node["help"], "Guidance")

    def test_native_layout_resolves_once_and_semantic_overlays_coexist(self):
        orchestrator = _load_orchestrator()
        configs = _ConfigModel({"view_orchestration": {"views": {"form": {
            "composition_mode": "native_semantic_surface",
            "semantic_anchors": [{"role": "summary", "fields": ["name"]}],
        }}}})
        env = _Env({"ui.business.config.contract": configs, "demo.business": _Model()})
        layout = [{"type": "group", "string": "Business", "children": [{"type": "field", "name": "name"}]}]
        result = orchestrator(env).compose({"layout": layout}, model_name="demo.business", view_type="form", action_id=12, view_id=34)
        self.assertEqual(len(configs.calls), 1)
        self.assertEqual(result["layout"], layout)
        resolved = result["governance"]["view_orchestration"]["form_structure_projection"]
        self.assertEqual(resolved["field_semantic_roles"], {"name": "summary"})
        self.assertEqual(resolved["form_structure_authority"], "native_authority")
        provenance = resolved["business_config_contracts"]
        self.assertTrue(provenance)
        for row in provenance:
            self.assertTrue(set(row).issubset({"id", "name", "priority", "view_type", "version_no", "source_kind"}), row)
        self.assertIn("status", result["source_trace"]["view_orchestration"]["business_config_contracts"][0])
        helper = sys.modules["odoo.addons.smart_core.core.form_structure_authority"]
        first = _Config({"view_orchestration": {"views": {"form": {"composition_mode": "native_semantic_surface", "help": "help"}}}})
        second = _Config({"view_orchestration": {"views": {"form": {"semantic_anchors": [{"role": "audit", "fields": ["state"]}]}}}})
        self.assertEqual(helper.diagnose_structure_ownership([first, second], model="demo.business"), [])

    def test_native_sparse_field_policies_do_not_own_structure(self):
        cls = _load_orchestrator()
        helper = sys.modules["odoo.addons.smart_core.core.form_structure_authority"]
        spec = {"composition_mode": "native_semantic_surface", "fields": [
            {"name": "name", "help": "Field guidance", "readonly": True},
        ]}
        config = _Config({"view_orchestration": {"views": {"form": spec}}})
        self.assertEqual(helper.diagnose_structure_ownership([config], model="demo.business"), [])
        env = _Env({"ui.business.config.contract": _ConfigModel(config.contract_json), "demo.business": _Model()})
        layout = [{"type": "group", "string": "Native chapter", "children": [
            {"type": "field", "name": "name"}, {"type": "field", "name": "state"}]}]
        result = cls(env).compose({"layout": layout}, model_name="demo.business", view_type="form", view_id=34)
        nodes = result["layout"][0]["children"]
        self.assertEqual([node["name"] for node in nodes], ["name", "state"])
        self.assertEqual(nodes[0]["help"], "Field guidance")
        self.assertTrue(nodes[0]["readonly"])
        self.assertEqual(result["governance"]["view_orchestration"]["form_structure_projection"]["compatibility_dependencies"], [])
        spec["fields"][0]["sequence"] = 1
        with self.assertRaisesRegex(ValueError, "STRUCTURE_CONFLICT"):
            helper.diagnose_structure_ownership([config], model="demo.business")

    def test_native_structure_conflict_names_entry_config_key_and_node(self):
        _load_orchestrator()
        helper = sys.modules["odoo.addons.smart_core.core.form_structure_authority"]
        native = _Config({"view_orchestration": {"views": {"form": {"composition_mode": "native_semantic_surface"}}}})
        competitor = _Config({"view_orchestration": {"views": {"form": {"sections": [{"key": "competing", "fields": ["name"]}]}}}})
        with self.assertRaises(ValueError) as raised:
            helper.diagnose_structure_ownership([native, competitor], model="demo.business", action_id=12, view_id=34)
        import json
        diagnostic = json.loads(str(raised.exception))[0]
        self.assertEqual(diagnostic["entry"], {"model": "demo.business", "action_id": 12, "view_id": 34})
        self.assertEqual(diagnostic["configuration"]["name"], "demo")
        self.assertEqual(diagnostic["key"], "sections")
        self.assertEqual(diagnostic["node"], "view_orchestration.views.form.sections")

class TestConfiguredNativeTree(unittest.TestCase):
    def setUp(self):
        _load_orchestrator()
        from odoo.addons.smart_core.core.form_configuration_compiler import compile_form_configuration
        self.compile = compile_form_configuration
        self.tree = [{"type": "group", "name": "identity", "native_locator": "/form/group[1]", "occurrence_index": 1,
                      "children": [{"type": "field", "name": name, "native_locator": "/form/group[1]/field[%s]" % i,
                                    "occurrence_index": 1, "source_position": i} for i, name in enumerate(("name", "email"), 1)]}]

    def config(self, patches, identifier=1):
        from types import SimpleNamespace
        return SimpleNamespace(id=identifier, name="view_orchestration:sample:%s" % identifier,
                               contract_json={"view_orchestration": {"context": {"source": "smart_core.lowcode.business_config"},
                                              "views": {"form": {"node_patches": patches}}}},
                               action_id=546, view_id=1431, role_key="business_config_admin", priority=100, version_no=1)

    def patch(self, field=0, **values):
        node = self.tree[0]["children"][field]
        return {"target": node["native_locator"], "expected": {key: node.get(key) for key in ("type", "name", "occurrence_index")}, "set": values}

    def test_label_order_group_and_visibility_preserve_occurrences(self):
        group = self.tree[0]
        patch = {"target": group["native_locator"], "expected": {key: group.get(key) for key in ("type", "name", "occurrence_index")},
                 "order": [node["native_locator"] for node in reversed(group["children"])],
                 "group": {"key": "contact", "label": "Contact", "members": [group["children"][1]["native_locator"]]}}
        out, trace = self.compile(self.tree, [self.config([self.patch(label="Configured"), self.patch(1, visible=False), patch])])
        self.assertEqual(out[0]["children"][0]["name"], "contact")
        self.assertEqual(out[0]["children"][1]["label"], "Configured")
        self.assertTrue(out[0]["children"][0]["children"][0]["invisible"])
        self.assertEqual(out[0]["children"][0]["children"][0]["native_locator"], self.tree[0]["children"][1]["native_locator"])
        self.assertEqual(len(trace), 3)
        self.assertNotIn("label", self.tree[0]["children"][0])

    def test_readonly_cannot_be_relaxed(self):
        self.tree[0]["children"][0]["modifiers"] = {"readonly": "state != 'draft'"}
        with self.assertRaisesRegex(ValueError, "CONFIG_BUSINESS_CONSTRAINT_RELAXED"):
            self.compile(self.tree, [self.config([self.patch(readonly=False)])])

    def test_business_required_cannot_be_hidden(self):
        with self.assertRaisesRegex(ValueError, "CONFIG_REQUIRED_FIELD_HIDDEN"):
            self.compile(self.tree, [self.config([self.patch(visible=False)])], fields_meta={"name": {"required": True}})

    def test_stale_identity_never_falls_back_to_same_name(self):
        patch = self.patch(label="Changed")
        patch["target"] = "/obsolete/name"
        with self.assertRaisesRegex(ValueError, "CONFIG_TARGET_STALE"):
            self.compile(self.tree, [self.config([patch])])

    def test_same_priority_conflict_is_independent_of_database_id_and_order(self):
        configs = [self.config([self.patch(label="A")], 1), self.config([self.patch(label="B")], 99)]
        for rows in (configs, list(reversed(configs))):
            with self.assertRaisesRegex(ValueError, "CONFIG_SAME_PRIORITY_CONFLICT"):
                self.compile(self.tree, rows)

    def test_distinct_properties_coexist(self):
        out, _ = self.compile(self.tree, [self.config([self.patch(label="A")]), self.config([self.patch(readonly=True)], 2)])
        self.assertTrue(out[0]["children"][0]["readonly"])
        self.assertTrue(out[0]["children"][0]["fieldInfo"]["readonly"])
        self.assertTrue(out[0]["children"][0]["modifiers"]["readonly"])
        self.assertEqual(out[0]["children"][0]["label"], "A")

    def test_hidden_native_field_cannot_be_revealed(self):
        self.tree[0]["children"][0]["invisible"] = True
        with self.assertRaisesRegex(ValueError, "CONFIG_VISIBILITY_CONSTRAINT_RELAXED"):
            self.compile(self.tree, [self.config([self.patch(visible=True)])])

    def group_patch(self, **changes):
        group = self.tree[0]
        return {"target": group["native_locator"], "expected": {key: group.get(key) for key in
                ("type", "name", "occurrence_index")}, **changes}

    def test_parent_hide_child_required_rejected_in_both_orders(self):
        patches = [self.group_patch(set={"visible": False}), self.patch(required=True)]
        errors = []
        for order in (patches, list(reversed(patches))):
            with self.assertRaisesRegex(ValueError, "CONFIG_REQUIRED_FIELD_HIDDEN") as error:
                self.compile(self.tree, [self.config(order)])
            errors.append(str(error.exception))
        self.assertEqual(errors[0], errors[1])

    def test_cross_configuration_final_constraints_are_order_independent(self):
        configs = [self.config([self.group_patch(set={"visible": False})], 1),
                   self.config([self.patch(required=True)], 2)]
        for order in (configs, list(reversed(configs))):
            with self.assertRaisesRegex(ValueError, "CONFIG_REQUIRED_FIELD_HIDDEN"):
                self.compile(self.tree, order)
        override = self.config([self.patch(required=False)], 3)
        override.priority = 200
        a, _ = self.compile(self.tree, configs + [override])
        b, _ = self.compile(self.tree, [override] + list(reversed(configs)))
        self.assertEqual(a, b)
        self.assertFalse(a[0]["children"][0]["required"])

    def test_hidden_override_is_checked_only_after_merge(self):
        low = self.config([self.group_patch(set={"visible": False}), self.patch(required=True)])
        high = self.config([self.group_patch(set={"visible": True})], 2)
        high.priority = 200
        result, _ = self.compile(self.tree, [high, low])
        self.assertTrue(result[0]["visible"])
        self.assertTrue(result[0]["children"][0]["required"])

    def test_grouping_cannot_hide_required_constraints(self):
        from itertools import permutations
        patches = [self.group_patch(set={"visible": False}, group={"key": "new", "members": [self.tree[0]["children"][0]["native_locator"]]}),
                   self.patch(required=True), self.patch(1, label="Unrelated")]
        for order in permutations(patches):
            with self.assertRaisesRegex(ValueError, "CONFIG_REQUIRED_FIELD_HIDDEN"):
                self.compile(self.tree, [self.config(list(order))])

    def test_native_hidden_required_is_preserved_but_not_tightened(self):
        self.tree[0]["modifiers"] = {"invisible": "state != 'draft'"}
        self.tree[0]["children"][0]["required"] = True
        result, _ = self.compile(self.tree, [self.config([self.patch(1, label="Allowed")])])
        self.assertEqual(result[0]["children"][1]["label"], "Allowed")
        with self.assertRaisesRegex(ValueError, "CONFIG_REQUIRED_FIELD_HIDDEN"):
            self.compile(self.tree, [self.config([self.group_patch(set={"visible": False})])])
        with self.assertRaisesRegex(ValueError, "CONFIG_REQUIRED_FIELD_HIDDEN"):
            self.compile(self.tree, [self.config([self.patch(1, required=True)])])

    def test_legal_combinations_are_invariant_under_unrelated_patch_order(self):
        from itertools import permutations
        patches = [self.group_patch(group={"key": "new", "members": [self.tree[0]["children"][0]["native_locator"]]}),
                   self.patch(required=True), self.patch(1, visible=False)]
        outputs = [self.compile(self.tree, [self.config(list(order))]) for order in permutations(patches)]
        self.assertTrue(all(result == outputs[0] for result in outputs))

    def test_group_members_follow_final_order_not_selection_order(self):
        first, second = [node["native_locator"] for node in self.tree[0]["children"]]
        patch = self.group_patch(order=[second, first], group={"key": "new", "members": [first, second]})
        result, _ = self.compile(self.tree, [self.config([patch])])
        self.assertEqual([node["native_locator"] for node in result[0]["children"][0]["children"]], [second, first])

    def test_equivalent_boolean_required_preserves_native_baseline(self):
        self.tree[0]["invisible"] = "1"
        self.tree[0]["children"][0]["required"] = "1"
        result, _ = self.compile(self.tree, [self.config([self.patch(required=True)])])
        self.assertTrue(result[0]["children"][0]["required"])

    def test_same_group_key_in_distinct_parents_has_distinct_navigation_anchors(self):
        from copy import deepcopy
        other = deepcopy(self.tree[0])
        other["native_locator"] = "/form/group[2]"
        other["occurrence_index"] = 2
        for child in other["children"]:
            child["native_locator"] = child["native_locator"].replace("group[1]", "group[2]")
        tree = self.tree + [other]
        patches = [{"target": group["native_locator"], "expected": {key: group.get(key) for key in
                    ("type", "name", "occurrence_index")}, "group": {"key": "designer", "members": [group["children"][0]["native_locator"]]}}
                   for group in tree]
        result, _ = self.compile(tree, [self.config(patches)])
        anchors = [group["children"][0]["attributes"]["data-sc-anchor"] for group in result]
        self.assertEqual(len(set(anchors)), 2)


if __name__ == "__main__":
    unittest.main()
