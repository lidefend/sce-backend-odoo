# -*- coding: utf-8 -*-
import base64
import json

from odoo.tests import TransactionCase, tagged

from odoo.addons.smart_core.core.page_block_data_contract import field_descriptor
from odoo.addons.smart_core.core.unified_page_contract_v2_assembler import (
    _strict_field_descriptor,
    _upgrade_contract_v2_field_descriptors,
    assemble_unified_page_contract_v2,
)
from odoo.addons.smart_construction_core.handlers.workspace_home_enter import WorkspaceHomeEnterHandler
from odoo.addons.smart_construction_core.services.scene_block_schema import build_contract, metric_card
from odoo.addons.smart_construction_core.services.workspace_contract_builder import WorkspaceContractBuilder


def _build_real_money_contract(env):
    project = env["project.project"].create({
        "name": "P0-A contract producer",
        "company_id": env.company.id,
    })
    field = project._fields["budget_active_cost_target"]
    if field.type != "monetary":
        raise AssertionError("budget_active_cost_target must be monetary")
    currency = project.company_currency_id or env.company.currency_id
    if not currency:
        raise AssertionError("P0-A monetary fixture requires a company currency")
    block = metric_card(
        "budget_active_cost_target",
        "当前预算成本",
        project.budget_active_cost_target,
        subtitle="真实项目金额事实",
        currency_identity=currency.id,
        currency={
            "id": currency.id,
            "code": currency.name,
            "symbol": currency.symbol,
        },
    )
    block["value_descriptor"] = field_descriptor(
        field_code="project.budget_active_cost_target",
        label="当前预算成本",
        field_type="monetary",
        widget_type="monetary",
        semantic_type="money",
        digits=[16, int(currency.decimal_places or 2)],
        currencyField="company_currency_id",
    )
    return build_contract(
        scene_key="p0a.monetary",
        title="P0-A 金额",
        blocks=[block],
        page_block_data_enabled=True,
        timezone=env.user.tz or "UTC",
    ), project, currency


