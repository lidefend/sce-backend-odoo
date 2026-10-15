from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.verify.role_surface_exposure_declaration_guard import (
    DECLARATIONS_PATH,
    SCHEMA_VERSION,
    group_closure,
    load_entry_universe,
    load_group_graph,
    load_published_face_entry_count,
    load_role_policy,
    validate,
    validate_published_face,
)


def _fixture():
    graph = {
        "t.role_a": ["t.cap_x"],
        "t.cap_x": [],
        "t.role_b": ["t.cap_y"],
        "t.cap_y": [],
    }
    closures = {group: group_closure(group, graph) for group in graph}
    entries = [
        {
            "menu": "t.menu_delivered",
            "chain": [{"menu_xmlid": "t.menu_delivered", "groups": ["t.cap_x"]}],
            "actions": [],
        },
        {
            "menu": "t.menu_narrowed",
            "chain": [{"menu_xmlid": "t.menu_narrowed", "groups": ["t.cap_x"]}],
            "actions": [],
        },
        {
            "menu": "t.menu_other",
            "chain": [{"menu_xmlid": "t.menu_other", "groups": ["t.cap_z"]}],
            "actions": [],
        },
    ]
    policy = {
        "role_a": {
            "primary_menu_xmlids": ["t.menu_delivered"],
            "role_home_menu_xmlids": [],
            "denied_menu_xmlids": [],
        },
        "role_b": {
            "primary_menu_xmlids": [],
            "role_home_menu_xmlids": [],
            "denied_menu_xmlids": [],
        },
    }
    declarations = {
        "schema_version": SCHEMA_VERSION,
        "excluded_roles": {},
        "roles": {
            "role_a": {
                "delivery_mode": "declared_whitelist",
                "identity_groups": ["t.role_a"],
                "rationale": "declared narrowing",
                "capability_reachable_not_delivered": ["t.menu_narrowed"],
                "delivered_without_declared_capability": [],
            },
            "role_b": {
                "delivery_mode": "declared_whitelist",
                "identity_groups": ["t.role_b"],
                "rationale": "no published surface",
                "capability_reachable_not_delivered": [],
                "delivered_without_declared_capability": [],
            },
        },
        "capability_reachable_by_no_role": ["t.menu_other"],
        "authority_pending_entries": {},
    }
    return declarations, policy, entries, closures


class RoleSurfaceExposureDeclarationGuardTest(unittest.TestCase):
    def test_fully_declared_divergence_passes(self):
        declarations, policy, entries, closures = _fixture()
        self.assertEqual(validate(declarations, policy, entries, {}, closures), [])

    def test_unregistered_reachable_entry_fails_closed(self):
        declarations, policy, entries, closures = _fixture()
        declarations["roles"]["role_a"]["capability_reachable_not_delivered"] = []
        errors = validate(declarations, policy, entries, {}, closures)
        self.assertTrue(any("capability_reachable_not_delivered drift" in row for row in errors))
        self.assertTrue(any("t.menu_narrowed" in row for row in errors))

    def test_stale_declaration_fails_closed(self):
        declarations, policy, entries, closures = _fixture()
        declarations["roles"]["role_a"]["capability_reachable_not_delivered"].append("t.menu_delivered")
        errors = validate(declarations, policy, entries, {}, closures)
        self.assertTrue(any("narrowed/delivered overlap" in row for row in errors))

    def test_delivered_without_capability_must_be_declared(self):
        declarations, policy, entries, closures = _fixture()
        declarations["roles"]["role_b"]["capability_reachable_not_delivered"] = []
        policy["role_b"]["primary_menu_xmlids"] = ["t.menu_delivered"]
        errors = validate(declarations, policy, entries, {}, closures)
        self.assertTrue(any("delivered_without_declared_capability drift" in row for row in errors))

    def test_missing_role_coverage_fails_closed(self):
        declarations, policy, entries, closures = _fixture()
        del declarations["roles"]["role_b"]
        errors = validate(declarations, policy, entries, {}, closures)
        self.assertTrue(any("policy roles missing from declarations" in row for row in errors))

    def test_no_role_set_is_locked(self):
        declarations, policy, entries, closures = _fixture()
        declarations["capability_reachable_by_no_role"] = []
        errors = validate(declarations, policy, entries, {}, closures)
        self.assertTrue(any("capability_reachable_by_no_role drift" in row for row in errors))

    def test_pending_entries_are_declared_not_dropped(self):
        declarations, policy, entries, closures = _fixture()
        errors = validate(declarations, policy, entries, {"t.menu_pending": "label"}, closures)
        self.assertTrue(any("authority_pending_entries drift" in row for row in errors))
        declarations["authority_pending_entries"] = {"t.menu_pending": "label"}
        self.assertEqual(validate(declarations, policy, entries, {"t.menu_pending": "label"}, closures), [])

    def test_delivery_mode_must_match_policy_flags(self):
        declarations, policy, entries, closures = _fixture()
        declarations["roles"]["role_b"]["delivery_mode"] = "capability_discover"
        errors = validate(declarations, policy, entries, {}, closures)
        self.assertTrue(any("discover_installed_capabilities is false" in row for row in errors))
        declarations["roles"]["role_a"]["delivery_mode"] = "denied"
        errors = validate(declarations, policy, entries, {}, closures)
        self.assertTrue(any("deny_all_navigation is false" in row for row in errors))

    def test_unresolvable_identity_group_fails_closed(self):
        declarations, policy, entries, closures = _fixture()
        declarations["roles"]["role_a"]["identity_groups"] = ["t.role_missing"]
        errors = validate(declarations, policy, entries, {}, closures)
        self.assertTrue(any("identity groups unresolvable" in row for row in errors))

    def test_repository_declarations_match_the_acceptance_universe(self):
        declarations = json.loads(Path(DECLARATIONS_PATH).read_text(encoding="utf-8"))
        policy = load_role_policy()
        entries, pending = load_entry_universe()
        graph = load_group_graph()
        closures = {group: group_closure(group, graph) for group in graph}
        self.assertEqual(validate(declarations, policy, entries, pending, closures), [])


