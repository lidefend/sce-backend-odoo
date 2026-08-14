# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


CORE_DIR = Path(__file__).resolve().parents[1] / "core"


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class _FixtureElement:
    def __init__(self, element, parent=None):
        self._element = element
        self._parent = parent
        self.tag = element.tag
        self.attrib = element.attrib
        self.text = element.text
        self.tail = element.tail

    def __iter__(self):
        return iter([_FixtureElement(child, self) for child in self._element])

    def get(self, key, default=None):
        return self._element.get(key, default)

    def getparent(self):
        return self._parent

    def xpath(self, expr):
        if "contains(" in expr:
            return []
        if expr == ".//header//button":
            return [
                _FixtureElement(button, self)
                for header in self._element.iter("header")
                for button in header.iter("button")
            ]
        descendant = expr.startswith(".//")
        direct = expr.startswith("./") and not descendant
        query = expr[3:] if descendant else expr[2:] if direct else expr
        if "/" in query or " and " in query:
            return []
        attr_name = ""
        attr_value = None
        tag = query
        if "[@" in query and query.endswith("]"):
            tag, predicate = query[:-1].split("[@", 1)
            if "=" in predicate:
                attr_name, raw_value = predicate.split("=", 1)
                attr_value = raw_value.strip().strip("'\"")
            else:
                attr_name = predicate
        candidates = list(self._element) if direct else list(self._element.iter())
        rows = []
        for candidate in candidates:
            if candidate is self._element:
                continue
            if tag not in ("*", candidate.tag):
                continue
            if attr_name and candidate.get(attr_name) is None:
                continue
            if attr_value is not None and candidate.get(attr_name) != attr_value:
                continue
            rows.append(_FixtureElement(candidate, self))
        return rows


def _install_lxml_fixture_shim():
    if "lxml" in sys.modules:
        return
    etree = types.SimpleNamespace(
        fromstring=lambda raw: _FixtureElement(ET.fromstring(raw.decode("utf-8") if isinstance(raw, bytes) else raw)),
        tostring=lambda node, encoding="unicode": ET.tostring(node._element, encoding=encoding),
    )
    lxml_module = types.ModuleType("lxml")
    lxml_module.etree = etree
    sys.modules["lxml"] = lxml_module
    sys.modules["lxml.etree"] = etree


sys.modules.setdefault("odoo", types.ModuleType("odoo"))
sys.modules.setdefault("odoo.addons", types.ModuleType("odoo.addons"))
smart_core_pkg = sys.modules.setdefault("odoo.addons.smart_core", types.ModuleType("odoo.addons.smart_core"))
smart_core_pkg.__path__ = [str(CORE_DIR.parent)]
core_pkg = sys.modules.setdefault("odoo.addons.smart_core.core", types.ModuleType("odoo.addons.smart_core.core"))
core_pkg.__path__ = [str(CORE_DIR)]
smart_core_pkg.core = core_pkg
odoo_pkg = sys.modules["odoo"]
odoo_pkg._ = lambda value: value
_install_lxml_fixture_shim()
utils_pkg = sys.modules.setdefault("odoo.addons.smart_core.utils", types.ModuleType("odoo.addons.smart_core.utils"))
utils_pkg.__path__ = [str(CORE_DIR.parent / "utils")]
_load_module(
    "odoo.addons.smart_core.utils.native_modifier",
    CORE_DIR.parent / "utils" / "native_modifier.py",
)
tree_form_parser = _load_module(
    "smart_core_tree_form_fixture_parser",
    CORE_DIR.parent / "app_config_engine" / "services" / "view_Parser" / "parsers Tree Form.py",
)

assembler = _load_module(
    "odoo.addons.smart_core.core.unified_page_contract_v2_assembler",
    CORE_DIR / "unified_page_contract_v2_assembler.py",
)
client = _load_module(
    "odoo.addons.smart_core.core.unified_page_contract_v2_client",
    CORE_DIR / "unified_page_contract_v2_client.py",
)


class _FixtureRelationModel:
    def sudo(self):
        return self

    def fields_get(self):
        return {"display_name": {"name": "display_name", "type": "char", "string": "Name"}}


class _NativeTreeFormFixtureParser(tree_form_parser._TreeFormParserMixin):
    env = {"res.groups": _FixtureRelationModel()}

    def _lossless_parse_xml(self, _xml_content):
        # The production parser prefers the DOM result.  The lossless branch is
        # an independent fallback and is not needed by these fixture-chain tests.
        return {}


def _native_view_fixture_arch(relative_path: str, record_id: str) -> str:
    path = CORE_DIR.parents[2] / relative_path
    root = ET.parse(path).getroot()
    record = root.find(f".//record[@id='{record_id}']")
    if record is None:
        raise AssertionError(f"missing native view fixture record: {record_id}")
    arch = record.find("./field[@name='arch']")
    if arch is None or not list(arch):
        raise AssertionError(f"missing native arch fixture: {record_id}")
    return ET.tostring(list(arch)[0], encoding="unicode")


