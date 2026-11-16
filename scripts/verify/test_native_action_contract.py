from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "addons/smart_core/core/native_action_contract.py"
SPEC = importlib.util.spec_from_file_location("native_action_contract", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def view_set():
    return {
        "orderAuthority": "ir.actions.act_window.views",
        "defaultViewType": "tree",
        "complete": True,
        "orderedViews": [
            {
                "viewType": "tree",
                "viewId": 11,
                "viewXmlId": "demo.partner_tree",
                "actionViewSequence": 1,
                "surfaceRole": "collection",
                "selectable": True,
                "projectionStatus": "ready",
                "rendererStatus": "unknown",
                "reasonCode": "",
                "profile": "tree",
            },
            {
                "viewType": "tree",
                "viewId": 12,
                "viewXmlId": "demo.partner_tree_alt",
                "actionViewSequence": 2,
                "surfaceRole": "collection",
                "selectable": True,
                "projectionStatus": "ready",
                "rendererStatus": "unknown",
                "reasonCode": "",
                "profile": "tree",
            },
            {
                "viewType": "form",
                "viewId": 13,
                "viewXmlId": "demo.partner_form",
                "actionViewSequence": 3,
                "surfaceRole": "record_detail",
                "selectable": False,
                "projectionStatus": "ready",
                "rendererStatus": "unknown",
                "reasonCode": "",
                "profile": "form",
            },
        ],
    }


class NativeActionContractTest(unittest.TestCase):
    def build(self, **overrides):
        values = {
            "model": "res.partner",
            "active_view_type": "tree",
            "action_identity": {
                "action_id": 7,
                "action_xmlid": "demo.action_partner",
                "model": "res.partner",
            },
            "view_set": view_set(),
            "search_identity": {
                "model": "res.partner",
                "actionId": 7,
                "viewId": 21,
                "viewXmlId": "demo.partner_search",
                "authority": "action_search_view",
            },
            "domain": [["active", "=", True]],
            "domain_raw": "[('active', '=', True)]",
            "context": {"default_customer_rank": 1},
            "context_raw": "{'default_customer_rank': 1}",
            "entry_refs": [{
                "kind": "menu",
                "menuId": 31,
                "menuXmlId": "demo.menu_partners",
            }],
        }
        values.update(overrides)
        return MODULE.build_native_action_contract(**values)

    def test_action_identity_order_duplicates_and_search_are_preserved(self):
        contract = self.build()

        self.assertEqual(contract["identity"]["actionId"], 7)
        self.assertEqual(contract["identity"]["actionXmlId"], "demo.action_partner")
        self.assertEqual(
            [(row["viewType"], row["viewId"]) for row in contract["viewSet"]["orderedViews"]],
            [("tree", 11), ("tree", 12), ("form", 13)],
        )
        self.assertEqual(contract["viewSet"]["defaultViewType"], "tree")
        self.assertEqual(contract["viewSet"]["activeViewType"], "tree")
        self.assertEqual(contract["search"]["viewId"], 21)
        self.assertEqual(contract["entryRefs"][0]["menuId"], 31)

    def test_three_readiness_axes_remain_independent(self):
        readiness = self.build()["readiness"]

        self.assertEqual(readiness["backendContract"]["status"], "ready")
        self.assertEqual(readiness["clientRenderer"]["status"], "unknown")
        self.assertEqual(readiness["businessExecution"]["status"], "not_applicable")

    def test_active_view_is_current_request_not_always_default(self):
        contract = self.build(active_view_type="form")

        self.assertEqual(contract["viewSet"]["defaultViewType"], "tree")
        self.assertEqual(contract["viewSet"]["activeViewType"], "form")

    def test_access_block_changes_projection_availability_only(self):
        contract = self.build(access_policy={
            "mode": "block",
            "reason_code": "MODEL_READ_FORBIDDEN",
        })

        self.assertEqual(contract["projectionAvailability"]["status"], "blocked")
        self.assertEqual(
            contract["projectionAvailability"]["reasonCode"],
            "MODEL_READ_FORBIDDEN",
        )
        self.assertEqual(contract["readiness"]["backendContract"]["status"], "ready")

    def test_no_action_identity_has_no_native_action_contract(self):
        self.assertIsNone(self.build(action_identity={}))

    def test_model_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "model mismatch"):
            self.build(model="res.users")

    def test_incomplete_view_set_is_explicitly_unresolved(self):
        contract = self.build(view_set={"complete": False, "orderedViews": []})

        self.assertEqual(contract["projectionAvailability"]["status"], "unresolved")
        self.assertEqual(contract["viewSet"]["orderedViews"], [])
        self.assertEqual(contract["readiness"]["backendContract"]["status"], "unresolved")


if __name__ == "__main__":
    unittest.main()
