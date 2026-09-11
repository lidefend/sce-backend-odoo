# -*- coding: utf-8 -*-
from copy import deepcopy

from lxml import etree
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.smart_construction_core import core_extension
from odoo.addons.smart_core.utils import contract_governance


@tagged("core_extension_v2_finalize")
class TestCoreExtensionV2Finalize(TransactionCase):
    @staticmethod
    def _effective_view_constraints(node):
        constraints = {}
        for attribute in ("groups", "invisible", "readonly", "required"):
            values = [
                current.get(attribute)
                for current in [node, *node.iterancestors()]
                if current.get(attribute) not in (None, "")
            ]
            constraints[attribute] = tuple(values)
        return constraints

    def test_project_maintenance_form_uses_authoritative_business_sections(self):
        view = self.env.ref("smart_construction_core.view_project_form_sc_core")
        arch = view._get_combined_arch()
        if isinstance(arch, (str, bytes)):
            arch = etree.fromstring(arch)

        sheet = arch.xpath("//form/sheet")[0]
        direct_groups = sheet.xpath("./group[@data-sc-anchor]")
        self.assertEqual(
            [group.get("string") for group in direct_groups[:4]],
            ["基本信息", "计划与责任", "责任矩阵", "关联业务"],
        )
        self.assertEqual(
            direct_groups[0].xpath(".//field/@name"),
            [
                "project_code", "partner_id", "project_type_id", "project_category_id",
                "operation_strategy", "location", "owner_contact", "contract_no", "phase_key",
            ],
        )
        self.assertEqual(
            direct_groups[1].xpath(".//field/@name"),
            [
                "initiation_date", "date_start", "start_date", "end_date", "user_id",
                "manager_id", "cost_manager_id", "doc_manager_id",
            ],
        )
        self.assertEqual(direct_groups[2].xpath("./field/@name"), ["responsibility_ids"])
        related_business = direct_groups[3]
        self.assertEqual(related_business.get("data-sc-anchor"), "project-related-business")
        self.assertEqual(
            related_business.get("col"),
            "1",
            "the project view, rather than a frontend widget heuristic, owns the related-business width",
        )
        self.assertEqual(len(related_business.xpath("./notebook")), 1)

        expected_identity_columns = {
            "wbs_ids": ["name", "code"],
            "boq_line_ids": ["name", "code"],
            "work_ids": ["name", "code"],
            "contract_ids": ["name", "subject"],
            "document_ids": ["name", "wbs_id"],
            "tender_bid_ids": ["tender_name", "tender_round"],
        }
        for field_name, expected_columns in expected_identity_columns.items():
            field = related_business.xpath(
                f".//field[@name='{field_name}' and not(ancestor::field)]"
            )[0]
            self.assertEqual(
                field.xpath("./tree/field/@name")[:2],
                expected_columns,
                f"{field_name} must expose record identity before auxiliary columns",
            )

        page_names = related_business.xpath("./notebook/page/@name")
        self.assertLess(page_names.index("sc_cockpit"), page_names.index("sc_construction"))
        operation_page = related_business.xpath("./notebook/page[@name='sc_construction']")[0]
        self.assertEqual(operation_page.get("string"), "经营概况")
        self.assertEqual(
            operation_page.xpath("./group/@string"),
            ["录入来源", "成本与进度"],
        )

        auxiliary_fields = related_business.xpath("./notebook/page[@name='sc_system']/group/field/@name")
        self.assertEqual(auxiliary_fields[:2], ["label_tasks", "tag_ids"])
        self.assertEqual(len(arch.xpath("//field[@name='responsibility_ids' and not(ancestor::field)]")), 1)
        self.assertEqual(len(arch.xpath("//field[@name='partner_id' and not(ancestor::field)]")), 1)
        self.assertEqual(len(arch.xpath("//form/header//field[@name='lifecycle_state']")), 1)
        self.assertEqual(len(arch.xpath("//sheet//field[@name='lifecycle_state']")), 0)

        callout = " ".join(arch.xpath("//sheet/div[contains(@class, 'alert')]/text()"))
        self.assertNotIn("自动保存", callout)
        self.assertIn("保存修改", callout)
        self.assertIn("提交立项", callout)

    def test_project_maintenance_form_preserves_moved_field_constraints(self):
        base_view = self.env.ref("project.edit_project")
        base_arch = etree.fromstring(base_view.arch_db.encode())
        merged_arch = self.env.ref(
            "smart_construction_core.view_project_form_sc_core"
        )._get_combined_arch()
        if isinstance(merged_arch, (str, bytes)):
            merged_arch = etree.fromstring(merged_arch)

        for field_name in ("partner_id", "user_id", "date_start", "label_tasks", "tag_ids"):
            base_nodes = base_arch.xpath(
                f"//sheet//field[@name='{field_name}' and not(ancestor::field)]"
            )
            merged_nodes = merged_arch.xpath(
                f"//sheet//field[@name='{field_name}' and not(ancestor::field)]"
            )
            self.assertEqual(len(base_nodes), 1, f"base field identity is ambiguous: {field_name}")
            self.assertEqual(len(merged_nodes), 1, f"moved field identity is ambiguous: {field_name}")
            self.assertEqual(
                self._effective_view_constraints(merged_nodes[0]),
                self._effective_view_constraints(base_nodes[0]),
                f"moved field constraints changed: {field_name}",
            )

        restricted_fields = (
            "project_code", "project_type_id", "project_category_id", "operation_strategy",
            "location", "owner_contact", "contract_no", "phase_key", "initiation_date",
            "start_date", "end_date", "manager_id", "cost_manager_id", "doc_manager_id",
            "responsibility_ids",
        )
        for field_name in restricted_fields:
            node = merged_arch.xpath(
                f"//sheet//field[@name='{field_name}' and not(ancestor::field)]"
            )[0]
            effective_groups = ",".join(self._effective_view_constraints(node)["groups"])
            self.assertIn(
                "smart_construction_core.group_sc_cap_project_read",
                effective_groups,
                f"project-read visibility constraint was lost: {field_name}",
            )

        company = self.env.ref("base.main_company")
        internal_user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "project-form-without-capability",
            "login": "project-form-without-capability",
            "email": "project-form-without-capability@example.com",
            "company_id": company.id,
            "company_ids": [(6, 0, [company.id])],
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        project_reader = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "project-form-with-capability",
            "login": "project-form-with-capability",
            "email": "project-form-with-capability@example.com",
            "company_id": company.id,
            "company_ids": [(6, 0, [company.id])],
            "groups_id": [(6, 0, [
                self.env.ref("smart_construction_core.group_sc_cap_project_read").id,
            ])],
        })
        view_id = self.env.ref("smart_construction_core.view_project_form_sc_core").id
        without_capability = etree.fromstring(
            self.env["project.project"].with_user(internal_user).get_view(
                view_id=view_id, view_type="form"
            )["arch"].encode()
        )
        with_capability = etree.fromstring(
            self.env["project.project"].with_user(project_reader).get_view(
                view_id=view_id, view_type="form"
            )["arch"].encode()
        )
        for field_name in restricted_fields:
            selector = f"//sheet//field[@name='{field_name}' and not(ancestor::field)]"
            self.assertFalse(without_capability.xpath(selector), field_name)
            self.assertTrue(with_capability.xpath(selector), field_name)
        for field_name in ("partner_id", "user_id", "date_start"):
            selector = f"//sheet//field[@name='{field_name}' and not(ancestor::field)]"
            self.assertTrue(without_capability.xpath(selector), field_name)
            self.assertTrue(with_capability.xpath(selector), field_name)

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

    def test_payment_settlement_lines_use_explicit_professional_component_contract(self):
        contract = {
            "layoutContract": {
                "containerTree": [{
                    "type": "group",
                    "children": [{
                        "type": "field",
                        "name": "outflow_line_ids",
                        "widgetId": "field.outflow_line_ids",
                        "componentKey": "sc.relation.table",
                        "componentConfig": {"fieldType": "one2many"},
                    }],
                    "widgetList": [{
                        "widgetId": "field.outflow_line_ids",
                        "fieldCode": "outflow_line_ids",
                        "componentKey": "sc.relation.table",
                        "componentConfig": {"fieldType": "one2many"},
                    }],
                }],
                "componentRegistry": {},
            },
            "statusContract": {"globalStatus": {}, "widgetStatus": []},
            "runtimeContract": {},
        }

        projected = core_extension.smart_core_finalize_unified_page_contract_v2(
            self.env,
            contract,
            {"source_contract": {"model": "payment.request", "view_type": "form"}},
        )

        nodes = [
            row for row in self._field_nodes(projected["layoutContract"]["containerTree"])
            if row.get("name") == "outflow_line_ids" or row.get("fieldCode") == "outflow_line_ids"
        ]
        self.assertTrue(nodes)
        self.assertTrue(all(row["componentKey"] == "sc.payment.settlement_detail_collection" for row in nodes))
        self.assertEqual(
            nodes[0]["componentConfig"]["actionRefs"],
            {
                "search": "payment.request.settlement.search",
                "preview": "payment.request.settlement.preview",
                "introduce": "payment.request.add.settlement.lines",
            },
        )
        self.assertEqual(
            projected["layoutContract"]["componentRegistry"]["sc.payment.settlement_detail_collection"]["adapter"]["web_pc"],
            "PaymentSettlementDetailCollectionControl",
        )

    def test_payment_and_project_forms_share_existing_v2_minimum_authority_chain(self):
        contracts = {
            "project.project": {
                "layoutContract": {
                    "containerTree": [{
                        "type": "group",
                        "containerId": "project.task",
                        "children": [{
                            "type": "field",
                            "name": "manager_id",
                            "fieldCode": "manager_id",
                            "widgetId": "field.manager_id",
                            "componentKey": "sc.value.user",
                            "componentConfig": {
                                "fieldType": "many2one",
                                "relationModel": "res.users",
                            },
                        }],
                    }],
                    "componentRegistry": {
                        "sc.value.user": {
                            "version": "1.0",
                            "adapter": {"web_pc": "UserValueControl"},
                        },
                    },
                },
                "statusContract": {
                    "globalStatus": {"pageAuth": "edit"},
                    "widgetStatus": [{
                        "widgetId": "field.manager_id",
                        "visible": True,
                        "readonly": False,
                        "required": True,
                        "disabled": False,
                        "auth": "edit",
                    }],
                },
                "actionContract": {
                    "actionRuleList": [{
                        "actionId": "form.save",
                        "sourceWidgetId": "form.project.project",
                        "backendIdentity": "project.project.create",
                    }],
                },
                "runtimeContract": {},
            },
            "payment.request": {
                "layoutContract": {
                    "containerTree": [{
                        "type": "group",
                        "containerId": "payment.relations",
                        "children": [{
                            "type": "field",
                            "name": "outflow_line_ids",
                            "fieldCode": "outflow_line_ids",
                            "widgetId": "field.outflow_line_ids",
                            "componentKey": "sc.relation.table",
                            "componentConfig": {"fieldType": "one2many"},
                        }],
                    }],
                    "componentRegistry": {},
                },
                "statusContract": {
                    "globalStatus": {"pageAuth": "edit"},
                    "widgetStatus": [{
                        "widgetId": "field.outflow_line_ids",
                        "visible": True,
                        "readonly": False,
                        "required": False,
                        "disabled": False,
                        "auth": "edit",
                    }],
                },
                "actionContract": {
                    "actionRuleList": [{
                        "actionId": "form.save",
                        "sourceWidgetId": "form.payment.request",
                        "backendIdentity": "payment.request.write",
                    }],
                },
                "runtimeContract": {},
            },
        }

        projected_by_model = {}
        for model_name, contract in contracts.items():
            projected = core_extension.smart_core_finalize_unified_page_contract_v2(
                self.env,
                contract,
                {"source_contract": {"model": model_name, "view_type": "form"}},
            ) or contract
            projected_by_model[model_name] = projected
            widgets = self._field_nodes(projected["layoutContract"]["containerTree"])
            self.assertTrue(widgets, model_name)
            status_by_id = {
                row["widgetId"]: row
                for row in projected["statusContract"]["widgetStatus"]
            }
            registry = projected["layoutContract"]["componentRegistry"]

            for widget in widgets:
                widget_id = widget.get("widgetId")
                component_key = widget.get("componentKey")
                self.assertTrue(widget.get("fieldCode") or widget.get("name"), model_name)
                self.assertTrue(widget_id, model_name)
                self.assertTrue(component_key, model_name)
                self.assertIn(widget_id, status_by_id, model_name)
                self.assertIn(component_key, registry, model_name)

            action = projected["actionContract"]["actionRuleList"][0]
            self.assertEqual(action["actionId"], "form.save")
            self.assertTrue(action["sourceWidgetId"], model_name)
            self.assertTrue(action["backendIdentity"], model_name)

        payment_widget = self._field_nodes(
            projected_by_model["payment.request"]["layoutContract"]["containerTree"]
        )[0]
        self.assertEqual(
            payment_widget["componentConfig"]["actionRefs"]["introduce"],
            "payment.request.add.settlement.lines",
        )

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
