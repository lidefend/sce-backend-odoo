# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.core.workflow_contract_injection import (
    inject_workflow_contract,
)
from odoo.addons.smart_core.utils.contract_governance import (
    register_workflow_contract_profile,
)


@tagged("post_install", "-at_install", "workflow_contract_platform")
class TestWorkflowContractPlatform(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.profile = {
            "state_field": "position",
            "state_phase": {
                "after": "draft",
                "before": "approved",
            },
            "state_actions": {
                "after": ["save_draft"],
            },
            "method_by_action": {
                "save_draft": None,
            },
        }
        cls.registered = register_workflow_contract_profile(
            "res.currency",
            cls.profile,
            source="smart_core.test_workflow_contract_platform",
        )

    def test_platform_service_owns_record_contract_shape(self):
        self.assertTrue(self.registered)
        currency = self.env["res.currency"].create({"name": "WCT", "symbol": "W"})

        contract = self.env["smart_core.workflow.contract"].describe_record(currency)

        self.assertEqual(contract["source"]["kind"], "sc_backend_workflow_contract")
        self.assertEqual(contract["model"], "res.currency")
        self.assertEqual(contract["stateField"], "position")
        self.assertEqual(contract["rawState"], "after")
        self.assertEqual(contract["businessPhase"], "draft")
        self.assertEqual(contract["approvalPhase"], "none")
        self.assertEqual(
            {row["key"] for row in contract["availableActions"]},
            {"save_draft"},
        )
        self.assertEqual(contract["availableActions"][0]["reason_code"], "OK")

    def test_platform_injection_is_the_contract_carrier(self):
        currency = self.env["res.currency"].create({"name": "WCI", "symbol": "W"})
        contract = {
            "statusContract": {
                "globalStatus": {
                    "pageAuth": "edit",
                    "effectiveRecordCapabilities": {"read": True, "write": True},
                    "effectiveRenderProfile": "edit",
                }
            }
        }
        source = {
            "model": "res.currency",
            "view_type": "form",
            "record_id": currency.id,
        }

        inject_workflow_contract(
            self.env,
            contract,
            source,
            model="res.currency",
            view_type="form",
        )

        self.assertEqual(contract["workflowContract"]["model"], "res.currency")
        self.assertEqual(contract["workflowContract"]["approvalPhase"], "none")
        self.assertEqual(
            contract["statusContract"]["globalStatus"]["workflowPhase"],
            "draft",
        )
        self.assertEqual(
            contract["statusContract"]["globalStatus"]["approvalPhase"],
            "none",
        )
