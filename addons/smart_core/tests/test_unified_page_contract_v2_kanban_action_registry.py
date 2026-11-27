# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
import importlib.util
import sys
import types
import unittest
from pathlib import Path


CORE_DIR = Path(__file__).resolve().parents[1] / "core"
sys.path.insert(0, str(CORE_DIR.parent))
from core.contract_runtime import semantic_resolver  # noqa: E402


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

    def test_kanban_surface_excludes_form_header_action_rules(self):
        source = _kanban_source()
        source["views"]["form"] = {
            "header_buttons": [{
                "key": "form_only_action",
                "name": "form_only_action",
                "label": "仅表单动作",
                "intent": "object_method",
                "native_identity": {
                    "authoritative": True,
                    "name": "form_only_action",
                    "native_locator": "/form[1]/header[1]/button[1]",
                    "occurrence_index": 1,
                    "type": "object",
                },
            }],
        }
        source["views"]["kanban"]["toolbar"] = {
            "header": [{
                "key": "kanban_toolbar_action",
                "name": "kanban_toolbar_action",
                "label": "看板动作",
                "intent": "open_scene",
                "target": {"scene_key": "project.project"},
            }],
        }
        source["views"]["kanban"]["row_actions"] = [{
            "key": "kanban_row_action",
            "name": "kanban_row_action",
            "kind": "object",
            "payload": {"method": "kanban_row_action"},
        }]
        source["views"]["tree"] = {
            "row_actions": [{
                "key": "tree_only_row_action",
                "name": "tree_only_row_action",
                "kind": "object",
                "payload": {"method": "tree_only_row_action"},
            }],
        }

        contract = self.assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.kanban.form-actions-excluded",
        )

        actions = (contract.get("actionContract") or {}).get("actionRuleList") or []
        keys = [row.get("actionKey") for row in actions]
        self.assertIn("kanban_toolbar_action", keys)
        self.assertIn("kanban_row_action", keys)
        self.assertNotIn("form_only_action", keys)
        self.assertNotIn("tree_only_row_action", keys)

    def test_active_tree_surface_excludes_kanban_toolbar_actions(self):
        source = _kanban_source()
        source["view_type"] = "tree"
        source["views"]["tree"] = {
            "toolbar": {
                "header": [{
                    "key": "tree_toolbar_action",
                    "name": "tree_toolbar_action",
                    "label": "树视图动作",
                    "intent": "open_scene",
                    "target": {"scene_key": "project.project"},
                }],
            },
            "row_actions": [],
        }
        source["views"]["kanban"] = {
            "toolbar": {
                "header": [{
                    "key": "kanban_toolbar_action",
                    "name": "kanban_toolbar_action",
                    "label": "看板动作",
                    "intent": "open_scene",
                    "target": {"scene_key": "project.project"},
                }],
            },
            "row_actions": [],
        }

        contract = self.assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.tree.kanban-actions-excluded",
        )

        keys = [
            row.get("actionKey")
            for row in ((contract.get("actionContract") or {}).get("actionRuleList") or [])
        ]
        self.assertIn("tree_toolbar_action", keys)
        self.assertNotIn("kanban_toolbar_action", keys)

    def test_requested_view_type_must_match_the_delivered_contract(self):
        contract = {
            "pageInfo": {"viewType": "list", "model": "project.project"},
            "nativeActionContract": {"viewSet": {"activeViewType": "tree"}},
        }
        self.assertTrue(self.assembler.requested_view_type_matches(contract, "tree"))
        self.assertTrue(self.assembler.requested_view_type_matches(contract, "list"))
        self.assertFalse(self.assembler.requested_view_type_matches(contract, "kanban"))

    def test_model_only_page_does_not_negotiate_an_action_view_set(self):
        contract = {"pageInfo": {"viewType": "form", "model": "project.project"}}
        self.assertTrue(self.assembler.requested_view_type_matches(contract, "form"))
        self.assembler._validate_action_view_scope(
            {
                **contract,
                "actionContract": {"actionRuleList": [{
                    "actionKey": "model_action",
                    "sourceChannel": "native_tree_row_action",
                    "nativeIdentity": {"model": "project.project", "viewType": "tree"},
                }]},
            },
            action_bound=False,
        )

    def test_requested_view_renderer_must_be_supported(self):
        contract = {
            "nativeActionContract": {
                "viewSet": {
                    "activeViewType": "kanban",
                    "orderedViews": [{
                        "viewType": "kanban",
                        "rendererStatus": "unsupported",
                    }],
                },
            },
        }
        self.assertFalse(self.assembler.requested_view_renderer_supported(contract))
        contract["nativeActionContract"]["viewSet"]["orderedViews"][0]["rendererStatus"] = "ready"
        self.assertTrue(self.assembler.requested_view_renderer_supported(contract))

    def test_assembler_rejects_action_sources_from_other_views(self):
        for source_channel in ("native_form_header", "native_tree_row_action"):
            with self.subTest(source_channel=source_channel):
                contract = {
                    "pageInfo": {"model": "project.project", "viewType": "kanban"},
                    "actionContract": {"actionRuleList": [{
                        "actionKey": "foreign_action",
                        "sourceChannel": source_channel,
                        "nativeIdentity": {"model": "project.project", "viewType": "kanban"},
                    }]},
                }
                with self.assertRaisesRegex(ValueError, "ACTION_VIEW_SCOPE_MISMATCH"):
                    self.assembler._validate_action_view_scope(contract)

    def test_assembler_rejects_native_identity_from_another_view(self):
        contract = {
            "pageInfo": {"model": "project.project", "viewType": "kanban"},
            "actionContract": {"actionRuleList": [{
                "actionKey": "foreign_identity",
                "sourceChannel": "contract_action",
                "nativeIdentity": {"model": "project.project", "viewType": "form"},
            }]},
        }
        with self.assertRaisesRegex(ValueError, "ACTION_VIEW_SCOPE_MISMATCH"):
            self.assembler._validate_action_view_scope(contract)

    def test_business_value_semantics_follow_field_metadata(self):
        cases = (
            ({"type": "monetary"}, "number", "money"),
            ({"type": "many2one", "relation": "res.currency"}, "select", "relation"),
            ({"type": "float"}, "percentage", "percentage"),
            ({"type": "selection"}, "statusbar", "status"),
            ({"type": "selection"}, "badge", "status"),
            ({"type": "float"}, "float_time", "duration"),
            ({"type": "many2one", "relation": "res.users"}, "select", "relation"),
            ({"type": "many2one", "relation": "res.company"}, "select", "relation"),
            ({"type": "many2one", "relation": "x.related"}, "select", "relation"),
            ({"type": "many2many", "relation": "x.related"}, "table", "relation_collection"),
            ({"type": "many2many", "relation": "res.users"}, "table", "relation_collection"),
            ({"type": "many2many", "relation": "res.users"}, "many2many_tags", "tag_collection"),
            ({"type": "one2many", "relation": "x.line"}, "table", "detail_collection"),
        )
        for descriptor, widget_type, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(semantic_resolver.semantic_of(widget_type, descriptor), expected)
                widget = self.assembler._field_widget(
                    {"name": "value", "string": "Value", **descriptor, "widget": widget_type},
                    layout_type="form",
                )
                self.assertEqual(widget["semanticType"], expected)
                self.assertNotIn("componentKey", widget)

    def test_business_value_semantics_do_not_guess_from_field_names(self):
        self.assertEqual(
            semantic_resolver.semantic_of("number", {"name": "payment_percentage", "type": "float"}),
            "number",
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
                self.assertEqual(widget["semanticType"], "readable_value")
                self.assertNotIn("componentKey", widget)

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
                self.assertEqual(widget["semanticType"], "reference")
                self.assertNotIn("componentKey", widget)
                config = widget["componentConfig"]
                # The declared type and the target-model authority survive; the
                # widget is not disguised as text and not smuggled as a string.
                self.assertEqual(config["fieldType"], "many2one_reference")
                self.assertEqual(config["model_field"], "sc_source_model")
                self.assertEqual(config["referenceModelField"], "sc_source_model")

    def test_strict_polymorphic_descriptor_preserves_native_model_pointer(self):
        widget = self.assembler._field_widget({
            "name": "source_id", "string": "Source", "type": "many2one_reference",
            "model_field": "source_model",
        }, layout_type="form")
        strict = self.assembler._strict_field_descriptor(widget)
        self.assertEqual(strict["referenceModelField"], "source_model")
        self.assertEqual(strict["fieldType"], "many2one_reference")
        self.assertNotIn("relation", strict)
        for invalid in (None, "", " ", 42, "source.model", "source_id"):
            with self.subTest(invalid=invalid):
                widget["componentConfig"]["referenceModelField"] = invalid
                with self.assertRaisesRegex(ValueError, "REFERENCE_MODEL_FIELD_INVALID"):
                    self.assembler._strict_field_descriptor(widget)
        # Legacy metadata is not a second authority for the final descriptor.
        widget["componentConfig"].pop("referenceModelField")
        with self.assertRaisesRegex(ValueError, "REFERENCE_MODEL_FIELD_INVALID"):
            self.assembler._strict_field_descriptor(widget)

    def test_strict_reference_and_fixed_relations_keep_distinct_semantics(self):
        for field_type, relation in (("reference", None), ("many2one", "res.partner"),
                                     ("one2many", "res.partner"), ("many2many", "res.partner")):
            widget = self.assembler._field_widget({
                "name": "target", "string": "Target", "type": field_type,
                **({"relation": relation} if relation else {}),
            }, layout_type="form")
            strict = self.assembler._strict_field_descriptor(widget)
            self.assertEqual(strict["fieldType"], field_type)
            self.assertEqual(strict.get("relation"), relation)
            self.assertNotIn("referenceModelField", strict)

    def test_reference_semantic_never_binds_an_editor_component(self):
        for field_type in ("many2one_reference", "reference"):
            for widget_type in ("input", field_type, "select", "number"):
                with self.subTest(field_type=field_type, widget_type=widget_type):
                    self.assertEqual(
                        semantic_resolver.semantic_of(widget_type, {"name": "src", "type": field_type}),
                        "reference",
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
                "widget_source": "native_explicit",
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
                "widget_source": "native_explicit",
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

    def test_unknown_explicit_widget_is_not_allowed_to_become_a_text_input(self):
        widget = self.assembler._field_widget(
            {
                "name": "future_editor",
                "string": "Future editor",
                "type": "char",
                "widget": "future_editor",
                "widget_source": "native_explicit",
            },
            layout_type="form",
        )

        self.assertEqual(widget["semanticType"], "unsupported_native_widget")
        self.assertNotIn("componentKey", widget)
        self.assertEqual(widget["componentConfig"]["nativeWidget"], "future_editor")
        self.assertEqual(
            widget["componentConfig"]["widgetProvenance"],
            {
                "nativeWidget": "future_editor",
                "widgetSource": "native_explicit",
                "declaredWidget": "future_editor",
                "derivedWidgetType": "",
                "resolvedWidgetType": "input",
                "resolutionStatus": "unsupported",
                "reasonCode": "NATIVE_WIDGET_UNRECOGNIZED",
            },
        )

    def test_form_node_assembly_does_not_promote_canonical_widget_to_native(self):
        cases = (
            {
                "label": "model-derived",
                "node": {
                    "type": "field",
                    "name": "name",
                    "widget": "input",
                    "fieldInfo": {
                        "type": "char",
                        "widget": "input",
                        "widget_source": "model_metadata_derived",
                    },
                },
                "source": "model_metadata_derived",
                "native": "",
                "node_widget": "input",
                "semantic": "text",
                "status": "not_applicable",
            },
            {
                "label": "unmarked-compatibility",
                "node": {
                    "type": "field",
                    "name": "name",
                    "widget": "input",
                    "fieldInfo": {"type": "char", "widget": "input"},
                },
                "source": "compatibility_default",
                "native": "",
                "node_widget": "input",
                "semantic": "text",
                "status": "not_applicable",
            },
            {
                "label": "unknown-explicit",
                "node": {
                    "type": "field",
                    "name": "name",
                    "widget": "input",
                    "attributes": {"widget": "future_editor"},
                    "fieldInfo": {
                        "type": "char",
                        "widget": "future_editor",
                        "widget_source": "native_explicit",
                    },
                },
                "source": "native_explicit",
                "native": "future_editor",
                "node_widget": "future_editor",
                "semantic": "unsupported_native_widget",
                "status": "unsupported",
            },
            {
                "label": "supported-explicit",
                "node": {
                    "type": "field",
                    "name": "date_start",
                    "widget": "date",
                    "attributes": {"widget": "daterange"},
                    "fieldInfo": {
                        "type": "date",
                        "widget": "daterange",
                        "widget_source": "native_explicit",
                    },
                },
                "source": "native_explicit",
                "native": "daterange",
                "node_widget": "daterange",
                "semantic": "date",
                "status": "ready",
            },
        )
        for case in cases:
            with self.subTest(case=case["label"]):
                node = self.assembler._native_field_node(
                    case["node"],
                    {},
                    layout_type="form",
                )
                config = node["componentConfig"]
                provenance = config["widgetProvenance"]
                self.assertEqual(provenance["widgetSource"], case["source"])
                self.assertEqual(provenance["nativeWidget"], case["native"])
                self.assertEqual(provenance["resolutionStatus"], case["status"])
                self.assertEqual(config.get("nativeWidget", ""), case["native"])
                self.assertEqual(node["semanticType"], case["semantic"])
                self.assertNotIn("componentKey", node)
                self.assertEqual(node["fieldInfo"]["widget"], case["node_widget"])
                formal_source = self.assembler._field_source_with_node_info(
                    node,
                    {},
                    fallback_name=case["node"]["name"],
                )
                formal_widget = self.assembler._field_widget(formal_source, layout_type="form")
                formal_provenance = formal_widget["componentConfig"]["widgetProvenance"]
                self.assertEqual(formal_provenance["widgetSource"], case["source"])
                self.assertEqual(formal_provenance["nativeWidget"], case["native"])
                self.assertEqual(formal_widget["semanticType"], case["semantic"])
                self.assertNotIn("componentKey", formal_widget)

    def test_form_node_assembly_preserves_native_domain_in_existing_descriptor(self):
        raw = "[('project_id', '=', project_id)]"
        context = "{'default_project_id': project_id}"
        options = "{'no_create': True}"
        node = self.assembler._native_field_node(
            {
                "type": "field",
                "name": "contract_id",
                "attributes": {
                    "domain": raw,
                    "context": context,
                    "options": options,
                },
                "fieldInfo": {
                    "type": "many2one",
                    "relation": "x.contract",
                    "domain": raw,
                    "context": context,
                    "widget_options": {"no_create": True},
                },
            },
            {},
            layout_type="form",
        )
        formal_source = self.assembler._field_source_with_node_info(
            node,
            {},
            fallback_name="contract_id",
        )
        formal = self.assembler._field_widget(formal_source, layout_type="form")
        self.assertEqual(formal["fieldDescriptor"]["domain"], raw)
        self.assertEqual(
            formal["fieldDescriptor"]["domain_expression"]["dependencies"],
            ["project_id"],
        )
        self.assertEqual(formal["fieldDescriptor"]["context"], context)
        self.assertEqual(formal["fieldDescriptor"]["widget_options"], {"no_create": True})
        self.assertNotIn("domainProjection", formal["componentConfig"])

        unsupported_raw = "[('x', '=', unsupported_call())]"
        unsupported = self.assembler._field_widget(
            {
                "name": "contract_id",
                "type": "many2one",
                "relation": "x.contract",
                "domain": unsupported_raw,
            },
            layout_type="form",
        )
        self.assertEqual(unsupported["fieldDescriptor"]["domain_expression"]["kind"], "unsupported")

    def test_embedded_native_widgets_publish_node_components_identity_and_field_isolation(self):
        view_identity = {
            "schemaVersion": "1.0.0",
            "model": "project.project",
            "viewType": "form",
            "viewId": 91,
            "viewXmlId": "smart_core.native_embedded_widget_form",
            "viewContentHash": "a" * 64,
            "viewStructureKey": "struct.v1." + "b" * 24,
            "crossEnvironmentStable": True,
            "sourceAuthority": {
                "kind": "ir.ui.view",
                "projectionOnly": True,
                "noBusinessFactAuthority": True,
            },
        }
        contract = self.assembler.assemble_unified_page_contract_v2(
            {
                "model": "project.project",
                "view_type": "form",
                "fields": {},
                "views": {
                    "form": {
                        "viewIdentity": view_identity,
                        "layout": [
                            {
                                "type": "widget",
                                "name": "web_ribbon",
                                "widget": "web_ribbon",
                                "label": "Paid",
                                "native_locator": "/form[1]/widget[1]",
                                "occurrence_index": 1,
                                "source_position": 1,
                                "attributes": {
                                    "name": "web_ribbon",
                                    "title": "Paid",
                                    "options": "{'bg_color': 'text-bg-success'}",
                                },
                                "options_raw": "{'bg_color': 'text-bg-success'}",
                                "options": {"bg_color": "text-bg-success"},
                                "options_resolution": "parsed",
                                "children": [],
                            },
                            {
                                "type": "widget",
                                "name": "web_ribbon",
                                "widget": "web_ribbon",
                                "label": "Draft",
                                "native_locator": "/form[1]/widget[2]",
                                "occurrence_index": 2,
                                "source_position": 2,
                                "attributes": {"name": "web_ribbon", "title": "Draft", "options": "False"},
                                "options_raw": "False",
                                "options": False,
                                "options_resolution": "parsed",
                                "children": [],
                            },
                            {
                                "type": "widget",
                                "name": "sc_stage_requirements",
                                "widget": "sc_stage_requirements",
                                "label": "Stages",
                                "native_locator": "/form[1]/widget[3]",
                                "occurrence_index": 1,
                                "source_position": 3,
                                "attributes": {
                                    "name": "sc_stage_requirements",
                                    "options": "{'limit': 3}",
                                },
                                "options_raw": "{'limit': 3}",
                                "options": {"limit": 3},
                                "options_resolution": "parsed",
                                "children": [],
                            },
                        ],
                    }
                },
            },
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.form.embedded.native.widgets",
        )

        nodes = contract["layoutContract"]["containerTree"]
        self.assertEqual([node["semanticType"] for node in nodes], [
            "display_ribbon",
            "display_ribbon",
            "unsupported_native_node",
        ])
        self.assertEqual([node["nativeIdentity"]["kind"] for node in nodes], ["widget", "widget", "widget"])
        self.assertNotEqual(nodes[0]["nativeIdentity"]["occurrenceKey"], nodes[1]["nativeIdentity"]["occurrenceKey"])
        self.assertEqual(nodes[0]["componentConfig"]["options"], {"bg_color": "text-bg-success"})
        self.assertIs(nodes[1]["componentConfig"]["options"], False)
        self.assertEqual(
            nodes[2]["componentConfig"]["reasonCode"],
            "NATIVE_VIEW_WIDGET_PAYLOAD_UNAVAILABLE",
        )
        self.assertEqual(nodes[2]["componentConfig"]["nativeWidget"], "sc_stage_requirements")
        self.assertTrue(all("fieldCode" not in node and "fieldDescriptor" not in node for node in nodes))
        self.assertNotIn("componentRegistry", contract["layoutContract"])
        self.assertTrue(all("componentKey" not in node for node in nodes))

        conflict_name = {
            "model": "project.project",
            "view_type": "form",
            "fields": {},
            "views": {
                "form": {
                    "viewIdentity": view_identity,
                    "layout": [{
                        "type": "widget",
                        "name": "web_ribbon",
                        "widget": "web_ribbon",
                        "attributes": {"name": "sc_next_actions"},
                        "native_locator": "/form[1]/widget[1]",
                        "occurrence_index": 1,
                        "children": [],
                    }],
                }
            },
        }
        with self.assertRaisesRegex(ValueError, "name conflicts"):
            self.assembler.assemble_unified_page_contract_v2(
                conflict_name,
                source_type="ui.contract",
                client_type="web_pc",
                request_id="test.form.embedded.widget.name_conflict",
            )

        conflict_options = copy.deepcopy(conflict_name)
        conflict_options["views"]["form"]["layout"][0].update({
            "name": "sc_stage_requirements",
            "widget": "sc_stage_requirements",
            "attributes": {"name": "sc_stage_requirements", "options": "{'limit': 3}"},
            "options_raw": "{'limit': 4}",
            "options": {"limit": 4},
            "options_resolution": "parsed",
        })
        with self.assertRaisesRegex(ValueError, "options conflict"):
            self.assembler.assemble_unified_page_contract_v2(
                conflict_options,
                source_type="ui.contract",
                client_type="web_pc",
                request_id="test.form.embedded.widget.options_conflict",
            )

        missing_identity = copy.deepcopy(conflict_name)
        missing_node = missing_identity["views"]["form"]["layout"][0]
        missing_node.update({
            "name": "web_ribbon",
            "widget": "web_ribbon",
            "attributes": {"name": "web_ribbon"},
            "native_locator": "",
            "occurrence_index": 0,
        })
        missing_contract = self.assembler.assemble_unified_page_contract_v2(
            missing_identity,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.form.embedded.widget.missing_identity",
        )
        missing_widget = missing_contract["layoutContract"]["containerTree"][0]
        self.assertEqual(missing_widget["semanticType"], "unsupported_native_node")
        self.assertEqual(missing_widget["componentConfig"]["widgetStatus"], "unsupported")
        self.assertEqual(
            missing_widget["componentConfig"]["reasonCode"],
            "NATIVE_VIEW_WIDGET_IDENTITY_MISSING",
        )

    def test_widget_projection_does_not_shadow_sibling_field_status(self):
        container_status = []
        widget_status = []
        nodes = self.assembler._normalize_native_layout_nodes(
            [
                {
                    "type": "widget",
                    "name": "web_ribbon",
                    "widget": "web_ribbon",
                    "attributes": {"name": "web_ribbon", "title": "Paid"},
                    "native_locator": "/form[1]/widget[1]",
                    "occurrence_index": 1,
                    "children": [],
                },
                {
                    "type": "field",
                    "name": "name",
                    "label": "Name",
                    "children": [],
                    "widgetList": [],
                },
            ],
            {"name": {"name": "name", "type": "char", "string": "Name"}},
            layout_type="form",
            container_status=container_status,
            widget_status=widget_status,
        )

        self.assertEqual(nodes[0]["componentConfig"]["widgetStatus"], "ready")
        self.assertEqual(nodes[1]["type"], "field")
        self.assertEqual(len(widget_status), 1)
        self.assertEqual(nodes[0]["semanticType"], "display_ribbon")

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

    def test_embedded_widget_payload_projection_is_generic_and_fail_closed(self):
        occurrence = "occ.v1.aaaaaaaaaaaaaaaaaaaaaaaa"

        def contract():
            return {
                "pageInfo": {"model": "project.project", "viewType": "form"},
                "layoutContract": {
                    "containerTree": [{
                        "containerId": "widget.stage",
                        "type": "widget",
                        "containerType": "widget",
                        "name": "sc_stage_requirements",
                        "widget": "sc_stage_requirements",
                        "semanticType": "action_list",
                        "componentConfig": {
                            "nativeWidget": "sc_stage_requirements",
                            "widgetStatus": "ready",
                            "identityComplete": True,
                            "optionsResolution": "parsed",
                            "options": {"limit": 3},
                        },
                        "nativeIdentity": {"occurrenceKey": occurrence},
                        "nativeLocator": "/form[1]/widget[1]",
                        "occurrenceIndex": 1,
                        "children": [],
                    }],
                },
                "statusContract": {
                    "containerStatus": [{"containerId": "widget.stage", "visible": True, "disabled": False}],
                },
                "dataContract": {"mainData": {"id": 7}},
            }

        hooks = types.ModuleType("odoo.addons.smart_core.utils.extension_hooks")

        def provider(_env, hook_name, _hook_env, request):
            self.assertEqual(hook_name, "smart_core_native_view_widget_payload")
            self.assertEqual(request["recordId"], 7)
            return {
                "widgets": {
                    occurrence: {
                        "payloadSchema": "action_list.v1",
                        "payload": {
                            "title": "阶段要求",
                            "emptyText": "暂无要求",
                            "items": [{
                                "id": "stage-1",
                                "title": "项目地点",
                                "description": "完成即可继续",
                                "state": "required",
                                "tone": "warning",
                                "actionType": "act_window_xmlid",
                                "actionRef": "smart_core.action_missing",
                                "actionLabel": "去处理",
                                "actionPayload": {"project_id": 7},
                                "enabled": True,
                            }],
                        },
                        "sourceAuthority": {
                            "kind": "smart_construction_core_native_view_widget_payload",
                            "module": "smart_construction_core",
                            "projectionOnly": False,
                            "noBusinessFactAuthority": False,
                        },
                    },
                },
            }

        hooks.call_extension_hook_first = provider
        previous = sys.modules.get("odoo.addons.smart_core.utils.extension_hooks")
        sys.modules["odoo.addons.smart_core.utils.extension_hooks"] = hooks
        try:
            projected = contract()
            self.assembler._project_native_view_widget_payloads(projected, object())
            node = projected["layoutContract"]["containerTree"][0]
            self.assertEqual(node["componentConfig"]["payloadSchema"], "action_list.v1")
            self.assertEqual(node["componentConfig"]["payload"]["items"][0]["title"], "项目地点")
            self.assertFalse(projected["statusContract"]["containerStatus"][0]["disabled"])

            missing = contract()
            hooks.call_extension_hook_first = lambda *_args, **_kwargs: {"widgets": {}}
            self.assembler._project_native_view_widget_payloads(missing, object())
            node = missing["layoutContract"]["containerTree"][0]
            self.assertEqual(node["semanticType"], "unsupported_native_node")
            self.assertEqual(
                node["componentConfig"]["reasonCode"],
                "NATIVE_VIEW_WIDGET_PAYLOAD_UNAVAILABLE",
            )
            self.assertTrue(missing["statusContract"]["containerStatus"][0]["disabled"])
        finally:
            if previous is None:
                sys.modules.pop("odoo.addons.smart_core.utils.extension_hooks", None)
            else:
                sys.modules["odoo.addons.smart_core.utils.extension_hooks"] = previous


if __name__ == "__main__":
    unittest.main()