@tagged("post_install", "-at_install", "p0_contract_producer_p0a")
class TestP0ContractProducerP0A(TransactionCase):
    def _request(self, **params):
        return {
            "params": {
                "client_type": "web_pc",
                "accepted_contract_versions": ["2.7.x"],
                "client_contract_capabilities": ["page_block_data.v1"],
                **params,
            }
        }

    def test_workspace_page_block_data_uses_real_orm_counts_and_raw_types(self):
        contract = WorkspaceContractBuilder(self.env).build(page_block_data_enabled=True)
        orchestration = contract["page_orchestration"]
        self.assertEqual(orchestration["contract_version"], "2.1.0")
        self.assertEqual(orchestration["schema_version"], "2.1.0")
        self.assertIn("block_field_descriptors", orchestration)
        self.assertIn("block_data_contracts", orchestration)
        self.assertAlmostEqual(
            orchestration["block_data_contracts"]["ds_project_total"]["rows"][0]["values"]["value"],
            float(self.env["project.project"].search_count([])),
            places=7,
        )
        descriptor = orchestration["block_field_descriptors"]["project_total.value"]
        self.assertEqual(descriptor["semanticType"], "number")
        self.assertEqual(descriptor["fieldType"], "integer")

    def test_workspace_projection_without_page_block_carrier(self):
        contract = WorkspaceContractBuilder(self.env).build(page_block_data_enabled=False)
        orchestration = contract["page_orchestration"]
        self.assertEqual(orchestration["contract_version"], "2.0.0")
        self.assertNotIn("block_field_descriptors", orchestration)
        self.assertNotIn("block_data_contracts", orchestration)

    def test_handler_negotiates_current_projection_only_for_declared_capability(self):
        handler = WorkspaceHomeEnterHandler(self.env)
        current = handler.handle(self._request())
        self.assertTrue(current["ok"])
        self.assertEqual(current["data"]["page_orchestration"]["contract_version"], "2.1.0")
        self.assertEqual(current["meta"]["contract_negotiation"]["contractVersion"], "2.7.0")

        unsupported = handler.handle({
            "params": {
                "client_type": "web_pc",
                "accepted_contract_versions": ["2.6.x"],
                "client_contract_capabilities": [],
            }
        })
        self.assertFalse(unsupported["ok"])
        self.assertEqual(unsupported["error"]["reason_code"], "CONTRACT_VERSION_UNSUPPORTED")

    def test_handler_rejects_unknown_client_negotiation(self):
        result = WorkspaceHomeEnterHandler(self.env).handle({
            "params": {
                "client_type": "unknown_native",
                "accepted_contract_versions": ["2.6.x"],
                "client_contract_capabilities": ["page_block_data.v1"],
            }
        })
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["reason_code"], "CONTRACT_VERSION_UNSUPPORTED")

    def test_pre_negotiation_request_fails_closed(self):
        result = WorkspaceHomeEnterHandler(self.env).handle({"params": {}})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["reason_code"], "CONTRACT_VERSION_UNSUPPORTED")

    def test_handler_rejects_24_only_as_no_common_version(self):
        result = WorkspaceHomeEnterHandler(self.env).handle({
            "params": {
                "client_type": "web_pc",
                "accepted_contract_versions": ["2.4.x"],
                "client_contract_capabilities": [],
            }
        })
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["reason_code"], "CONTRACT_VERSION_UNSUPPORTED")

    def test_handler_rejects_20_only_as_no_common_version(self):
        result = WorkspaceHomeEnterHandler(self.env).handle({
            "params": {
                "client_type": "web_pc",
                "accepted_contract_versions": ["2.0.x"],
                "client_contract_capabilities": [],
            }
        })
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["reason_code"], "CONTRACT_VERSION_UNSUPPORTED")

    def test_real_monetary_model_field_keeps_raw_value_and_currency_semantics(self):
        contract, project, currency = _build_real_money_contract(self.env)
        data_contract = contract["page_orchestration"]["block_data_contracts"]["ds_budget_active_cost_target"]
        row = data_contract["rows"][0]
        self.assertEqual(row["values"]["value"], project.budget_active_cost_target)
        self.assertEqual(row["values"]["company_currency_id"], currency.id)
        self.assertIn("company_currency_id", data_contract["fieldRefs"])
        self.assertEqual(
            data_contract["context"]["currencies"][str(currency.id)]["code"],
            currency.name,
        )
        descriptor = contract["page_orchestration"]["block_field_descriptors"]["budget_active_cost_target.value"]
        self.assertEqual(descriptor["semanticType"], "money")
        self.assertEqual(descriptor["currencyField"], "company_currency_id")
        self.assertEqual(descriptor["digits"], [16, int(currency.decimal_places or 2)])
        currency_descriptor = contract["page_orchestration"]["block_field_descriptors"][
            "budget_active_cost_target.company_currency_id"
        ]
        self.assertEqual(currency_descriptor["fieldCode"], "company_currency_id")
        self.assertEqual(currency_descriptor["relation"], "res.currency")

    def test_real_monetary_page_block_without_currency_identity_fails_closed(self):
        project = self.env["project.project"].create({
            "name": "P0-A missing currency",
            "company_id": self.env.company.id,
        })
        block = metric_card(
            "missing_currency_amount",
            "缺少币种金额",
            project.budget_active_cost_target,
        )
        block["value_descriptor"] = field_descriptor(
            field_code="project.budget_active_cost_target",
            label="缺少币种金额",
            field_type="monetary",
            widget_type="monetary",
            semantic_type="money",
            digits=[16, int(project.company_currency_id.decimal_places or 2)],
            currencyField="company_currency_id",
        )
        with self.assertRaisesRegex(ValueError, "requires a declared currency field and matching identity"):
            build_contract(
                scene_key="p0a.missing.currency",
                title="P0-A 缺少币种",
                blocks=[block],
                page_block_data_enabled=True,
                timezone=self.env.user.tz or "UTC",
            )

    def test_strict_widget_descriptor_uses_native_vocabulary_and_selection_pairs(self):
        descriptor = _strict_field_descriptor({
            "fieldCode": "operation_strategy",
            "label": "经营方式",
            "fieldDescriptor": {
                "schemaVersion": "1.0.0",
                "name": "operation_strategy",
                "type": "selection",
                "widget": "selection",
                "help": "选择项目的经营模式",
                "sc_ui_usage": "fact",
                "change_default": True,
                "searchable": True,
                "sortable": False,
                "store": True,
                "translate": True,
                "trim": True,
                "size": 64,
                "related": ["parent_id", "operation_strategy"],
            },
            "componentConfig": {
                "fieldType": "selection",
                "selection": [
                    {"value": "direct", "label": "公司直营"},
                    {"value": "joint", "label": "联营项目"},
                ],
            },
        })
        self.assertIsNotNone(descriptor)
        self.assertEqual(descriptor["widgetType"], "select")
        self.assertEqual(descriptor["semanticType"], "choice")
        self.assertEqual(descriptor["help"], "选择项目的经营模式")
        self.assertEqual(descriptor["uiUsage"], "fact")
        self.assertIs(descriptor["changeDefault"], True)
        self.assertIs(descriptor["searchable"], True)
        self.assertIs(descriptor["sortable"], False)
        self.assertIs(descriptor["store"], True)
        self.assertIs(descriptor["translate"], True)
        self.assertIs(descriptor["trim"], True)
        self.assertEqual(descriptor["size"], 64)
        self.assertEqual(descriptor["related"], ["parent_id", "operation_strategy"])
        self.assertEqual(
            descriptor["selection"],
            [["direct", "公司直营"], ["joint", "联营项目"]],
        )

        numeric = _strict_field_descriptor({
            "fieldCode": "dashboard_progress_rate",
            "label": "进度(%)",
            "fieldDescriptor": {
                "schemaVersion": "1.0.0",
                "name": "dashboard_progress_rate",
                "type": "float",
                "widget": "float",
            },
            "componentConfig": {"fieldType": "float"},
        })
        self.assertIsNotNone(numeric)
        self.assertEqual(numeric["widgetType"], "number")
        self.assertEqual(numeric["semanticType"], "number")

    def test_strict_descriptor_separates_native_expression_from_contract_semantics(self):
        """Native widget tokens remain presentation facts; contract meaning is canonical.

        This matrix is intentionally broader than the reported daterange case:
        explicit native rules keep their declared meaning, while recognizable
        presentation variants fall back to the canonical field-type/control
        semantics instead of the generic readable-value default.
        """
        cases = (
            {
                "fieldCode": "date_start",
                "label": "项目周期",
                "fieldType": "date",
                "nativeWidget": "daterange",
                "semanticType": "date",
                "widgetOptions": {"end_date_field": "date", "always_range": "1"},
            },
            {
                "fieldCode": "display_date",
                "label": "日期展示",
                "fieldType": "date",
                "nativeWidget": "display",
                "semanticType": "date",
            },
            {
                "fieldCode": "planned_at",
                "label": "计划时间",
                "fieldType": "datetime",
                "nativeWidget": "display",
                "semanticType": "datetime",
            },
            {
                "fieldCode": "phone",
                "label": "电话",
                "fieldType": "char",
                "nativeWidget": "phone",
                "semanticType": "text",
            },
            {
                "fieldCode": "state",
                "label": "状态",
                "fieldType": "selection",
                "nativeWidget": "statusbar",
                "semanticType": "status",
            },
            {
                "fieldCode": "activity_ids",
                "label": "活动",
                "fieldType": "one2many",
                "nativeWidget": "list_activity",
                "semanticType": "activity_collection",
                "relation": "mail.activity",
            },
            {
                "fieldCode": "tag_ids",
                "label": "标签",
                "fieldType": "many2many",
                "nativeWidget": "many2many_tags",
                "semanticType": "tag_collection",
                "relation": "res.partner.category",
            },
            {
                "fieldCode": "owner_id",
                "label": "负责人",
                "fieldType": "many2one",
                "nativeWidget": "many2one_avatar_user",
                "semanticType": "relation",
                "relation": "res.users",
            },
        )
        for case in cases:
            with self.subTest(field=case["fieldCode"], widget=case["nativeWidget"]):
                descriptor = _strict_field_descriptor({
                    "fieldCode": case["fieldCode"],
                    "label": case["label"],
                    "fieldDescriptor": {
                        "schemaVersion": "1.0.0",
                        "name": case["fieldCode"],
                        "type": case["fieldType"],
                    },
                    "componentConfig": {
                        "fieldType": case["fieldType"],
                        "nativeWidget": case["nativeWidget"],
                        **(
                            {"relation": case["relation"]}
                            if "relation" in case
                            else {}
                        ),
                        **(
                            {"widgetOptions": case["widgetOptions"]}
                            if "widgetOptions" in case
                            else {}
                        ),
                    },
                })
                self.assertIsNotNone(descriptor)
                self.assertEqual(descriptor["widgetType"], case["nativeWidget"])
                self.assertEqual(descriptor["fieldType"], case["fieldType"])
                self.assertEqual(descriptor["semanticType"], case["semanticType"])
                self.assertNotIn("componentKey", descriptor)
                if case["fieldType"] == "date":
                    self.assertEqual(
                        descriptor["temporal"],
                        {"kind": "date", "timezoneAuthority": "not_applicable"},
                    )
                if case["fieldType"] == "datetime":
                    self.assertEqual(
                        descriptor["temporal"],
                        {"kind": "datetime", "timezoneAuthority": "user"},
                    )
                if "widgetOptions" in case:
                    self.assertEqual(descriptor["widgetOptions"], case["widgetOptions"])

    def test_strict_monetary_descriptor_uses_authoritative_currency_precision(self):
        project = self.env["project.project"].create({
            "name": "Strict monetary descriptor",
            "company_id": self.env.company.id,
        })
        contract = {
            "pageInfo": {"model": "project.project"},
            "layoutContract": {
                "containerTree": [{
                    "widgetList": [{
                        "widgetId": "field.company_currency_id.occ.1234567890abcdef",
                        "fieldCode": "budget_active_cost_target",
                        "label": "当前预算成本",
                        "fieldDescriptor": {
                            "schemaVersion": "1.0.0",
                            "name": "budget_active_cost_target",
                            "type": "monetary",
                        },
                        "componentConfig": {
                            "fieldType": "monetary",
                            "currency_field": "company_currency_id",
                        },
                    }],
                    "children": [],
                }],
            },
            "dataContract": {
                "mainData": {
                    "id": project.id,
                    "company_currency_id": [
                        self.env.company.currency_id.id,
                        self.env.company.currency_id.name,
                    ],
                },
            },
        }
        upgraded = _upgrade_contract_v2_field_descriptors(contract, env=self.env)
        descriptor = upgraded["layoutContract"]["containerTree"][0]["widgetList"][0]["fieldDescriptor"]
        self.assertEqual(descriptor["currencyField"], "company_currency_id")
        self.assertEqual(
            descriptor["digits"],
            [16, int(self.env.company.currency_id.decimal_places or 2)],
        )

    def test_strict_attachment_descriptor_gets_a_platform_owned_role(self):
        descriptor = _strict_field_descriptor({
            "fieldCode": "attachment_ids",
            "label": "附件",
            "fieldDescriptor": {
                "schemaVersion": "1.0.0",
                "name": "attachment_ids",
                "type": "many2many",
                "relation": "ir.attachment",
            },
            "componentConfig": {
                "fieldType": "many2many",
                "nativeWidget": "many2many_binary",
                "relation": "ir.attachment",
            },
        }, model_name="sc.labor.usage")
        self.assertIsNotNone(descriptor)
        self.assertEqual(
            descriptor["attachmentRole"],
            "attachment:sc.labor.usage:attachment_ids",
        )

    def test_strict_embedded_native_tokens_project_platform_capabilities(self):
        activity = _strict_field_descriptor({
            "fieldCode": "activity_ids",
            "label": "活动",
            "fieldDescriptor": {
                "schemaVersion": "1.0.0",
                "name": "activity_ids",
                "type": "one2many",
                "relation": "mail.activity",
                "relationField": "res_id",
            },
            "componentConfig": {
                "fieldType": "one2many",
                "nativeWidget": "list_activity",
                "relation": "mail.activity",
                "relationField": "res_id",
                "relationEntry": {
                    "model": "mail.activity",
                    "can_create": True,
                    "page_size": 20,
                },
            },
        }, model_name="res.users")
        self.assertIsNotNone(activity)
        self.assertEqual(activity["semanticType"], "activity_collection")
        self.assertNotIn("componentKey", activity)
        self.assertEqual(activity["relationEntry"]["page_size"], 20)

        account_type = _strict_field_descriptor({
            "fieldCode": "account_type",
            "label": "类型",
            "fieldDescriptor": {
                "schemaVersion": "1.0.0",
                "name": "account_type",
                "type": "selection",
            },
            "componentConfig": {
                "fieldType": "selection",
                "nativeWidget": "account_type_selection",
                "selection": [["asset_cash", "银行和现金"]],
            },
        }, model_name="account.account")
        self.assertIsNotNone(account_type)
        self.assertEqual(account_type["semanticType"], "choice")
        self.assertNotIn("componentKey", account_type)

    def test_strict_monetary_descriptor_keeps_currency_binding_without_inventing_precision(self):
        contract = {
            "pageInfo": {"model": "project.project"},
            "layoutContract": {
                "containerTree": [{
                    "widgetList": [{
                        "widgetId": "field.budget_active_cost_target.occ.1234567890abcdef",
                        "fieldCode": "budget_active_cost_target",
                        "label": "当前预算成本",
                        "fieldDescriptor": {
                            "schemaVersion": "1.0.0",
                            "name": "budget_active_cost_target",
                            "type": "monetary",
                        },
                        "componentConfig": {
                            "fieldType": "monetary",
                            "currency_field": "company_currency_id",
                        },
                    }],
                    "children": [],
                }],
            },
            "dataContract": {"mainData": {"id": 0}},
        }
        upgraded = _upgrade_contract_v2_field_descriptors(contract, env=self.env)
        descriptor = upgraded["layoutContract"]["containerTree"][0]["widgetList"][0]["fieldDescriptor"]
        self.assertEqual(descriptor["currencyField"], "company_currency_id")
        self.assertNotIn("digits", descriptor)

    def test_strict_non_monetary_descriptor_does_not_inherit_currency_digits(self):
        upgraded = _upgrade_contract_v2_field_descriptors({
            "layoutContract": {
                "containerTree": [{
                    "widgetList": [{
                        "widgetId": "field.outflow_line_ids.occ.1234567890abcdef",
                        "fieldCode": "outflow_line_ids",
                        "label": "付款申请明细",
                        "fieldDescriptor": {
                            "schemaVersion": "1.0.0",
                            "name": "outflow_line_ids",
                            "type": "one2many",
                        },
                        "componentConfig": {
                            "fieldType": "one2many",
                            "relation": "payment.request.line",
                        },
                    }],
                    "children": [],
                }],
            },
            "dataContract": {"mainData": {}},
        }, env=self.env)
        descriptor = upgraded["layoutContract"]["containerTree"][0]["widgetList"][0]["fieldDescriptor"]
        self.assertNotIn("digits", descriptor)


