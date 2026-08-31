# -*- coding: utf-8 -*-
from copy import deepcopy

from lxml import etree
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.smart_construction_core import core_extension
from odoo.addons.smart_core.utils import contract_governance


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

    def test_project_form_finalize_keeps_native_membership_and_adds_responsibility_group_once(self):
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

        self.assertIn("user_id", field_names)
        self.assertIn("field.user_id", widget_status_ids)
        self.assertEqual(field_names.count("responsibility_ids"), 1)
        self.assertEqual(field_names.count("collaborator_ids"), 1)
        self.assertIn("responsibility_ids", widget_names)
        self.assertIn("collaborator_ids", widget_names)
        self.assertTrue(all("field_info" not in row for row in field_nodes))
        self.assertEqual(projected["layoutContract"]["componentRegistry"]["sc.relation.table"]["version"], "1.0")
        self.assertEqual(projected["layoutContract"]["componentRegistry"]["sc.relation.many2many"]["version"], "1.0")
        widget_component_keys = {
            row.get("fieldCode"): row.get("componentKey")
            for row in widget_nodes
            if row.get("fieldCode") in {"responsibility_ids", "collaborator_ids"}
        }
        self.assertEqual(widget_component_keys["responsibility_ids"], "sc.relation.table")
        self.assertEqual(widget_component_keys["collaborator_ids"], "sc.relation.many2many")
        self.assertIn(
            "sc_project_responsibility_collaboration",
            {row["containerId"] for row in projected["statusContract"]["containerStatus"]},
        )

        second_field_nodes = self._field_nodes(projected_again["layoutContract"]["containerTree"], include_widget_list=False)
        second_field_names = [
            row.get("name") or str(row.get("widgetId") or "").replace("field.", "")
            for row in second_field_nodes
        ]
        second_status_ids = {row["widgetId"] for row in projected_again["statusContract"]["widgetStatus"]}
        self.assertIn("user_id", second_field_names)
        self.assertIn("field.user_id", second_status_ids)
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

    def test_explicit_project_form_view_keeps_native_field_membership(self):
        contract = self._base_project_contract()

        projected = core_extension.smart_core_finalize_unified_page_contract_v2(
            self.env,
            contract,
            {
                "source_contract": {
                    "model": "project.project",
                    "view_type": "form",
                    "render_profile": "readonly",
                },
                "view_type": "form",
                "meta": {"params": {"viewId": 1700}},
            },
        )

        self.assertIsInstance(projected, dict)
        field_names = {
            row.get("name") or str(row.get("widgetId") or "").replace("field.", "")
            for row in self._field_nodes(projected["layoutContract"]["containerTree"], include_widget_list=False)
        }
        self.assertIn("user_id", field_names)
        self.assertNotIn("responsibility_ids", field_names)
        self.assertNotIn("collaborator_ids", field_names)
        self.assertIn(
            "root",
            {row["containerId"] for row in projected["statusContract"]["containerStatus"]},
        )

    def test_non_project_contract_is_unchanged_without_workflow_record(self):
        contract = self._base_project_contract()

        projected = core_extension.smart_core_finalize_unified_page_contract_v2(
            self.env,
            contract,
            {"source_contract": {"model": "res.partner", "view_type": "tree"}, "view_type": "tree"},
        )

        self.assertIsNone(projected)

    def test_general_contract_normalizer_preserves_native_v2_form_identity(self):
        widget_id = "field.contract_name.occ.native"
        contract = {
            "pageInfo": {"model": "sc.general.contract", "viewType": "form"},
            "layoutContract": {
                "containerTree": [
                    {
                        "type": "group",
                        "containerType": "group",
                        "containerId": "native.group.contract",
                        "children": [
                            {
                                "type": "field",
                                "containerType": "field",
                                "containerId": widget_id,
                                "widgetId": widget_id,
                                "fieldCode": "contract_name",
                                "nativeLocator": "form/group[1]/field[name=contract_name]",
                                "occurrenceIndex": 1,
                                "sourcePosition": 2,
                                "children": [],
                                "widgetList": [],
                            }
                        ],
                        "widgetList": [],
                    }
                ]
            },
            "statusContract": {
                "widgetStatus": [
                    {
                        "widgetId": widget_id,
                        "visible": True,
                        "readonly": False,
                        "required": True,
                        "disabled": False,
                        "auth": "edit",
                    }
                ]
            },
        }
        original = deepcopy(contract)

        projected = core_extension.smart_core_normalize_unified_page_contract_v2(
            self.env,
            contract,
            {"source_contract": {"model": "sc.general.contract", "view_type": "form"}},
        )

        self.assertIsNone(projected)
        self.assertEqual(contract, original)

    def test_standard_product_models_do_not_register_migration_aliases(self):
        for model_name in ("payment.request", "tender.doc.purchase", "construction.contract"):
            aliases = [name for name in self.env[model_name]._fields if name.startswith("p1_visible_")]
            self.assertFalse(aliases, model_name)

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

    def test_payment_request_formal_list_projects_page_and_total_amount_semantics(self):
        action = self.env.ref(
            "smart_construction_core.action_payment_request_user_payment_apply"
        )
        projected = core_extension.smart_core_finalize_projected_contract_data(
            self.env,
            {
                "model": "payment.request",
                "view_type": "tree",
                "action_id": action.id,
                "fields": {},
                "views": {},
            },
            {"view_type": "tree"},
        )

        self.assertIsInstance(projected, dict)
        schema = {
            row["name"]: row
            for row in projected["views"]["tree"]["columns_schema"]
        }
        amount = schema["request_amount_display"]
        self.assertEqual(amount["display_field"], "request_amount_display")
        self.assertEqual(amount["value_field"], "amount")
        self.assertEqual(amount["aggregation_field"], "amount")
        self.assertEqual(amount["data_type"], "monetary")
        self.assertEqual(amount["currency_field"], "currency_id")
        self.assertEqual(amount["aggregate"], "sum")
        self.assertEqual(amount["sum"], "申请付款金额合计")
        self.assertEqual(amount["sort_field"], "amount")
        self.assertEqual(amount["filter_field"], "amount")
        self.assertEqual(amount["export_field"], "amount")

    def test_project_list_profile_keeps_native_optional_manager_column_hidden(self):
        data = {
            "model": "project.project",
            "view_type": "tree",
            "fields": {
                "name": {"type": "char", "string": "项目名称"},
                "project_code": {"type": "char", "string": "项目编号"},
                "user_id": {"type": "many2one", "string": "项目负责人"},
                "manager_id": {"type": "many2one", "string": "项目经理"},
            },
            "views": {
                "tree": {
                    "columns": ["name", "project_code", "user_id", "manager_id"],
                    "columns_schema": [
                        {"name": "name", "label": "项目名称", "optional": "show"},
                        {"name": "project_code", "label": "项目编号", "optional": "show"},
                        {"name": "user_id", "label": "项目负责人", "optional": "show"},
                        {"name": "manager_id", "label": "项目经理", "optional": "hide"},
                    ],
                }
            },
        }

        contract_governance.apply_project_form_domain_override(data, "user")

        profile = data["list_profile"]
        self.assertIn("user_id", profile["columns"])
        self.assertIn("manager_id", profile["columns"])
        self.assertEqual(profile["column_labels"]["user_id"], "项目负责人")
        self.assertEqual(profile["column_labels"]["manager_id"], "项目经理")
        manager_schema = next(row for row in data["views"]["tree"]["columns_schema"] if row["name"] == "manager_id")
        self.assertEqual(manager_schema["optional"], "hide")

    def test_project_governance_does_not_change_explicit_native_form_membership(self):
        data = {
            "model": "project.project",
            "view_type": "form",
            "fields": {
                "user_id": {"type": "many2one", "string": "项目负责人"},
            },
            "views": {"form": {
                "meta": {"projection_identity": {"source_view_id": 1700}},
                "layout": [{"type": "field", "name": "user_id"}],
            }},
        }

        contract_governance.apply_project_form_domain_override(data, "user")

        self.assertEqual(data["views"]["form"]["layout"], [{"type": "field", "name": "user_id"}])
        self.assertNotIn("responsibility_ids", data["fields"])
        self.assertNotIn("collaborator_ids", data["fields"])

    def test_partner_trace_columns_have_business_labels(self):
        labels = core_extension.smart_core_legacy_visible_business_column_labels(self.env)

        self.assertEqual(labels["project.project"]["name"], "项目名称")
        partner_labels = labels["res.partner"]
        self.assertEqual(partner_labels["sc_business_role_label"], "业务角色")
        self.assertEqual(partner_labels["sc_source_project_name"], "来源项目")
        self.assertEqual(partner_labels["sc_source_partner_code"], "来源客商编码")

    def test_partner_trace_columns_are_opt_in_by_default(self):
        policy = core_extension.smart_core_business_list_default_visibility(self.env)["res.partner"]

        self.assertNotIn("visible", policy)
        self.assertIn("sc_source_project_name", policy["hidden"])
        self.assertIn("sc_business_role_label", policy["hidden"])
