# -*- coding: utf-8 -*-
from copy import deepcopy

from lxml import etree
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.smart_construction_core import core_extension
from odoo.addons.smart_construction_core.models.support.p1_daily_business_visible_alias_fields import (
    MODEL_LABEL_SOURCE_OVERRIDES,
    p1_visible_alias_semantics,
)


@tagged("core_extension_v2_finalize")
class TestCoreExtensionV2Finalize(TransactionCase):
    def _base_project_contract(self):
        return {
            "layoutContract": {
                "containerTree": [
                    {
                        "type": "form",
                        "containerId": "root",
                        "children": [
                            {
                                "type": "group",
                                "containerId": "base",
                                "children": [
                                    {"type": "field", "name": "user_id", "widgetId": "field.user_id"},
                                    {"type": "field", "name": "partner_id", "widgetId": "field.partner_id"},
                                    {"type": "field", "name": "manager_id", "widgetId": "field.manager_id"},
                                ],
                            }
                        ],
                    }
                ],
                "componentRegistry": {},
            },
            "statusContract": {
                "globalStatus": {"pageAuth": "edit"},
                "widgetStatus": [
                    {"widgetId": "field.user_id", "visible": True},
                    {"widgetId": "field.partner_id", "visible": True},
                ],
            },
            "runtimeContract": {},
        }

    def _field_nodes(self, value, *, include_widget_list=True):
        nodes = []
        if isinstance(value, list):
            for item in value:
                nodes.extend(self._field_nodes(item, include_widget_list=include_widget_list))
            return nodes
        if not isinstance(value, dict):
            return nodes
        if value.get("type") == "field" or str(value.get("widgetId") or "").startswith("field."):
            nodes.append(value)
        keys = ["children", "tabs", "pages", "nodes", "items"]
        if include_widget_list:
            keys.append("widgetList")
        for key in keys:
            nodes.extend(self._field_nodes(value.get(key), include_widget_list=include_widget_list))
        return nodes

    def test_finalize_handles_non_dict_context_without_mutation(self):
        contract = self._base_project_contract()

        projected = core_extension.smart_core_finalize_unified_page_contract_v2(None, contract, None)

        self.assertIsNone(projected)
        self.assertIn("field.user_id", {row["widgetId"] for row in contract["statusContract"]["widgetStatus"]})

    def test_project_form_finalize_prunes_user_field_and_adds_responsibility_group_once(self):
        contract = self._base_project_contract()
        source = {"model": "project.project", "view_type": "form", "render_profile": "edit"}

        projected = core_extension.smart_core_finalize_unified_page_contract_v2(
            self.env,
            contract,
            {"source_contract": source, "view_type": "form"},
        )
        projected_again = core_extension.smart_core_finalize_unified_page_contract_v2(
            self.env,
            deepcopy(projected),
            {"source_contract": source, "view_type": "form"},
        ) or projected

        self.assertIsInstance(projected, dict)
        field_nodes = self._field_nodes(projected["layoutContract"]["containerTree"], include_widget_list=False)
        widget_nodes = self._field_nodes(projected["layoutContract"]["containerTree"], include_widget_list=True)
        field_names = [row.get("name") or str(row.get("widgetId") or "").replace("field.", "") for row in field_nodes]
        widget_names = [row.get("fieldCode") for row in widget_nodes if row.get("fieldCode")]
        widget_status_ids = {row["widgetId"] for row in projected["statusContract"]["widgetStatus"]}

        self.assertNotIn("user_id", field_names)
        self.assertNotIn("field.user_id", widget_status_ids)
        self.assertEqual(field_names.count("responsibility_ids"), 1)
        self.assertEqual(field_names.count("collaborator_ids"), 1)
        self.assertIn("responsibility_ids", widget_names)
        self.assertIn("collaborator_ids", widget_names)
        self.assertEqual(projected["layoutContract"]["componentRegistry"]["sc.table.data"]["componentKey"], "sc.table.data")

        second_field_nodes = self._field_nodes(projected_again["layoutContract"]["containerTree"], include_widget_list=False)
        second_field_names = [
            row.get("name") or str(row.get("widgetId") or "").replace("field.", "")
            for row in second_field_nodes
        ]
        second_status_ids = {row["widgetId"] for row in projected_again["statusContract"]["widgetStatus"]}
        self.assertNotIn("user_id", second_field_names)
        self.assertNotIn("field.user_id", second_status_ids)
        self.assertEqual(second_field_names.count("responsibility_ids"), 1)
        self.assertEqual(second_field_names.count("collaborator_ids"), 1)

    def test_project_create_profile_does_not_add_collaborators(self):
        projected = core_extension.smart_core_finalize_unified_page_contract_v2(
            self.env,
            self._base_project_contract(),
            {"source_contract": {"model": "project.project", "view_type": "form", "render_profile": "create"}},
        )

        field_names = [
            row.get("name") or str(row.get("widgetId") or "").replace("field.", "")
            for row in self._field_nodes(projected["layoutContract"]["containerTree"], include_widget_list=False)
        ]

        self.assertIn("responsibility_ids", field_names)
        self.assertNotIn("collaborator_ids", field_names)

    def test_non_project_contract_is_unchanged_without_workflow_record(self):
        contract = self._base_project_contract()

        projected = core_extension.smart_core_finalize_unified_page_contract_v2(
            self.env,
            contract,
            {"source_contract": {"model": "res.partner", "view_type": "tree"}, "view_type": "tree"},
        )

        self.assertIsNone(projected)

    def test_p1_visible_amount_preserves_formal_monetary_aggregation_semantics(self):
        alias = "p1_visible_34943c40c9af"
        contract = {
            "model": "tender.doc.purchase",
            "view_type": "tree",
            "fields": {alias: {"type": "char", "string": "金额"}},
            "views": {
                "tree": {
                    "columns": [alias],
                    "columns_schema": [
                        {"name": alias, "label": "金额", "type": "char", "sum": "金额"},
                    ],
                },
            },
        }

        projected = core_extension.smart_core_normalize_projected_contract_data(
            self.env,
            contract,
            {"view_type": "tree"},
        )
        semantic = projected["views"]["tree"]["columns_schema"][0]

        self.assertEqual(semantic["display_field"], alias)
        self.assertEqual(semantic["value_field"], "amount")
        self.assertEqual(semantic["aggregation_field"], "amount")
        self.assertEqual(semantic["data_type"], "monetary")
        self.assertEqual(semantic["aggregate"], "sum")
        self.assertEqual(semantic["semantic_status"], "DECLARED")

    def test_p1_visible_amount_semantics_reach_v2_widget_config(self):
        alias = "p1_visible_34943c40c9af"
        source = {
            "model": "tender.doc.purchase",
            "view_type": "tree",
            "fields": {alias: {"type": "char", "string": "金额"}},
            "views": {
                "tree": {
                    "columns": [alias],
                    "columns_schema": [
                        {"name": alias, "label": "金额", "type": "char", "sum": "报名费合计"},
                    ],
                },
            },
        }
        contract = {
            "layoutContract": {
                "containerTree": [{
                    "containerId": "main.table",
                    "widgetList": [{
                        "widgetId": f"field.{alias}",
                        "widgetType": "table",
                        "fieldCode": alias,
                        "componentConfig": {"fieldType": "char"},
                    }],
                }],
            },
        }

        projected = core_extension.smart_core_finalize_unified_page_contract_v2(
            self.env,
            contract,
            {"source_contract": source, "view_type": "tree"},
        )
        semantic = projected["layoutContract"]["containerTree"][0]["widgetList"][0]["componentConfig"]

        self.assertEqual(semantic["display_field"], alias)
        self.assertEqual(semantic["value_field"], "amount")
        self.assertEqual(semantic["aggregation_field"], "amount")
        self.assertEqual(semantic["data_type"], "monetary")
        self.assertEqual(semantic["currency_field"], "currency_id")
        self.assertEqual(semantic["aggregate"], "sum")
        self.assertEqual(semantic["aggregate_label"], "报名费合计")

    def test_all_runtime_p1_aliases_have_an_explicit_semantic_classification(self):
        unresolved = []
        inspected = 0
        for model_name in sorted(MODEL_LABEL_SOURCE_OVERRIDES):
            if model_name not in self.env:
                continue
            model = self.env[model_name]
            for field_name in sorted(name for name in model._fields if name.startswith("p1_visible_")):
                inspected += 1
                semantic = p1_visible_alias_semantics(model, field_name)
                self.assertIn(
                    semantic.get("semantic_status"),
                    {"DECLARED", "UNRESOLVED_FORMAL_SOURCE"},
                    f"{model_name}.{field_name}",
                )
                source_name = semantic.get("value_field")
                if not source_name:
                    unresolved.append((model_name, field_name))
                    continue
                self.assertIn(source_name, model._fields)
                self.assertEqual(semantic.get("data_type"), model._fields[source_name].type)
        self.assertGreater(inspected, 0)
        self.assertLessEqual(len(unresolved), inspected)

    def test_all_published_list_sum_fields_have_numeric_formal_semantics(self):
        numeric_types = {"integer", "float", "monetary"}
        for view in self.env["ir.ui.view"].sudo().search([("type", "in", ["tree", "list"]), ("active", "=", True)]):
            model_name = str(view.model or "")
            if not model_name or model_name not in self.env:
                continue
            try:
                root = etree.fromstring((view.arch_db or "<tree/>").encode())
            except etree.XMLSyntaxError:
                continue
            model = self.env[model_name]
            for node in root.xpath(".//field[@sum]"):
                field_name = str(node.get("name") or "").strip()
                field = model._fields.get(field_name)
                source_type = str(getattr(field, "type", "") or "")
                if field_name.startswith("p1_visible_"):
                    semantic = p1_visible_alias_semantics(model, field_name)
                    source_type = str(semantic.get("data_type") or "")
                    self.assertTrue(semantic.get("value_field"), f"{model_name}.{field_name}")
                self.assertIn(source_type, numeric_types, f"{model_name}.{field_name}")

    def test_projected_data_finalize_does_not_override_business_list_config_columns(self):
        data = {
            "model": "project.material.plan",
            "view_type": "tree",
            "action_id": 525,
            "list_profile": {
                "columns": [
                    "legacy_visible_01",
                    "legacy_visible_02",
                    "source_created_by",
                    "source_created_at",
                ],
                "fact_columns": [
                    "legacy_visible_01",
                    "legacy_visible_02",
                    "source_created_by",
                    "source_created_at",
                ],
                "column_policy": {
                    "mode": "strict",
                    "reason": "business_list_config_contract_authoritative",
                },
            },
        }

        projected = core_extension.smart_core_finalize_projected_contract_data(self.env, data, {"view_type": "tree"})

        self.assertIsNone(projected)
