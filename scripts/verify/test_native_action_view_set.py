from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "addons/smart_core/core/native_action_view_set.py"
SPEC = importlib.util.spec_from_file_location("native_action_view_set", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class NativeActionViewSetTest(unittest.TestCase):
    def test_effective_action_views_order_wins_and_view_mode_only_supplements(self):
        view_set = MODULE.build_action_view_set(
            views=[(22, "form"), (11, "tree"), (33, "kanban")],
            view_mode="tree,form,pivot",
            action_view_id=11,
            action_view_type="tree",
        )

        self.assertEqual(
            [row["viewType"] for row in view_set["orderedViews"]],
            ["form", "tree", "kanban", "pivot"],
        )
        self.assertEqual(
            [row["actionViewSequence"] for row in view_set["orderedViews"]],
            [1, 2, 3, 4],
        )
        self.assertEqual(view_set["defaultViewType"], "form")
        self.assertEqual(view_set["defaultViewId"], 22)
        self.assertEqual(view_set["supplementedViewTypes"], ["pivot"])

    def test_duplicate_same_type_action_views_remain_distinct(self):
        view_set = MODULE.build_action_view_set(
            views=[(11, "tree"), (12, "tree")],
            view_mode="tree,form",
            action_view_id=12,
            action_view_type="tree",
        )

        self.assertEqual(
            [(row["viewType"], row["viewId"]) for row in view_set["orderedViews"]],
            [("tree", 11), ("tree", 12), ("form", 0)],
        )
        self.assertTrue(view_set["orderedViews"][0]["selectable"])
        self.assertFalse(view_set["orderedViews"][-1]["selectable"])
        self.assertEqual(view_set["orderedViews"][-1]["surfaceRole"], "record_detail")

    def test_view_mode_fills_action_default_view_id_only_for_matching_type(self):
        view_set = MODULE.build_action_view_set(
            views=[],
            view_mode="tree,form",
            action_view_id=91,
            action_view_type="form",
        )

        self.assertEqual(
            [(row["viewType"], row["viewId"], row["source"]) for row in view_set["orderedViews"]],
            [
                ("tree", 0, "view_mode_supplement"),
                ("form", 91, "view_mode_supplement"),
            ],
        )

    def test_requested_view_id_must_match_action_candidate(self):
        view_set = MODULE.build_action_view_set(
            views=[(11, "tree"), (12, "form")],
            view_mode="tree,form",
        )

        allowed = MODULE.resolve_requested_action_view(
            view_set,
            requested_view_id=12,
            requested_view_type="form",
        )
        denied = MODULE.resolve_requested_action_view(
            view_set,
            requested_view_id=99,
            requested_view_type="form",
        )

        self.assertTrue(allowed["allowed"])
        self.assertEqual(allowed["view"]["viewId"], 12)
        self.assertFalse(denied["allowed"])
        self.assertEqual(denied["reasonCode"], "ACTION_VIEW_REQUEST_OVERRIDE_DENIED")

    def test_authorized_override_is_explicit_and_not_a_candidate(self):
        view_set = MODULE.build_action_view_set(
            views=[(11, "tree")],
            view_mode="tree,form",
        )

        result = MODULE.resolve_requested_action_view(
            view_set,
            requested_view_id=99,
            requested_view_type="form",
            authorized_override=True,
        )

        self.assertTrue(result["allowed"])
        self.assertTrue(result["authorizedOverride"])
        self.assertEqual(result["view"]["source"], "authorized_override")

    def test_explicit_view_against_unresolved_set_fails_closed(self):
        result = MODULE.resolve_requested_action_view(
            {"orderedViews": []},
            requested_view_id=99,
            requested_view_type="form",
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["reasonCode"], "ACTION_VIEW_REQUEST_OVERRIDE_DENIED")

    def test_default_selection_uses_effective_first_view(self):
        view_set = MODULE.build_action_view_set(
            views=[(22, "kanban"), (11, "tree")],
            view_mode="tree,kanban,form",
        )

        result = MODULE.resolve_requested_action_view(view_set)

        self.assertTrue(result["allowed"])
        self.assertEqual(result["view"]["viewType"], "kanban")
        self.assertEqual(result["view"]["viewId"], 22)

    def test_list_alias_uses_tree_identity_and_neutral_action_shape(self):
        view_set = MODULE.build_action_view_set(
            views=[(11, "list")],
            view_mode="list,form",
        )

        self.assertEqual(view_set["orderedViews"][0]["viewType"], "tree")
        self.assertEqual(view_set["defaultViewType"], "tree")
        self.assertNotIn("menuId", view_set)
        self.assertNotIn("sceneKey", view_set)

    def test_override_authority_requires_the_verified_internal_marker(self):
        unverified_contexts = (
            {},
            {"business_config_preview_token": "token"},
            {"preview_token": "token"},
            {"contract_view_override_authorized": True},
            {MODULE.NATIVE_ACTION_VIEW_OVERRIDE_AUTHORIZED: "true"},
            {MODULE.NATIVE_ACTION_VIEW_OVERRIDE_AUTHORIZED: 1},
        )

        for context in unverified_contexts:
            with self.subTest(context=context):
                self.assertFalse(MODULE.has_authorized_action_view_override(context))
        self.assertTrue(
            MODULE.has_authorized_action_view_override({
                MODULE.NATIVE_ACTION_VIEW_OVERRIDE_AUTHORIZED: True,
            })
        )


if __name__ == "__main__":
    unittest.main()
