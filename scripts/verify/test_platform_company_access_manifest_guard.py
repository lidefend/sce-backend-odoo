#!/usr/bin/env python3

import ast
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "verify" / "platform_company_access_manifest_guard.py"
TREE = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
BODY = [
    node
    for node in TREE.body
    if (
        isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id in {
                "CUSTOM_SECURITY_POLICY_GLOB",
                "OPTIONAL_RETIRED_GUARD_SOURCE_PATHS",
                "GENERAL_AUTHENTICATED_NAVIGATION_SURFACES",
            }
            for target in node.targets
        )
    )
    or (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in {
            "_custom_security_policy_paths",
            "_custom_security_policy_errors",
            "_guard_source_text",
        }
    )
]
NAMESPACE = {"Path": Path}
exec(compile(ast.Module(body=BODY, type_ignores=[]), str(MODULE_PATH), "exec"), NAMESPACE)
custom_security_policy_paths = NAMESPACE["_custom_security_policy_paths"]
custom_security_policy_errors = NAMESPACE["_custom_security_policy_errors"]
guard_source_text = NAMESPACE["_guard_source_text"]
general_authenticated_navigation_surfaces = NAMESPACE["GENERAL_AUTHENTICATED_NAVIGATION_SURFACES"]


class PlatformCompanyAccessManifestGuardTest(unittest.TestCase):
    def test_optional_customer_policy_absence_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(custom_security_policy_paths(Path(directory)), [])

    def test_discovers_only_formal_customer_addon_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "customer_addons" / "customer_one" / "models" / "security_policy.py"
            ignored = root / "addons" / "legacy_customer" / "models" / "security_policy.py"
            expected.parent.mkdir(parents=True)
            ignored.parent.mkdir(parents=True)
            expected.write_text("platform_admin_group_xmlids()\n", encoding="utf-8")
            ignored.write_text("legacy\n", encoding="utf-8")
            self.assertEqual(custom_security_policy_paths(root), [expected])

    def test_compliant_customer_policy_is_accepted(self):
        errors = custom_security_policy_errors(
            Path("customer_addons/customer_one/models/security_policy.py"),
            "from odoo.addons.smart_core.security.platform_admin import platform_admin_group_xmlids\n",
        )
        self.assertEqual(errors, [])

    def test_missing_helper_and_legacy_group_are_rejected(self):
        errors = custom_security_policy_errors(
            Path("customer_addons/customer_one/models/security_policy.py"),
            'GROUP = "smart_construction_core.group_sc_cap_config_admin"\n',
        )
        self.assertEqual(len(errors), 2)
        self.assertIn("must consume platform admin group xmlids", errors[0])
        self.assertIn("must not hardcode", errors[1])

    def test_retired_guard_source_may_be_absent_but_is_scanned_if_restored(self):
        rel_path = "addons/smart_construction_core/models/support/history_todo.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNone(guard_source_text(root, rel_path))
            path = root / rel_path
            path.parent.mkdir(parents=True)
            path.write_text("restored source\n", encoding="utf-8")
            self.assertEqual(guard_source_text(root, rel_path), "restored source\n")

    def test_unexpected_missing_guard_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError, "required guard source is missing"):
                guard_source_text(Path(directory), "addons/current/models/security.py")

    def test_platform_menu_api_is_governed_as_general_authenticated_navigation(self):
        self.assertEqual(
            general_authenticated_navigation_surfaces,
            {"addons/smart_core/controllers/platform_menu_api.py"},
        )


if __name__ == "__main__":
    unittest.main()
