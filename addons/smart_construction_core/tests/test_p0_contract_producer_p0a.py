# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged

from odoo.addons.smart_core.core.page_block_data_contract import field_descriptor
from odoo.addons.smart_core.core.unified_page_contract_v2_assembler import _strict_field_descriptor
from odoo.addons.smart_construction_core.handlers.workspace_home_enter import WorkspaceHomeEnterHandler
from odoo.addons.smart_construction_core.services.scene_block_schema import build_contract, metric_card
from odoo.addons.smart_construction_core.services.workspace_contract_builder import WorkspaceContractBuilder


@tagged("post_install", "-at_install", "p0_contract_producer_p0a")
class TestP0ContractProducerP0A(TransactionCase):
    def _request(self, **params):
        return {
            "params": {
                "client_type": "web_pc",
                "accepted_contract_versions": ["2.0.x", "2.5.x", "2.6.x"],
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

    def test_legacy_workspace_projection_has_no_page_block_data(self):
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
        self.assertEqual(current["meta"]["contract_negotiation"]["contractVersion"], "2.6.0")

        legacy = handler.handle({
            "params": {
                "client_type": "web_pc",
                "accepted_contract_versions": ["2.5.x", "2.6.x"],
                "client_contract_capabilities": [],
            }
        })
        self.assertEqual(legacy["data"]["page_orchestration"]["contract_version"], "2.0.0")
        self.assertNotIn("block_data_contracts", legacy["data"]["page_orchestration"])

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

    def test_real_monetary_model_field_keeps_raw_value_and_currency_semantics(self):
        project = self.env["project.project"].create({"name": "P0-A contract producer"})
        field = project._fields["budget_active_cost_target"]
        self.assertEqual(field.type, "monetary")
        block = metric_card(
            "budget_active_cost_target",
            "当前预算成本",
            project.budget_active_cost_target,
            subtitle="真实项目金额事实",
        )
        block["value_descriptor"] = field_descriptor(
            field_code="project.budget_active_cost_target",
            label="当前预算成本",
            field_type="monetary",
            widget_type="monetary",
            component_key="sc.value.money",
            semantic_type="money",
            digits=[16, int(project.company_currency_id.decimal_places or 2)],
            currencyField="company_currency_id",
        )
        block["currencies"] = {
            project.company_currency_id.id: {
                "id": project.company_currency_id.id,
                "code": project.company_currency_id.name,
                "symbol": project.company_currency_id.symbol,
            },
        }
        contract = build_contract(
            scene_key="p0a.monetary",
            title="P0-A 金额",
            blocks=[block],
            page_block_data_enabled=True,
            timezone=self.env.user.tz or "UTC",
        )
        row = contract["page_orchestration"]["block_data_contracts"]["ds_budget_active_cost_target"]["rows"][0]
        self.assertEqual(row["values"]["value"], project.budget_active_cost_target)
        descriptor = contract["page_orchestration"]["block_field_descriptors"]["budget_active_cost_target.value"]
        self.assertEqual(descriptor["semanticType"], "money")
        self.assertEqual(descriptor["currencyField"], "company_currency_id")
        self.assertEqual(descriptor["digits"], [16, int(project.company_currency_id.decimal_places or 2)])

    def test_strict_widget_descriptor_uses_native_vocabulary_and_selection_pairs(self):
        descriptor = _strict_field_descriptor({
            "fieldCode": "operation_strategy",
            "label": "经营方式",
            "fieldDescriptor": {
                "schemaVersion": "1.0.0",
                "name": "operation_strategy",
                "type": "selection",
                "widget": "selection",
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
