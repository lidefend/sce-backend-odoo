from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "addons/smart_core/core/native_action_search_view.py"
SPEC = importlib.util.spec_from_file_location("native_action_search_view", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class NativeActionSearchViewTest(unittest.TestCase):
    def test_action_search_identity_preserves_native_authority(self):
        identity = MODULE.build_search_native_identity(
            model="payment.request",
            action_id=11,
            view_id=22,
            view_xmlid="smart_construction_core.view_payment_request_search",
            authority=MODULE.ACTION_SEARCH_VIEW_AUTHORITY,
        )

        self.assertEqual(identity["model"], "payment.request")
        self.assertEqual(identity["actionId"], 11)
        self.assertEqual(identity["viewId"], 22)
        self.assertEqual(
            identity["viewXmlId"],
            "smart_construction_core.view_payment_request_search",
        )
        self.assertEqual(identity["authority"], "action_search_view")
        self.assertEqual(
            identity["sourceLocator"],
            "ir.actions.act_window.search_view_id",
        )

    def test_model_default_search_identity_has_no_action_identity(self):
        identity = MODULE.build_search_native_identity(
            model="project.project",
            view_id=33,
            authority=MODULE.MODEL_SEARCH_VIEW_AUTHORITY,
        )

        self.assertIsNone(identity["actionId"])
        self.assertEqual(identity["authority"], "model_default_search_view")
        self.assertEqual(identity["sourceLocator"], "ir.ui.view:search")

    def test_action_search_identity_requires_action_and_resolved_view(self):
        with self.assertRaisesRegex(ValueError, "requires an action id"):
            MODULE.build_search_native_identity(
                model="project.project",
                view_id=33,
                authority=MODULE.ACTION_SEARCH_VIEW_AUTHORITY,
            )
        with self.assertRaisesRegex(ValueError, "resolved view id"):
            MODULE.build_search_native_identity(
                model="project.project",
                action_id=11,
                authority=MODULE.ACTION_SEARCH_VIEW_AUTHORITY,
            )

    def test_raw_authority_names_are_not_accepted(self):
        for authority in ("", "search_view", "odoo", "ACTION_SEARCH_VIEW"):
            with self.subTest(authority=authority):
                with self.assertRaisesRegex(ValueError, "authority is invalid"):
                    MODULE.build_search_native_identity(
                        model="res.partner",
                        action_id=11,
                        view_id=22,
                        authority=authority,
                    )

    def test_identity_normalizes_empty_xmlid_without_inventing_one(self):
        identity = MODULE.build_search_native_identity(
            model="res.partner",
            action_id=11,
            view_id=22,
            authority=MODULE.ACTION_SEARCH_VIEW_AUTHORITY,
        )

        self.assertEqual(identity["viewXmlId"], "")


if __name__ == "__main__":
    unittest.main()