class PublishedFaceBalanceTest(unittest.TestCase):
    """The acceptance universe must account for every published leaf.

    The matrix addresses entries through ``action_xmlid``, so a published leaf
    that delivers a scene route instead of an action can never appear there.
    The released population therefore equals the acceptance rows plus the
    declared non-action carriers, and a released leaf that is neither fails
    closed. Leaf identity is decided by the runtime probe, which compares the
    observed non-action leaves with this same declaration.
    """

    @staticmethod
    def _carrier(**overrides):
        row = {
            "scene_key": "workspace.home",
            "route": "/s/workspace.home",
            "reason": "declared scene carrier",
            "evidence": "product contract",
        }
        row.update(overrides)
        return row

    def test_declared_carrier_balances_the_published_face(self):
        universe = {"t.menu_a", "t.menu_b"}
        declarations = {"non_action_delivery_entries": {"t.menu_scene": self._carrier()}}
        self.assertEqual(validate_published_face(declarations, universe, 3), [])

    def test_undeclared_carrier_fails_even_though_the_rows_are_unchanged(self):
        universe = {"t.menu_a", "t.menu_b"}
        errors = validate_published_face({"non_action_delivery_entries": {}}, universe, 3)
        self.assertTrue(any("published face entry count drift" in row for row in errors))

    def test_published_growth_without_a_declaration_fails_closed(self):
        universe = {"t.menu_a", "t.menu_b"}
        declarations = {"non_action_delivery_entries": {"t.menu_scene": self._carrier()}}
        errors = validate_published_face(declarations, universe, 4)
        self.assertTrue(any("published face entry count drift" in row for row in errors))
        self.assertFalse(validate_published_face(declarations, universe | {"t.menu_c"}, 4))

    def test_carrier_must_not_overlap_the_acceptance_universe(self):
        universe = {"t.menu_a", "t.menu_scene"}
        declarations = {"non_action_delivery_entries": {"t.menu_scene": self._carrier()}}
        errors = validate_published_face(declarations, universe, 2)
        self.assertTrue(any("overlaps the acceptance universe" in row for row in errors))

    def test_carrier_requires_scene_route_reason_and_evidence(self):
        universe = {"t.menu_a", "t.menu_b"}
        declarations = {"non_action_delivery_entries": {"t.menu_scene": {"scene_key": "workspace.home"}}}
        errors = validate_published_face(declarations, universe, 3)
        for field in ("route", "reason", "evidence"):
            self.assertTrue(any(f"is missing {field}" in row for row in errors))

    def test_repository_declaration_balances_the_contract(self):
        declarations = json.loads(Path(DECLARATIONS_PATH).read_text(encoding="utf-8"))
        entries, _pending = load_entry_universe()
        universe = {entry["menu"] for entry in entries}
        published = load_published_face_entry_count()
        self.assertEqual(validate_published_face(declarations, universe, published), [])
        self.assertGreater(len(declarations.get("non_action_delivery_entries") or {}), 0)


if __name__ == "__main__":
    unittest.main()
