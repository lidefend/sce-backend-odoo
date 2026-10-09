#!/usr/bin/env python3
"""Lock the accepted-menu-count mechanism, never a menu number.

The acceptance lanes must derive the accepted navigation action count from the
versioned product contract.  These tests fail closed if a lane re-introduces a
pinned count, if the authority is not a versioned contract in exact mode, or if
the authority cannot be resolved.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from acceptance_action_count import (  # noqa: E402
    ActionCountAuthorityError,
    resolve_action_count,
    resolve_daily_action_count,
    resolve_daily_principal_role,
)

ROOT = Path(__file__).resolve().parents[2]


def _authority(**overrides) -> dict:
    value = {
        "kind": "versioned_contract",
        "path": "contract.json",
        "field": "policy_strategy.effective_menu_count_per_product",
        "mode": "exact",
    }
    value.update(overrides)
    return value


class AcceptanceActionCountTests(unittest.TestCase):
    def _policy(self, authority, **pinned) -> dict:
        navigation = {"action_count_authority": authority, "forbidden_labels": [], "required_paths": []}
        navigation.update(pinned)
        return {"navigation_policy": navigation}

    def test_daily_policy_resolves_from_the_versioned_contract(self):
        self.assertEqual(resolve_daily_action_count(ROOT), 89)
        self.assertGreaterEqual(resolve_daily_action_count(ROOT), 1)

    def test_pinned_count_fails_closed(self):
        for key in ("min_actions", "max_actions", "action_count"):
            with self.subTest(key=key):
                with self.assertRaises(ActionCountAuthorityError):
                    resolve_action_count(self._policy(_authority(), **{key: 89}), ROOT)

    def test_missing_or_wrong_authority_fails_closed(self):
        with self.assertRaises(ActionCountAuthorityError):
            resolve_action_count({"navigation_policy": {}}, ROOT)
        with self.assertRaises(ActionCountAuthorityError):
            resolve_action_count(self._policy(_authority(kind="code_constant")), ROOT)
        with self.assertRaises(ActionCountAuthorityError):
            resolve_action_count(self._policy(_authority(mode="range")), ROOT)

    def test_unresolvable_field_fails_closed(self):
        real = "scripts/verify/baselines/formal_business_product_menu_policy_v1.json"
        with self.assertRaises(ActionCountAuthorityError):
            resolve_action_count(self._policy(_authority(path=real, field="policy_strategy.missing")), ROOT)
        with self.assertRaises(ActionCountAuthorityError):
            resolve_action_count(self._policy(_authority(path="missing-contract.json")), ROOT)

    def test_contract_iteration_changes_the_count_without_editing_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "contract.json").write_text(
                json.dumps({"policy_strategy": {"effective_menu_count_per_product": 123}}),
                encoding="utf-8",
            )
            self.assertEqual(resolve_action_count(self._policy(_authority()), root), 123)


def _locked_role_policy(principal, surfaces) -> dict:
    return {
        "navigation_policy": {
            "action_count_authority": {
                "kind": "versioned_contract",
                "mode": "exact",
                "scope": "locked_role_surface",
                "principal_role": principal,
                "role_surfaces": surfaces,
            }
        }
    }


class LockedRoleSurfaceTests(unittest.TestCase):
    """A menu count is only determinate once a concrete role is locked."""

    def test_daily_principal_role_is_locked_and_resolves(self):
        role = resolve_daily_principal_role(ROOT)
        self.assertTrue(role)
        self.assertEqual(resolve_daily_action_count(ROOT), resolve_action_count(
            json.loads((ROOT / "config/frontend/acceptance_environments_v1.json").read_text(encoding="utf-8"))["profiles"]["daily"],
            ROOT,
            principal_role=role,
        ))

    def test_real_roles_resolve_to_their_locked_surfaces(self):
        daily = json.loads(
            (ROOT / "config/frontend/acceptance_environments_v1.json").read_text(encoding="utf-8")
        )["profiles"]["daily"]
        self.assertEqual(resolve_action_count(daily, ROOT, principal_role="finance"), 45)
        self.assertEqual(resolve_action_count(daily, ROOT, principal_role="pm"), 24)
        self.assertEqual(resolve_action_count(daily, ROOT, principal_role="owner"), 5)
        self.assertEqual(resolve_action_count(daily, ROOT, principal_role="project_member"), 10)
        self.assertGreaterEqual(resolve_action_count(daily, ROOT, principal_role="business_config_admin"), 1)

    def test_roles_with_different_surfaces_disagree(self):
        daily = json.loads(
            (ROOT / "config/frontend/acceptance_environments_v1.json").read_text(encoding="utf-8")
        )["profiles"]["daily"]
        finance = resolve_action_count(daily, ROOT, principal_role="finance")
        pm = resolve_action_count(daily, ROOT, principal_role="pm")
        self.assertNotEqual(finance, pm)

    def test_principal_role_without_surface_fails_closed(self):
        policy = _locked_role_policy(
            "executive",
            {"finance": {"kind": "installed_capability_surface", "path": "contract.json", "field": "policy_strategy.effective_menu_count_per_product"}},
        )
        with self.assertRaises(ActionCountAuthorityError):
            resolve_action_count(policy, ROOT)

    def test_missing_principal_role_fails_closed(self):
        policy = _locked_role_policy("", {"finance": {"kind": "installed_capability_surface", "path": "contract.json", "field": "x"}})
        with self.assertRaises(ActionCountAuthorityError):
            resolve_action_count(policy, ROOT)

    def test_pinned_count_fails_closed_in_locked_scope(self):
        policy = _locked_role_policy(
            "finance",
            {"finance": {"kind": "installed_capability_surface", "path": "contract.json", "field": "policy_strategy.effective_menu_count_per_product"}},
        )
        policy["navigation_policy"]["action_count"] = 45
        with self.assertRaises(ActionCountAuthorityError):
            resolve_action_count(policy, ROOT)

    def test_manifest_count_must_match_locked_identity_list(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "nav.json").write_text(
                json.dumps({"roles": {"finance": {"expected_count": 3, "leaf_keys": ["a|b|c", "d|e|f"]}}}),
                encoding="utf-8",
            )
            surface = {"kind": "locked_role_navigation_manifest", "path": "nav.json", "roles_field": "roles", "count_field": "expected_count", "identity_field": "leaf_keys"}
            with self.assertRaises(ActionCountAuthorityError):
                resolve_action_count(_locked_role_policy("finance", {"finance": surface}), root)

    def test_locked_identity_list_drives_the_count(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            surface = {"kind": "locked_role_navigation_manifest", "path": "nav.json", "roles_field": "roles", "count_field": "expected_count", "identity_field": "leaf_keys"}
            count = 0
            for keys in (["a|a|m", "b|b|m"], ["a|a|m", "b|b|m", "c|c|m", "d|d|m"]):
                count += 1
                (root / "nav.json").write_text(
                    json.dumps({"roles": {"finance": {"expected_count": len(keys), "leaf_keys": keys}}}),
                    encoding="utf-8",
                )
                self.assertEqual(
                    resolve_action_count(_locked_role_policy("finance", {"finance": surface}), root),
                    len(keys),
                )
            self.assertEqual(count, 2)

    def test_manifest_role_alias_resolves(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "nav.json").write_text(
                json.dumps({"roles": {"project_a_member": {"expected_count": 2, "leaf_keys": ["a|a|m", "b|b|m"]}}}),
                encoding="utf-8",
            )
            surface = {"kind": "locked_role_navigation_manifest", "path": "nav.json", "roles_field": "roles", "count_field": "expected_count", "identity_field": "leaf_keys", "manifest_role": "project_a_member"}
            self.assertEqual(
                resolve_action_count(_locked_role_policy("project_member", {"project_member": surface}), root),
                2,
            )


if __name__ == "__main__":
    unittest.main()