@tagged("post_install", "-at_install", "p0_contract_producer_p0a_money_evidence")
class TestP0ContractProducerMoneyEvidence(TransactionCase):
    def test_emit_real_orm_page_block_money_contract(self):
        contract, _project, currency = _build_real_money_contract(self.env)
        orchestration = contract["page_orchestration"]
        row = orchestration["block_data_contracts"]["ds_budget_active_cost_target"]["rows"][0]
        self.assertEqual(row["values"]["company_currency_id"], currency.id)
        encoded = base64.b64encode(
            json.dumps(orchestration, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).decode("ascii")
        print(f"P0A_REAL_ORM_MONEY_CONTRACT_B64={encoded}", flush=True)


@tagged("post_install", "-at_install", "p0_contract_descriptor_conformance_evidence")
class TestP0ContractDescriptorConformanceEvidence(TransactionCase):
    def test_emit_real_project_ledger_form_contract(self):
        from odoo.tools import date_utils
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler

        action = self.env.ref("smart_construction_core.action_sc_project_list")
        menu = self.env.ref("smart_construction_core.menu_sc_project_project")
        project = self.env["project.project"].create({
            "name": "P0 descriptor conformance",
            "company_id": self.env.company.id,
        })
        common = {
            "client_type": "web_pc",
            "accepted_contract_versions": ["2.7.x"],
            "client_contract_capabilities": [
                "container_tree.v2",
                "data_source.v2",
                "action_rule.v2",
                "relation_entry.v2",
                "status_contract.v2",
                "page_block_data.v1",
            ],
            "action_id": action.id,
            "menu_id": menu.id,
            "scene_key": "projects.ledger",
            "delivery_profile": "full",
        }
        handler = UiContractV2Handler(
            self.env,
            su_env=self.env["ir.model"].sudo().env,
        )
        form_result = handler.handle({
            "op": "action_open",
            "model": "project.project",
            "view_type": "form",
            "record_id": project.id,
            "render_profile": "edit",
            "contract_surface": "user",
            "source_mode": "governance_pipeline",
            **common,
        })
        form_result = (
            form_result.to_legacy_dict()
            if hasattr(form_result, "to_legacy_dict")
            else form_result
        )
        self.assertTrue(form_result.get("ok", True), form_result.get("error"))
        form_contract = form_result["data"]

        date_start = None

        def walk(nodes):
            nonlocal date_start
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                if node.get("fieldCode") == "date_start":
                    date_start = node
                    return
                for widget in node.get("widgetList") or []:
                    if (
                        isinstance(widget, dict)
                        and widget.get("fieldCode") == "date_start"
                    ):
                        date_start = widget
                        return
                walk(node.get("children") or [])

        walk(form_contract["layoutContract"]["containerTree"])
        self.assertIsNotNone(date_start)
        descriptor = date_start["fieldDescriptor"]
        self.assertEqual(descriptor["fieldType"], "date")
        self.assertEqual(descriptor["widgetType"], "daterange")
        self.assertEqual(descriptor["semanticType"], "date")
        self.assertNotIn("componentKey", descriptor)
        self.assertNotIn("componentRegistry", form_contract["layoutContract"])
        self.assertEqual(
            descriptor["temporal"],
            {"kind": "date", "timezoneAuthority": "not_applicable"},
        )
        encoded = base64.b64encode(
            json.dumps(
                {
                    "form": form_contract,
                    "project_id": project.id,
                },
                ensure_ascii=False,
                sort_keys=True,
                default=date_utils.json_default,
            ).encode("utf-8")
        ).decode("ascii")
        print(f"P0_CONTRACT_DESCRIPTOR_EVIDENCE_B64={encoded}", flush=True)


@tagged('post_install', '-at_install', 'p0_polymorphic_reference_evidence')
class TestPolymorphicReferenceContractEvidence(TransactionCase):
    def test_real_notification_contract_preserves_polymorphic_identity(self):
        from odoo.tools import date_utils
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
        from odoo.addons.smart_core.core.unified_page_contract_v2_assembler import _field_widget, _strict_field_descriptor
        from odoo.addons.smart_core.utils.native_field_descriptor import project_native_field_descriptor

        project = self.env['project.project'].create({
            'name': 'Isolated polymorphic contract evidence', 'company_id': self.env.company.id,
        })
        message = self.env['mail.message'].create({
            'model': 'project.project', 'res_id': project.id,
            'body': 'Isolated contract evidence', 'message_type': 'notification',
        })
        notification = self.env['mail.notification'].create({
            'mail_message_id': message.id, 'res_partner_id': self.env.user.partner_id.id,
            'notification_type': 'inbox',
        })
        action = self.env.ref('smart_construction_core.action_sc_product_message_notification_v1')
        menu = self.env.ref('smart_construction_core.menu_sc_product_message_notification_v1')
        result = UiContractV2Handler(self.env, su_env=self.env["ir.model"].sudo().env).handle({
            'op': 'action_open', 'model': 'mail.notification', 'view_type': 'form',
            'record_id': notification.id, 'render_profile': 'readonly',
            'contract_surface': 'user', 'source_mode': 'governance_pipeline',
            'client_type': 'web_pc', 'accepted_contract_versions': ['2.7.x'],
            'client_contract_capabilities': ['container_tree.v2', 'data_source.v2', 'action_rule.v2',
                                             'relation_entry.v2', 'status_contract.v2', 'page_block_data.v1'],
            'action_id': action.id, 'menu_id': menu.id, 'delivery_profile': 'full',
        })
        result = result.to_legacy_dict() if hasattr(result, 'to_legacy_dict') else result
        self.assertTrue(result.get('ok', True), result.get('error'))
        contract = result['data']
        def widgets(rows):
            for row in rows:
                yield from row.get('widgetList', [])
                yield from widgets(row.get('children', []))
        reference_widgets = [row for row in widgets(contract['layoutContract']['containerTree'])
                             if row.get('fieldCode') == 'sc_source_res_id']
        self.assertTrue(reference_widgets)
        for row in reference_widgets:
            descriptor = row['fieldDescriptor']
            self.assertEqual(descriptor['fieldType'], 'many2one_reference')
            self.assertEqual(descriptor['referenceModelField'], 'sc_source_model')
            self.assertNotIn('relation', descriptor)
        main = contract['dataContract']['mainData']
        self.assertEqual(main['sc_source_model'], 'project.project')
        self.assertEqual(main['sc_source_res_id'], project.id)
        # A native Reference value includes its model. Produce its descriptor
        # from real fields_get metadata, not a handcrafted wire descriptor.
        metadata = self.env['ir.ui.menu'].fields_get(['action'])['action']
        native = project_native_field_descriptor('action', metadata)
        reference = _strict_field_descriptor(_field_widget(native, layout_type='form'))
        self.assertEqual(reference['fieldType'], 'reference')
        self.assertNotIn('relation', reference)
        reference_value = menu.read(['action'])[0]['action']
        self.assertEqual(reference_value, 'ir.actions.act_window,%s' % action.id)
        payload = {'notification': contract, 'native_reference': reference, 'native_reference_value': reference_value}
        encoded = base64.b64encode(json.dumps(payload, ensure_ascii=False, default=date_utils.json_default).encode()).decode()
        print('P0_POLYMORPHIC_REFERENCE_EVIDENCE_B64=' + encoded, flush=True)


@tagged('post_install', '-at_install', 'p0_relation_active_actions_evidence')
class TestRelationActiveActionsContractEvidence(TransactionCase):
    def test_strict_relation_active_actions_ignore_component_config_conflicts(self):
        descriptor = _strict_field_descriptor({
            'fieldCode': 'partner_id',
            'label': 'Partner',
            'fieldDescriptor': {
                'schemaVersion': '1.0.0',
                'name': 'partner_id',
                'type': 'many2one',
                'relation': 'res.partner',
                'relation_active_actions': {'create': False},
            },
            'componentConfig': {
                'fieldType': 'many2one',
                'relation': 'res.partner',
                'relationActiveActions': {'create': True, 'write': True},
                'relation_active_actions': {'create': True, 'write': True},
            },
        }, model_name='res.partner')
        self.assertEqual(descriptor['relationActiveActions'], {'create': False})
        self.assertNotIn('write', descriptor['relationActiveActions'])

    def test_real_assembler_emits_occurrence_relation_actions_in_field_descriptor(self):
        dynamic_write = {
            'kind': 'field_compare',
            'semantics': 'python',
            'field': 'state',
            'operator': '!=',
            'value': 'done',
            'raw': "state != 'done'",
        }
        source = {
            'model': 'x.relation_action_probe',
            'view_type': 'form',
            'fields': {
                'partner_id': {
                    'name': 'partner_id',
                    'type': 'many2one',
                    'relation': 'res.partner',
                    'string': 'Partner',
                },
                'reviewer_id': {
                    'name': 'reviewer_id',
                    'type': 'many2one',
                    'relation': 'res.users',
                    'string': 'Reviewer',
                },
                'tag_ids': {
                    'name': 'tag_ids',
                    'type': 'many2many',
                    'relation': 'res.partner.category',
                    'string': 'Tags',
                },
            },
            'views': {'form': {'layout': [{
                'type': 'sheet',
                'span': 12,
                'children': [
                    {
                        'type': 'field',
                        'span': 6,
                        'name': 'partner_id',
                        'source_position': 1,
                        'relation_active_actions': {'create': False, 'write': True},
                    },
                    {
                        'type': 'field',
                        'span': 6,
                        'name': 'reviewer_id',
                        'source_position': 2,
                        'relation_active_actions': {'create': dynamic_write},
                    },
                    {
                        'type': 'field',
                        'span': 6,
                        'name': 'tag_ids',
                        'source_position': 3,
                        'attributes': {'widget': 'many2many_tags'},
                        'relation_active_actions': {'create': True, 'write': False},
                    },
                ],
            }]}},
        }
        contract = assemble_unified_page_contract_v2(
            source,
            source_type='ui.contract',
            request_id='p0.relation.active.actions.evidence',
        )
        widgets = []

        def collect(rows):
            for row in rows:
                widgets.extend(row.get('widgetList', []))
                collect(row.get('children', []))

        collect(contract['layoutContract']['containerTree'])
        by_field = {
            row['fieldCode']: row
            for row in widgets
            if row.get('fieldCode')
        }
        first = by_field['partner_id']
        second = by_field['reviewer_id']
        tags = by_field['tag_ids']
        self.assertEqual(
            first['fieldDescriptor']['relationActiveActions'],
            {'create': False, 'write': True},
        )
        self.assertEqual(
            second['fieldDescriptor']['relationActiveActions'],
            {'create': dynamic_write},
        )
        self.assertNotIn('write', second['fieldDescriptor']['relationActiveActions'])
        self.assertEqual(
            tags['fieldDescriptor']['relationActiveActions'],
            {'create': True, 'write': False},
        )
        for widget in (first, second, tags):
            self.assertNotIn('relationActiveActions', widget['componentConfig'])
            self.assertNotIn('relation_active_actions', widget['componentConfig'])
        encoded = base64.b64encode(
            json.dumps({'contract': contract}, ensure_ascii=False, sort_keys=True).encode('utf-8')
        ).decode('ascii')
        print(f'P0_RELATION_ACTIVE_ACTIONS_EVIDENCE_B64={encoded}', flush=True)
