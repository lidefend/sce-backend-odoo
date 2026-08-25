import importlib.util
import unittest
from pathlib import Path
from unittest.mock import ANY, patch


ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load_module("frontend_accounting_center_rollout", ROOT / "scripts/verify/frontend_accounting_center_rollout.py")


class TestFrontendAccountingCenterRollout(unittest.TestCase):
    def test_uses_exact_formal_accounting_scope(self):
        self.assertEqual(runtime.DOMAIN_KEY, "accounting_center")
        self.assertEqual(runtime.ROOT_MENU_XMLIDS, ("smart_construction_core.menu_sc_accounting_center",))
        self.assertEqual(runtime.OWNER_MODULE, "smart_construction_core")
        self.assertEqual(len(runtime.EXPECTED_ANCHORS), 3)

    def test_collect_delegates_exact_identity(self):
        expected = {"status": "PASS", "gaps": []}
        with patch.object(runtime, "collect_domain", return_value=expected) as collector:
            self.assertIs(runtime.collect(object()), expected)
        collector.assert_called_once_with(
            ANY, domain_key="accounting_center", root_menu_xmlids=runtime.ROOT_MENU_XMLIDS,
            owner_module="smart_construction_core", expected_anchors=runtime.EXPECTED_ANCHORS,
        )

    def test_models_are_not_encoded_as_rollout_special_cases(self):
        source = (ROOT / "scripts/verify/frontend_accounting_center_rollout.py").read_text(encoding="utf-8")
        for model in ("account.journal", "account.analytic.account", "account.analytic.distribution.model"):
            self.assertNotIn(model, source)

    def test_browser_uses_formal_entry_and_security_denial_without_writes(self):
        browser = (ROOT / "scripts/verify/frontend_accounting_center_browser.mjs").read_text(encoding="utf-8")
        resolver = (ROOT / "scripts/verify/local_dev_accounting_center_ids.py").read_text(encoding="utf-8")
        self.assertIn("account.journal", browser)
        self.assertIn("url.pathname === '/access-denied'", browser)
        self.assertIn("mutations.length === 0", browser)
        self.assertIn("smart_construction_demo.sc_demo_user_test_admin", resolver)
        self.assertIn("smart_construction_demo.user_demo_role_finance", resolver)
        self.assertNotIn(".create(", resolver)
        self.assertNotIn(".write(", resolver)


if __name__ == "__main__":
    unittest.main()
