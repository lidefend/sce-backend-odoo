# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged

from odoo.addons.smart_core.core.unified_page_contract_v2_action import (
    build_action_partial_update_v2,
)
from odoo.addons.smart_core.handlers.execute_button import ExecuteButtonHandler
from odoo.addons.smart_construction_core.handlers.workspace_home_enter import (
    WorkspaceHomeEnterHandler,
)
from odoo.addons.smart_construction_core.services.scene_block_schema import (
    action_target,
    build_contract,
    metric_card,
)
from odoo.addons.smart_construction_core.services.workspace_contract_builder import (
    WorkspaceContractBuilder,
)


@tagged("post_install", "-at_install", "p0_contract_producer_p0c")
class TestP0ContractProducerP0C(TransactionCase):
    def _user_with_group(self, login, group_xmlid):
        groups = self.env.ref("base.group_user") | self.env.ref(group_xmlid)
        return self.env["res.users"].with_context(no_reset_password=True).create({
            "name": login,
            "login": login,
            "email": f"{login}@invalid.local",
            "company_id": self.env.company.id,
            "company_ids": [(6, 0, [self.env.company.id])],
            "groups_id": [(6, 0, groups.ids)],
        })

    def _request(self, capabilities):
        return {
            "params": {
                "client_type": "web_pc",
                "accepted_contract_versions": ["2.5.x", "2.6.x"],
                "client_contract_capabilities": capabilities,
            }
        }

    def _button_handler(
        self,
        *,
        action_id,
        method_name,
        allowed=True,
        trace_id,
    ):
        partner = self.env["res.partner"].create({
            "name": f"P0-C action {trace_id}",
        })
        backend_identity = f"contract_action:{method_name}"
        rule = {
            "actionId": action_id,
            "actionKey": action_id,
            "label": "执行动作",
            "intent": "execute_button",
            "backendIdentity": backend_identity,
            "sourceWidgetId": "field.active",
            "button": {"name": method_name, "type": "object"},
            "triggerType": "click",
            "targetIds": [],
            "dispatchMode": "server",
            "targetScope": "page",
            "refreshMode": "partial",
            "allowed": allowed,
            "enabled": allowed,
            "disabled": not allowed,
            "entitlementEvaluated": True,
            "reasonCode": "" if allowed else "ACTION_NOT_AUTHORIZED",
            "reasonMessage": "" if allowed else "当前角色无权执行该动作",
        }
        contract = {
            "actionContract": {"actionRuleList": [rule]},
            "statusContract": {
                "buttonStatus": [{
                    "backendIdentity": backend_identity,
                    "visible": True,
                    "disabled": False,
                }],
            },
        }
        handler = ExecuteButtonHandler(
            self.env,
            context={"trace_id": trace_id},
            payload={
                "params": {
                    "model": "res.partner",
                    "record_id": partner.id,
                    "button": {
                        "type": "object",
                        "name": method_name,
                        "action_id": action_id,
                        "backend_identity": backend_identity,
                        "source_widget_id": "field.active",
                    },
                },
                "meta": {"action_id": 1, "menu_id": 1},
            },
        )
        handler._load_current_action_contract = lambda **_kwargs: contract
        return handler

    def test_workspace_page_block_action_uses_published_action_authority(self):
        user = self._user_with_group(
            "p0c_project_manager",
            "smart_construction_core.group_sc_role_project_manager",
        )
        contract = WorkspaceContractBuilder(self.env(user=user)).build(
            page_block_action_enabled=True,
        )
        orchestration = contract["page_orchestration"]
        self.assertEqual(orchestration["contract_version"], "2.1.0")
        schema = orchestration["action_schema"]
        rules = orchestration["action_contract"]["actionRuleList"]
        self.assertEqual(schema["carrier"], "page-block-action.v1")
        self.assertTrue(rules)
        self.assertEqual(
            {row["actionId"] for row in rules},
            set(schema["actions"]),
        )
        enabled = 0
        for action_id, carrier in schema["actions"].items():
            rule = next(row for row in rules if row["actionId"] == action_id)
            self.assertEqual(carrier["actionRuleRef"], rule["actionId"])
            self.assertEqual(carrier["target"]["value"], rule["target"])
            self.assertTrue(carrier["permission"]["evaluated"])
            self.assertTrue(carrier["permission"]["businessAvailable"])
            self.assertEqual(
                carrier["permission"]["allowed"],
                carrier["permission"]["authorizationAllowed"],
            )
            self.assertEqual(
                carrier["state"]["enabled"],
                carrier["permission"]["allowed"],
            )
            if carrier["state"]["enabled"]:
                enabled += 1
            self.assertNotIn("authorizationSubject", str(carrier))
        self.assertGreater(enabled, 0, schema)

    def test_unauthorized_user_receives_disabled_actions_with_reason(self):
        user = self._user_with_group(
            "p0c_no_action_groups",
            "base.group_user",
        )
        contract = WorkspaceContractBuilder(self.env(user=user)).build(
            page_block_action_enabled=True,
        )
        carriers = contract["page_orchestration"]["action_schema"]["actions"]
        self.assertTrue(carriers)
        denied = [
            row for row in carriers.values()
            if row["permission"]["authorizationAllowed"] is False
        ]
        self.assertTrue(denied)
        for carrier in denied:
            self.assertFalse(carrier["state"]["enabled"])
            self.assertEqual(
                carrier["state"]["reasonCode"],
                "ACTION_NOT_AUTHORIZED",
            )
            self.assertTrue(carrier["state"]["reasonMessage"])

    def test_missing_target_is_not_replaced_with_open_scene(self):
        block = metric_card(
            "missing_target",
            "缺少目标",
            1,
            target={"type": "none"},
        )
        contract = build_contract(
            scene_key="p0c.missing.target",
            title="P0-C missing target",
            blocks=[block],
            page_block_action_enabled=True,
            action_authority=lambda _target: self.fail(
                "a missing target must never be sent to the authority resolver"
            ),
            timezone="UTC",
        )
        self.assertEqual(
            contract["page_orchestration"]["action_schema"]["actions"],
            {},
        )

    def test_handler_enables_action_carrier_only_when_declared(self):
        handler = WorkspaceHomeEnterHandler(self.env)
        action_only = handler.handle(self._request(["page_block_action.v1"]))
        self.assertTrue(action_only["ok"], action_only)
        orchestration = action_only["data"]["page_orchestration"]
        self.assertEqual(orchestration["contract_version"], "2.1.0")
        self.assertIn("action_schema", orchestration)
        self.assertNotIn("block_data_contracts", orchestration)
        self.assertEqual(
            action_only["meta"]["contract_negotiation"]["compatibilityMode"],
            "page_block_action_v1",
        )

        data_only = handler.handle(self._request(["page_block_data.v1"]))
        self.assertTrue(data_only["ok"], data_only)
        self.assertIn("block_data_contracts", data_only["data"]["page_orchestration"])
        self.assertNotIn("action_schema", data_only["data"]["page_orchestration"])
        self.assertFalse(
            data_only["meta"]["contract_negotiation"]["carriers"][
                "page_block_action.v1"
            ]["enabled"]
        )

    def test_legacy_projection_has_no_action_carrier(self):
        result = WorkspaceHomeEnterHandler(self.env).handle({
            "params": {
                "client_type": "web_pc",
                "accepted_contract_versions": ["2.5.x"],
                "client_contract_capabilities": ["page_block_action.v1"],
            }
        })
        self.assertTrue(result["ok"], result)
        orchestration = result["data"]["page_orchestration"]
        self.assertEqual(orchestration["contract_version"], "2.0.0")
        self.assertNotIn("action_schema", orchestration)
        self.assertNotIn("action_contract", orchestration)

    def test_action_patch_produces_correlated_feedback(self):
        patch = build_action_partial_update_v2(
            {
                "ok": False,
                "error": {
                    "code": 403,
                    "reason_code": "ACTION_NOT_AUTHORIZED",
                    "message": "当前角色无权执行该动作",
                },
                "meta": {"trace_id": "trace-p0c-action"},
            },
            action_id="open_project",
        )
        feedback = patch["runtimePatch"]["actionFeedback"]
        self.assertEqual(len(feedback), 1)
        self.assertEqual(feedback[0]["actionId"], "action.open_project")
        self.assertEqual(feedback[0]["status"], "denied")
        self.assertEqual(feedback[0]["reasonCode"], "ACTION_NOT_AUTHORIZED")
        self.assertEqual(feedback[0]["traceId"], "trace-p0c-action")

    def test_real_action_success_carries_correlated_feedback(self):
        action_id = "action.partner_toggle_active"
        handler = self._button_handler(
            action_id=action_id,
            method_name="toggle_active",
            trace_id="trace-execute-p0c-success",
        )
        result = handler.handle()
        self.assertTrue(result["ok"], result)
        feedback = result["data"]["runtimePatch"]["actionFeedback"]
        self.assertEqual(len(feedback), 1)
        self.assertEqual(feedback[0]["actionId"], action_id)
        self.assertEqual(feedback[0]["status"], "success")
        self.assertEqual(feedback[0]["traceId"], "trace-execute-p0c-success")

    def test_real_denied_action_carries_correlated_feedback(self):
        action_id = "action.partner_toggle_active_denied"
        handler = self._button_handler(
            action_id=action_id,
            method_name="toggle_active",
            allowed=False,
            trace_id="trace-execute-p0c-denied",
        )
        result = handler.handle()
        self.assertFalse(result["ok"], result)
        feedback = result["data"]["runtimePatch"]["actionFeedback"]
        self.assertEqual(len(feedback), 1)
        self.assertEqual(feedback[0]["actionId"], action_id)
        self.assertEqual(feedback[0]["status"], "denied")
        self.assertEqual(feedback[0]["reasonCode"], "ACTION_NOT_AUTHORIZED")
        self.assertEqual(feedback[0]["traceId"], "trace-execute-p0c-denied")
        self.assertEqual(
            result["error"]["details"]["runtimePatch"]["actionFeedback"],
            feedback,
        )

    def test_real_failed_action_carries_correlated_feedback(self):
        action_id = "action.partner_write_failed"
        handler = self._button_handler(
            action_id=action_id,
            method_name="write",
            trace_id="trace-execute-p0c-failed",
        )
        result = handler.handle()
        self.assertFalse(result["ok"], result)
        feedback = result["data"]["runtimePatch"]["actionFeedback"]
        self.assertEqual(len(feedback), 1)
        self.assertEqual(feedback[0]["actionId"], action_id)
        self.assertEqual(feedback[0]["status"], "failed")
        self.assertEqual(feedback[0]["traceId"], "trace-execute-p0c-failed")


if __name__ == "__main__":
    import unittest

    unittest.main()
