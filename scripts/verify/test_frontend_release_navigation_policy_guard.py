from __future__ import annotations

import unittest

from scripts.verify.frontend_release_navigation_policy_guard import ROLE_MAP, validate


def _fixture():
    roles = {}
    policies = {}
    for manifest_role, policy_role in ROLE_MAP.items():
        key = f"x.menu_{policy_role}|x.action_{policy_role}|x.model"
        roles[manifest_role] = {"expected_count": 1, "leaf_keys": [key]}
        policies[policy_role] = {
            "primary_menu_xmlids": [f"x.menu_{policy_role}"],
            "role_home_menu_xmlids": [],
            "contextual_menu_xmlids": [],
            "denied_menu_xmlids": [],
        }
    return {"roles": roles}, policies


class ReleaseNavigationPolicyGuardTest(unittest.TestCase):
    def test_exact_release_projection_passes(self):
        manifest, policies = _fixture()
        self.assertEqual(validate(manifest, policies), [])

    def test_missing_release_leaf_fails_closed(self):
        manifest, policies = _fixture()
        policies["finance"]["primary_menu_xmlids"] = []
        self.assertTrue(any("finance: release projection differs" in row for row in validate(manifest, policies)))

    def test_contextual_or_denied_overlap_fails_closed(self):
        manifest, policies = _fixture()
        policies["owner"]["contextual_menu_xmlids"] = ["x.menu_owner"]
        policies["pm"]["denied_menu_xmlids"] = ["x.menu_pm"]
        errors = validate(manifest, policies)
        self.assertTrue(any("owner: released/contextual overlap" in row for row in errors))
        self.assertTrue(any("pm: released/denied overlap" in row for row in errors))


if __name__ == "__main__":
    unittest.main()
