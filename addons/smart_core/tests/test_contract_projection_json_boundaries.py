#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import ast
import sys
import types
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SERVICE_PATH = ROOT / "addons/smart_core/app_config_engine/services/contract_governance_filter.py"
SEARCH_PATH = ROOT / "addons/smart_core/app_config_engine/models/app_search_config.py"
WORKFLOW_PATH = ROOT / "addons/smart_core/app_config_engine/models/app_workflow_config.py"


class _FieldFactory:
    def __getattr__(self, _name):
        def _field(*_args, **_kwargs):
            return None

        return _field


class _Api:
    @staticmethod
    def model(func):
        return func


class _Groups:
    ids = []


class _User:
    groups_id = _Groups()


class _Env(dict):
    uid = 7
    user = _User()

    def ref(self, *_args, **_kwargs):
        return None


class _ElementWrapper:
    def __init__(self, element, parent=None):
        self._element = element
        self._parent = parent
        self.tag = element.tag
        self.attrib = element.attrib

    def get(self, key, default=None):
        return self._element.get(key, default)

    def getparent(self):
        return self._parent

    def __iter__(self):
        return iter([_ElementWrapper(child, self) for child in list(self._element)])

    def __eq__(self, other):
        return isinstance(other, _ElementWrapper) and self._element is other._element

    def iter(self):
        rows = []

        def visit(element, parent=None):
            current = _ElementWrapper(element, parent)
            rows.append(current)
            for child in list(element):
                visit(child, current)

        visit(self._element, self._parent)
        return iter(rows)


def _install_lxml_stub():
    etree = types.SimpleNamespace(
        fromstring=lambda raw: _ElementWrapper(ET.fromstring(raw.decode("utf-8") if isinstance(raw, bytes) else raw))
    )
    lxml = types.ModuleType("lxml")
    lxml.etree = etree
    sys.modules["lxml"] = lxml
    sys.modules["lxml.etree"] = etree


def _install_odoo_stub():
    odoo = types.ModuleType("odoo")
    odoo.models = types.SimpleNamespace(Model=object, AbstractModel=object)
    odoo.fields = _FieldFactory()
    odoo.api = _Api()
    odoo._ = lambda text, *args, **kwargs: text % args if args else text

    tools = types.ModuleType("odoo.tools")
    safe_eval_mod = types.ModuleType("odoo.tools.safe_eval")
    safe_eval_mod.safe_eval = lambda value, *_args, **_kwargs: value
    tools.safe_eval = safe_eval_mod.safe_eval

    sys.modules["odoo"] = odoo
    sys.modules["odoo.tools"] = tools
    sys.modules["odoo.tools.safe_eval"] = safe_eval_mod


def _load_module(name, path):
    _install_odoo_stub()
    _install_lxml_stub()
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ContractProjectionJsonBoundaryTests(unittest.TestCase):
    def test_runtime_governance_filter_serializes_non_json_scalars(self):
        module = _load_module("smart_core_test_contract_governance_filter", SERVICE_PATH)
        owner = types.SimpleNamespace(env=_Env(), groups_id=None)

        result = module.ContractGovernanceFilterService(owner).apply_runtime_filter(
            {
                "toolbar": {"header": [{"name": "sync", "amount": Decimal("12.30")}]},
                "layout": [{"name": "base", "updated_on": date(2026, 6, 30)}],
            },
            "x.demo",
        )

        self.assertEqual(result["toolbar"]["header"][0]["amount"], "12.30")
        self.assertEqual(result["layout"][0]["updated_on"], "2026-06-30")

    def test_search_contract_serializes_non_json_scalars(self):
        module = _load_module("smart_core_test_app_search_config", SEARCH_PATH)
        record = module.AppSearchConfig.__new__(module.AppSearchConfig)
        record.env = _Env()
        record.model = "x.demo"
        record.version = 3
        record.search_def = {
            "filters": [{"key": "recent", "since": date(2026, 6, 30)}],
            "group_by": [],
            "facets": {"enabled": True},
            "defaults": {"amount": Decimal("12.30")},
        }
        record.ensure_one = lambda: None

        result = record.get_search_contract(filter_runtime=False, include_user_filters=False)

        self.assertEqual(result["filters"][0]["since"], "2026-06-30")
        self.assertEqual(result["defaults"]["amount"], "12.30")

        result = record.get_search_contract(filter_runtime=True, include_user_filters=False)
        self.assertEqual(result["filters"][0]["since"], "2026-06-30")
        self.assertEqual(result["defaults"]["amount"], "12.30")

    def test_search_view_preserves_filter_field_occurrences(self):
        module = _load_module("smart_core_test_app_search_config_occurrences", SEARCH_PATH)
        record = module.AppSearchConfig.__new__(module.AppSearchConfig)
        record._safe_eval_expr = lambda raw: ast.literal_eval(raw) if raw else None

        filters, groupbys, fields = record._parse_search_view("""
            <search>
                <group>
                    <filter name="status" string="Open" domain="[('state', '=', 'open')]" help="Open only"/>
                    <filter name="status" string="Closed" domain="[('state', '=', 'closed')]" date="date_done"/>
                    <filter name="by_partner" string="Partner" context="{'group_by': 'partner_id'}"/>
                    <field name="partner_id" string="Customer" filter_domain="[('partner_id', 'child_of', self)]"/>
                    <field name="partner_id" string="Invoice Customer" operator="=" optional="hide"/>
                </group>
            </search>
        """)

        self.assertEqual(len(filters), 2)
        self.assertEqual([item["occurrence_index"] for item in filters], [1, 2])
        self.assertNotEqual(filters[0]["native_locator"], filters[1]["native_locator"])
        self.assertEqual(filters[0]["attributes"]["help"], "Open only")
        self.assertEqual(filters[1]["date"], "date_done")
        self.assertEqual(groupbys[0]["field"], "partner_id")
        self.assertEqual(groupbys[0]["native_locator"], "/search[1]/group[1]/filter[3]")
        self.assertEqual(len(fields), 2)
        self.assertEqual([item["occurrence_index"] for item in fields], [1, 2])
        self.assertEqual(fields[0]["filter_domain"], "[('partner_id', 'child_of', self)]")
        self.assertEqual(fields[1]["attributes"]["optional"], "hide")

        search_def = record._build_search_def(
            model_name="x.demo",
            filters=filters,
            fields=fields,
            saved_filters=[],
            group_by=groupbys,
            facets={"enabled": True},
            custom={},
            defaults={"limit": 20, "order": "id desc"},
        )
        self.assertEqual([item["label"] for item in search_def["fields"]], ["Customer", "Invoice Customer"])

        with self.assertRaises(ValueError):
            record._parse_search_view("")
        with self.assertRaises(Exception):
            record._parse_search_view("<search><field></search>")

    def test_workflow_contract_serializes_non_json_scalars(self):
        module = _load_module("smart_core_test_app_workflow_config", WORKFLOW_PATH)
        record = module.AppWorkflowConfig.__new__(module.AppWorkflowConfig)
        record.env = _Env()
        record.workflows_def = {
            "states": [{"key": "draft", "updated_on": date(2026, 6, 30)}],
            "transitions": [{"key": "submit", "amount": Decimal("12.30")}],
        }
        record.ensure_one = lambda: None

        result = record.get_workflow_contract(filter_runtime=False)

        self.assertEqual(result["states"][0]["updated_on"], "2026-06-30")
        self.assertEqual(result["transitions"][0]["amount"], "12.30")


if __name__ == "__main__":
    unittest.main()