class TestUnifiedPageContractV2MobileCompact(unittest.TestCase):
    def test_complex_view_types_remain_explicit_in_v2_contract(self):
        for view_type in ("pivot", "graph", "calendar", "gantt", "activity", "dashboard"):
            with self.subTest(view_type=view_type):
                contract = assembler.assemble_unified_page_contract_v2(
                    {"model": "x.report", "view_type": view_type, "fields": {}},
                    source_type="ui.contract",
                    client_type="web_pc",
                    request_id=f"test.complex.{view_type}",
                )
                self.assertEqual(contract["pageInfo"]["viewType"], view_type)
                self.assertEqual(contract["pageInfo"]["layoutType"], view_type)
                self.assertEqual(contract["layoutContract"]["layoutType"], view_type)

    def test_mobile_compact_preserves_create_business_context_outside_compat(self):
        source = {
            "model": "project.project",
            "view_type": "form",
            "head": {
                "render_profile": "create",
                "context": {
                    "default_manager_id": 43,
                    "default_user_id": 43,
                    "default_phase_key": "initiation",
                    "sc_return_to_overview": 1,
                },
            },
            "fields": {
                "name": {"name": "name", "type": "char"},
                "manager_id": {"name": "manager_id", "type": "many2one"},
                "user_id": {"name": "user_id", "type": "many2one"},
                "phase_key": {"name": "phase_key", "type": "selection"},
            },
            "context_raw": "{'default_manager_id': uid, 'default_phase_key': 'initiation'}",
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="harmony_h5",
            request_id="test.mobile.compact.create",
        )
        trimmed = client.trim_unified_page_contract_v2(
            full,
            client_type="harmony_h5",
            delivery_profile="mobile_compact",
        )

        data_contract = trimmed["dataContract"]
        source_context = data_contract["dataMeta"]["sourceContext"]
        self.assertEqual(source_context["renderProfile"], "create")
        self.assertEqual(source_context["context"]["default_phase_key"], "initiation")
        self.assertEqual(data_contract["mainData"]["manager_id"], 43)
        self.assertEqual(data_contract["mainData"]["user_id"], 43)
        self.assertEqual(data_contract["mainData"]["phase_key"], "initiation")
        self.assertEqual(trimmed["statusContract"]["globalStatus"]["pageAuth"], "edit")

    def test_ui_contract_v2_edit_form_page_auth_follows_write_permission(self):
        source = {
            "model": "project.project",
            "view_type": "form",
            "head": {
                "render_profile": "edit",
                "permissions": {
                    "read": True,
                    "write": True,
                    "create": True,
                    "unlink": False,
                },
            },
            "fields": {
                "name": {"name": "name", "type": "char", "readonly": False},
                "partner_id": {"name": "partner_id", "type": "many2one", "readonly": False},
            },
            "record_id": 771,
            "render_profile": "edit",
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.edit.auth",
        )

        self.assertEqual(full["statusContract"]["globalStatus"]["pageAuth"], "edit")

    def test_ui_contract_v2_uses_head_title_as_page_name(self):
        source = {
            "model": "project.project",
            "view_type": "form",
            "head": {"title": "项目"},
            "fields": {
                "name": {"name": "name", "type": "char", "string": "项目名称"},
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.form.head.title",
        )

        self.assertEqual(full["pageInfo"]["pageName"], "项目")

    def test_top_level_header_buttons_project_to_form_header(self):
        source = {
            "model": "project.project",
            "view_type": "form",
            "head": {"title": "项目"},
            "fields": {
                "name": {"name": "name", "type": "char", "string": "项目名称"},
            },
            "header_buttons": [
                {
                    "name": "action_submit",
                    "label": "提交",
                    "kind": "object",
                    "payload": {"method": "action_submit", "type": "object"},
                }
            ],
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.form.top.level.header.buttons",
        )

        header = full["layoutContract"]["containerTree"][0]
        self.assertEqual(header["type"], "header")
        self.assertEqual(header["children"][0]["type"], "button")
        self.assertEqual(header["children"][0]["name"], "action_submit")
        self.assertEqual(header["children"][0]["label"], "提交")

        action_rule = full["actionContract"]["actionRuleList"][0]
        self.assertEqual(action_rule["actionKey"], "action_submit")
        self.assertEqual(action_rule["button"], {"name": "action_submit", "type": "object"})

    def test_object_button_payload_method_is_preserved_in_v2_action_contract(self):
        source = {
            "model": "sc.norm.import.wizard",
            "view_type": "form",
            "head": {"title": "导入定额", "render_profile": "create"},
            "fields": {
                "data_file": {"name": "data_file", "type": "binary", "required": True},
            },
            "meta_fields": [
                {"name": "data_file", "type": "binary", "required": True},
            ],
            "views": {
                "form": {
                    "layout": [
                        {"type": "group", "children": [{"type": "field", "name": "data_file"}]},
                    ],
                    "header_buttons": [
                        {
                            "key": "obj_action_import_导入",
                            "label": "导入",
                            "kind": "object",
                            "payload": {"method": "action_import", "type": "object"},
                        }
                    ],
                }
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.form.binary.object.action",
        )

        component_registry = full["layoutContract"]["componentRegistry"]
        self.assertIn("sc.input.binary", component_registry)
        action_rule = full["actionContract"]["actionRuleList"][0]
        self.assertEqual(action_rule["actionKey"], "obj_action_import_导入")
        self.assertEqual(action_rule["button"], {"name": "action_import", "type": "object"})

    def test_native_object_button_visibility_is_preserved_in_v2_action_contract(self):
        visible = {
            "states": [],
            "attrs": {"invisible": ["state", "!=", "upload"]},
        }
        source = {
            "model": "sc.norm.import.wizard",
            "view_type": "form",
            "head": {"title": "导入定额", "render_profile": "create"},
            "fields": {
                "state": {"name": "state", "type": "selection"},
                "data_file": {"name": "data_file", "type": "binary", "required": True},
            },
            "views": {
                "form": {
                    "layout": [{"type": "group", "children": [{"type": "field", "name": "data_file"}]}],
                    "header_buttons": [{
                        "key": "obj_action_preflight_预检",
                        "label": "预检",
                        "kind": "object",
                        "payload": {"method": "action_preflight", "type": "object"},
                        "visible": visible,
                    }],
                }
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.form.native.button.visibility",
        )

        action_rule = full["actionContract"]["actionRuleList"][0]
        self.assertEqual(action_rule["visible"], visible)

    def test_actions_with_same_backend_method_merge_fail_closed_and_keep_trace(self):
        source = {
            "model": "x.approval",
            "view_type": "form",
            "fields": {"state": {"name": "state", "type": "selection"}},
            "views": {"form": {"layout": [], "header_buttons": [{
                "key": "native_submit",
                "label": "原生提交",
                "kind": "object",
                "payload": {"method": "action_submit", "type": "object"},
                "visible": {"attrs": {"invisible": {"kind": "field_compare", "field": "state", "operator": "!=", "value": "draft"}}},
                "visible_profiles": ["edit", "readonly"],
                "allowed": True,
                "enabled": True,
                "required_groups": ["base.group_user"],
                "action_safety": {"classification": "safe", "requires_confirm": False},
            }]},},
            "business_actions": [{
                "key": "semantic_submit",
                "label": "提交审批",
                "kind": "object",
                "payload": {"method": "action_submit", "type": "object"},
                "visible": {"attrs": {"invisible": {"kind": "field_compare", "field": "state", "operator": "=", "value": "cancel"}}},
                "visible_profiles": ["readonly"],
                "allowed": True,
                "enabled": False,
                "allowed_role_codes": ["approver"],
                "presentation": {"tier": "primary"},
                "action_safety": {"classification": "danger", "requires_confirm": True},
            }],
            "buttons": [{
                "key": "compat_submit",
                "label": "兼容提交",
                "kind": "object",
                "payload": {"method": "action_submit", "type": "object"},
            }],
        }

        full = assembler.assemble_unified_page_contract_v2(
            source, source_type="ui.contract", client_type="web_pc", request_id="test.action.identity.merge"
        )

        rules = full["actionContract"]["actionRuleList"]
        submit_rules = [row for row in rules if row.get("backendIdentity") == "button:object:action_submit"]
        self.assertEqual(len(submit_rules), 1)
        rule = submit_rules[0]
        self.assertEqual(rule["label"], "提交审批")
        self.assertEqual(rule["presentationAuthority"], "product_contract")
        self.assertEqual(rule["visibleProfiles"], ["readonly"])
        self.assertEqual(rule["presentation"]["tier"], "primary")
        self.assertEqual(rule["actionSafety"]["classification"], "danger")
        self.assertTrue(rule["actionSafety"]["requires_confirm"])
        self.assertFalse(rule["enabled"])
        self.assertEqual(rule["permissionConstraints"]["policy"], "all_sources_must_allow")
        self.assertEqual(len(rule["permissionConstraints"]["clauses"]), 2)
        self.assertEqual(len(rule["sourceTrace"]), 3)
        self.assertEqual(rule["visible"]["attrs"]["invisible"]["kind"], "any")
        graph_targets = [
            target
            for targets in full["actionContract"]["dependencyGraph"].values()
            for target in targets
        ]
        self.assertEqual(graph_targets.count(rule["actionId"]), 1)
        submit_statuses = [
            row for row in full["statusContract"]["buttonStatus"]
            if row.get("backendIdentity") == "button:object:action_submit"
        ]
        self.assertEqual(len(submit_statuses), 1)
        self.assertTrue(submit_statuses[0]["disabled"])

    def test_same_label_with_different_backend_methods_does_not_merge(self):
        source = {
            "model": "x.approval",
            "view_type": "form",
            "fields": {},
            "business_actions": [
                {"key": "approve_one", "label": "批准", "kind": "object", "payload": {"method": "action_approve", "type": "object"}},
                {"key": "approve_two", "label": "批准", "kind": "object", "payload": {"method": "action_set_approved", "type": "object"}},
            ],
        }

        full = assembler.assemble_unified_page_contract_v2(
            source, source_type="ui.contract", client_type="web_pc", request_id="test.action.label.not.identity"
        )

        identities = [row.get("backendIdentity") for row in full["actionContract"]["actionRuleList"]]
        self.assertIn("button:object:action_approve", identities)
        self.assertIn("button:object:action_set_approved", identities)
        self.assertEqual(len(identities), 2)

    def test_disabled_source_keeps_canonical_action_visible_with_reason(self):
        source = {
            "model": "x.approval",
            "view_type": "form",
            "fields": {},
            "views": {"form": {"layout": [], "header_buttons": [{
                "key": "submit_native",
                "label": "提交",
                "kind": "object",
                "payload": {"method": "action_submit", "type": "object"},
                "allowed": True,
                "enabled": False,
                "reason_code": "WAITING_FOR_REQUIRED_FACTS",
            }]}},
            "business_actions": [{
                "key": "submit_product",
                "label": "提交审批",
                "kind": "object",
                "payload": {"method": "action_submit", "type": "object"},
                "allowed": True,
                "enabled": True,
                "presentation": {"tier": "primary"},
            }],
        }

        full = assembler.assemble_unified_page_contract_v2(
            source, source_type="ui.contract", client_type="web_pc", request_id="test.action.disabled.visible"
        )

        rules = full["actionContract"]["actionRuleList"]
        self.assertEqual(len(rules), 1)
        rule = rules[0]
        self.assertEqual(rule["backendIdentity"], "button:object:action_submit")
        self.assertTrue(rule["allowed"])
        self.assertFalse(rule["enabled"])
        self.assertFalse(rule.get("disabled", False))
        self.assertNotEqual(
            ((rule.get("visible") or {}).get("attrs") or {}).get("invisible"),
            {"kind": "static", "value": True},
        )
        statuses = [
            row for row in full["statusContract"]["buttonStatus"]
            if row.get("backendIdentity") == "button:object:action_submit"
        ]
        self.assertEqual(len(statuses), 1)
        self.assertTrue(statuses[0]["visible"])
        self.assertTrue(statuses[0]["disabled"])
        self.assertEqual(statuses[0]["reasonCode"], "WAITING_FOR_REQUIRED_FACTS")

    def test_runtime_business_action_is_promoted_to_normalized_authority(self):
        contract = assembler.assemble_unified_page_contract_v2(
            {
                "model": "x.document",
                "view_type": "form",
                "views": {"form": {"layout": []}},
            },
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.runtime.business.action",
        )
        contract["runtimeContract"]["businessActions"] = [{
            "key": "open_followup",
            "label": "Open follow-up",
            "kind": "open",
            "level": "header",
            "source_widget_id": "page.header",
            "target": "self",
            "url": "/f/x.followup/new",
            "visible_profiles": ["readonly"],
            "presentation": {"tier": "secondary"},
            "allowed": True,
            "enabled": True,
        }]

        assembler.project_runtime_business_actions(contract)
        promoted = [
            row for row in contract["actionContract"]["actionRuleList"]
            if row.get("actionKey") == "open_followup"
        ]

        self.assertEqual(len(promoted), 1)
        self.assertEqual(promoted[0]["target"]["url"], "/f/x.followup/new")
        self.assertEqual(promoted[0]["target"]["target"], "self")
        self.assertEqual(promoted[0]["sourceChannel"], "runtime_business_action")
        self.assertEqual(promoted[0]["presentationAuthority"], "product_contract")
        self.assertEqual(promoted[0]["visibleProfiles"], ["readonly"])
        self.assertEqual(promoted[0]["targetScope"], "page")

        assembler.project_runtime_business_actions(contract)
        promoted_again = [
            row for row in contract["actionContract"]["actionRuleList"]
            if row.get("actionKey") == "open_followup"
        ]
        self.assertEqual(len(promoted_again), 1)

    def test_runtime_business_action_without_explicit_permission_fails_closed(self):
        contract = assembler.assemble_unified_page_contract_v2(
            {"model": "x.document", "view_type": "form", "views": {"form": {"layout": []}}},
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.runtime.business.action.permission",
        )
        contract["runtimeContract"]["businessActions"] = [{
            "key": "open_followup",
            "label": "Open follow-up",
            "kind": "open",
            "url": "/f/x.followup/new",
        }]

        assembler.project_runtime_business_actions(contract)
        rule = next(row for row in contract["actionContract"]["actionRuleList"] if row["actionKey"] == "open_followup")
        status = next(row for row in contract["statusContract"]["buttonStatus"] if row.get("backendIdentity") == rule["backendIdentity"])

        self.assertFalse(rule["allowed"])
        self.assertFalse(rule["enabled"])
        self.assertTrue(rule["disabled"])
        self.assertFalse(status["visible"])
        self.assertTrue(status["disabled"])
        self.assertEqual(status["reasonCode"], "ACTION_PERMISSION_UNRESOLVED")

    def test_runtime_business_action_key_collision_remains_idempotent(self):
        contract = assembler.assemble_unified_page_contract_v2(
            {
                "model": "x.document",
                "view_type": "form",
                "views": {"form": {"layout": [], "header_buttons": [{
                    "key": "approve",
                    "label": "Native approve",
                    "kind": "object",
                    "payload": {"method": "action_native", "type": "object"},
                    "allowed": True,
                    "enabled": True,
                }]}},
            },
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.runtime.business.action.key.collision",
        )
        contract["runtimeContract"]["businessActions"] = [
            {"key": "approve", "label": "Runtime approve", "kind": "object", "method": "action_runtime", "allowed": True, "enabled": True},
            {"key": "approve", "label": "Duplicate key", "kind": "object", "method": "action_duplicate", "allowed": True, "enabled": True},
        ]

        assembler.project_runtime_business_actions(contract)
        assembler.project_runtime_business_actions(contract)

        runtime_rules = [
            row for row in contract["actionContract"]["actionRuleList"]
            if row.get("backendIdentity") == "button:object:action_runtime"
        ]
        self.assertEqual(len(runtime_rules), 1)
        runtime_trace = [
            row for row in runtime_rules[0]["sourceTrace"]
            if row.get("sourceChannel") == "runtime_business_action"
        ]
        self.assertEqual(len(runtime_trace), 1)
        self.assertEqual(runtime_trace[0]["sourceActionKey"], "approve")
        self.assertFalse(any(
            row.get("backendIdentity") == "button:object:action_duplicate"
            for row in contract["actionContract"]["actionRuleList"]
        ))

    def test_runtime_business_action_merges_three_sources_fail_closed(self):
        source = {
            "model": "x.document",
            "view_type": "form",
            "views": {"form": {"layout": [], "header_buttons": [{
                "key": "native_submit",
                "label": "Submit",
                "kind": "object",
                "payload": {"method": "action_submit", "type": "object"},
                "allowed": True,
                "enabled": True,
            }]}},
            "business_actions": [{
                "key": "semantic_submit",
                "label": "Submit document",
                "kind": "object",
                "payload": {"method": "action_submit", "type": "object"},
                "allowed": True,
                "enabled": True,
                "presentation": {"tier": "primary"},
            }],
        }
        contract = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.runtime.business.action.merge",
        )
        contract["runtimeContract"]["businessActions"] = [{
            "key": "runtime_submit",
            "label": "Submit safely",
            "kind": "object",
            "method": "action_submit",
            "allowed": True,
            "enabled": False,
            "reason_code": "RUNTIME_PRECONDITION_BLOCKED",
            "presentation": {"tier": "primary"},
            "action_safety": {"classification": "danger", "requires_confirm": True},
        }]

        assembler.project_runtime_business_actions(contract)
        rules = [row for row in contract["actionContract"]["actionRuleList"] if row.get("backendIdentity") == "button:object:action_submit"]

        self.assertEqual(len(rules), 1)
        self.assertFalse(rules[0]["enabled"])
        self.assertEqual(rules[0]["actionSafety"]["classification"], "danger")
        self.assertTrue(rules[0]["actionSafety"]["requires_confirm"])
        self.assertEqual(len(rules[0]["sourceTrace"]), 3)
        primary = [
            row for row in contract["actionContract"]["actionRuleList"]
            if (row.get("presentation") or {}).get("tier") == "primary"
        ]
        self.assertEqual(len(primary), 1)
        status = next(row for row in contract["statusContract"]["buttonStatus"] if row.get("backendIdentity") == "button:object:action_submit")
        self.assertTrue(status["visible"])
        self.assertTrue(status["disabled"])
        self.assertEqual(status["reasonCode"], "RUNTIME_PRECONDITION_BLOCKED")
        dependency_targets = {
            target
            for targets in contract["actionContract"]["dependencyGraph"].values()
            for target in targets
        }
        self.assertEqual(dependency_targets, {rules[0]["actionId"]})

    def test_runtime_action_merges_with_entitled_native_payload_button(self):
        source = {
            "model": "x.document",
            "view_type": "form",
            "views": {"form": {"layout": [], "header_buttons": [{
                "key": "payment_submit",
                "label": "Submit for approval",
                "kind": "object",
                "payload": {
                    "method": "action_submit",
                    "type": "object",
                    "groups_xmlids": ["x.group_finance_user"],
                },
            }]}},
            "action_policies": {
                "payment_submit": {
                    "enabled": True,
                    "entitlement_evaluated": True,
                    "visible_profiles": ["create", "edit", "readonly"],
                    "enabled_when": {"required_groups": ["x.group_finance_user"]},
                },
            },
        }
        contract = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.runtime.entitled.native.payload",
        )
        contract["runtimeContract"]["businessActions"] = [{
            "key": "payment_submit",
            "label": "Submit",
            "kind": "mutation",
            "method": "action_submit",
            "level": "header",
            "source_widget_id": "page.header",
            "target_scope": "page",
            "visible_profiles": ["edit", "readonly"],
            "allowed": True,
            "enabled": True,
            "disabled": False,
            "presentation": {"tier": "primary"},
        }]

        assembler.project_runtime_business_actions(contract)
        rules = [
            row for row in contract["actionContract"]["actionRuleList"]
            if row.get("backendIdentity") == "button:object:action_submit"
        ]
        statuses = [
            row for row in contract["statusContract"]["buttonStatus"]
            if row.get("backendIdentity") == "button:object:action_submit"
        ]

        self.assertEqual(len(rules), 1)
        self.assertTrue(rules[0]["allowed"])
        self.assertTrue(rules[0]["enabled"])
        self.assertFalse(rules[0]["disabled"])
        self.assertEqual(rules[0]["label"], "Submit")
        self.assertEqual(rules[0]["visibleProfiles"], ["edit", "readonly"])
        self.assertEqual(len(statuses), 1)
        self.assertTrue(statuses[0]["visible"])
        self.assertFalse(statuses[0]["disabled"])

    def test_runtime_business_action_identity_matrix_and_final_seal(self):
        contract = assembler.assemble_unified_page_contract_v2(
            {"model": "x.document", "view_type": "form", "views": {"form": {"layout": []}}},
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.runtime.business.action.identity",
        )
        contract["runtimeContract"]["businessActions"] = [
            {"key": "window", "label": "Open", "kind": "open", "action_id": 81, "allowed": True, "enabled": True},
            {"key": "object_a", "label": "Review", "kind": "object", "method": "action_review_a", "allowed": True, "enabled": True},
            {"key": "object_b", "label": "Review", "kind": "object", "method": "action_review_b", "allowed": True, "enabled": True},
            {"key": "url", "label": "Open", "kind": "open", "url": "/x/status", "allowed": True, "enabled": True},
            {"key": "client", "label": "Configure", "kind": "client", "target": {"mode": "configure"}, "allowed": True, "enabled": True},
        ]

        assembler.project_runtime_business_actions(contract)
        identities = {row["backendIdentity"] for row in contract["actionContract"]["actionRuleList"]}
        self.assertIn("window_action:81", identities)
        self.assertIn("button:object:action_review_a", identities)
        self.assertIn("button:object:action_review_b", identities)
        self.assertIn("url:/x/status", identities)
        self.assertTrue(any(identity.startswith("target:") for identity in identities))

        sealed = assembler.seal_unified_page_contract(
            contract,
            source_payload={"model": "x.document"},
            source_type="ui.contract",
            request_id="test.runtime.business.action.identity.sealed",
            trace_id="trace.runtime.business.action.identity",
            client_type="web_pc",
            stage="runtime_delivery",
            generator="test.runtime",
            generator_version="2.2.0",
            source_authority=assembler.source_authority_contract(),
        )
        digest = sealed["meta"]["lifecycle"]["integrity"]["contractSha256"]
        semantic = {key: value for key, value in sealed.items() if key != "meta"}
        self.assertEqual(digest, assembler.payload_sha256(semantic))
        self.assertTrue(any(row.get("actionKey") == "window" for row in sealed["actionContract"]["actionRuleList"]))

    def test_same_action_key_with_different_backend_methods_keeps_both_sources(self):
        source = {
            "model": "x.document",
            "view_type": "form",
            "fields": {},
            "views": {"form": {"layout": [], "header_buttons": [
                {"key": "approve", "label": "原生批准", "kind": "object", "payload": {"method": "action_approve", "type": "object"}},
            ]}},
            "business_actions": [
                {"key": "approve", "label": "升级批准", "kind": "object", "payload": {"method": "action_escalate_approve", "type": "object"}},
            ],
        }

        full = assembler.assemble_unified_page_contract_v2(
            source, source_type="ui.contract", client_type="web_pc", request_id="test.action.same.key"
        )

        rules = full["actionContract"]["actionRuleList"]
        self.assertEqual(len(rules), 2)
        self.assertEqual(len({row["actionId"] for row in rules}), 2)
        self.assertEqual(
            {row["backendIdentity"] for row in rules},
            {"button:object:action_approve", "button:object:action_escalate_approve"},
        )

    def test_resolved_action_policy_is_normalized_fail_closed(self):
        source = {
            "model": "x.document",
            "view_type": "form",
            "fields": {},
            "business_actions": [
                {"key": "publish", "label": "发布", "kind": "object", "payload": {"method": "action_publish", "type": "object"}},
                {"key": "export", "label": "导出", "kind": "object", "payload": {"method": "action_export", "type": "object"}, "required_role_key": "auditor"},
            ],
            "action_policies": {
                "publish": {
                    "enabled": False,
                    "allowed": False,
                    "reason_code": "ACTION_GROUP_ACCESS_DENIED",
                    "entitlement_evaluated": True,
                    "enabled_when": {"required_groups": ["base.group_system"]},
                },
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source, source_type="ui.contract", client_type="web_pc", request_id="test.action.policy.fail.closed"
        )

        rules = {row["backendIdentity"]: row for row in full["actionContract"]["actionRuleList"]}
        rule = rules["button:object:action_publish"]
        self.assertFalse(rule["allowed"])
        self.assertFalse(rule["enabled"])
        self.assertEqual(
            rule["permissionConstraints"]["clauses"][0]["requiredGroups"],
            ["base.group_system"],
        )
        statuses = {row["backendIdentity"]: row for row in full["statusContract"]["buttonStatus"]}
        status = statuses["button:object:action_publish"]
        self.assertFalse(status["visible"])
        self.assertTrue(status["disabled"])
        self.assertEqual(status["reasonCode"], "ACTION_GROUP_ACCESS_DENIED")
        unresolved = rules["button:object:action_export"]
        self.assertFalse(unresolved["allowed"])
        self.assertFalse(unresolved["enabled"])
        unresolved_status = statuses["button:object:action_export"]
        self.assertTrue(unresolved_status["disabled"])
        self.assertEqual(unresolved_status["reasonCode"], "ACTION_PERMISSION_UNRESOLVED")

    def test_window_and_url_actions_use_stable_distinct_identity(self):
        source = {
            "model": "x.collection",
            "view_type": "tree",
            "fields": {},
            "business_actions": [
                {"key": "open_records", "label": "打开", "kind": "open", "action_id": 81, "payload": {"action_id": 81}},
                {"key": "open_help", "label": "帮助", "kind": "open", "payload": {"url": "https://example.invalid/help"}},
                {"key": "open_route", "label": "内部帮助", "kind": "open", "payload": {"route": "/help/product"}},
                {"key": "server_refresh", "label": "服务端刷新", "kind": "server", "payload": {"server_action_id": 91}},
            ],
        }

        full = assembler.assemble_unified_page_contract_v2(
            source, source_type="ui.contract", client_type="web_pc", request_id="test.action.target.identity"
        )

        identities = {row["backendIdentity"] for row in full["actionContract"]["actionRuleList"]}
        self.assertEqual(identities, {
            "window_action:81",
            "url:https://example.invalid/help",
            "route:/help/product",
            "server_action:91",
        })

    def test_window_action_xmlid_refs_do_not_collapse_without_numeric_id(self):
        source = {
            "model": "res.partner",
            "view_type": "form",
            "fields": {},
            "business_actions": [
                {"key": "open_partner", "kind": "open", "label": "Partner", "payload": {"ref": "base.action_partner_form"}},
                {"key": "open_project", "kind": "open", "label": "Project", "payload": {"xml_id": "project.open_view_project_all"}},
            ],
        }

        full = assembler.assemble_unified_page_contract_v2(
            source, source_type="ui.contract", client_type="web_pc", request_id="test.action.xmlid.identity"
        )
        rules = full["actionContract"]["actionRuleList"]
        self.assertEqual(len(rules), 2)
        self.assertEqual(
            {row["backendIdentity"] for row in rules},
            {
                "window_action_ref:base.action_partner_form",
                "window_action_ref:project.open_view_project_all",
            },
        )

    def test_generic_open_keys_remain_distinct_contract_actions_without_explicit_ref(self):
        source = {
            "model": "x.collection",
            "view_type": "tree",
            "fields": {},
            "business_actions": [
                {"key": "open_primary", "kind": "open", "label": "Primary"},
                {"key": "open_secondary", "kind": "open", "label": "Secondary"},
            ],
        }

        full = assembler.assemble_unified_page_contract_v2(
            source, source_type="ui.contract", client_type="web_pc", request_id="test.action.generic.open.identity"
        )

        rules = full["actionContract"]["actionRuleList"]
        self.assertEqual(len(rules), 2)
        self.assertEqual(len({row["backendIdentity"] for row in rules}), 2)
        self.assertTrue(all(row["backendIdentity"].startswith("contract_action:") for row in rules))

    def test_evaluated_entitlement_without_explicit_verdict_fails_closed(self):
        for constraint_key, constraint_value in (
            ("required_role_key", "reviewer"),
            ("required_groups", ["base.group_system"]),
            ("required_user_id", 42),
        ):
            with self.subTest(constraint=constraint_key):
                source = {
                    "model": "x.document",
                    "view_type": "form",
                    "fields": {},
                    "business_actions": [{
                        "key": "review",
                        "kind": "object",
                        "label": "Review",
                        "payload": {"method": "action_review", "type": "object"},
                        constraint_key: constraint_value,
                        "entitlement_evaluated": True,
                    }],
                }

                full = assembler.assemble_unified_page_contract_v2(
                    source,
                    source_type="ui.contract",
                    client_type="web_pc",
                    request_id=f"test.action.entitlement.no.verdict.{constraint_key}",
                )

                rule = full["actionContract"]["actionRuleList"][0]
                self.assertFalse(rule["allowed"])
                self.assertFalse(rule["enabled"])
                status = full["statusContract"]["buttonStatus"][0]
                self.assertTrue(status["disabled"])
                self.assertEqual(status["reasonCode"], "ACTION_PERMISSION_UNRESOLVED")

    def test_three_generic_page_samples_preserve_platform_boundaries(self):
        parser = _NativeTreeFormFixtureParser()
        policy_fields = {
            "company_id": {"name": "company_id", "type": "many2one"},
            "menu_id": {"name": "menu_id", "type": "many2one"},
            "role_group_ids": {"name": "role_group_ids", "type": "many2many", "relation": "res.groups"},
            "visible": {"name": "visible", "type": "boolean"},
            "active": {"name": "active", "type": "boolean"},
            "custom_label": {"name": "custom_label", "type": "char"},
            "effect_summary": {"name": "effect_summary", "type": "char"},
        }
        policy_form_arch = _native_view_fixture_arch(
            "addons/smart_core/views/ui_menu_config_policy_views.xml",
            "view_ui_menu_config_policy_form",
        )
        policy_tree_arch = _native_view_fixture_arch(
            "addons/smart_core/views/ui_menu_config_policy_views.xml",
            "view_ui_menu_config_policy_tree",
        )
        route_fields = {
            "active": {"name": "active", "type": "boolean"},
            "sequence": {"name": "sequence", "type": "integer"},
            "login": {"name": "login", "type": "char"},
            "target_db": {"name": "target_db", "type": "char"},
            "entry_kind": {"name": "entry_kind", "type": "selection"},
            "product_key": {"name": "product_key", "type": "char"},
            "label": {"name": "label", "type": "char"},
            "note": {"name": "note", "type": "text"},
        }
        route_form_arch = _native_view_fixture_arch(
            "addons/smart_core/views/platform_company_access_views.xml",
            "view_sc_login_route_form",
        )
        samples = [
            {
                "model": "ui.menu.config.policy",
                "view_type": "form",
                "fields": policy_fields,
                "views": {"form": parser._parse_form_view(policy_form_arch, policy_fields, "ui.menu.config.policy")},
                "expected": "第一步：选择要调整的菜单",
            },
            {
                "model": "sc.login.route",
                "view_type": "form",
                "fields": route_fields,
                "views": {"form": parser._parse_form_view(route_form_arch, route_fields, "sc.login.route")},
                "expected": "路由信息",
            },
            {
                "model": "ui.menu.config.policy",
                "view_type": "tree",
                "fields": policy_fields,
                "views": {"tree": parser._parse_tree_view(policy_tree_arch, policy_fields)},
                "expected": "menu_id",
            },
        ]

        for index, source in enumerate(samples):
            with self.subTest(model=source["model"]):
                full = assembler.assemble_unified_page_contract_v2(
                    source,
                    source_type="ui.contract",
                    client_type="web_pc",
                    request_id=f"test.generic.sample.{index}",
                )
                self.assertEqual(full["pageInfo"]["model"], source["model"])
                self.assertTrue(full["layoutContract"]["containerTree"])
                self.assertIn(source["expected"], str(full["layoutContract"]["containerTree"]))

    def test_production_tree_parser_row_object_action_consumes_method_and_groups_payload(self):
        parser = _NativeTreeFormFixtureParser()
        fields = {"name": {"name": "name", "type": "char", "string": "Name"}}
        parsed = parser._parse_tree_view(
            """
            <tree>
              <field name="name"/>
              <button name="action_review" string="Review" type="object" groups="base.group_system"/>
            </tree>
            """,
            fields,
        )
        source = {
            "model": "x.document",
            "view_type": "tree",
            "fields": fields,
            "views": {"tree": parsed},
        }

        full = assembler.assemble_unified_page_contract_v2(
            source, source_type="ui.contract", client_type="web_pc", request_id="test.tree.row.parser.payload"
        )

        rule = full["actionContract"]["actionRuleList"][0]
        self.assertEqual(rule["backendIdentity"], "button:object:action_review")
        self.assertEqual(
            rule["permissionConstraints"]["clauses"][0]["requiredGroups"],
            ["base.group_system"],
        )
        self.assertFalse(rule["allowed"])
        self.assertFalse(rule["enabled"])
        status = full["statusContract"]["buttonStatus"][0]
        self.assertFalse(status["visible"])
        self.assertTrue(status["disabled"])
        self.assertEqual(status["reasonCode"], "ACTION_PERMISSION_UNRESOLVED")
        trace = rule["sourceTrace"][0]
        self.assertEqual(trace["sourceChannel"], "native_tree_row_action")
        self.assertIn("base.group_system", str(trace["permissionConstraints"]))

    def test_only_one_primary_is_effective_for_current_record_state(self):
        source = {
            "model": "x.approval",
            "view_type": "form",
            "record": {"state": "draft"},
            "fields": {"state": {"name": "state", "type": "selection"}},
            "business_actions": [
                {
                    "key": "submit",
                    "label": "提交",
                    "kind": "object",
                    "payload": {"method": "action_submit", "type": "object"},
                    "presentation": {"tier": "primary"},
                    "visible": {"attrs": {"invisible": {"kind": "field_compare", "field": "state", "operator": "!=", "value": "draft"}}},
                },
                {
                    "key": "approve",
                    "label": "批准",
                    "kind": "object",
                    "payload": {"method": "action_approve", "type": "object"},
                    "presentation": {"tier": "primary"},
                    "visible": {"attrs": {"invisible": {"kind": "field_compare", "field": "state", "operator": "!=", "value": "waiting"}}},
                },
                {
                    "key": "duplicate_draft_primary",
                    "label": "草稿主动作二",
                    "kind": "object",
                    "payload": {"method": "action_prepare", "type": "object"},
                    "presentation": {"tier": "primary"},
                    "visible": {"attrs": {"invisible": {"kind": "field_compare", "field": "state", "operator": "!=", "value": "draft"}}},
                },
            ],
        }

        full = assembler.assemble_unified_page_contract_v2(
            source, source_type="ui.contract", client_type="web_pc", request_id="test.action.single.primary"
        )

        rules = full["actionContract"]["actionRuleList"]
        tiers = {row["backendIdentity"]: (row.get("presentation") or {}).get("tier") for row in rules}
        self.assertEqual(tiers["button:object:action_submit"], "primary")
        self.assertEqual(tiers["button:object:action_approve"], "primary")
        self.assertEqual(tiers["button:object:action_prepare"], "secondary")
        resolution = full["actionContract"]["primaryResolution"]
        self.assertEqual(resolution["winner"], "button:object:action_submit")

    def test_entry_semantic_surface_layout_wins_while_native_modifiers_and_relations_survive(self):
        source = {
            "model": "x.business.document",
            "view_type": "form",
            "governance": {"view_orchestration": {"applied": True, "form_structure_authority": "entry_semantic_surface"}},
            "source_trace": {"view_orchestration": {"form_structure_authority": "entry_semantic_surface"}},
            "fields": {
                "name": {"name": "name", "type": "char", "required": True},
                "line_ids": {"name": "line_ids", "type": "one2many", "readonly": True},
            },
            "views": {"form": {"layout": [
                {"type": "group", "string": "业务主信息", "children": [{"type": "field", "name": "name", "required": True}]},
                {"type": "notebook", "string": "从属关系", "tabs": [{"type": "page", "string": "明细", "children": [{"type": "field", "name": "line_ids", "readonly": True}]}]},
            ]}},
            "form_structure_contract": {
                "source": "ui.contract.v2.form_structure_contract",
                "slots": [{"slot": "primary_facts", "title": "分类模板", "groups": [{"name": "fallback", "title": "分类模板", "fieldRefs": ["name"]}]}],
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source, source_type="ui.contract", client_type="web_pc", request_id="test.semantic.surface.precedence"
        )

        tree = full["layoutContract"]["containerTree"]
        self.assertIn("业务主信息", str(tree))
        self.assertIn("从属关系", str(tree))
        self.assertIn("line_ids", str(tree))
        self.assertNotIn("分类模板", str(tree))
        statuses = {row["widgetId"]: row for row in full["statusContract"]["widgetStatus"]}
        self.assertTrue(statuses["field.name"]["required"])
        self.assertTrue(statuses["field.line_ids"]["readonly"])

    def test_data_source_and_formal_metadata_projection_carry_source_authority(self):
        source = {
            "model": "project.project",
            "view_type": "form",
            "head": {"title": "项目"},
            "fields": {
                "name": {"name": "name", "type": "char", "string": "项目名称"},
            },
            "business_operation_profile": {
                "source": "test",
                "common_fields": ["name"],
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.form.data.source.authority",
        )

        primary = full["dataContract"]["dataSource"]["primary"]
        self.assertEqual(primary["sourceAuthority"]["runtime_carrier"], "ui.contract.v2.dataContract.dataSource")
        self.assertTrue(primary["sourceAuthority"]["projection_only"])
        self.assertTrue(primary["sourceAuthority"]["no_business_fact_authority"])
        profile = full["dataContract"]["dataMeta"]["businessOperationProfile"]
        self.assertEqual(profile["sourceAuthority"]["runtime_carrier"], "ui.contract.v2.dataMeta.businessOperationProfile")
        self.assertTrue(profile["sourceAuthority"]["projection_only"])
        self.assertTrue(profile["sourceAuthority"]["no_business_fact_authority"])
        self.assertTrue(profile["sourceAuthority"]["formal_projection"])
        self.assertNotIn("legacyContractProjection", full["dataContract"]["dataMeta"])

    def test_form_data_source_keeps_deep_form_fields(self):
        fields = {
            f"field_{index}": {
                "name": f"field_{index}",
                "type": "char",
                "string": f"字段{index}",
            }
            for index in range(70)
        }
        source = {
            "model": "construction.contract.income",
            "view_type": "form",
            "fields": fields,
            "record_id": 991,
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.form.deep.fields",
        )

        requested_fields = full["dataContract"]["dataSource"]["primary"]["params"]["fields"]
        self.assertIn("field_69", requested_fields)
        self.assertGreater(len(requested_fields), 40)

    def test_ui_contract_v2_readonly_form_page_auth_stays_read(self):
        source = {
            "model": "project.project",
            "view_type": "form",
            "head": {
                "render_profile": "readonly",
                "permissions": {
                    "read": True,
                    "write": True,
                    "create": True,
                    "unlink": False,
                },
            },
            "fields": {
                "name": {"name": "name", "type": "char", "readonly": False},
            },
            "record_id": 771,
            "render_profile": "readonly",
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.readonly.auth",
        )

        self.assertEqual(full["statusContract"]["globalStatus"]["pageAuth"], "read")

    def _source_with_form_structure_summary(self, render_profile):
        return {
            "model": "tender.doc.purchase",
            "view_type": "form",
            "render_profile": render_profile,
            "head": {"render_profile": render_profile},
            "fields": {
                "invoice_no": {"name": "invoice_no", "type": "char", "string": "发票号/凭证号"},
                "amount": {"name": "amount", "type": "monetary", "string": "金额", "readonly": False},
                "bid_id": {"name": "bid_id", "type": "many2one", "string": "投标", "readonly": False},
                "receipt_partner_name": {"name": "receipt_partner_name", "type": "char", "string": "历史/快照收款单位", "readonly": True},
                "legacy_state": {"name": "legacy_state", "type": "char", "string": "历史状态", "readonly": True},
                "legacy_source_user": {"name": "legacy_source_user", "type": "char", "string": "历史录入人", "readonly": True},
            },
            "form_structure_contract": {
                "source": "ui.contract.v2.form_structure_contract",
                "viewType": "form",
                "slots": [
                    {
                        "slot": "overview",
                        "title": "办理总览",
                        "fieldRefs": ["invoice_no", "amount"],
                    },
                    {
                        "slot": "primary_facts",
                        "title": "主业务事实",
                        "groups": [
                            {"name": "identity", "title": "申请信息", "fieldRefs": ["bid_id", "receipt_partner_name"]},
                        ],
                    },
                    {
                        "slot": "amount_progress",
                        "title": "金额与进度",
                        "groups": [
                            {"name": "amounts", "title": "金额信息", "fieldRefs": ["amount"]},
                        ],
                    },
                    {
                        "slot": "details_source",
                        "title": "明细与来源",
                        "groups": [
                            {
                                "name": "history_check",
                                "title": "历史核对信息",
                                "role": "history_check",
                                "fieldRefs": ["legacy_state", "legacy_source_user"],
                            },
                        ],
                    },
                ],
            },
        }

    def test_form_structure_create_layout_starts_with_task_not_summary(self):
        full = assembler.assemble_unified_page_contract_v2(
            self._source_with_form_structure_summary("create"),
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.create.form.no.summary.first",
        )

        sheet = full["layoutContract"]["containerTree"][0]
        self.assertEqual([child["type"] for child in sheet["children"]], ["group", "group"])
        self.assertEqual([child["label"] for child in sheet["children"]], ["申请信息", "金额信息"])
        rendered_names = [
            node.get("name")
            for group in sheet["children"]
            for node in group.get("children", [])
        ]
        self.assertNotIn("receipt_partner_name", rendered_names)
        self.assertNotIn("legacy_state", rendered_names)
        self.assertNotIn("legacy_source_user", rendered_names)

    def test_form_structure_readonly_layout_keeps_summary_first(self):
        full = assembler.assemble_unified_page_contract_v2(
            self._source_with_form_structure_summary("readonly"),
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.readonly.form.summary.first",
        )

        sheet = full["layoutContract"]["containerTree"][0]
        self.assertEqual(sheet["children"][0]["type"], "group")
        self.assertEqual(sheet["children"][0]["label"], "办理总览")
        self.assertEqual(sheet["children"][1]["type"], "notebook")
        tabs = sheet["children"][1]["tabs"]
        history_tab = next(tab for tab in tabs if tab["label"] == "明细与来源")
        history_fields = [
            node.get("name")
            for group in history_tab.get("children", [])
            for node in group.get("children", [])
        ]
        primary_tab = next(tab for tab in tabs if tab["label"] == "主业务事实")
        primary_fields = [
            node.get("name")
            for group in primary_tab.get("children", [])
            for node in group.get("children", [])
        ]
        self.assertIn("receipt_partner_name", primary_fields)
        self.assertIn("legacy_state", history_fields)
        self.assertIn("legacy_source_user", history_fields)

    def test_ui_contract_v2_preserves_tree_column_optional_hide(self):
        source = {
            "model": "hr.department",
            "view_type": "tree",
            "fields": {
                "name": {"name": "name", "type": "char", "string": "部门名称"},
                "create_uid": {"name": "create_uid", "type": "many2one", "string": "创建人"},
                "create_date": {"name": "create_date", "type": "datetime", "string": "创建日期"},
            },
            "views": {
                "tree": {
                    "columns": ["name", "create_uid", "create_date"],
                    "columns_schema": [
                        {"name": "name", "string": "部门名称", "type": "char"},
                        {
                            "name": "create_uid",
                            "string": "创建人",
                            "type": "many2one",
                            "optional": "hide",
                        },
                        {
                            "name": "create_date",
                            "string": "创建日期",
                            "type": "datetime",
                            "optional": "hide",
                        },
                    ],
                },
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.tree.optional.hide",
        )

        widgets = [
            widget
            for container in full["layoutContract"]["containerTree"]
            for widget in container["widgetList"]
        ]
        by_field = {widget["fieldCode"]: widget for widget in widgets}
        self.assertEqual(by_field["create_uid"]["componentConfig"]["optional"], "hide")
        self.assertEqual(by_field["create_date"]["componentConfig"]["optional"], "hide")
        status = {row["widgetId"]: row for row in full["statusContract"]["widgetStatus"]}
        self.assertTrue(status[by_field["create_uid"]["widgetId"]]["visible"])
        self.assertTrue(status[by_field["create_date"]["widgetId"]]["visible"])

    def test_ui_contract_v2_preserves_tree_column_value_semantics(self):
        source = {
            "model": "tender.doc.purchase",
            "view_type": "tree",
            "fields": {
                "visible_amount": {
                    "name": "visible_amount",
                    "type": "char",
                    "string": "金额",
                },
            },
            "views": {
                "tree": {
                    "columns": ["visible_amount"],
                    "columns_schema": [{
                        "name": "visible_amount",
                        "string": "金额",
                        "type": "char",
                        "display_field": "visible_amount",
                        "value_field": "amount",
                        "aggregation_field": "amount",
                        "data_type": "monetary",
                        "currency_field": "currency_id",
                        "aggregate": "sum",
                        "aggregate_label": "报名费合计",
                        "sort_field": "amount",
                        "filter_field": "amount",
                        "export_field": "amount",
                    }],
                },
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.tree.value.semantics",
        )

        widget = full["layoutContract"]["containerTree"][0]["widgetList"][0]
        config = widget["componentConfig"]
        self.assertEqual(config["display_field"], "visible_amount")
        self.assertEqual(config["value_field"], "amount")
        self.assertEqual(config["aggregation_field"], "amount")
        self.assertEqual(config["data_type"], "monetary")
        self.assertEqual(config["currency_field"], "currency_id")
        self.assertEqual(config["aggregate"], "sum")
        self.assertEqual(config["sort_field"], "amount")
        self.assertEqual(config["filter_field"], "amount")
        self.assertEqual(config["export_field"], "amount")

    def test_ui_contract_v2_preserves_tree_selection_options(self):
        source = {
            "model": "project.project",
            "view_type": "tree",
            "fields": {
                "name": {"name": "name", "type": "char", "string": "名称"},
                "operation_strategy": {
                    "name": "operation_strategy",
                    "type": "selection",
                    "string": "经营方式",
                    "selection": [["direct", "公司直营"], ["joint", "联营项目"]],
                },
                "lifecycle_state": {
                    "name": "lifecycle_state",
                    "type": "selection",
                    "string": "项目状态",
                    "selection": [["draft", "草稿"], ["in_progress", "在建"]],
                },
            },
            "views": {
                "tree": {
                    "columns": ["name", "operation_strategy", "lifecycle_state"],
                    "columns_schema": [
                        {"name": "name", "string": "名称", "type": "char"},
                        {"name": "operation_strategy", "string": "经营方式", "type": "selection"},
                        {"name": "lifecycle_state", "string": "项目状态", "type": "selection"},
                    ],
                },
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.tree.selection.options",
        )

        widgets = [
            widget
            for container in full["layoutContract"]["containerTree"]
            for widget in container["widgetList"]
        ]
        by_field = {widget["fieldCode"]: widget for widget in widgets}
        self.assertEqual(
            by_field["operation_strategy"]["componentConfig"]["selection"],
            [["direct", "公司直营"], ["joint", "联营项目"]],
        )
        self.assertEqual(
            by_field["lifecycle_state"]["componentConfig"]["selection"],
            [["draft", "草稿"], ["in_progress", "在建"]],
        )

    def test_web_pc_drops_source_compat_when_not_requested(self):
        source = {
            "model": "project.project",
            "view_type": "form",
            "fields": {
                "name": {"name": "name", "type": "char", "string": "名称"},
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.no.compat",
        )
        trimmed = client.trim_unified_page_contract_v2(
            full,
            client_type="web_pc",
            delivery_profile="full",
        )
        self.assertNotIn("compat", trimmed["meta"])

    def test_ui_contract_v2_preserves_native_form_layout_tree(self):
        source = {
            "model": "project.project",
            "view_type": "form",
            "views": {
                "form": {
                    "layout": [
                        {
                            "type": "header",
                            "name": "project_header",
                            "children": [
                                {
                                    "type": "button",
                                    "name": "action_submit",
                                    "label": "提交",
                                    "buttonType": "object",
                                }
                            ],
                        },
                        {
                            "type": "sheet",
                            "name": "project_sheet",
                            "children": [
                                {
                                    "type": "group",
                                    "name": "project_core",
                                    "string": "基础信息",
                                    "children": [
                                        {"type": "field", "name": "name"},
                                        {"type": "field", "name": "manager_id", "fieldInfo": {"label": "项目经理"}},
                                    ],
                                },
                                {
                                    "type": "notebook",
                                    "name": "project_tabs",
                                    "tabs": [
                                        {
                                            "type": "page",
                                            "name": "settings_page",
                                            "string": "设置",
                                            "children": [
                                                {
                                                    "type": "group",
                                                    "name": "settings_group",
                                                    "children": [
                                                        {"type": "field", "name": "company_id"},
                                                    ],
                                                }
                                            ],
                                        }
                                    ],
                                },
                            ],
                        },
                    ]
                }
            },
            "fields": {
                "name": {"name": "name", "type": "char", "string": "名称"},
                "manager_id": {"name": "manager_id", "type": "many2one", "string": "项目经理"},
                "company_id": {"name": "company_id", "type": "many2one", "string": "公司"},
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.native.form.tree",
        )

        tree = full["layoutContract"]["containerTree"]
        self.assertEqual([node["type"] for node in tree], ["header", "sheet"])
        self.assertEqual(tree[1]["children"][0]["type"], "group")
        self.assertEqual(tree[1]["children"][1]["type"], "notebook")
        self.assertEqual(tree[1]["children"][1]["tabs"][0]["type"], "page")
        core_group = tree[1]["children"][0]
        self.assertEqual([node["name"] for node in core_group["children"]], ["name", "manager_id"])
        self.assertEqual([widget["fieldCode"] for widget in core_group["widgetList"]], ["name", "manager_id"])
        page_group = tree[1]["children"][1]["tabs"][0]["children"][0]
        self.assertEqual([node["name"] for node in page_group["children"]], ["company_id"])
        self.assertEqual(page_group["children"][0]["fieldInfo"]["label"], "公司")

    def test_form_structure_contract_rebuilds_business_task_layout(self):
        source = {
            "model": "construction.contract.income",
            "view_type": "form",
            "views": {
                "form": {
                    "layout": [
                        {
                            "type": "header",
                            "name": "contract_header",
                            "children": [{"type": "button", "name": "action_confirm", "label": "提交"}],
                        },
                        {
                            "type": "sheet",
                            "name": "native_sheet",
                            "children": [
                                {
                                    "type": "group",
                                    "name": "native_group",
                                    "children": [{"type": "field", "name": "name"}],
                                }
                            ],
                        },
                        {
                            "type": "group",
                            "name": "hidden_native_group",
                            "children": [
                                {
                                    "type": "field",
                                    "name": "hidden_internal_note",
                                    "invisible": True,
                                    "modifiers": {"invisible": True},
                                }
                            ],
                        },
                    ]
                }
            },
            "fields": {
                "name": {"name": "name", "type": "char", "string": "编号"},
                "subject": {"name": "subject", "type": "char", "string": "标题"},
                "project_id": {"name": "project_id", "type": "many2one", "string": "项目"},
                "visible_contract_amount": {"name": "visible_contract_amount", "type": "monetary", "string": "合同金额"},
                "line_ids": {"name": "line_ids", "type": "one2many", "string": "明细"},
                "hidden_internal_note": {"name": "hidden_internal_note", "type": "char", "string": "隐藏内部说明"},
            },
            "form_structure_contract": {
                "source": "ui.contract.v2.form_structure_contract",
                "mode": "business_task_form",
                "navigation": {"title": "业务办理"},
                "fieldRoles": {
                    "subject": {"role": "identity", "slot": "primary_facts", "group": "identity"},
                    "line_ids": {"role": "detail", "slot": "details_source", "group": "details"},
                },
                "slots": [
                    {
                        "slot": "overview",
                        "title": "办理总览",
                        "readonly": True,
                        "fieldRefs": ["subject", "project_id", "visible_contract_amount"],
                    },
                    {
                        "slot": "primary_facts",
                        "title": "主业务事实",
                        "groups": [
                            {"name": "identity", "title": "业务识别", "fieldRefs": ["name", "subject"]},
                            {"name": "other_facts", "title": "其他事实", "fieldRefs": ["hidden_internal_note"]},
                        ],
                    },
                    {
                        "slot": "details_source",
                        "title": "明细与来源",
                        "groups": [
                            {"name": "details", "title": "业务明细", "fieldRefs": ["line_ids"]},
                        ],
                    },
                ],
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.form.structure",
        )

        self.assertEqual(full["formStructureContract"]["source"], "ui.contract.v2.form_structure_contract")
        tree = full["layoutContract"]["containerTree"]
        self.assertEqual([node["type"] for node in tree], ["header", "sheet"])
        sheet_children = tree[1]["children"]
        self.assertEqual([node["type"] for node in sheet_children], ["group", "group"])
        self.assertEqual([node["label"] for node in sheet_children], ["业务识别", "业务明细"])
        self.assertEqual(sheet_children[0]["formStructure"]["slot"], "primary_facts")
        self.assertEqual(sheet_children[0]["formStructure"]["role"], "identity")
        self.assertEqual(sheet_children[0]["children"][1]["formStructureRole"]["role"], "identity")
        rendered_names = [
            node.get("name")
            for group in sheet_children
            for node in group.get("children", [])
        ]
        self.assertNotIn("hidden_internal_note", rendered_names)
        self.assertEqual(sheet_children[1]["children"][0]["name"], "line_ids")

    def test_governed_form_layout_overlay_takes_precedence_over_form_structure(self):
        source = {
            "model": "res.partner",
            "view_type": "form",
            "governance": {
                "view_orchestration": {
                    "applied": True,
                    "form_layout_overlay": True,
                }
            },
            "source_trace": {
                "view_orchestration": {
                    "form_layout_overlay": True,
                    "business_config_contracts": [{"id": 261, "name": "partner customer preference"}],
                }
            },
            "views": {
                "form": {
                    "layout": [
                        {
                            "type": "sheet",
                            "name": "sc_custom_partner_form_sheet",
                            "children": [
                                {
                                    "type": "group",
                                    "name": "sc_custom_partner_flat_fields",
                                    "columns": 3,
                                    "children": [
                                        {"type": "field", "name": "name", "label": "客户名称"},
                                        {"type": "field", "name": "company_type", "label": "客户类型"},
                                        {"type": "field", "name": "vat", "label": "统一社会信用代码"},
                                    ],
                                }
                            ],
                        }
                    ]
                }
            },
            "fields": {
                "name": {"name": "name", "type": "char", "string": "名称"},
                "company_type": {"name": "company_type", "type": "selection", "string": "客户类型"},
                "vat": {"name": "vat", "type": "char", "string": "税号"},
                "category_id": {"name": "category_id", "type": "many2many", "string": "标签"},
            },
            "form_structure_contract": {
                "source": "ui.contract.v2.form_structure_contract",
                "mode": "business_task_form",
                "fieldRoles": {
                    "category_id": {"role": "identity", "slot": "primary_facts", "group": "identity"},
                    "name": {"role": "identity", "slot": "primary_facts", "group": "identity"},
                },
                "slots": [
                    {
                        "slot": "primary_facts",
                        "title": "主业务事实",
                        "groups": [
                            {"name": "identity", "title": "业务识别", "fieldRefs": ["category_id", "name"]},
                        ],
                    },
                ],
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.form.layout.overlay.precedence",
        )

        self.assertNotIn("formStructureContract", full)
        group = full["layoutContract"]["containerTree"][0]["children"][0]
        self.assertEqual(group["name"], "sc_custom_partner_flat_fields")
        self.assertEqual(group["columns"], 3)
        self.assertEqual(
            [node["name"] for node in group["children"]],
            ["name", "company_type", "vat"],
        )

    def test_form_structure_contract_preserves_configured_group_columns(self):
        source = {
            "model": "res.partner",
            "view_type": "form",
            "views": {
                "form": {
                    "layout": [
                        {
                            "type": "sheet",
                            "children": [
                                {
                                    "type": "group",
                                    "name": "native_group",
                                    "cols": 2,
                                    "children": [
                                        {"type": "field", "name": "name"},
                                        {"type": "field", "name": "company_type"},
                                        {"type": "field", "name": "vat"},
                                    ],
                                }
                            ],
                        }
                    ]
                }
            },
            "fields": {
                "name": {"name": "name", "type": "char", "string": "名称"},
                "company_type": {"name": "company_type", "type": "selection", "string": "客户类型"},
                "vat": {"name": "vat", "type": "char", "string": "税号"},
            },
            "form_structure_contract": {
                "source": "ui.contract.v2.form_structure_contract",
                "mode": "business_task_form",
                "slots": [
                    {
                        "slot": "configured_form",
                        "title": "表单字段",
                        "groups": [
                            {
                                "name": "configured_group_1",
                                "title": "基础信息",
                                "cols": 3,
                                "fieldRefs": ["name", "company_type", "vat"],
                            },
                        ],
                    },
                ],
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.form.structure.configured.columns",
        )

        group = full["layoutContract"]["containerTree"][0]["children"][0]
        self.assertEqual(group["label"], "基础信息")
        self.assertEqual(group["cols"], 3)
        self.assertEqual(group["attributes"]["col"], "3")

    def test_form_structure_columns_apply_to_governed_form_layout(self):
        source = {
            "model": "res.partner",
            "view_type": "form",
            "governance": {
                "view_orchestration": {
                    "applied": True,
                    "form_layout_overlay": True,
                }
            },
            "views": {
                "form": {
                    "layout": [
                        {
                            "type": "sheet",
                            "children": [
                                {
                                    "type": "group",
                                    "name": "configured_business_fields",
                                    "string": "业务配置字段",
                                    "columns": 3,
                                    "children": [
                                        {"type": "field", "name": "name"},
                                        {"type": "field", "name": "company_type"},
                                    ],
                                }
                            ],
                        }
                    ]
                }
            },
            "fields": {
                "name": {"name": "name", "type": "char", "string": "名称"},
                "company_type": {"name": "company_type", "type": "selection", "string": "客户类型"},
            },
            "form_structure_contract": {
                "source": "ui.contract.v2.form_structure_contract",
                "mode": "business_task_form",
                "columns": 2,
                "slots": [
                    {
                        "slot": "configured_form",
                        "title": "表单字段",
                        "groups": [
                            {
                                "name": "configured_group_1",
                                "title": "业务配置字段",
                                "fieldRefs": ["name", "company_type"],
                            },
                        ],
                    },
                ],
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.form.structure.columns.overlay",
        )

        group = full["layoutContract"]["containerTree"][0]["children"][0]
        self.assertEqual(group["label"], "业务配置字段")
        self.assertEqual(group["cols"], 2)
        self.assertEqual(group["columns"], 2)
        self.assertEqual(group["attributes"]["col"], "2")

    def test_ui_contract_v2_preserves_relation_entry_search_dialog(self):
        search_dialog = {
            "columns": [
                {"name": "display_name", "label": "名称", "type": "char"},
                {"name": "phone", "label": "电话", "type": "char"},
            ],
            "read_fields": ["id", "display_name", "phone"],
            "order": "display_name asc",
            "limit": 120,
            "source": "relation_target_native_view",
        }
        source = {
            "model": "project.project",
            "view_type": "form",
            "views": {
                "form": {
                    "layout": [
                        {
                            "type": "sheet",
                            "name": "project_sheet",
                            "children": [
                                {
                                    "type": "group",
                                    "name": "project_core",
                                    "children": [{"type": "field", "name": "partner_id"}],
                                }
                            ],
                        }
                    ]
                }
            },
            "fields": {
                "partner_id": {
                    "name": "partner_id",
                    "type": "many2one",
                    "string": "客户",
                    "relation": "res.partner",
                    "relation_entry": {
                        "model": "res.partner",
                        "can_read": True,
                        "can_create": True,
                        "create_mode": "page",
                        "search_dialog": search_dialog,
                    },
                },
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.relation.search.dialog",
        )

        field_node = full["layoutContract"]["containerTree"][0]["children"][0]["children"][0]
        self.assertEqual(
            field_node["fieldInfo"]["relation_entry"]["search_dialog"]["source"],
            "relation_target_native_view",
        )
        self.assertEqual(
            field_node["componentConfig"]["relationEntry"]["search_dialog"]["columns"][1]["name"],
            "phone",
        )
        widget = full["layoutContract"]["containerTree"][0]["children"][0]["widgetList"][0]
        self.assertEqual(
            widget["componentConfig"]["relationEntry"]["search_dialog"]["read_fields"],
            ["id", "display_name", "phone"],
        )

    def test_ui_contract_v2_uses_button_badge_display_label(self):
        source = {
            "model": "project.project",
            "view_type": "form",
            "record": {
                "tender_count": 0,
            },
            "views": {
                "form": {
                    "layout": [
                        {
                            "type": "sheet",
                            "name": "project_sheet",
                            "children": [
                                {
                                    "type": "button",
                                    "name": "564",
                                    "label": "投标管理",
                                    "buttonType": "action",
                                    "action": {
                                        "name": "564",
                                        "label": "投标管理",
                                        "kind": "open",
                                        "level": "smart",
                                        "selection": "none",
                                        "intent": "open",
                                        "payload": {
                                            "ref": "564",
                                            "type": "action",
                                        },
                                        "badge": {
                                            "kind": "statinfo",
                                            "field": "tender_count",
                                            "label": "投标",
                                        },
                                    },
                                },
                            ],
                        },
                    ]
                }
            },
            "fields": {
                "tender_count": {"name": "tender_count", "type": "integer", "string": "投标"},
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.button.badge.label",
        )

        button = full["layoutContract"]["containerTree"][0]["children"][0]
        self.assertEqual(button["label"], "投标管理")
        self.assertEqual(button["displayLabel"], "0投标")
        self.assertEqual(button["action"]["displayLabel"], "0投标")

    def test_ui_contract_v2_preserves_search_filters_and_group_by(self):
        source = {
            "model": "project.project",
            "view_type": "tree",
            "views": {
                "tree": {
                    "fields": ["name", "manager_id", "lifecycle_state"],
                },
            },
            "fields": {
                "name": {"name": "name", "type": "char"},
                "manager_id": {"name": "manager_id", "type": "many2one", "relation": "res.users"},
                "lifecycle_state": {"name": "lifecycle_state", "type": "selection"},
            },
            "search": {
                "default_sort": "write_date desc",
                "filters": [
                    {"key": "filter_my_projects", "label": "我的项目", "domain_raw": "[('manager_id', '=', uid)]"},
                ],
                "saved_filters": [
                    {
                        "id": 7,
                        "name": "用户收藏",
                        "domain": [],
                        "context": {},
                        "owner": 16,
                        "is_shared": False,
                    },
                ],
                "group_by": [
                    {
                        "key": "group_manager",
                        "label": "按项目经理",
                        "field": "manager_id",
                        "context_raw": "{'group_by': 'manager_id'}",
                    },
                ],
                "fields": [{"field": "name", "label": "名称"}],
            },
        }

        full = assembler.assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            client_type="web_pc",
            request_id="test.web.search.contract",
        )

        self.assertEqual(full["searchContract"]["filters"][0]["key"], "filter_my_projects")
        self.assertEqual(full["searchContract"]["saved_filters"][0]["name"], "用户收藏")
        self.assertEqual(full["searchContract"]["group_by"][0]["field"], "manager_id")
        self.assertEqual(full["dataContract"]["search"]["default_sort"], "write_date desc")


if __name__ == "__main__":
    unittest.main()
