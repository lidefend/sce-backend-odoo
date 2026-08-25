import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = load_module(
    "frontend_systemwide_coverage_audit",
    ROOT / "scripts/verify/frontend_systemwide_coverage_audit.py",
)


class TestFrontendSystemwideCoverageAudit(unittest.TestCase):
    def test_uses_exact_locked_ten_center_authority(self):
        self.assertEqual(len(audit.CENTER_ROOTS), 10)
        self.assertEqual(set(audit.CENTER_ROOTS), {
            "workbench", "project", "contract", "cost", "finance", "tax",
            "accounting", "reporting", "administration", "product_configuration",
        })
        self.assertNotIn("smart_construction_core.menu_sc_config_center", audit.CENTER_ROOTS.values())

    def test_consumes_every_delivered_domain_report(self):
        self.assertEqual(len(audit.DELIVERED_REPORTS), 11)
        self.assertIn("administration-domain-coverage-v1.json", audit.DELIVERED_REPORTS)
        self.assertIn("project-domain-coverage-v1.json", audit.DELIVERED_REPORTS)
        self.assertIn("workbench-center-coverage-v1.json", audit.DELIVERED_REPORTS)

    def test_exact_menu_action_identity_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in audit.DELIVERED_REPORTS:
                (root / name).write_text(json.dumps({
                    "domain": name,
                    "status": "PASS",
                    "summary": {"action_count": 1, "gap_count": 0},
                    "actions": [{"menuXmlid": "module.menu", "actionXmlid": "module.action"}],
                }), encoding="utf-8")
            reports, covered, gaps = audit._load_evidence(root)
        self.assertEqual(len(reports), 11)
        self.assertEqual(covered, {("module.menu", "module.action")})
        self.assertEqual(gaps, [])
        self.assertNotIn(("module.other_menu", "module.action"), covered)

    def test_missing_or_failed_report_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            reports, covered, gaps = audit._load_evidence(Path(directory))
        self.assertEqual(reports, [])
        self.assertEqual(covered, set())
        self.assertEqual(len(gaps), 11)
        self.assertTrue(all(row["reason"] == "DELIVERED_REPORT_MISSING" for row in gaps))

    def test_runtime_requires_formal_menu_and_action_owners(self):
        self.assertEqual(
            audit._formal_identity_status(
                "smart_construction_core.menu", "smart_construction_core.action"
            ),
            "formal",
        )
        self.assertEqual(
            audit._formal_identity_status(
                "smart_construction_demo.menu", "smart_construction_core.action"
            ),
            "foreign",
        )
        self.assertEqual(
            audit._formal_identity_status(
                "customer_overlay.menu", "smart_construction_core.action"
            ),
            "foreign",
        )
        self.assertEqual(
            audit._formal_identity_status(
                "smart_construction_core.menu", "customer_overlay.action"
            ),
            "foreign",
        )
        self.assertEqual(audit._formal_identity_status("", "smart_construction_core.action"), "missing")


if __name__ == "__main__":
    unittest.main()
